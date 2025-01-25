from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class Advisor(BaseModel):
    name: str
    model: str
    temperature: float
    max_tokens: int = 0  # Default to 0 to handle max_output_tokens in MD files
    stream: bool = True
    messages: List[Message]
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    tools: Optional[List[str]] = None

class AdvisorSummary(BaseModel):
    name: str
    description: Optional[str] = None
    model: str

class AdvisorCreate(BaseModel):
    """Model for creating a new advisor"""
    name: str
    model: str
    temperature: float
    max_tokens: int = 1000
    stream: bool = True
    messages: List[Message]
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    tools: Optional[List[str]] = None
    format: str = "json"  # Either "json" or "md" 