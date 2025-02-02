from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from ..database import Base
from ..config import DB_TYPE

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    settings = Column(JSON, server_default="{}")

    # Relationships
    files = relationship("UserFile", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    snippets = relationship("Snippet", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

# Pydantic Models
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: Optional[str] = None
    current_token: Optional[str] = None
    created_at: datetime
    settings: Dict[str, Any]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: str
    exp: datetime 