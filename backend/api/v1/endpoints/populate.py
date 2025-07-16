from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
import threading

from backend.core.dependencies import get_db

router = APIRouter()

executor = ThreadPoolExecutor(max_workers=2)

@router.post("/populate/companies/")
def populate_companies(db: Session = Depends(get_db)):
    from backend.services.populate_services import CompanyPopulate
    cp = CompanyPopulate(db)

    def run_population():
        try:
            cp.get_companies()
        except Exception as e:
            logger.exception("Error populating companies from FastAPI:")

    executor.submit(run_population)
    return {"status": "started"}

