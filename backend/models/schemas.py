from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator,ValidationInfo, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

# Auth Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ResponseModel(BaseModel):
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

class User(UserInDB):
    pass

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
    pat_positive: bool = Field(True, description="PAT > 0 filter")
    
    # Ranking criteria
    ranking_metrics: List[Dict[str, bool]] = Field(
        default_factory=lambda: [{"roe": True}],
        description="Metrics for ranking"
    )
    # metric_weights: Optional[Dict[str, float]] = Field(None, description="Weights for metrics")
    
    # Benchmark
    benchmark_symbol: str = Field("NIFTY50", description="Benchmark index symbol")