from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.services.stock_data_services import StockDataServices
from backend.models.schemas import ResponseModel
from backend.db.session import get_db
from typing import Optional

router = APIRouter()

@router.get("/universe", response_model=ResponseModel)
def get_stock_universe(
    sector: Optional[str] = Query(None),
    min_market_cap: Optional[float] = Query(None, ge=0),
    pe_min: Optional[float] = Query(None, ge=0),
    pe_max: Optional[float] = Query(None, ge=0),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        service = StockDataServices(db)

        # Convert PE filter to tuple if both provided
        pe_range = (pe_min, pe_max) if pe_min is not None and pe_max is not None else None

        data = service.get_filtered_stock_universe(
            sector=sector,
            min_market_cap=min_market_cap,
            pe_range=pe_range,
            search=search
        )
        return ResponseModel(
                message="Data fetched Successfully",
                data=data
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data: {str(e)}"
        )


@router.get("/universe/statistics", response_model=ResponseModel)
def get_stock_statistics(db: Session = Depends(get_db)):
    try:
        service = StockDataServices(db)
        data = service.statics_stock()
        return ResponseModel(
            message="Data fetched Successfully",
            data=data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data: {str(e)}"
        )


