from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..database import Base

class Conversation(Base):
    """SQLAlchemy model for chat conversations"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    advisor_id = Column(String(36), ForeignKey('advisors.id'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    title = Column(String, nullable=True)
    status = Column(String, nullable=False, default='active')
    message_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    advisor = relationship("AdvisorModel", back_populates="conversations")
    user = relationship("User", back_populates="conversations")

    __table_args__ = (
        Index('ix_conversations_advisor_id', 'advisor_id'),
        Index('ix_conversations_user_id', 'user_id'),
        Index('ix_conversations_status', 'status'),
    )

class Message(Base):
    """SQLAlchemy model for chat messages"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey('conversations.id'), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    name = Column(String, nullable=True)
    llm_message_id = Column(String, nullable=True)
    parent_message_id = Column(String(36), nullable=True)
    sequence = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finish_reason = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_messages_conversation_id', 'conversation_id'),
        Index('ix_messages_sequence', 'conversation_id', 'sequence'),
    )

class ToolCall(Base):
    """SQLAlchemy model for tool calls in messages"""
    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id = Column(String(36), ForeignKey('messages.id'), nullable=False)
    tool_call_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    function_name = Column(String, nullable=False)
    function_arguments = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="tool_calls")

    __table_args__ = (
        Index('ix_tool_calls_message_id', 'message_id'),
    )

# Pydantic Models for API
class ToolCallResponse(BaseModel):
    id: str
    type: str
    function: Dict[str, Any]

class MessageCreate(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCallResponse]] = None

class MessageResponse(BaseModel):
    id: str
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCallResponse]] = None
    created_at: datetime
    sequence: int

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    advisor_id: str
    title: Optional[str] = None
    user_id: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    advisor_id: str
    title: Optional[str] = None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    messages: List[MessageResponse]

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    """A single message in a chat conversation"""
    role: str = Field(..., description="Role of the message sender (user/assistant/system/tool)")
    content: str = Field(..., description="Content of the message")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made by the assistant")
    tool_call_id: Optional[str] = Field(None, description="ID of the tool call this message responds to")

class ChatRequest(BaseModel):
    """Request body for sending a message"""
    message: str = Field(..., description="The message content")
    stream: bool = Field(False, description="Whether to stream the response")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (files, tools, etc.)")

class ChatResponse(BaseModel):
    """Response for a chat message"""
    conversation_id: str = Field(..., description="ID of the conversation")
    message: ChatMessage = Field(..., description="The assistant's response message")

class ConversationMetadata(BaseModel):
    """Metadata about a conversation"""
    id: str = Field(..., description="Unique identifier for the conversation")
    advisor_id: str = Field(..., description="ID of the advisor")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(..., description="When the conversation was last updated")
    message_count: int = Field(..., description="Number of messages in the conversation")

class ConversationHistory(BaseModel):
    """Full conversation history"""
    id: str = Field(..., description="Unique identifier for the conversation")
    advisor_id: str = Field(..., description="ID of the advisor")
    messages: List[ChatMessage] = Field(default_factory=list, description="List of messages in the conversation")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(..., description="When the conversation was last updated")

class NewConversation(BaseModel):
    """Response when creating a new conversation"""
    id: str = Field(..., description="Unique identifier for the new conversation")
    advisor_id: str = Field(..., description="ID of the advisor")
    created_at: datetime = Field(..., description="When the conversation was created") 