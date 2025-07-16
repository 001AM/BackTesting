from typing import Generator, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.config.database import SessionLocal
from backend.core.security import verify_token
from backend.models.schemas import User
from backend.services.user_service import UserService
from backend.models.database import User
# Database dependency
def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# JWT Authentication
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_email(email)
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to ensure current user is superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, otherwise None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
    

