from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from backend.models.database import Company
from backend.models.schemas import CompanyCreate
from pydantic import TypeAdapter
import secrets

class CompanyPopulate:

    def __init__(db:Session):
        self.db = db

    def company_create(company:CompanyCreate):
        company_create = Company(
            symbol= company.company,
            name= company.name,
            sector= company.sector,
            industry= company.industry,
            market_cap_category=company.market_cap_category,# e.g., Large, Mid, Small
            exchange=company.exchange,
            is_active=True
        )

        self.db.add(company_create)
        self.db.commit()
        return True
    
    


