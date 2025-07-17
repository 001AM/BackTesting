from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
import threading
import logging

from backend.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

executor = ThreadPoolExecutor(max_workers=2)
from backend.models.schemas import SymbolListRequest
@router.post("/populate/companies/")
def populate_companies(request:SymbolListRequest,db: Session = Depends(get_db)):
    """
    Populate companies from Nifty 200 list.
    This endpoint runs the population process in the background.
    """
    from backend.services.populate_services import BacktestingDataManager
    
    try:
        cp = BacktestingDataManager(db)

        def run_population():
            try:
                logger.info("Starting company population process...")
                success = cp.fast_setup_backtesting_data(request.symbol_list)
                if success:
                    logger.info("✅ Company population completed successfully")
                else:
                    logger.error("❌ Company population failed")
            except Exception as e:
                logger.exception("❌ Error populating companies from FastAPI:")

        # Submit the task to the executor
        future = executor.submit(run_population)
        
        return {
            "status": "started",
            "message": "Company population process has been initiated in the background"
        }
        
    except Exception as e:
        logger.exception("❌ Error starting company population:")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start company population: {str(e)}"
        )


@router.get("/populate/companies/status")
def get_population_status():
    """
    Get the status of the population process.
    This is a simple endpoint to check if the service is running.
    """
    return {
        "status": "Service is running",
        "active_threads": threading.active_count(),
        "executor_info": {
            "max_workers": executor._max_workers,
            "threads": len(executor._threads) if hasattr(executor, '_threads') else 0
        }
    }