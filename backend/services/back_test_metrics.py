from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass
from enum import Enum

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
    """Comprehensive performance metrics calculator"""
    
    def __init__(self):
        self.risk_free_rate = 0.06  # 6% annual risk-free rate
        
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
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate cumulative returns
        df['daily_return'] = df['total_value'].pct_change().fillna(0)
        df['cumulative_return'] = (1 + df['daily_return']).cumprod() - 1
        
        return df[['date', 'total_value', 'daily_return', 'cumulative_return']]
    
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
    
    def get_top_winners_losers(self, transaction_history: List[Dict], top_n: int = 10) -> Dict[str, List[SecurityPerformance]]:
        """Get top winning and losing securities"""
        if not transaction_history:
            return {"winners": [], "losers": []}
        
        # Group transactions by security
        securities = {}
        for tx in transaction_history:
            key = (tx['symbol'], tx['company_name'], tx['company_id'])
            if key not in securities:
                securities[key] = []
            securities[key].append(tx)
        
        performances = []
        
        for (symbol, company_name, company_id), txs in securities.items():
            buys = [tx for tx in txs if tx['action'] == 'BUY']
            sells = [tx for tx in txs if tx['action'] == 'SELL']
            
            if not buys:
                continue
                
            total_pnl = 0.0
            total_trades = 0
            winning_trades = 0
            buy_value = 0.0
            sell_value = 0.0
            
            # Calculate P&L and metrics
            for sell in sells:
                for buy in buys:
                    if buy.get('used_quantity', 0) < buy['quantity']:
                        trade_qty = min(sell['quantity'], buy['quantity'] - buy.get('used_quantity', 0))
                        pnl = (sell['price'] - buy['price']) * trade_qty
                        
                        total_pnl += pnl
                        total_trades += 1
                        if pnl > 0:
                            winning_trades += 1
                            
                        buy_value += buy['price'] * trade_qty
                        sell_value += sell['price'] * trade_qty
                        
                        buy['used_quantity'] = buy.get('used_quantity', 0) + trade_qty
                        sell['quantity'] -= trade_qty
                        
                        if sell['quantity'] <= 0:
                            break
            
            if buy_value == 0:
                continue
                
            total_return = float((sell_value - buy_value) / buy_value * 100)
            
            # Calculate holding period
            first_buy = min(buys, key=lambda x: x['date'])
            last_sell = max(sells, key=lambda x: x['date']) if sells else max(buys, key=lambda x: x['date'])
            holding_days = (datetime.strptime(str(last_sell['date']), '%Y-%m-%d') - 
                          datetime.strptime(str(first_buy['date']), '%Y-%m-%d')).days
            
            # Annualized return
            years = holding_days / 365.25 if holding_days > 0 else 1
            annualized_return = float(((1 + total_return/100) ** (1/years) - 1) * 100)
            
            win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0
            
            performance = SecurityPerformance(
                symbol=symbol,
                company_name=company_name,
                company_id=company_id,
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=0.0,  # Would need daily price data
                sharpe_ratio=0.0,  # Would need daily returns
                max_drawdown=0.0,  # Would need daily price data
                win_rate=win_rate,
                profit_factor=0.0,  # Would need more detailed calculation
                total_trades=int(total_trades),
                holding_period_days=int(holding_days),
                total_pnl=float(total_pnl)
            )
            
            performances.append(performance)
        
        # Sort by total return
        performances.sort(key=lambda x: x.total_return, reverse=True)
        
        return {
            "winners": performances[:top_n],
            "losers": performances[-top_n:][::-1]  # Reverse to show worst first
        }
    
    def calculate_comprehensive_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all comprehensive metrics"""
        portfolio_history = backtest_results.get('portfolio_history', [])
        transaction_history = backtest_results.get('transaction_history', [])
        
        if not portfolio_history:
            return {}
        
        # Calculate returns series
        returns = self.calculate_returns_series(portfolio_history)
        
        # Calculate equity curve
        equity_curve = self.calculate_equity_curve(portfolio_history)
        
        # Calculate drawdown metrics
        drawdown_data = self.calculate_max_drawdown(portfolio_history)
        drawdown_series = self.calculate_drawdown_series(portfolio_history)
        
        # Calculate risk metrics
        volatility = self.calculate_volatility(returns)
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        sortino_ratio = self.calculate_sortino_ratio(returns)
        calmar_ratio = self.calculate_calmar_ratio(returns, drawdown_data['max_drawdown'])
        
        # Calculate additional metrics
        win_rate = self.calculate_win_rate(transaction_history)
        profit_factor = self.calculate_profit_factor(transaction_history)
        var_95 = self.calculate_var(returns, 0.05)
        skewness = self.calculate_skewness(returns)
        kurtosis = self.calculate_kurtosis(returns)
        
        # Get top winners and losers
        winners_losers = self.get_top_winners_losers(transaction_history)
        
        # Calculate additional portfolio metrics
        total_days = len(portfolio_history)
        profitable_days = len(returns[returns > 0])
        unprofitable_days = len(returns[returns < 0])
        
        comprehensive_metrics = {
            # Return Metrics
            "total_return_percentage": float(backtest_results.get('total_return_percentage', 0)),
            "annualized_return": float(backtest_results.get('annualized_return', 0)),
            "compound_annual_growth_rate": float(backtest_results.get('annualized_return', 0)),
            
            # Risk Metrics
            "volatility": volatility,
            "max_drawdown": drawdown_data['max_drawdown'],
            "max_drawdown_duration": drawdown_data['max_drawdown_duration'],
            "var_95": var_95,
            "skewness": skewness,
            "kurtosis": kurtosis,
            
            # Risk-Adjusted Ratios
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            
            # Trading Metrics
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": int(len(transaction_history)),
            "profitable_days": int(profitable_days),
            "unprofitable_days": int(unprofitable_days),
            "profitable_days_ratio": float(profitable_days / total_days) if total_days > 0 else 0,
            
            # Drawdown Details
            "max_drawdown_start": drawdown_data['max_drawdown_start'],
            "max_drawdown_end": drawdown_data['max_drawdown_end'],
            "recovery_date": drawdown_data['recovery_date'],
            
            # Data for Charts
            "equity_curve": self._convert_to_serializable(equity_curve.to_dict('records')),
            "drawdown_series": self._convert_to_serializable(drawdown_series.to_dict('records')),
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