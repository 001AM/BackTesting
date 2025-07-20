from typing import Generator
from backend.config.database import SessionLocal
# Database dependency
def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
