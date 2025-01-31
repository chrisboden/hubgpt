from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import relationship

from ..config import DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_MODEL, DB_TYPE
from ..database import Base

# SQLAlchemy Models
class AdvisorModel(Base):
    """SQLAlchemy model for advisors in the database"""
    __tablename__ = "advisors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    model = Column(String, default=DEFAULT_MODEL)
    temperature = Column(Float, default=DEFAULT_TEMPERATURE)
    max_tokens = Column(Integer, default=DEFAULT_MAX_TOKENS)
    stream = Column(Boolean, default=True)
    messages = Column(JSON, nullable=False)  # Store messages as JSON
    gateway = Column(String, default='openrouter')
    tools = Column(JSON)  # Store tools list as JSON
    top_p = Column(Float)
    frequency_penalty = Column(Float)
    presence_penalty = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="advisor", cascade="all, delete-orphan")

# Pydantic Models
class Message(BaseModel):
    role: str
    content: str

class Advisor(BaseModel):
    name: str
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    stream: bool = True
    messages: List[Message]
    gateway: Optional[str] = 'openrouter'
    tools: Optional[List[str]] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None

    class Config:
        from_attributes = True

class AdvisorSummary(BaseModel):
    name: str
    description: Optional[str] = None
    model: str = DEFAULT_MODEL

class AdvisorCreate(BaseModel):
    """Model for creating a new advisor"""
    name: str
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    stream: bool = True
    messages: List[Message]
    gateway: Optional[str] = 'openrouter'
    tools: Optional[List[str]] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    format: str = "json"  # Either "json" or "md" 