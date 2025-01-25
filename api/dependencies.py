from fastapi import HTTPException, Request
from typing import Optional
import logging
from pathlib import Path
from .services.advisor_service import load_advisor
from .services.chat_service import load_conversation
from . import config

logger = logging.getLogger(__name__)

async def get_advisor(advisor_id: str):
    """Dependency to get and validate an advisor"""
    advisor_path = config.ADVISORS_DIR / f"{advisor_id}.json"
    md_path = config.ADVISORS_DIR / f"{advisor_id}.md"
    
    if advisor_path.exists():
        advisor_data = load_advisor(advisor_path)
        if advisor_data:
            return advisor_data
    elif md_path.exists():
        advisor_data = load_advisor(md_path)
        if advisor_data:
            return advisor_data
            
    raise HTTPException(status_code=404, detail="Advisor not found")

async def get_chat(conversation_id: str):
    """Dependency to get and validate a chat conversation"""
    data = load_conversation(conversation_id)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return data

async def validate_api_key(request: Request) -> bool:
    """Dependency to validate API key (for future use)"""
    # TODO: Implement API key validation
    return True 