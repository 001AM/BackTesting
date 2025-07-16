from typing import Optional, List
from sqlalchemy.orm import Session
from backend.models.database import User
from backend.models.schemas import UserCreate, UserUpdate
from backend.core.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user by token"""
        return self.db.query(User).filter(User.token == token).first()
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user(self, user_create: UserCreate) -> User:
        """Create new user"""
        # Hash password
        hashed_password = get_password_hash(user_create.password)
        
        # Create user
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=user_create.is_active
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users"""
        return self.db.query(User).offset(skip).limit(limit).all()
