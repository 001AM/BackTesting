from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.services.back_test_services import BackTestServices
from backend.models.schemas import BacktestRequest
from backend.models.schemas import ResponseModel
from backend.db.session import get_db
from typing import Optional

router = APIRouter()


@router.post("/backtest", response_model=ResponseModel)
def back_test_metrics(
    request:BacktestRequest,
    db: Session = Depends(get_db)
):
    try:
        service = BackTestServices(db)
        data = service.run_backtest(request)
        return ResponseModel(
            message="Data fetched Successfully",
            data=data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data: {str(e)}"
        )


