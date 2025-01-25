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
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    tools: Optional[List[str]] = None

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
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    tools: Optional[List[str]] = None
    format: str = "json"  # Either "json" or "md" 