from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime, Text, JSON, DECIMAL, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Float,
    BigInteger, SmallInteger, TIMESTAMP, func, text, Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from backend.config.database import Base
from backend.config.settings import settings
import uuid
import secrets
import hashlib
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from typing import Dict, Optional, List
from enum import Enum
fernet = Fernet(settings.FERNET_KEY)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
    total_requests = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True))


    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_last_activity', 'last_activity_at'),
        CheckConstraint(
            "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", 
            name='valid_email'
        ),
    )

    @validates('email')
    def validate_email(self, key, address):
        assert '@' in address, "Invalid email address"
        return address.lower()

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

# Enhanced FundamentalData class with growth metrics

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

    # Existing Metrics & Ratios (as percentages)
    roce = Column(DECIMAL(8, 4))           # Percentage
    roe = Column(DECIMAL(8, 4))            # Percentage
    roa = Column(DECIMAL(8, 4))            # Percentage
    eps = Column(DECIMAL(15, 4))
    pe_ratio = Column(DECIMAL(15, 6))      # ✅ Available
    pb_ratio = Column(DECIMAL(15, 6))      # ✅ Available (P/BV)
    debt_to_equity = Column(DECIMAL(15, 6)) # ✅ Available
    current_ratio = Column(DECIMAL(15, 6))  # ✅ Available
    quick_ratio = Column(DECIMAL(15, 6))
    gross_margin = Column(DECIMAL(8, 4))    # Percentage
    operating_margin = Column(DECIMAL(8, 4)) # Percentage
    net_margin = Column(DECIMAL(8, 4))      # Percentage

    # NEW: Growth Metrics (stored as percentages)
    revenue_growth_yoy = Column(DECIMAL(10, 4))  # Year-over-year revenue growth %
    profit_growth_yoy = Column(DECIMAL(10, 4))   # Year-over-year profit growth %
    ebitda_growth_yoy = Column(DECIMAL(10, 4))   # Year-over-year EBITDA growth %
    eps_growth_yoy = Column(DECIMAL(10, 4))      # Year-over-year EPS growth %
    
    # Optional: Quarter-over-quarter growth
    revenue_growth_qoq = Column(DECIMAL(10, 4))  # Quarter-over-quarter revenue growth %
    profit_growth_qoq = Column(DECIMAL(10, 4))   # Quarter-over-quarter profit growth %

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
        # Add indexes for growth metrics
        Index('idx_revenue_growth_yoy', 'revenue_growth_yoy'),
        Index('idx_profit_growth_yoy', 'profit_growth_yoy'),
        # Constraints for growth metrics (can be negative)
        CheckConstraint('revenue_growth_yoy >= -100', name='valid_revenue_growth'),
        CheckConstraint('profit_growth_yoy >= -100', name='valid_profit_growth'),
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


# ─────────────────────────────────────────────────────────────────────────────
# Market Holidays
# ─────────────────────────────────────────────────────────────────────────────
class MarketHoliday(Base):
    __tablename__ = "market_holidays"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    description = Column(String(255))
    exchange = Column(String(10), default='NSE')
    created_at = Column(DateTime, default=func.now())
