from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator,ValidationInfo, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

class ResponseModel(BaseModel):
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None

class CompanyCreate(BaseModel):
    symbol : str
    name :str
    sector : str
    industry : str
    market_cap_category : str  # e.g., Large, Mid, Small
    exchange : str
    is_active : bool

class StockFilterParams(BaseModel):
    sector: Optional[str] = None
    min_market_cap: Optional[float] = None
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    search: Optional[str] = None

class StockStatsResponse(BaseModel):
    total_stocks: int
    total_sectors: int
    data_completeness: float
    last_updated: Optional[str]

class SymbolListRequest(BaseModel):
    symbol_list : List

class BacktestRequest(BaseModel):
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    portfolio_size: int = Field(20, ge=1, le=100, description="Number of stocks")
    rebalancing_frequency: str = Field("quarterly", description="quarterly, monthly, yearly")
    weighting_method: str = Field("equal", description="equal, market_cap, metric_weighted")
    initial_capital :int
    
    # Filtering criteria
    min_market_cap: Optional[float] = Field(None, description="Minimum market cap (Cr)")
    max_market_cap: Optional[float] = Field(None, description="Maximum market cap (Cr)")
    min_roce: Optional[float] = Field(15, description="Minimum ROCE (%)")
    pat_positive: int = Field(10, description="PAT > 0 filter")
    
    # Ranking criteria
    ranking_metrics: List[Dict[str, bool]] = Field(
        default_factory=lambda: [{"roe": True}],
        description="Metrics for ranking"
    )
    # metric_weights: Optional[Dict[str, float]] = Field(None, description="Weights for metrics")
    
    # Benchmark
    benchmark_symbol: str = Field("NIFTY50", description="Benchmark index symbol")