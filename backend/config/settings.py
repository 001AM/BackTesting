from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Back Testing"
    VERSION: str = "1.0.0"
    DATABASE_ECHO: bool = False
    
    # Database
    DATABASE_URL: str
    DATABASE_ASYNC_URL: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Default Admin
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
