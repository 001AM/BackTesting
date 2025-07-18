from backend.models.schemas import BacktestRequest
from backend.models.database import Company, StockPrice, FundamentalData
from backend.services.back_test_metrics import PerformanceMetrics
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
from decimal import Decimal, ROUND_HALF_UP, getcontext, InvalidOperation, ROUND_DOWN
import pandas as pd
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackTestServices:

    def __init__(self, db: Session):
        self.db = db
        self.price_cache = {}
        self.metrics_calculator = PerformanceMetrics()
        self.initialize_portfolio()
        getcontext().prec = 16
        
    def initialize_portfolio(self):
        """Initialize or reset the portfolio"""
        self.portfolio = {
            "holdings": {},       # {company_id: {'quantity': qty, 'avg_price': price, 'symbol' symbol, 'company_name' : name}}
            "cash_balance": 0,    # Available cash
            "total_value": 0,     # Total portfolio value (cash + investments)
            "transaction_history": []
        }
        self.portfolio_history = []
        self.companies_list= {}

    def get_company_info(self, company_id: int) -> Company:
        if company_id not in self.companies_list:
            """Get company information from database"""
            c = self.db.query(Company).filter(Company.id == company_id).first()
            if c:  # Only cache if we found a company
                self.companies_list[company_id] = c
            return c
        return self.companies_list[company_id]

    def get_current_price(self, company_id: int, as_of_date: date) -> float:
        """Get current price for a company on specific date with fallback logic"""
        # Try exact date first
        prices = self.get_stock_prices([company_id], as_of_date, as_of_date)
        if not prices.empty and company_id in prices.columns and not pd.isna(prices.iloc[-1][company_id]):
            return float(prices.iloc[-1][company_id])
        
        # Fallback: Try previous 30 days
        fallback_start = as_of_date - timedelta(days=30)
        prices = self.get_stock_prices([company_id], fallback_start, as_of_date)
        if not prices.empty and company_id in prices.columns:
            # Get the last available price (iterate backwards)
            for i in range(len(prices) - 1, -1, -1):
                if not pd.isna(prices.iloc[i][company_id]):
                    logger.info(f"Using fallback price for company {company_id} on {as_of_date}: {float(prices.iloc[i][company_id])}")
                    return float(prices.iloc[i][company_id])
        
        # Extended fallback: Try previous 90 days
        extended_fallback_start = as_of_date - timedelta(days=90)
        prices = self.get_stock_prices([company_id], extended_fallback_start, as_of_date)
        if not prices.empty and company_id in prices.columns:
            for i in range(len(prices) - 1, -1, -1):
                if not pd.isna(prices.iloc[i][company_id]):
                    logger.warning(f"Using extended fallback price for company {company_id} on {as_of_date}: {float(prices.iloc[i][company_id])}")
                    return float(prices.iloc[i][company_id])
        
        logger.error(f"No price data found for company {company_id} on or before {as_of_date}")
        return 0.0

    def weights_changed(self, current_weights: Dict[int, float], new_weights: Dict[int, Decimal], tolerance: float = 0.01) -> bool:
        """Check if portfolio weights have changed significantly with type safety"""
        if set(current_weights.keys()) != set(new_weights.keys()):
            return True
        
        for cid in current_weights:
            try:
                current = Decimal(str(current_weights[cid]))
                new = new_weights.get(cid, Decimal('0'))
                if abs(current - new) > Decimal(str(tolerance)):
                    return True
            except (TypeError, ValueError, InvalidOperation) as e:
                logger.error(f"Weight comparison error for {cid}: {e}")
                return True
        return False

    def calculate_current_weights(self) -> Dict[int, Decimal]:
        """Calculate current portfolio weights with Decimal precision"""
        if not self.portfolio['holdings']:
            return {}
            
        total_value = Decimal(str(self.get_portfolio_value(date.today())))
        if total_value <= Decimal('0'):
            return {}
            
        weights = {}
        for cid, holding in self.portfolio['holdings'].items():
            try:
                current_price = Decimal(str(self.get_current_price(cid, date.today())))
                if current_price > Decimal('0'):
                    holding_value = Decimal(str(holding['quantity'])) * current_price
                    weights[cid] = holding_value / total_value
                else:
                    weights[cid] = Decimal('0')
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Error calculating weight for {cid}: {e}")
                weights[cid] = Decimal('0')
                
        return weights

    def get_portfolio_value(self, as_of_date: date) -> float:
        """Calculate current portfolio value"""
        cash = Decimal(str(self.portfolio['cash_balance']))
        holdings_value = Decimal('0')
        
        for company_id, holding in self.portfolio['holdings'].items():
            price = self.get_current_price(company_id, as_of_date)
            if price > 0:
                holdings_value += Decimal(str(holding['quantity'])) * Decimal(str(price))
            else:
                logger.warning(f"Zero price for company {company_id} on {as_of_date}, excluding from portfolio value")
        
        total_value = cash + holdings_value
        return float(total_value.quantize(Decimal('0.01'), ROUND_HALF_UP))

    def query_for_rebalance(self, backtestfilters: BacktestRequest, rebalance_date: date) -> List[Company]:
        """Query for companies that meet the criteria at a specific rebalance date"""
        query = self.db.query(Company, FundamentalData).join(FundamentalData, Company.fundamentals)
        query = query.filter(Company.is_active == True)
        
        # Get latest fundamental data before rebalance date
        latest_data = self.db.query(
            FundamentalData.company_id,
            func.max(FundamentalData.report_date).label('latest_date')
        ).filter(
            FundamentalData.report_date <= rebalance_date
        ).group_by(FundamentalData.company_id).subquery()
        
        query = query.join(
            latest_data,
            and_(
                FundamentalData.company_id == latest_data.c.company_id,
                FundamentalData.report_date == latest_data.c.latest_date
            )
        )
        
        # Apply filters
        if backtestfilters.min_market_cap:
            query = query.filter(FundamentalData.market_cap >= backtestfilters.min_market_cap * 10**7)
        
        if backtestfilters.max_market_cap:
            print(backtestfilters.max_market_cap * 10**7)
            query = query.filter(FundamentalData.market_cap <= backtestfilters.max_market_cap * 10**7)
        
        if backtestfilters.min_roce:
            query = query.filter(FundamentalData.roce >= backtestfilters.min_roce)
        
        if backtestfilters.pat_positive:
            query = query.filter(FundamentalData.pat > backtestfilters.pat_positive)
        
        return query.all()

    def get_stock_prices(self, company_ids: List[int], start_date: date, end_date: date) -> pd.DataFrame:
        """Get stock prices for given companies between dates"""
        if not company_ids:
            return pd.DataFrame()

        cache_key = (tuple(sorted(company_ids)), start_date, end_date)
        
        if cache_key in self.price_cache:
            return self.price_cache[cache_key].copy()
        
        try:
            prices = self.db.query(
                StockPrice.date,
                StockPrice.company_id,
                StockPrice.close,
                StockPrice.adjusted_close
            ).filter(
                StockPrice.company_id.in_(company_ids),
                StockPrice.date.between(start_date, end_date)
            ).order_by(StockPrice.date).all()
            
            if not prices:
                return pd.DataFrame()
                
            price_data = [{
                'date': p.date,
                'company_id': p.company_id,
                'price': p.adjusted_close if p.adjusted_close is not None else p.close
            } for p in prices]
            
            df = pd.DataFrame(price_data)
            df = df.pivot(index='date', columns='company_id', values='price')
            
            # Ensure all requested companies are present
            for cid in company_ids:
                if cid not in df.columns:
                    df[cid] = np.nan
            
            # Forward fill missing values to handle gaps
            df = df.ffill()
            
            self.price_cache[cache_key] = df.copy()
            return df
            
        except Exception as e:
            logger.error(f"Error fetching stock prices: {e}")
            return pd.DataFrame()

    def rank_companies(self, companies: List[Tuple[Company, FundamentalData]], 
                                metrics: List[Dict[str, bool]]) -> List[Tuple[Company, FundamentalData, float]]:
        """Vectorized ranking using numpy operations"""
        if not metrics or not companies:
            return [(c[0], c[1], 0.0) for c in companies]
        
        metrics_dict = metrics[0]
        
        # Convert to numpy arrays for vectorized operations
        scores = np.zeros(len(companies))
        
        for metric, higher_is_better in metrics_dict.items():
            values = []
            for _, fundamental in companies:
                value = getattr(fundamental, metric, None)
                if value is not None:
                    try:
                        values.append(float(value))
                    except (TypeError, ValueError):
                        values.append(0.0)
                else:
                    values.append(0.0)
            
            values_array = np.array(values)
            if higher_is_better:
                scores += values_array
            else:
                scores -= values_array
        
        # Create ranked results
        ranked_indices = np.argsort(scores)[::-1]  # Sort in descending order
        return [(companies[i][0], companies[i][1], scores[i]) for i in ranked_indices]

    def calculate_weights(self, companies: List[Tuple[Company, FundamentalData, float]], 
                        method: str) -> Dict[int, float]:
        """Calculate portfolio weights based on specified method with Decimal safety"""
        if not companies:
            return {}
            
        try:
            if method == "equal":
                weight = Decimal('1') / Decimal(str(len(companies)))
                return {c[0].id: float(weight) for c in companies}
                
            elif method == "market_cap":
                valid = []
                for c in companies:
                    try:
                        if hasattr(c[1], 'market_cap') and c[1].market_cap:
                            market_cap = Decimal(str(c[1].market_cap))
                            if market_cap > Decimal('0'):
                                valid.append((c[0].id, market_cap))
                    except:
                        continue
                        
                if not valid:
                    return {c[0].id: 0 for c in companies}
                    
                total = sum(mc for _, mc in valid)
                return {cid: float(mc/total) for cid, mc in valid}
                
            elif method == "metric_weighted":
                valid = []
                for c in companies:
                    try:
                        if hasattr(c[1], 'roce') and c[1].roce is not None:
                            roce_str = str(c[1].roce).strip().replace('%', '')
                            score = Decimal(roce_str)
                            if score > Decimal('0'):
                                valid.append((c[0].id, score))
                    except:
                        continue
                        
                if not valid:
                    return {c[0].id: 0 for c in companies}
                    
                total = sum(score for _, score in valid)
                return {cid: float(score/total) for cid, score in valid}
                
            else:
                raise ValueError(f"Unknown weighting method: {method}")
        except Exception as e:
            logger.error(f"Error calculating weights: {e}")
            return {c[0].id: 0 for c in companies}

    def validate_prices_before_rebalance(self, company_ids: List[int], rebalance_date: date) -> List[int]:
        """Validate that price data exists for companies before rebalancing"""
        valid_companies = []
        for company_id in company_ids:
            price = self.get_current_price(company_id, rebalance_date)
            if price > 0:
                valid_companies.append(company_id)
            else:
                logger.warning(f"Excluding company {company_id} from rebalance due to missing price data")
        return valid_companies

    def execute_rebalance(self, weights: Dict[int, float], current_date: date):
        """Execute portfolio rebalancing with proper validation and tracking"""
        try:
            # Initialize decimal context for this operation
            getcontext().prec = 16
            getcontext().rounding = ROUND_HALF_UP

            # Validate that we have price data for all companies
            valid_company_ids = []
            for company_id in weights.keys():
                try:
                    price = Decimal(str(self.get_current_price(company_id, current_date)))
                    if price > Decimal('0'):
                        valid_company_ids.append(company_id)
                    else:
                        logger.warning(f"Invalid price for company {company_id} on {current_date}")
                except (ValueError, InvalidOperation) as e:
                    logger.error(f"Price conversion error for company {company_id}: {e}")
                    continue

            if not valid_company_ids:
                logger.warning(f"No valid companies for rebalancing on {current_date}")
                return

            # Filter and normalize weights
            try:
                total_weight = sum(Decimal(str(weights[cid])) for cid in valid_company_ids)
                if total_weight <= Decimal('0'):
                    logger.error(f"Invalid total weight {total_weight} for rebalance")
                    return

                valid_weights = {
                    cid: (Decimal(str(weights[cid])) / total_weight).quantize(Decimal('0.000001'))
                    for cid in valid_company_ids
                }
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Weight calculation error: {e}")
                return

            # Check if weights have changed significantly
            current_weights = self.calculate_current_weights()
            if current_weights and not self.weights_changed(current_weights, valid_weights):
                logger.info(f"Portfolio weights unchanged, skipping rebalance on {current_date}")
                return

            logger.info(f"Executing rebalance on {current_date} with {len(valid_weights)} companies")

            # 1. Sell all existing holdings
            holdings_copy = dict(self.portfolio['holdings'])
            for company_id, holding in holdings_copy.items():
                try:
                    price = Decimal(str(self.get_current_price(company_id, current_date)))
                    if price <= Decimal('0'):
                        logger.error(f"Invalid price for company {company_id}")
                        continue

                    quantity = Decimal(str(holding['quantity']))
                    if quantity <= Decimal('0'):
                        continue

                    self.execute_sell(
                        company_id=company_id,
                        quantity=int(quantity),
                        price=float(price),
                        date=current_date
                    )
                except (ValueError, InvalidOperation) as e:
                    logger.error(f"Sell operation failed for company {company_id}: {e}")
                    continue

            # 2. Calculate target allocations
            try:
                total_capital = Decimal(str(self.portfolio['cash_balance']))
                if total_capital <= Decimal('0'):
                    logger.error("No capital available for rebalance")
                    return

                target_values = {}
                for cid, weight in valid_weights.items():
                    try:
                        target_value = (total_capital * weight).quantize(Decimal('0.01'))
                        target_values[cid] = target_value
                    except (ValueError, InvalidOperation) as e:
                        logger.error(f"Target value calculation failed for {cid}: {e}")
                        continue
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Capital calculation error: {e}")
                return

            # 3. Execute buys according to targets
            for company_id, target_value in target_values.items():
                try:
                    price = Decimal(str(self.get_current_price(company_id, current_date)))
                    if price <= Decimal('0'):
                        logger.warning(f"Invalid price for company {company_id}")
                        continue

                    quantity = (target_value / price).quantize(Decimal('1.'), rounding=ROUND_DOWN)
                    if quantity <= Decimal('0'):
                        continue

                    self.execute_buy(
                        company_id=company_id,
                        quantity=int(quantity),
                        price=float(price),
                        date=current_date
                    )
                except (ValueError, InvalidOperation) as e:
                    logger.error(f"Buy operation failed for company {company_id}: {e}")
                    continue

            # 4. Record portfolio snapshot
            self.record_portfolio_snapshot(current_date)

        except Exception as e:
            logger.error(f"Rebalance failed on {current_date}: {str(e)}", exc_info=True)
            raise

    def execute_buy(self, company_id: int, quantity: int, price: float, date: date):
        """Execute buy with proper validation and tracking"""
        if price <= 0:
            logger.error(f"Cannot execute buy for company {company_id}: invalid price {price}")
            return
            
        cost = Decimal(str(quantity * price)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        cash_balance = Decimal(str(self.portfolio['cash_balance']))
        
        if cost > cash_balance:
            logger.warning(f"Insufficient cash for buy order: need {cost}, have {cash_balance}")
            return
        
        # Update cash and holdings
        self.portfolio['cash_balance'] = float(cash_balance - cost)
        company = self.get_company_info(company_id)
        
        if company_id in self.portfolio['holdings']:
            holding = self.portfolio['holdings'][company_id]
            new_quantity = holding['quantity'] + quantity
            total_cost = (Decimal(str(holding['quantity'])) * Decimal(str(holding['avg_price']))) + cost
            new_avg_price = (total_cost / Decimal(str(new_quantity))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            
            holding.update({
                'symbol' : company.symbol,
                'company_name' : company.name,
                'quantity': new_quantity,
                'avg_price': float(new_avg_price)
            })
        else:
            self.portfolio['holdings'][company_id] = {
                'symbol' : company.symbol,
                'company_name' : company.name,
                'quantity': quantity,
                'avg_price': price
            }
        
        # Record transaction
        if company:
            self.portfolio['transaction_history'].append({
                "date": date,
                "symbol": company.symbol,
                "company_id": company_id,
                "company_name": company.name,
                "action": "BUY",
                "quantity": quantity,
                "price": price,
                "total_value": float(cost),
                "portfolio_value": self.get_portfolio_value(date),
                "cash_balance": self.portfolio['cash_balance']
            })
            logger.info(f"BUY: {quantity} shares of {company.symbol} at {price} on {date}")

    def execute_sell(self, company_id: int, quantity: int, price: float, date: date):
        """Execute sell with proper validation and tracking"""
        if company_id not in self.portfolio['holdings']:
            logger.warning(f"Cannot sell company {company_id}: not in portfolio")
            return
            
        if price <= 0:
            logger.error(f"Cannot execute sell for company {company_id}: invalid price {price}")
            return
            
        holding = self.portfolio['holdings'][company_id]
        sell_qty = min(quantity, holding['quantity'])
        proceeds = Decimal(str(sell_qty * price)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        
        # Update portfolio
        self.portfolio['cash_balance'] = float(
            Decimal(str(self.portfolio['cash_balance'])) + proceeds
        )
        holding['quantity'] -= sell_qty
        
        if holding['quantity'] <= 0:
            del self.portfolio['holdings'][company_id]
        
        # Record transaction
        company = self.get_company_info(company_id)
        if company:
            self.portfolio['transaction_history'].append({
                "date": date,
                "symbol": company.symbol,
                "company_id": company_id,
                "company_name": company.name,
                "action": "SELL",
                "quantity": sell_qty,
                "price": price,
                "total_value": float(proceeds),
                "portfolio_value": self.get_portfolio_value(date),
                "cash_balance": self.portfolio['cash_balance']
            })
            logger.info(f"SELL: {sell_qty} shares of {company.symbol} at {price} on {date}")

    def record_portfolio_snapshot(self, date: date):
        """Record complete portfolio state at given date with safe decimal operations"""
        try:
            getcontext().prec = 16
            getcontext().rounding = ROUND_HALF_UP

            holdings_detail = {}
            holdings_value = Decimal('0')
            
            for cid, holding in self.portfolio['holdings'].items():
                company = self.get_company_info(cid)
                try:
                    current_price = Decimal(str(self.get_current_price(cid, date)))
                    if current_price <= Decimal('0'):
                        logger.warning(f"Invalid price for company {cid} on {date}")
                        current_price = Decimal('0')
                    
                    quantity = Decimal(str(holding['quantity']))
                    value = quantity * current_price
                    holdings_value += value
                    print("Value before quantize:", value, type(value))
                    holdings_detail[cid] = {
                        'symbol': company.symbol,
                        'company_name': company.name,
                        'quantity': int(quantity),
                        'avg_price': float(Decimal(str(holding['avg_price'])).quantize(Decimal('0.01'))),
                        'current_price': float(current_price.quantize(Decimal('0.01'))),
                        'value': float(value.quantize(Decimal('0.01')))
                    }
                except (ValueError, InvalidOperation) as e:
                    logger.error(f"Error recording holding for company {cid}: {e}")
                    holdings_detail[cid] = {
                        'symbol': company.symbol,
                        'company_name': company.name,
                        'quantity': holding['quantity'],
                        'avg_price': holding['avg_price'],
                        'current_price': 0.0,
                        'value': 0.0
                    }
                    continue
            
            try:
                cash_balance = Decimal(str(self.portfolio['cash_balance']))
                total_value = cash_balance + holdings_value
                
                # Ensure total_value is properly quantized
                if not total_value.is_finite():
                    logger.error(f"Invalid total value calculation: {total_value}")
                    total_value = Decimal('0')
                
                snapshot = {
                    "date": date,
                    "holdings": holdings_detail,
                    "cash_balance": float(cash_balance.quantize(Decimal('0.01'))),
                    "total_value": float(total_value.quantize(Decimal('0.01')))
                }
                
                self.portfolio_history.append(snapshot)
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Error recording portfolio snapshot: {e}")
                raise

        except Exception as e:
            logger.error(f"Failed to record portfolio snapshot on {date}: {e}", exc_info=True)
            raise

    def run_backtest(self, request: BacktestRequest) -> Dict[str, Any]:
        """Run complete backtest with proper portfolio tracking and final liquidation"""
        try:
            logger.info(f"Starting backtest from {request.start_date} to {request.end_date}")
            
            getcontext().prec = 16
            
            # Initialize portfolio
            self.initialize_portfolio()
            self.portfolio['cash_balance'] = float(request.initial_capital)
            
            # Generate rebalance dates (quarterly/yearly based on request)
            freq = 'QE' if request.rebalancing_frequency == 'quarterly' else 'YE'
            rebalance_dates = pd.date_range(
                start=request.start_date,
                end=request.end_date,
                freq=freq
            ).date
            
            logger.info(f"Rebalance dates: {[str(d) for d in rebalance_dates]}")
            
            # Initial purchase
            logger.info("Executing initial portfolio construction")
            companies = self.query_for_rebalance(request, request.start_date)
            if companies:
                ranked = self.rank_companies(companies, request.ranking_metrics)
                top_stocks = ranked[:request.portfolio_size]
                weights = self.calculate_weights(top_stocks, request.weighting_method)
                self.execute_rebalance(weights, request.start_date)
            else:
                logger.warning("No companies found for initial portfolio construction")
            
            # Periodic rebalancing
            for rebalance_date in rebalance_dates:
                if rebalance_date <= request.start_date:
                    continue
                    
                try:
                    logger.info(f"Executing rebalance on {rebalance_date}")
                    companies = self.query_for_rebalance(request, rebalance_date)
                    if not companies:
                        logger.warning(f"No companies found for rebalancing on {rebalance_date}")
                        continue
                        
                    ranked = self.rank_companies(companies, request.ranking_metrics)
                    top_stocks = ranked[:request.portfolio_size]
                    weights = self.calculate_weights(top_stocks, request.weighting_method)
                    self.execute_rebalance(weights, rebalance_date)
                except Exception as e:
                    logger.error(f"Error during rebalance on {rebalance_date}: {str(e)}")
                    continue
            
            # FINAL LIQUIDATION - SELL ALL HOLDINGS ON LAST DAY
            logger.info("Executing final liquidation")
            if self.portfolio['holdings']:
                company_ids = list(self.portfolio['holdings'].keys())
                final_prices = self.get_stock_prices(
                    company_ids,
                    request.end_date - timedelta(days=5),
                    request.end_date
                )
                
                liquidation_successful = True
                for company_id, holding in list(self.portfolio['holdings'].items()):
                    price = self.get_current_price(company_id, request.end_date)
                    if price > 0:
                        self.execute_sell(
                            company_id=company_id,
                            quantity=holding['quantity'],
                            price=price,
                            date=request.end_date
                        )
                    else:
                        logger.error(f"Cannot liquidate {holding['quantity']} shares of company {company_id} due to missing price data")
                        liquidation_successful = False
                
                if not liquidation_successful:
                    logger.warning("Some positions could not be liquidated due to missing price data")
            
            # Verify all positions were liquidated
            if len(self.portfolio['holdings']) > 0:
                logger.warning(f"Warning: {len(self.portfolio['holdings'])} holdings not liquidated")
            
            # Calculate final metrics
            final_value = self.portfolio['cash_balance']
            initial_capital = float(request.initial_capital)
            total_return = ((final_value - initial_capital) / initial_capital) * 100
            
            # Calculate annualized return
            days = (request.end_date - request.start_date).days
            years = days / 365.25
            annualized_return = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
            
            # Prepare results
            results = {
                "initial_capital": initial_capital,
                "final_value": round(final_value, 2),
                "total_return_percentage": round(total_return, 2),
                "annualized_return": round(annualized_return, 2),
                "total_profit_loss": round(final_value - initial_capital, 2),
                "total_transactions": len(self.portfolio['transaction_history']),
                "buy_transactions": len([t for t in self.portfolio['transaction_history'] if t['action'] == 'BUY']),
                "sell_transactions": len([t for t in self.portfolio['transaction_history'] if t['action'] == 'SELL']),
                "start_date": str(request.start_date),
                "end_date": str(request.end_date),
                "rebalance_dates": [str(d) for d in rebalance_dates],
                "transaction_history": self.portfolio['transaction_history'],
                "portfolio_history": self.portfolio_history,
                "final_portfolio": {
                    "holdings": dict(self.portfolio['holdings']),
                    "cash_balance": self.portfolio['cash_balance'],
                    "total_value": final_value
                }
            }
            
            logger.info(f"Backtest completed. Final value: {final_value}, Total return: {total_return:.2f}%")
            comprehensive_metrics = self.metrics_calculator.calculate_comprehensive_metrics(results)    
            results.update(comprehensive_metrics)
            print(generate_backtest_report(results))
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            raise e
        

def generate_backtest_report(backtest_results: Dict[str, Any]) -> str:
    """Generate a comprehensive backtest report"""
    report = f"""
    BACKTEST PERFORMANCE REPORT
    ===========================
    
    SUMMARY METRICS:
    - Initial Capital: ${backtest_results.get('initial_capital', 0):,.2f}
    - Final Value: ${backtest_results.get('final_value', 0):,.2f}
    - Total Return: {backtest_results.get('total_return_percentage', 0):.2f}%
    - Annualized Return: {backtest_results.get('annualized_return', 0):.2f}%
    - Total P&L: ${backtest_results.get('total_profit_loss', 0):,.2f}
    
    RISK METRICS:
    - Volatility: {backtest_results.get('volatility', 0):.2f}%
    - Max Drawdown: {backtest_results.get('max_drawdown', 0):.2f}%
    - Max Drawdown Duration: {backtest_results.get('max_drawdown_duration', 0)} days
    - VaR (95%): {backtest_results.get('var_95', 0):.2f}%
    - Skewness: {backtest_results.get('skewness', 0):.3f}
    - Kurtosis: {backtest_results.get('kurtosis', 0):.3f}
    
    RISK-ADJUSTED RATIOS:
    - Sharpe Ratio: {backtest_results.get('sharpe_ratio', 0):.3f}
    - Sortino Ratio: {backtest_results.get('sortino_ratio', 0):.3f}
    - Calmar Ratio: {backtest_results.get('calmar_ratio', 0):.3f}
    
    TRADING METRICS:
    - Total Trades: {backtest_results.get('total_trades', 0)}
    - Win Rate: {backtest_results.get('win_rate', 0):.2f}%
    - Profit Factor: {backtest_results.get('profit_factor', 0):.2f}
    - Profitable Days: {backtest_results.get('profitable_days', 0)}
    - Unprofitable Days: {backtest_results.get('unprofitable_days', 0)}
    - Profitable Days Ratio: {backtest_results.get('profitable_days_ratio', 0):.2f}%
    
    TOP WINNERS:
    """
    
    for i, winner in enumerate(backtest_results.get('top_winners', [])[:5], 1):
        report += f"""
    {i}. {winner['symbol']} - {winner['company_name']}
       Total Return: {winner['total_return']:.2f}%
       Annualized Return: {winner['annualized_return']:.2f}%
       Total P&L: ${winner['total_pnl']:,.2f}
       Holding Period: {winner['holding_period_days']} days
    """
    
    report += "\n    TOP LOSERS:"
    
    for i, loser in enumerate(backtest_results.get('top_losers', [])[:5], 1):
        report += f"""
    {i}. {loser['symbol']} - {loser['company_name']}
       Total Return: {loser['total_return']:.2f}%
       Annualized Return: {loser['annualized_return']:.2f}%
       Total P&L: ${loser['total_pnl']:,.2f}
       Holding Period: {loser['holding_period_days']} days
    """
    
    return report