from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime, Text, DECIMAL, 
    ForeignKey, Index,BigInteger, func
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from backend.config.database import Base

# ─────────────────────────────────────────────────────────────────────────────
# Company Table
# ─────────────────────────────────────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap_category = Column(String(50))  # e.g., Large, Mid, Small
    exchange = Column(String(10), default='NSE')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    prices = relationship("StockPrice", back_populates="company", cascade="all, delete-orphan")
    fundamentals = relationship("FundamentalData", back_populates="company", cascade="all, delete-orphan")
    updates = relationship("DataUpdateLog", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_sector', 'sector'),
        Index('idx_market_cap_category', 'market_cap_category'),
    )

# ─────────────────────────────────────────────────────────────────────────────
# Stock Price Table
# ─────────────────────────────────────────────────────────────────────────────
class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(Date, nullable=False)

    open = Column(DECIMAL(12, 4))
    high = Column(DECIMAL(12, 4))
    low = Column(DECIMAL(12, 4))
    close = Column(DECIMAL(12, 4))
    adjusted_close = Column(DECIMAL(12, 4))
    volume = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

    # Relationship
    company = relationship("Company", back_populates="prices")

    __table_args__ = (
        Index('idx_company_date_unique', 'company_id', 'date', unique=True),
        Index('idx_date', 'date'),
    )

# ─────────────────────────────────────────────────────────────────────────────
# Fundamental Data Table
# ─────────────────────────────────────────────────────────────────────────────
class FundamentalData(Base):
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    period_type = Column(String(10), nullable=False)  # 'Q' or 'A'

    # Profit & Loss
    revenue = Column(DECIMAL(18, 2))
    pat = Column(DECIMAL(18, 2))  # Profit After Tax
    ebitda = Column(DECIMAL(18, 2))
    operating_profit = Column(DECIMAL(18, 2))
    interest_expense = Column(DECIMAL(18, 2))

    # Balance Sheet
    total_assets = Column(DECIMAL(18, 2))
    total_liabilities = Column(DECIMAL(18, 2))
    shareholders_equity = Column(DECIMAL(18, 2))
    cash_and_equivalents = Column(DECIMAL(18, 2))
    total_debt = Column(DECIMAL(18, 2))

    # Cash Flow
    operating_cash_flow = Column(DECIMAL(18, 2))
    capex = Column(DECIMAL(18, 2))
    free_cash_flow = Column(DECIMAL(18, 2))

    # Market
    market_cap = Column(DECIMAL(18, 2))
    shares_outstanding = Column(BigInteger)

    roce = Column(DECIMAL(8, 4))           
    roe = Column(DECIMAL(8, 4))            
    roa = Column(DECIMAL(8, 4))            
    eps = Column(DECIMAL(15, 4))
    pe_ratio = Column(DECIMAL(15, 6))      
    pb_ratio = Column(DECIMAL(15, 6))     
    debt_to_equity = Column(DECIMAL(15, 6)) 
    current_ratio = Column(DECIMAL(15, 6))  
    quick_ratio = Column(DECIMAL(15, 6))
    gross_margin = Column(DECIMAL(8, 4))    
    operating_margin = Column(DECIMAL(8, 4)) 
    net_margin = Column(DECIMAL(8, 4))      

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship
    company = relationship("Company", back_populates="fundamentals")

    __table_args__ = (
        Index('idx_company_report_period', 'company_id', 'report_date', 'period_type', unique=True),
        Index('idx_roe', 'roe'),
        Index('idx_roce', 'roce'),
        Index('idx_pe', 'pe_ratio'),
        Index('idx_market_cap', 'market_cap'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data Update Logs
# ─────────────────────────────────────────────────────────────────────────────
class DataUpdateLog(Base):
    __tablename__ = "data_update_logs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    data_type = Column(String(50), nullable=False)  # 'price', 'fundamental'
    last_update_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)  # 'success', 'failed', etc.
    error_message = Column(Text)
    records_updated = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    # Relationship
    company = relationship("Company", back_populates="updates")

    __table_args__ = (
        Index('idx_company_data_type', 'company_id', 'data_type'),
        Index('idx_last_update_date', 'last_update_date'),
    )

