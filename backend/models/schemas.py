from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator,ValidationInfo, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Auth Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ResponseModel(BaseModel):
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

class User(UserInDB):
    pass

class CompanyCreate(BaseModel):
    symbol : str
    name :str
    sector : str
    industry : str
    market_cap_category : str  # e.g., Large, Mid, Small
    exchange : str
    is_active : bool
