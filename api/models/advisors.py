from pydantic import BaseModel
from typing import List, Optional
from ..config import DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_MODEL

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