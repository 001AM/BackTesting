from backend.models.schemas import BacktestRequest
from backend.models.database import Company, StockPrice, FundamentalData
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
from decimal import Decimal
import pandas as pd
import numpy as np

class BackTestServices:

    def __init__(self, db: Session):
        self.db = db
        self.price_cache = {}
        self.portfolio = {
            "stocks":[{}], # {'id' : 'quantity'}
            "cash_balance": 0, 
            "portfolio_balance": 0,
            "total_stocks": 0
        }
        self.transaction = pd.DataFrame(columns=[
            "date",             # Buy/Sell date
            "symbol",           # Ticker symbol
            "company_id",       # Ids
            "company_name",     # Full company name
            "action",           # "BUY" or "SELL"
            "quantity",         # Number of shares bought/sold
            "price",            # Price per share
            "total_value",      # quantity * price
            "portfolio_balance" # Balance after transaction (optional)
        ])
        self.portfolio_history = []

    def query_for_rebalance(self, backtestfilters: BacktestRequest, rebalance_date: date) -> List[Company]:
        """Query for companies that meet the criteria at a specific rebalance date"""
        query = self.db.query(Company, FundamentalData).join(FundamentalData, Company.fundamentals)
        
        # Filter by active companies
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
            query = query.filter(FundamentalData.market_cap >= backtestfilters.min_market_cap * 10**7)  # Convert Cr to actual value
        
        if backtestfilters.max_market_cap:
            query = query.filter(FundamentalData.market_cap <= backtestfilters.max_market_cap * 10**7)
        
        if backtestfilters.min_roce:
            query = query.filter(FundamentalData.roce >= backtestfilters.min_roce)
        
        if backtestfilters.pat_positive:
            query = query.filter(FundamentalData.pat > 0)
            
        from sqlalchemy.dialects import postgresql
        print(str(query.statement.compile(dialect=postgresql.dialect())))

        return query.all()
        
    def get_stock_prices(self, company_ids: List[int], start_date: date, end_date: date) -> pd.DataFrame:
        """Get stock prices for given companies between dates
        
        Args:
            company_ids: List of company IDs to fetch prices for
            start_date: Start date of the period
            end_date: End date of the period
            
        Returns:
            DataFrame with dates as index, company IDs as columns, and prices as values
            Returns empty DataFrame if no data found
        """
        print(company_ids,start_date,end_date)
        if not company_ids:
            return pd.DataFrame()

        # Create cache key (convert to tuple for hashability)
        cache_key = (tuple(sorted(company_ids)), start_date, end_date)
        
        # Check cache first
        if cache_key in self.price_cache:
            return self.price_cache[cache_key].copy()  # Return copy to prevent cache modification
        
        # Query database for prices
        try:
            query = self.db.query(
                StockPrice.date,
                StockPrice.company_id,
                StockPrice.close,
                StockPrice.adjusted_close
            ).filter(
                StockPrice.company_id.in_(company_ids),
                StockPrice.date.between(start_date, end_date)
            ).order_by(
                StockPrice.date,
                StockPrice.company_id
            )
            
            # Print the SQL statement before execution
            from sqlalchemy.dialects import postgresql
            print(str(query.statement.compile(dialect=postgresql.dialect())))
            
            # Execute the query
            prices = query.all()
        except Exception as e:
            print(f"Error fetching stock prices: {e}")
            return pd.DataFrame()
        
        if not prices:
            return pd.DataFrame()
        
        # Create DataFrame with proper structure
        price_data = []
        for price in prices:
            price_data.append({
                'date': price.date,
                'company_id': price.company_id,
                'price': price.adjusted_close if price.adjusted_close is not None else price.close
            })
        
        df = pd.DataFrame(price_data)
        
        # Pivot to get dates as index and companies as columns
        if not df.empty:
            try:
                df = df.pivot(index='date', columns='company_id', values='price')
                # Ensure all requested companies are in the columns (fill with NaN if missing)
                for cid in company_ids:
                    if cid not in df.columns:
                        df[cid] = np.nan
                df = df[sorted(company_ids)]  # Sort columns by company_ids order
            except Exception as e:
                print(f"Error pivoting price data: {e}")
                return pd.DataFrame()
        
        # Cache the result
        self.price_cache[cache_key] = df.copy()
        return df

    def rank_companies(self, companies: List[Tuple[Company, FundamentalData]], 
                    selected_metrics: Optional[List[Dict[str, bool]]] = None) -> List[Tuple[Company, float]]:
        """Rank companies based on selected metrics with proper direction handling
        
        Args:
            companies: List of (Company, FundamentalData) tuples
            selected_metrics: List of dictionaries [{metric_name: direction}] where:
                            - True: Higher values are better (High-to-Low)
                            - False: Lower values are better (Low-to-High)
        Returns:
            List of tuples (Company, composite_score) sorted by score descending
        """
        if not selected_metrics:
            # Return equal ranking if no metrics specified
            return [(company, 0.0) for company, _ in companies]
        
        metrics_dict = selected_metrics[0]  # Assuming single dict in list
        
        ranked_companies = []
        for company, fundamental in companies:
            score = 0.0
            for metric, higher_is_better in metrics_dict.items():
                metric_value = getattr(fundamental, metric, Decimal('0'))
                
                # Convert Decimal to float if needed
                if isinstance(metric_value, Decimal):
                    metric_value = float(metric_value)
                
                # Add to score (positive if higher is better, negative otherwise)
                score += metric_value if higher_is_better else -metric_value
            
            ranked_companies.append((company, score))
        
        # Sort by score descending
        ranked_companies.sort(key=lambda x: x[1], reverse=True)
        
        return ranked_companies

    def calculate_weights(self, companies: List[Tuple[Company, FundamentalData, float]], method: str) -> Dict[int, Decimal]:
        """Decimal-preserving version"""
        if not companies:
            return {}
        
        if method == "equal":
            weight = Decimal(1) / Decimal(len(companies))
            print({c[0].name: weight for c in companies})
            return {c[0].id: weight for c in companies}
        
        elif method == "market_cap":
            valid_companies = [c for c in companies 
                            if hasattr(c[1], 'market_cap') 
                            and c[1].market_cap is not None]
            
            if not valid_companies:
                return {c[0].id: Decimal(0) for c in companies}
                
            total_mcap = sum(Decimal(str(c[1].market_cap)) for c in valid_companies)
            return {c[0].id: Decimal(str(c[1].market_cap))/total_mcap for c in valid_companies}
        
        elif method == "metric_weighted":
            scores = [Decimal(str(c[2])) for c in companies]
            total_score = sum(scores)
            
            if total_score == 0:
                return {c[0].id: Decimal(0) for c in companies}
                
            return {c[0].id: Decimal(str(c[2]))/total_score for c in companies}
        
        else:
            raise ValueError(f"Unknown weighting method: {method}")

    def first_date_purchase(self,backtestfilters:BacktestRequest):
        try:
            self.portfolio["cash_balance"] = backtestfilters.initial_capital
            weights , stocks = self.top_rebalance_stocks(backtestfilters)
            self.update_portfolio(stocks,weights,backtestfilters.start_date)
        except Exception as e:
            print(str(e))

    def top_rebalance_stocks(self,backtestfilters:BacktestRequest):
        companies = self.query_for_rebalance(backtestfilters,backtestfilters.start_date)
        if companies:
            companies = self.rank_companies(companies,backtestfilters.ranking_metrics)
        top_stocks = companies[:backtestfilters.portfolio_size]
        weights = self.calculate_weights(top_stocks,backtestfilters.weighting_method)
        company_ids = [key for key, value in weights.items()]
        return weights , self.get_stock_prices(company_ids,backtestfilters.start_date - timedelta(days=5),backtestfilters.start_date)
        

    def update_portfolio(self, stocks, weights, current_date):
        # Get the last row (most recent prices) for each stock
        new_stock_last_prices = stocks.iloc[-1]
        
        # Calculate current portfolio value before rebalancing
        current_portfolio_value = self.portfolio["cash_balance"]
        if self.portfolio["stocks"][0]:
            # Get prices for current holdings
            company_ids = list(self.portfolio["stocks"][0].keys())
            current_prices_df = self.get_stock_prices(company_ids, current_date - timedelta(days=5), current_date)
            current_prices = current_prices_df.iloc[-1] if not current_prices_df.empty else {}
            
            # Calculate value of current holdings
            for company_id, quantity in self.portfolio["stocks"][0].items():
                if company_id in current_prices:
                    current_portfolio_value += quantity * float(current_prices[company_id])
        
        # Sell all existing stocks if we have any
        if self.portfolio["stocks"][0]:
            company_ids = list(self.portfolio["stocks"][0].keys())
            sell_prices_df = self.get_stock_prices(company_ids, current_date - timedelta(days=5), current_date)
            sell_prices = sell_prices_df.iloc[-1] if not sell_prices_df.empty else {}
            
            total_sell_value = 0
            for company_id, quantity in self.portfolio["stocks"][0].items():
                if company_id in sell_prices:
                    sell_price = float(sell_prices[company_id])
                    sell_value = quantity * sell_price
                    total_sell_value += sell_value
                    
                    # Record sell transaction
                    sell_transaction = {
                        "date": current_date,
                        "symbol": "",
                        "company_id": company_id,
                        "company_name": "",
                        "action": "SELL",
                        "quantity": quantity,
                        "price": sell_price,
                        "total_value": sell_value,
                        "portfolio_balance": self.portfolio["cash_balance"] + total_sell_value
                    }
                    self.transaction = pd.concat([self.transaction, pd.DataFrame([sell_transaction])], ignore_index=True)
            
            # Update cash balance after selling
            self.portfolio["cash_balance"] += total_sell_value
            self.portfolio["stocks"] = [{}]
        
        # Calculate total available capital for new purchases
        total_capital = self.portfolio["cash_balance"]
        
        # Purchase new stocks according to weights
        total_stocks_value = 0
        remaining_cash = total_capital
        
        # First pass: allocate according to weights
        for company_id, weight in weights.items():
            if company_id in new_stock_last_prices and not pd.isna(new_stock_last_prices[company_id]):
                stock_price = float(new_stock_last_prices[company_id])
                allocation = total_capital * float(weight)
                quantity = int(allocation // stock_price)
                
                if quantity > 0:
                    purchase_value = quantity * stock_price
                    if purchase_value <= remaining_cash:
                        self.portfolio["stocks"][0][company_id] = quantity
                        total_stocks_value += purchase_value
                        remaining_cash -= purchase_value
                        
                        # Record transaction
                        new_transaction = {
                            "date": current_date,
                            "symbol": "",
                            "company_id": company_id,
                            "company_name": "",
                            "action": "BUY",
                            "quantity": quantity,
                            "price": stock_price,
                            "total_value": purchase_value,
                            "portfolio_balance": remaining_cash
                        }
                        self.transaction = pd.concat([self.transaction, pd.DataFrame([new_transaction])], ignore_index=True)
        
        # Second pass: use remaining cash to buy more shares of the cheapest stock
        if remaining_cash > 0 and self.portfolio["stocks"][0]:
            cheapest_stock = None
            cheapest_price = float('inf')
            
            for company_id in weights.keys():
                if company_id in new_stock_last_prices and not pd.isna(new_stock_last_prices[company_id]):
                    stock_price = float(new_stock_last_prices[company_id])
                    if stock_price < cheapest_price:
                        cheapest_price = stock_price
                        cheapest_stock = company_id
            
            if cheapest_stock and cheapest_price <= remaining_cash:
                additional_quantity = int(remaining_cash // cheapest_price)
                if additional_quantity > 0:
                    additional_value = additional_quantity * cheapest_price
                    if additional_value <= remaining_cash:
                        if cheapest_stock in self.portfolio["stocks"][0]:
                            self.portfolio["stocks"][0][cheapest_stock] += additional_quantity
                        else:
                            self.portfolio["stocks"][0][cheapest_stock] = additional_quantity
                        
                        remaining_cash -= additional_value
                        total_stocks_value += additional_value
                        
                        # Record additional purchase
                        additional_transaction = {
                            "date": current_date,
                            "symbol": "",
                            "company_id": cheapest_stock,
                            "company_name": "",
                            "action": "BUY",
                            "quantity": additional_quantity,
                            "price": cheapest_price,
                            "total_value": additional_value,
                            "portfolio_balance": remaining_cash
                        }
                        self.transaction = pd.concat([self.transaction, pd.DataFrame([additional_transaction])], ignore_index=True)
        
        # Update portfolio balances
        self.portfolio["cash_balance"] = remaining_cash
        self.portfolio["portfolio_balance"] = total_stocks_value + remaining_cash
        self.portfolio["total_stocks"] = len(self.portfolio["stocks"][0])
        
        # Update portfolio history
        self.portfolio_history.append({
            "stocks": [dict(self.portfolio["stocks"][0])],  # Make a copy
            "cash_balance": self.portfolio["cash_balance"],
            "portfolio_balance": self.portfolio["portfolio_balance"],
            "total_stocks": self.portfolio["total_stocks"],
            "date": current_date
        })

    def run_backtest(self, request: BacktestRequest) -> Dict[str, Any]:
        """Run complete backtest with proper portfolio tracking and transactions"""
        from decimal import Decimal, getcontext
        from datetime import timedelta
        getcontext().prec = 8  # Set precision for Decimal operations
        
        # Initialize portfolio with initial capital
        self.portfolio = {
            "stocks": [{}],  # {'company_id': quantity}
            "cash_balance": float(request.initial_capital),
            "portfolio_balance": float(request.initial_capital),
            "total_stocks": 0
        }
        
        # Clear previous data
        self.transaction = pd.DataFrame(columns=[
            "date", "symbol", "company_id", "company_name", 
            "action", "quantity", "price", "total_value", 
            "portfolio_balance"
        ])
        self.portfolio_history = []
        
        # Generate rebalance dates
        rebalance_dates = pd.date_range(
            start=request.start_date,
            end=request.end_date,
            freq='QE' if request.rebalancing_frequency == 'quarterly' else 'YE'
        ).date
        
        # Initial purchase
        self.first_date_purchase(request)
        
        # Run backtest for each rebalance date
        for rebalance_date in rebalance_dates:
            if rebalance_date == request.start_date:
                continue  # Skip initial purchase date
                
            try:
                weights, stocks = self.top_rebalance_stocks(request)
                if not stocks.empty:
                    self.update_portfolio(stocks, weights, rebalance_date)
            except Exception as e:
                print(f"Error during rebalance on {rebalance_date}: {str(e)}")
                continue
        
        # Final liquidation on end date
        final_date = request.end_date
        if self.portfolio["stocks"][0]:
            company_ids = list(self.portfolio["stocks"][0].keys())
            final_prices_df = self.get_stock_prices(
                company_ids, 
                final_date - timedelta(days=5), 
                final_date
            )
            final_prices = final_prices_df.iloc[-1] if not final_prices_df.empty else {}
            
            total_sell_value = 0
            for company_id, quantity in self.portfolio["stocks"][0].items():
                if company_id in final_prices:
                    sell_price = float(final_prices[company_id])
                    sell_value = quantity * sell_price
                    total_sell_value += sell_value
                    
                    # Record final sell transaction
                    sell_transaction = {
                        "date": final_date,
                        "symbol": "",
                        "company_id": company_id,
                        "company_name": "",
                        "action": "SELL",
                        "quantity": quantity,
                        "price": sell_price,
                        "total_value": sell_value,
                        "portfolio_balance": self.portfolio["cash_balance"] + total_sell_value
                    }
                    self.transaction = pd.concat(
                        [self.transaction, pd.DataFrame([sell_transaction])], 
                        ignore_index=True
                    )
            
            # Update final cash balance
            self.portfolio["cash_balance"] += total_sell_value
            self.portfolio["stocks"] = [{}]
        
        # Calculate final portfolio value
        final_value = self.portfolio["cash_balance"]
        
        # Calculate performance metrics
        initial_capital = float(request.initial_capital)
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        # Prepare portfolio history with dates
        dated_portfolio_history = []
        for i, entry in enumerate(self.portfolio_history):
            dated_entry = entry.copy()
            dated_entry["date"] = rebalance_dates[i] if i < len(rebalance_dates) else final_date
            dated_portfolio_history.append(dated_entry)
        
        # Calculate annualized return
        days_in_backtest = (request.end_date - request.start_date).days
        years_in_backtest = days_in_backtest / 365.25
        annualized_return = ((1 + (total_return/100))**(1/years_in_backtest)) - 1
        
        results = {
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return_percentage": round(total_return, 2),
            "annualized_return": round(annualized_return * 100, 2),
            "total_profit_loss": round(final_value - initial_capital, 2),
            "total_transactions": len(self.transaction),
            "buy_transactions": len(self.transaction[self.transaction['action'] == 'BUY']),
            "sell_transactions": len(self.transaction[self.transaction['action'] == 'SELL']),
            "start_date": str(request.start_date),
            "end_date": str(request.end_date),
            "rebalance_dates": [str(date) for date in rebalance_dates],
            "portfolio_history": dated_portfolio_history,
            "transaction_history": self.transaction.to_dict('records'),
            "final_portfolio": self.portfolio,
            "metrics": {
                "sharpe_ratio": None,  # Can be calculated if you have benchmark data
                "max_drawdown": None,   # Can be calculated from portfolio_history
                "volatility": None      # Can be calculated from portfolio_history
            }
        }
        
        # Print summary
        print(f"\nBacktest Results ({request.start_date} to {request.end_date})")
        print(f"Initial Capital: ${initial_capital:,.2f}")
        print(f"Final Value: ${final_value:,.2f}")
        print(f"Total Return: {total_return:.2f}%")
        print(f"Annualized Return: {annualized_return*100:.2f}%")
        print(f"Total Transactions: {len(self.transaction)}")
        print(f"Buy Transactions: {len(self.transaction[self.transaction['action'] == 'BUY'])}")
        print(f"Sell Transactions: {len(self.transaction[self.transaction['action'] == 'SELL'])}")
        print(self.transaction)
        
        return results
