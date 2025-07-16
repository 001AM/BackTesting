from sqlalchemy import or_
from sqlalchemy.sql import func, distinct
from sqlalchemy.orm import aliased
from datetime import datetime
from backend.models.database import Company, FundamentalData,DataUpdateLog
from typing import Optional, List

class StockDataServices():
    def __init__(self, db):
        self.db = db

    def get_all_stock(self):
        return self.db.query(Company).filter(Company.is_active == True).all()

    def statics_stock(self):
        total_stocks = self.db.query(func.count(Company.id)).filter(Company.is_active == True).scalar()
        total_sectors = self.db.query(func.count(distinct(Company.sector))).filter(Company.is_active == True).scalar()

        # Total companies with fundamental data (assume latest by report_date)
        subq = (
            self.db.query(FundamentalData.company_id)
            .distinct(FundamentalData.company_id)
            .subquery()
        )
        companies_with_fundamentals = self.db.query(func.count(subq.c.company_id)).scalar()

        data_completeness = 0.0
        if total_stocks > 0:
            data_completeness = round((companies_with_fundamentals / total_stocks) * 100, 1)

        # Get latest update timestamp from DataUpdateLog
        last_update = (
            self.db.query(func.max(DataUpdateLog.created_at))
            .filter(DataUpdateLog.data_type == 'fundamental')
            .scalar()
        )

        return {
            "total_stocks": total_stocks,
            "total_sectors": total_sectors,
            "data_completeness": data_completeness,
            "last_updated": last_update.isoformat() if last_update else None
        }


    def get_filtered_stock_universe(self,
        sector: Optional[str] = None,
        min_market_cap: Optional[float] = None,
        pe_range: Optional[tuple] = None,
        search: Optional[str] = None) -> List[dict]:

        CompanyModel = Company
        Fundamental = FundamentalData
        UpdateLog = DataUpdateLog

        # Subquery to get latest report_date for each company
        latest_fundamental_subq = (
            self.db.query(
                Fundamental.company_id.label('company_id'),
                func.max(Fundamental.report_date).label('max_date')
            )
            .group_by(Fundamental.company_id)
            .subquery()
        )

        # Aliased FundamentalData so we can join it properly
        LatestFundamental = aliased(Fundamental)

        # Now join all properly
        query = (
            self.db.query(
                CompanyModel.symbol,
                CompanyModel.name,
                CompanyModel.sector,
                LatestFundamental.market_cap,
                LatestFundamental.pe_ratio,
                LatestFundamental.roe,
                LatestFundamental.roce,
                UpdateLog.status
            )
            .select_from(CompanyModel)
            .join(
                latest_fundamental_subq,
                latest_fundamental_subq.c.company_id == CompanyModel.id
            )
            .join(
                LatestFundamental,
                (LatestFundamental.company_id == CompanyModel.id) &
                (LatestFundamental.report_date == latest_fundamental_subq.c.max_date)
            )
            .outerjoin(
                UpdateLog,
                (UpdateLog.company_id == CompanyModel.id) &
                (UpdateLog.data_type == 'fundamental')
            )
            .filter((CompanyModel.is_active == True) & (LatestFundamental.period_type == 'A'))
        )

        # Apply filters
        if sector:
            query = query.filter(CompanyModel.sector == sector)

        if min_market_cap:
            query = query.filter(LatestFundamental.market_cap >= min_market_cap)

        if pe_range:
            min_pe, max_pe = pe_range
            query = query.filter(LatestFundamental.pe_ratio.between(min_pe, max_pe))

        if search:
            ilike_pattern = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(CompanyModel.symbol).ilike(ilike_pattern),
                    func.lower(CompanyModel.name).ilike(ilike_pattern)
                )
            )

        result = query.all()

        return [
            {
                "symbol": r.symbol,
                "company_name": r.name,
                "sector": r.sector,
                "market_cap": float(r.market_cap) if r.market_cap else None,
                "pe_ratio": float(r.pe_ratio) if r.pe_ratio else None,
                "roe": float(r.roe) if r.roe else None,
                "roce": float(r.roce) if r.roce else None,
                "status": r.status or "Unknown"
            }
            for r in result
        ]
