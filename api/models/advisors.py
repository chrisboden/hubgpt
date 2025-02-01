from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import relationship

from ..config import DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_MODEL, DB_TYPE
from ..database import Base

# SQLAlchemy Model
class AdvisorModel(Base):
    """Database model for advisors"""
    __tablename__ = "advisors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    model = Column(String, nullable=False)
    temperature = Column(Float, default=1.0)
    max_tokens = Column(Integer, default=1000)
    stream = Column(Boolean, default=True)
    messages = Column(JSON, nullable=False)
    gateway = Column(String, nullable=True)
    tools = Column(JSON, nullable=True)
    top_p = Column(Float, nullable=True)
    frequency_penalty = Column(Float, nullable=True)
    presence_penalty = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    conversations = relationship("Conversation", back_populates="advisor", cascade="all, delete-orphan")

# Pydantic Models
class Message(BaseModel):
    """Message model for advisor system messages"""
    role: str
    content: str
    name: Optional[str] = None

    def dict(self, *args, **kwargs):
        """Custom dict method to ensure proper serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "name": self.name
        }

class AdvisorBase(BaseModel):
    """Base model for advisor data"""
    name: str
    description: Optional[str] = None
    model: str
    temperature: float = 1.0
    max_tokens: int = 1000
    stream: bool = True
    messages: List[Dict[str, Any]]
    gateway: Optional[str] = None
    tools: Optional[List[str]] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None

class AdvisorCreate(AdvisorBase):
    """Model for creating a new advisor"""
    pass

class Advisor(AdvisorBase):
    """Model for advisor responses"""
    class Config:
        from_attributes = True

class AdvisorSummary(BaseModel):
    """Summary model for advisor listings"""
    name: str
    description: Optional[str] = None
    model: str

    class Config:
        from_attributes = True

class AdvisorUpdate(BaseModel):
    """Model for updating an advisor"""
    description: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = None
    messages: Optional[List[Dict[str, Any]]] = None
    gateway: Optional[str] = None
    tools: Optional[List[str]] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None 