from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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