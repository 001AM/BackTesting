from backend.models.schemas import BacktestRequest
from backend.models.database import Company, StockPrice, FundamentalData
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
from decimal import Decimal, ROUND_HALF_UP, getcontext
import pandas as pd
import numpy as np

class BackTestServices:

    def __init__(self, db: Session):
        self.db = db
        self.price_cache = {}
        self.initialize_portfolio()
        getcontext().prec = 8
        
    def initialize_portfolio(self):
        """Initialize or reset the portfolio"""
        self.portfolio = {
            "holdings": {},       # {company_id: {'quantity': qty, 'avg_price': price}}
            "cash_balance": 0,    # Available cash
            "total_value": 0,     # Total portfolio value (cash + investments)
            "transaction_history": []
        }
        self.portfolio_history = []

    def get_company_info(self, company_id: int) -> Company:
        """Get company information from database"""
        return self.db.query(Company).filter(Company.id == company_id).first()

    def get_current_price(self, company_id: int, as_of_date: date) -> float:
        """Get current price for a company on specific date"""
        prices = self.get_stock_prices([company_id], as_of_date, as_of_date)
        if not prices.empty and not pd.isna(prices.iloc[-1][company_id]):
            return float(prices.iloc[-1][company_id])
        return 0.0

    def calculate_current_weights(self) -> Dict[int, float]:
        """Calculate current portfolio weights"""
        if not self.portfolio['holdings']:
            return {}
            
        total_value = self.get_portfolio_value(date.today())
        if total_value <= 0:
            return {}
            
        return {
            cid: (holding['quantity'] * self.get_current_price(cid, date.today())) / total_value
            for cid, holding in self.portfolio['holdings'].items()
        }

    def get_portfolio_value(self, as_of_date: date) -> float:
        """Calculate current portfolio value"""
        cash = Decimal(str(self.portfolio['cash_balance']))
        holdings_value = Decimal('0')
        
        for company_id, holding in self.portfolio['holdings'].items():
            price = Decimal(str(self.get_current_price(company_id, as_of_date)))
            holdings_value += Decimal(str(holding['quantity'])) * price
            
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
            query = query.filter(FundamentalData.market_cap <= backtestfilters.max_market_cap * 10**7)
        
        if backtestfilters.min_roce:
            query = query.filter(FundamentalData.roce >= backtestfilters.min_roce)
        
        if backtestfilters.pat_positive:
            query = query.filter(FundamentalData.pat > 0)
            
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
            
            self.price_cache[cache_key] = df.copy()
            return df
            
        except Exception as e:
            print(f"Error fetching stock prices: {e}")
            return pd.DataFrame()

    def rank_companies(self, companies: List[Tuple[Company, FundamentalData]], 
                     metrics: List[Dict[str, bool]]) -> List[Tuple[Company, float]]:
        """Rank companies based on selected metrics"""
        if not metrics:
            return [(company, 0.0) for company, _ in companies]
        
        metrics_dict = metrics[0]
        ranked = []
        
        for company, fundamental in companies:
            score = 0.0
            for metric, higher_is_better in metrics_dict.items():
                value = float(getattr(fundamental, metric, 0))
                score += value if higher_is_better else -value
            ranked.append((company, score))
        
        return sorted(ranked, key=lambda x: x[1], reverse=True)

    def calculate_weights(self, companies: List[Tuple[Company, FundamentalData, float]], 
                        method: str) -> Dict[int, float]:
        """Calculate portfolio weights based on specified method"""
        if not companies:
            return {}
            
        if method == "equal":
            weight = 1.0 / len(companies)
            return {c[0].id: weight for c in companies}
            
        elif method == "market_cap":
            valid = [c for c in companies if hasattr(c[1], 'market_cap') and c[1].market_cap]
            if not valid:
                return {c[0].id: 0 for c in companies}
            total = sum(float(c[1].market_cap) for c in valid)
            return {c[0].id: float(c[1].market_cap)/total for c in valid}
            
        elif method == "metric_weighted":
            scores = [float(c[2]) for c in companies]
            total = sum(scores)
            return {c[0].id: (float(c[2])/total if total != 0 else 0) for c in companies}
            
        else:
            raise ValueError(f"Unknown weighting method: {method}")

    def execute_rebalance(self, weights: Dict[int, float], current_date: date):
        """Execute portfolio rebalancing with proper value tracking"""
        # Skip if weights haven't changed
        current_weights = self.calculate_current_weights()
        if current_weights and current_weights == weights:
            return
            
        # 1. Sell all existing holdings
        holdings_copy = dict(self.portfolio['holdings'])
        for company_id, holding in holdings_copy.items():
            price = self.get_current_price(company_id, current_date)
            if price > 0:
                self.execute_sell(company_id, holding['quantity'], price, current_date)
        
        # 2. Calculate target allocations
        total_capital = Decimal(str(self.portfolio['cash_balance']))
        target_values = {
            cid: (total_capital * Decimal(str(weight))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            for cid, weight in weights.items()
        }
        
        # 3. Execute buys according to targets
        for company_id, target_value in target_values.items():
            price = Decimal(str(self.get_current_price(company_id, current_date)))
            if price <= 0:
                continue
                
            quantity = int(target_value / price)
            if quantity > 0:
                self.execute_buy(company_id, quantity, float(price), current_date)
        
        # 4. Record portfolio snapshot
        self.record_portfolio_snapshot(current_date)

    def execute_buy(self, company_id: int, quantity: int, price: float, date: date):
        """Execute buy with proper value tracking"""
        cost = Decimal(str(quantity * price)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        cash_balance = Decimal(str(self.portfolio['cash_balance']))
        
        if cost > cash_balance:
            return
        
        # Update cash and holdings
        self.portfolio['cash_balance'] = float(cash_balance - cost)
        
        if company_id in self.portfolio['holdings']:
            holding = self.portfolio['holdings'][company_id]
            new_quantity = holding['quantity'] + quantity
            total_cost = (Decimal(str(holding['quantity'])) * Decimal(str(holding['avg_price']))) + cost
            new_avg_price = (total_cost / Decimal(str(new_quantity))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            
            holding.update({
                'quantity': new_quantity,
                'avg_price': float(new_avg_price)
            })
        else:
            self.portfolio['holdings'][company_id] = {
                'quantity': quantity,
                'avg_price': price
            }
        
        # Record transaction
        company = self.get_company_info(company_id)
        if company:
            current_value = self.get_portfolio_value(date)
            self.portfolio['transaction_history'].append({
                "date": date,
                "symbol": company.symbol,
                "company_id": company_id,
                "company_name": company.name,
                "action": "BUY",
                "quantity": quantity,
                "price": price,
                "total_value": float(cost),
                "portfolio_value": current_value,
                "cash_balance": self.portfolio['cash_balance']
            })

    def execute_sell(self, company_id: int, quantity: int, price: float, date: date):
        """Execute sell with proper value tracking"""
        if company_id not in self.portfolio['holdings']:
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
            current_value = self.get_portfolio_value(date)
            self.portfolio['transaction_history'].append({
                "date": date,
                "symbol": company.symbol,
                "company_id": company_id,
                "company_name": company.name,
                "action": "SELL",
                "quantity": sell_qty,
                "price": price,
                "total_value": float(proceeds),
                "portfolio_value": current_value,
                "cash_balance": self.portfolio['cash_balance']
            })

    def record_portfolio_snapshot(self, date: date):
        """Record complete portfolio state at given date"""
        holdings_detail = {}
        holdings_value = Decimal('0')
        
        for cid, holding in self.portfolio['holdings'].items():
            current_price = Decimal(str(self.get_current_price(cid, date)))
            value = Decimal(str(holding['quantity'])) * current_price
            holdings_value += value
            
            holdings_detail[cid] = {
                'quantity': holding['quantity'],
                'avg_price': holding['avg_price'],
                'current_price': float(current_price),
                'value': float(value)
            }
        
        total_value = Decimal(str(self.portfolio['cash_balance'])) + holdings_value
        self.portfolio_history.append({
            "date": date,
            "holdings": holdings_detail,
            "cash_balance": self.portfolio['cash_balance'],
            "total_value": float(total_value.quantize(Decimal('0.01'), ROUND_HALF_UP))
        })

    def run_backtest(self, request: BacktestRequest) -> Dict[str, Any]:
        """Run complete backtest with proper portfolio tracking and final liquidation"""
        from decimal import Decimal, getcontext
        getcontext().prec = 8
        
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
        
        # Initial purchase
        companies = self.query_for_rebalance(request, request.start_date)
        if companies:
            ranked = self.rank_companies(companies, request.ranking_metrics)
            top_stocks = ranked[:request.portfolio_size]
            weights = self.calculate_weights(top_stocks, request.weighting_method)
            self.execute_rebalance(weights, request.start_date)
        
        # Periodic rebalancing
        for rebalance_date in rebalance_dates:
            if rebalance_date == request.start_date:
                continue
                
            try:
                companies = self.query_for_rebalance(request, rebalance_date)
                if not companies:
                    continue
                    
                ranked = self.rank_companies(companies, request.ranking_metrics)
                top_stocks = ranked[:request.portfolio_size]
                weights = self.calculate_weights(top_stocks, request.weighting_method)
                self.execute_rebalance(weights, rebalance_date)
            except Exception as e:
                print(f"Error during rebalance on {rebalance_date}: {str(e)}")
                continue
        
        # FINAL LIQUIDATION - SELL ALL HOLDINGS ON LAST DAY
        if self.portfolio['holdings']:
            company_ids = list(self.portfolio['holdings'].keys())
            final_prices = self.get_stock_prices(
                company_ids,
                request.end_date - timedelta(days=5),
                request.end_date
            )
            
            if not final_prices.empty:
                for company_id, holding in list(self.portfolio['holdings'].items()):
                    if company_id in final_prices.columns and not pd.isna(final_prices.iloc[-1][company_id]):
                        price = float(final_prices.iloc[-1][company_id])
                        self.execute_sell(
                            company_id=company_id,
                            quantity=holding['quantity'],
                            price=price,
                            date=request.end_date
                        )
        
        # Verify all positions were liquidated
        if len(self.portfolio['holdings']) > 0:
            print(f"Warning: {len(self.portfolio['holdings'])} holdings not liquidated")
        
        # Calculate final metrics
        final_value = self.portfolio['cash_balance']
        initial_capital = float(request.initial_capital)
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        # Calculate annualized return
        days = (request.end_date - request.start_date).days
        years = days / 365.25
        annualized_return = ((final_value / initial_capital) ** (1/years) - 1) * 100
        metrics = BacktestMetricsCalculator.calculate_all_metrics(
            portfolio_history=self.portfolio_history,
            risk_free_rate=0.05,  # Adjust based on current rates
            benchmark_data=request.benchmark_values if hasattr(request, 'benchmark_values') else None
        )
        
        equity_data = BacktestMetricsCalculator.generate_equity_curve(self.portfolio_history)
        drawdown_analysis = BacktestMetricsCalculator.calculate_drawdown_analysis(equity_data)
        
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
                "holdings": {},
                "cash_balance": self.portfolio['cash_balance'],
                "total_value": final_value
            },
            "metrics": {
                "cagr": metrics["cagr"],
                "total_returns": metrics["total_returns"],
                "max_drawdown": metrics["max_drawdown"],
                "volatility": metrics["volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "win_rate": metrics["win_rate"],
                "alpha": metrics["alpha"],
                "beta": metrics["beta"],
                "benchmark_returns": metrics["benchmark_returns"]
            },
            "equity_curve": equity_data,
            "drawdown_analysis": drawdown_analysis
        }
        
        return results
    
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import date, timedelta
from scipy.stats import linregress
from math import sqrt

class BacktestMetricsCalculator:
    
    @staticmethod
    def calculate_all_metrics(portfolio_history: List[Dict], 
                            risk_free_rate: float = 0.05,
                            benchmark_data: Optional[List[float]] = None) -> Dict:
        """
        Calculate comprehensive performance metrics from portfolio history
        Args:
            portfolio_history: List of daily/weekly portfolio snapshots with 'total_value'
            risk_free_rate: Annual risk-free rate for Sharpe ratio
            benchmark_data: Optional list of benchmark values (same frequency as portfolio)
        Returns:
            Dict of calculated metrics matching QuantAnalysis report format
        """
        if not portfolio_history:
            return {}
            
        # Extract portfolio values and dates
        values = [x['total_value'] for x in portfolio_history]
        dates = [x['date'] for x in portfolio_history]
        
        # Convert to pandas Series for easier calculations
        portfolio_series = pd.Series(values, index=pd.to_datetime(dates))
        
        # Calculate basic returns
        returns = portfolio_series.pct_change().dropna()
        cumulative_returns = (portfolio_series.iloc[-1] / portfolio_series.iloc[0]) - 1
        
        # Annualized metrics
        days_in_backtest = (portfolio_series.index[-1] - portfolio_series.index[0]).days
        years = days_in_backtest / 365.25
        
        # 1. CAGR Calculation
        cagr = (portfolio_series.iloc[-1] / portfolio_series.iloc[0]) ** (1/years) - 1
        
        # 2. Max Drawdown Calculation
        rolling_max = portfolio_series.cummax()
        daily_drawdown = portfolio_series / rolling_max - 1
        max_drawdown = daily_drawdown.min()
        
        # 3. Volatility (Annualized)
        volatility = returns.std() * sqrt(252 if len(returns) > 252 else len(returns))
        
        # 4. Sharpe Ratio
        sharpe_ratio = (cagr - risk_free_rate) / volatility if volatility != 0 else 0
        
        # 5. Win Rate (Profitable periods)
        win_rate = (returns > 0).mean()
        
        # 6. Alpha/Beta vs Benchmark (if provided)
        alpha = beta = benchmark_returns = None
        if benchmark_data and len(benchmark_data) == len(portfolio_series):
            benchmark_series = pd.Series(benchmark_data, index=portfolio_series.index)
            benchmark_returns = benchmark_series.pct_change().dropna()
            
            # Ensure aligned dates
            aligned_returns = returns[returns.index.isin(benchmark_returns.index)]
            aligned_bench = benchmark_returns[benchmark_returns.index.isin(returns.index)]
            
            if len(aligned_returns) > 1:
                beta, alpha, _, _, _ = linregress(aligned_bench, aligned_returns)
        
        metrics = {
            "cagr": cagr * 100,
            "total_returns": cumulative_returns * 100,
            "max_drawdown": max_drawdown * 100,
            "volatility": volatility * 100,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate * 100,
            "alpha": alpha * 100 if alpha else None,
            "beta": beta if beta else None,
            "benchmark_returns": benchmark_series.pct_change().sum() * 100 if benchmark_data else None
        }
        
        return metrics

    @staticmethod
    def generate_equity_curve(portfolio_history: List[Dict]) -> Dict:
        """Generate normalized equity curve data for visualization"""
        if not portfolio_history:
            return {}
            
        base_value = portfolio_history[0]['total_value']
        normalized = [
            {
                'date': x['date'],
                'value': (x['total_value'] / base_value) * 100  # As percentage
            }
            for x in portfolio_history
        ]
        
        return {
            'equity_curve': normalized,
            'peak_values': [x['value'] for x in normalized],  # For drawdown calculation
            'dates': [x['date'] for x in normalized]
        }

    @staticmethod
    def calculate_drawdown_analysis(equity_data: Dict) -> Dict:
        """Calculate detailed drawdown statistics"""
        if not equity_data:
            return {}
            
        peak = 0
        drawdowns = []
        current_drawdown = {'start_date': None, 'end_date': None, 'depth': 0}
        
        for point in equity_data['equity_curve']:
            if point['value'] > peak:
                peak = point['value']
                if current_drawdown['depth'] != 0:
                    drawdowns.append(current_drawdown)
                    current_drawdown = {'start_date': None, 'end_date': None, 'depth': 0}
            else:
                dd = (point['value'] - peak) / peak * 100
                if current_drawdown['depth'] == 0:
                    current_drawdown['start_date'] = point['date']
                    current_drawdown['peak_value'] = peak
                current_drawdown['depth'] = min(current_drawdown['depth'], dd)
                current_drawdown['end_date'] = point['date']
        
        if current_drawdown['depth'] != 0:
            drawdowns.append(current_drawdown)
        
        return {
            'max_drawdown': min(x['depth'] for x in drawdowns) if drawdowns else 0,
            'average_drawdown': np.mean([x['depth'] for x in drawdowns]) if drawdowns else 0,
            'drawdown_events': drawdowns
        }