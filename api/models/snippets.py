from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base

class Snippet(Base):
    """SQLAlchemy model for snippets"""
    __tablename__ = "snippets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    source_type = Column(String, nullable=False)  # advisor, notepad, team
    source_name = Column(String, nullable=False)  # specific source identifier
    content = Column(Text, nullable=False)  # stored as Markdown
    content_html = Column(Text)  # cached HTML rendering
    title = Column(String)  # extracted from first heading
    tags = Column(JSON, server_default='[]')  # array of tags
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    snippet_metadata = Column(JSON, server_default="{}")

    # Relationships
    user = relationship("User", back_populates="snippets")

    __table_args__ = (
        Index("ix_snippets_user_id", "user_id"),
        Index("ix_snippets_title", "title"),
    )

    def __repr__(self):
        return f"<Snippet(id={self.id}, user_id={self.user_id}, title={self.title})>"

# Pydantic Models
class SnippetBase(BaseModel):
    """Base model for snippet data"""
    source_type: str = Field(..., description="Type of source (advisor, notepad, team)")
    source_name: str = Field(..., description="Name or identifier of the source")
    content: str = Field(..., description="Markdown content of the snippet")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    snippet_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class SnippetCreate(SnippetBase):
    """Model for creating a new snippet"""
    pass

class SnippetUpdate(BaseModel):
    """Model for updating a snippet"""
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    snippet_metadata: Optional[Dict[str, Any]] = None

class SnippetResponse(SnippetBase):
    """Model for snippet responses"""
    id: str
    user_id: str
    title: Optional[str] = None
    content_html: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 