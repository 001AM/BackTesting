from backend.models.schemas import BacktestRequest
from backend.models.database import Company, StockPrice, FundamentalData
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from pydantic import BaseModel, Field
from decimal import Decimal
import pandas as pd
import numpy as np

class BackTestServices:

    def __init__(self, db: Session):
        self.db = db

    def query_for_rebalance(self, backtestfilters: BacktestRequest, rebalance_date: date) -> List[Company]:
        """Query for companies that meet the criteria at a specific rebalance date"""
        query = self.db.query(Company).join(FundamentalData)
        
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
            query = query.filter(FundamentalData.market_cap >= backtestfilters.min_market_cap * 100)  # Convert Cr to actual value
        
        if backtestfilters.max_market_cap:
            query = query.filter(FundamentalData.market_cap <= backtestfilters.max_market_cap * 100)
        
        if backtestfilters.min_roce:
            query = query.filter(FundamentalData.roce >= backtestfilters.min_roce)
        
        if backtestfilters.pat_positive:
            query = query.filter(FundamentalData.pat > 0)
            
        # Apply limit if portfolio size is specified
        if backtestfilters.portfolio_size:
            query = query.limit(backtestfilters.portfolio_size)
            
        return query.all()

    def calculate_weights(self, companies: List[Tuple[Company, float]], method: str) -> Dict[int, float]:
        """Calculate portfolio weights based on specified method"""
        if method == "equal":
            weight = 1.0 / len(companies)
            return {c[0].id: weight for c in companies}
        elif method == "market_cap":
            total_mcap = sum(c[0].fundamental_data[0].market_cap for c in companies)
            return {c[0].id: c[0].fundamental_data[0].market_cap/total_mcap for c in companies}
        elif method == "metric_weighted":
            # Use the ranking score for weighting
            total_score = sum(c[1] for c in companies)
            return {c[0].id: c[1]/total_score for c in companies}
        else:
            raise ValueError(f"Unknown weighting method: {method}")
        
    def run_backtest(self, request: BacktestRequest) -> Dict[str, Any]:
        """Run complete backtest and return results"""
        # Get rebalancing dates
        rebalance_dates = pd.date_range(
            start=request.start_date,
            end=request.end_date,
            freq='QE' if request.rebalancing_frequency == 'quarterly' else 'YE'
        ).date  # Convert to date objects
        print(rebalance_dates)
        
        portfolio_history = []
        transaction_history = []
        
        for rebalance_date in rebalance_dates:
            # Get companies that meet criteria at rebalance date
            companies = self.query_for_rebalance(request, rebalance_date)
            
            if not companies:
                continue  # Skip if no companies meet criteria
                
            # Get stock prices for these companies around the rebalance date
            company_ids = [c.id for c in companies]
            
            # Here you would typically:
            # 1. Calculate portfolio weights (equal-weighted or based on some criteria)
            # 2. Track performance between rebalance dates
            # 3. Record transactions and portfolio value
            
            # For each company, store relevant information
            for company in companies:
                portfolio_history.append({
                    'date': rebalance_date,
                    'company_id': company.id,
                    'company_name': company.name,
                    # Add other relevant fields
                })
                
                transaction_history.append({
                    'date': rebalance_date,
                    'company_id': company.id,
                    'action': 'BUY',  # or 'SELL' for rebalancing
                    # Add other transaction details
                })
            
            # Print first company name for debugging
            print(f"Rebalance date {rebalance_date}: {companies[0].name}")

        # Convert to DataFrames
        stocks_df = pd.DataFrame(portfolio_history)
        transactions_df = pd.DataFrame(transaction_history)
        
        # Here you would typically:
        # 1. Calculate performance metrics
        # 2. Generate summary statistics
        # 3. Prepare the final results
        
        return {
            'portfolio_history': stocks_df.to_dict(orient='records'),
            'transactions': transactions_df.to_dict(orient='records'),
            'performance_metrics': {}  # Add actual metrics
        }