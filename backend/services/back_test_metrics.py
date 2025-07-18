from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import partial

logger = logging.getLogger(__name__)

class MetricType(Enum):
    RETURN = "return"
    RISK = "risk"
    RATIO = "ratio"
    DRAWDOWN = "drawdown"

@dataclass
class SecurityPerformance:
    """Data class for individual security performance"""
    symbol: str
    company_name: str
    company_id: int
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    holding_period_days: int
    total_pnl: float

class PerformanceMetrics:
    """Comprehensive performance metrics calculator with threading optimization"""
    
    def __init__(self, max_workers: int = 4):
        self.risk_free_rate = 0.06  # 6% annual risk-free rate
        self.max_workers = max_workers
        self._thread_local = threading.local()
        
    def _convert_to_serializable(self, value: Any) -> Any:
        """Convert numpy/pandas types to native Python types for serialization"""
        if isinstance(value, (np.integer, np.int64)):
            return int(value)
        elif isinstance(value, (np.floating, np.float64)):
            return float(value)
        elif isinstance(value, (np.ndarray, pd.Series)):
            return value.tolist()
        elif isinstance(value, pd.Timestamp):
            return value.isoformat()
        elif isinstance(value, (pd.DataFrame, pd.Index)):
            return value.to_dict()
        elif isinstance(value, Decimal):
            return float(value)
        return value
        
    def _clean_metrics_dict(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all values in metrics dictionary are serializable"""
        return {k: self._convert_to_serializable(v) for k, v in metrics.items()}
    
    def calculate_returns_series(self, portfolio_history: List[Dict]) -> pd.Series:
        """Calculate daily returns from portfolio history"""
        if len(portfolio_history) < 2:
            return pd.Series(dtype=float)
            
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df['daily_return'] = df['total_value'].pct_change()
        
        return df.set_index('date')['daily_return'].dropna()
    
    def calculate_equity_curve(self, portfolio_history: List[Dict]) -> pd.DataFrame:
        """Calculate equity curve data"""
        import yfinance as yf
        import pandas as pd
            # Process portfolio data
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Get initial portfolio value
        initial_value = df['total_value'].iloc[0]

        # Fetch and flatten Nifty 50 data
        start_date = df['date'].iloc[0].strftime('%Y-%m-%d')
        end_date = df['date'].iloc[-1].strftime('%Y-%m-%d')
        nifty_data = yf.download('^NSEI', start=start_date, end=end_date)
        nifty_data.columns = ['_'.join(col).strip() for col in nifty_data.columns.values]  # Fix: Flatten MultiIndex
        nifty_data = nifty_data.reset_index()  # Convert Date index to a column

        # Merge with portfolio data
        df = pd.merge(
            df,
            nifty_data[['Date', 'Close_^NSEI']],
            left_on='date',
            right_on='Date',
            how='left'
        )
        df.rename(columns={'Close_^NSEI': 'nifty_close'}, inplace=True)

        # Forward-fill missing Nifty data (e.g., weekends)
        df['nifty_close'] = df['nifty_close'].ffill()

        # Calculate Nifty investment value (buy-and-hold)
        nifty_day1_close = df['nifty_close'].iloc[0]
        nifty_units = initial_value / nifty_day1_close
        df['nifty_investment_value'] = nifty_units * df['nifty_close']

        return df[['date', 'total_value', 'nifty_investment_value', 'nifty_close']]
    
    def calculate_drawdown_series(self, portfolio_history: List[Dict]) -> pd.DataFrame:
        """Calculate drawdown series"""
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate running maximum (peak)
        df['peak'] = df['total_value'].expanding().max()
        df['drawdown'] = (df['total_value'] - df['peak']) / df['peak'] * 100
        df['drawdown_duration'] = 0
        
        # Calculate drawdown duration
        in_drawdown = False
        start_idx = 0
        
        for i in range(len(df)):
            if df.iloc[i]['drawdown'] < 0:
                if not in_drawdown:
                    in_drawdown = True
                    start_idx = i
                df.iloc[i, df.columns.get_loc('drawdown_duration')] = i - start_idx
            else:
                in_drawdown = False
                df.iloc[i, df.columns.get_loc('drawdown_duration')] = 0
        
        return df[['date', 'total_value', 'peak', 'drawdown', 'drawdown_duration']]
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = None) -> float:
        """Calculate Sharpe ratio"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
            
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
            
        excess_returns = float(returns.mean() * 252 - risk_free_rate)  # Annualized
        volatility = float(returns.std() * np.sqrt(252))  # Annualized
        
        return excess_returns / volatility if volatility != 0 else 0.0
    
    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = None) -> float:
        """Calculate Sortino ratio"""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
            
        if len(returns) == 0:
            return 0.0
            
        excess_returns = float(returns.mean() * 252 - risk_free_rate)
        downside_returns = returns[returns < 0]
        downside_deviation = float(downside_returns.std() * np.sqrt(252))
        
        return excess_returns / downside_deviation if downside_deviation != 0 else 0.0
    
    def calculate_calmar_ratio(self, returns: pd.Series, max_drawdown: float) -> float:
        """Calculate Calmar ratio"""
        if max_drawdown == 0:
            return 0.0
            
        annual_return = float(returns.mean() * 252)
        return annual_return / abs(max_drawdown)
    
    def calculate_max_drawdown(self, portfolio_history: List[Dict]) -> Dict[str, Any]:
        """Calculate maximum drawdown and related metrics"""
        drawdown_df = self.calculate_drawdown_series(portfolio_history)
        
        if drawdown_df.empty:
            return {
                "max_drawdown": 0.0,
                "max_drawdown_duration": 0,
                "max_drawdown_start": None,
                "max_drawdown_end": None,
                "recovery_date": None
            }
        
        max_dd_idx = drawdown_df['drawdown'].idxmin()
        max_drawdown = float(drawdown_df.loc[max_dd_idx, 'drawdown'])
        max_drawdown_date = drawdown_df.loc[max_dd_idx, 'date']
        
        # Find start of drawdown period
        dd_start_idx = max_dd_idx
        for i in range(max_dd_idx, -1, -1):
            if drawdown_df.iloc[i]['drawdown'] >= -0.01:  # Within 1% of peak
                dd_start_idx = i
                break
        
        # Find recovery date
        recovery_idx = None
        for i in range(max_dd_idx, len(drawdown_df)):
            if drawdown_df.iloc[i]['drawdown'] >= -0.01:
                recovery_idx = i
                break
        
        max_duration = int(drawdown_df['drawdown_duration'].max())
        
        return {
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_duration,
            "max_drawdown_start": drawdown_df.iloc[dd_start_idx]['date'] if dd_start_idx is not None else None,
            "max_drawdown_end": max_drawdown_date,
            "recovery_date": drawdown_df.iloc[recovery_idx]['date'] if recovery_idx is not None else None
        }
    
    def calculate_win_rate(self, transaction_history: List[Dict]) -> float:
        """Calculate win rate from transactions"""
        if not transaction_history:
            return 0.0
            
        # Group transactions by symbol to calculate P&L per trade
        trades = {}
        for tx in transaction_history:
            symbol = tx['symbol']
            if symbol not in trades:
                trades[symbol] = []
            trades[symbol].append(tx)
        
        winning_trades = 0
        total_trades = 0
        
        for symbol, txs in trades.items():
            buys = [tx for tx in txs if tx['action'] == 'BUY']
            sells = [tx for tx in txs if tx['action'] == 'SELL']
            
            for sell in sells:
                # Find matching buy (FIFO)
                for buy in buys:
                    if buy.get('used_quantity', 0) < buy['quantity']:
                        trade_qty = min(sell['quantity'], buy['quantity'] - buy.get('used_quantity', 0))
                        pnl = (sell['price'] - buy['price']) * trade_qty
                        
                        if pnl > 0:
                            winning_trades += 1
                        total_trades += 1
                        
                        buy['used_quantity'] = buy.get('used_quantity', 0) + trade_qty
                        sell['quantity'] -= trade_qty
                        
                        if sell['quantity'] <= 0:
                            break
        
        return float(winning_trades / total_trades) if total_trades > 0 else 0.0
    
    def calculate_profit_factor(self, transaction_history: List[Dict]) -> float:
        """Calculate profit factor"""
        if not transaction_history:
            return 0.0
            
        gross_profit = 0.0
        gross_loss = 0.0
        
        # Group by symbol for P&L calculation
        trades = {}
        for tx in transaction_history:
            symbol = tx['symbol']
            if symbol not in trades:
                trades[symbol] = []
            trades[symbol].append(tx)
        
        for symbol, txs in trades.items():
            buys = [tx for tx in txs if tx['action'] == 'BUY']
            sells = [tx for tx in txs if tx['action'] == 'SELL']
            
            for sell in sells:
                for buy in buys:
                    if buy.get('used_quantity', 0) < buy['quantity']:
                        trade_qty = min(sell['quantity'], buy['quantity'] - buy.get('used_quantity', 0))
                        pnl = (sell['price'] - buy['price']) * trade_qty
                        
                        if pnl > 0:
                            gross_profit += pnl
                        else:
                            gross_loss += abs(pnl)
                        
                        buy['used_quantity'] = buy.get('used_quantity', 0) + trade_qty
                        sell['quantity'] -= trade_qty
                        
                        if sell['quantity'] <= 0:
                            break
        
        return float(gross_profit / gross_loss) if gross_loss > 0 else 0.0
    
    def calculate_volatility(self, returns: pd.Series) -> float:
        """Calculate annualized volatility"""
        if len(returns) == 0:
            return 0.0
        return float(returns.std() * np.sqrt(252))
    
    def calculate_var(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Value at Risk"""
        if len(returns) == 0:
            return 0.0
        return float(np.percentile(returns, confidence_level * 100))
    
    def calculate_skewness(self, returns: pd.Series) -> float:
        """Calculate skewness"""
        if len(returns) == 0:
            return 0.0
        return float(returns.skew())
    
    def calculate_kurtosis(self, returns: pd.Series) -> float:
        """Calculate kurtosis"""
        if len(returns) == 0:
            return 0.0
        return float(returns.kurtosis())
    
    def _calculate_security_performance(self, security_data: Tuple[Tuple[str, str, int], List[Dict]]) -> Optional[SecurityPerformance]:
        """Calculate performance for a single security (thread-safe)"""
        (symbol, company_name, company_id), txs = security_data
        
        # Sort all transactions by date
        txs_sorted = sorted(txs, key=lambda x: x['date'])
        
        # Track inventory using FIFO method
        inventory = []
        total_pnl = 0.0
        total_trades = 0
        winning_trades = 0
        buy_value = 0.0
        sell_value = 0.0
        
        for tx in txs_sorted:
            if tx['action'] == 'BUY':
                # Add to inventory
                quantity = tx.get('quantity', 1)
                if quantity == 0:  # Handle possible 0 quantity buys
                    quantity = int(tx['total_value'] / tx['price'])
                inventory.append({
                    'date': tx['date'],
                    'price': tx['price'],
                    'quantity': quantity
                })
            elif tx['action'] == 'SELL':
                # Calculate sell quantity - use quantity if available, otherwise calculate from total_value
                sell_qty = tx.get('quantity', 0)
                if sell_qty == 0:
                    sell_qty = int(tx['total_value'] / tx['price'])
                sell_price = tx['price']
                
                while sell_qty > 0 and inventory:
                    oldest_buy = inventory[0]
                    trade_qty = min(sell_qty, oldest_buy['quantity'])
                    
                    # Calculate P&L for this portion
                    pnl = (sell_price - oldest_buy['price']) * trade_qty
                    total_pnl += pnl
                    total_trades += 1
                    if pnl > 0:
                        winning_trades += 1
                    
                    buy_value += oldest_buy['price'] * trade_qty
                    sell_value += sell_price * trade_qty
                    
                    # Update quantities
                    oldest_buy['quantity'] -= trade_qty
                    sell_qty -= trade_qty
                    
                    if oldest_buy['quantity'] <= 0:
                        inventory.pop(0)
        
        if buy_value == 0:
            return None
            
        total_return = float((sell_value - buy_value) / buy_value * 100)
        
        # Calculate holding period (using first buy and last sell)
        buys = [tx for tx in txs if tx['action'] == 'BUY']
        sells = [tx for tx in txs if tx['action'] == 'SELL']
        
        if not buys:
            return None
            
        first_buy = min(buys, key=lambda x: x['date'])
        last_sell = max(sells, key=lambda x: x['date']) if sells else max(buys, key=lambda x: x['date'])
        holding_days = (last_sell['date'] - first_buy['date']).days
        
        # Annualized return
        years = holding_days / 365.25 if holding_days > 0 else 1
        annualized_return = float(((1 + total_return/100) ** (1/years) - 1) * 100)
        
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0
        
        return SecurityPerformance(
            symbol=symbol,
            company_name=company_name,
            company_id=company_id,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=win_rate,
            profit_factor=0.0,
            total_trades=int(total_trades),
            holding_period_days=int(holding_days),
            total_pnl=float(total_pnl)
        )
    
    def get_top_winners_losers(self, transaction_history: List[Dict], top_n: int = 10) -> Dict[str, List[SecurityPerformance]]:
        """Get top winning and losing securities using threading"""
        if not transaction_history:
            return {"winners": [], "losers": []}
        
        # Group transactions by security
        securities = {}
        for tx in transaction_history:
            key = (tx['symbol'], tx['company_name'], tx['company_id'])
            if key not in securities:
                securities[key] = []
            securities[key].append(tx)
        
        # Use threading to process securities in parallel
        performances = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_security = {
                executor.submit(self._calculate_security_performance, (key, txs)): key 
                for key, txs in securities.items()
            }
            
            for future in as_completed(future_to_security):
                performance = future.result()
                if performance is not None:
                    performances.append(performance)
        
        # Sort by total return
        performances.sort(key=lambda x: x.total_return, reverse=True)
        
        return {
            "winners": performances[:top_n],
            "losers": performances[-top_n:][::-1] if len(performances) >= top_n else []
        }

    def _calculate_basic_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate basic metrics in a thread-safe manner"""
        return {
            "volatility": self.calculate_volatility(returns),
            "var_95": self.calculate_var(returns, 0.05),
            "skewness": self.calculate_skewness(returns),
            "kurtosis": self.calculate_kurtosis(returns)
        }
    
    def _calculate_ratio_metrics(self, returns: pd.Series, max_drawdown: float) -> Dict[str, float]:
        """Calculate ratio metrics in a thread-safe manner"""
        return {
            "sharpe_ratio": self.calculate_sharpe_ratio(returns),
            "sortino_ratio": self.calculate_sortino_ratio(returns),
            "calmar_ratio": self.calculate_calmar_ratio(returns, max_drawdown)
        }
    
    def _calculate_trading_metrics(self, transaction_history: List[Dict]) -> Dict[str, float]:
        """Calculate trading metrics in a thread-safe manner"""
        return {
            "win_rate": self.calculate_win_rate(transaction_history),
            "profit_factor": self.calculate_profit_factor(transaction_history)
        }

    def calculate_comprehensive_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all comprehensive metrics with threading optimization"""
        portfolio_history = backtest_results.get('portfolio_history', [])
        transaction_history = backtest_results.get('transaction_history', [])
        
        if not portfolio_history:
            return {}
        
        # Calculate returns series (needed for multiple calculations)
        returns = self.calculate_returns_series(portfolio_history)
        
        # Use ThreadPoolExecutor for parallel calculation of independent metrics
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all independent calculations
            futures = {
                'equity_curve': executor.submit(self.calculate_equity_curve, portfolio_history),
                'drawdown_data': executor.submit(self.calculate_max_drawdown, portfolio_history),
                'drawdown_series': executor.submit(self.calculate_drawdown_series, portfolio_history),
                'basic_metrics': executor.submit(self._calculate_basic_metrics, returns),
                'trading_metrics': executor.submit(self._calculate_trading_metrics, transaction_history),
                'winners_losers': executor.submit(self.get_top_winners_losers, transaction_history)
            }
            
            # Collect results
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"Error calculating {key}: {e}")
                    results[key] = {} if key in ['basic_metrics', 'trading_metrics'] else None
        
        # Calculate ratio metrics (depends on drawdown_data)
        drawdown_data = results['drawdown_data']
        if drawdown_data:
            ratio_metrics = self._calculate_ratio_metrics(returns, drawdown_data['max_drawdown'])
        else:
            ratio_metrics = {"sharpe_ratio": 0.0, "sortino_ratio": 0.0, "calmar_ratio": 0.0}
        
        # Calculate additional portfolio metrics
        total_days = len(portfolio_history)
        profitable_days = len(returns[returns > 0])
        unprofitable_days = len(returns[returns < 0])
        
        # Combine all metrics
        basic_metrics = results.get('basic_metrics', {})
        trading_metrics = results.get('trading_metrics', {})
        winners_losers = results.get('winners_losers', {"winners": [], "losers": []})
        equity_curve = results.get('equity_curve')
        drawdown_series = results.get('drawdown_series')
        
        comprehensive_metrics = {
            # Return Metrics
            "total_return_percentage": float(backtest_results.get('total_return_percentage', 0)),
            "annualized_return": float(backtest_results.get('annualized_return', 0)),
            "compound_annual_growth_rate": float(backtest_results.get('annualized_return', 0)),
            
            # Risk Metrics
            "volatility": basic_metrics.get('volatility', 0.0),
            "max_drawdown": drawdown_data.get('max_drawdown', 0.0) if drawdown_data else 0.0,
            "max_drawdown_duration": drawdown_data.get('max_drawdown_duration', 0) if drawdown_data else 0,
            "var_95": basic_metrics.get('var_95', 0.0),
            "skewness": basic_metrics.get('skewness', 0.0),
            "kurtosis": basic_metrics.get('kurtosis', 0.0),
            
            # Risk-Adjusted Ratios
            "sharpe_ratio": ratio_metrics.get('sharpe_ratio', 0.0),
            "sortino_ratio": ratio_metrics.get('sortino_ratio', 0.0),
            "calmar_ratio": ratio_metrics.get('calmar_ratio', 0.0),
            
            # Trading Metrics
            "win_rate": trading_metrics.get('win_rate', 0.0),
            "profit_factor": trading_metrics.get('profit_factor', 0.0),
            "total_trades": int(len(transaction_history)),
            "profitable_days": int(profitable_days),
            "unprofitable_days": int(unprofitable_days),
            "profitable_days_ratio": float(profitable_days / total_days) if total_days > 0 else 0,
            
            # Drawdown Details
            "max_drawdown_start": drawdown_data.get('max_drawdown_start') if drawdown_data else None,
            "max_drawdown_end": drawdown_data.get('max_drawdown_end') if drawdown_data else None,
            "recovery_date": drawdown_data.get('recovery_date') if drawdown_data else None,
            
            # Data for Charts
            "equity_curve": self._convert_to_serializable(equity_curve.to_dict('records')) if equity_curve is not None else [],
            "drawdown_series": self._convert_to_serializable(drawdown_series.to_dict('records')) if drawdown_series is not None else [],
            "returns_series": self._convert_to_serializable(returns.to_dict()),
            
            # Top Winners/Losers
            "top_winners": [
                {
                    "symbol": w.symbol,
                    "company_name": w.company_name,
                    "total_return": w.total_return,
                    "annualized_return": w.annualized_return,
                    "total_pnl": w.total_pnl,
                    "holding_period_days": w.holding_period_days,
                    "total_trades": w.total_trades,
                    "win_rate": w.win_rate
                } for w in winners_losers["winners"]
            ],
            "top_losers": [
                {
                    "symbol": l.symbol,
                    "company_name": l.company_name,
                    "total_return": l.total_return,
                    "annualized_return": l.annualized_return,
                    "total_pnl": l.total_pnl,
                    "holding_period_days": l.holding_period_days,
                    "total_trades": l.total_trades,
                    "win_rate": l.win_rate
                } for l in winners_losers["losers"]
            ]
        }
        
        return self._clean_metrics_dict(comprehensive_metrics)