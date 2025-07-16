from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.config.settings import settings
from app.models.database import Base
import logging

logger = logging.getLogger(__name__)

# Database engine configuration
engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# Add connection pooling for production
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
    })
else:
    # SQLite specific configuration
    engine_kwargs.update({
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session for non-FastAPI usage"""
    return SessionLocal()
