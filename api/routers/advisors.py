from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..database import get_db
from ..models.advisors import (
    Advisor,
    AdvisorSummary,
    AdvisorCreate,
    AdvisorModel
)
from ..models.users import User
from ..services.auth_service import get_current_user_from_request
from ..api_utils.prompt_utils import process_inclusions
from pydantic import BaseModel

router = APIRouter(tags=["advisors"])
logger = logging.getLogger(__name__)

class AdvisorResponse(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    temperature: float
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    max_tokens: int
    tools: List[str]
    created_at: str
    updated_at: str

@router.get("/", response_model=List[Advisor])
async def list_advisors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """List all available advisors"""
    advisors = db.query(AdvisorModel).all()
    return advisors

@router.get("/{advisor_id}", response_model=Advisor)
async def get_advisor(
    advisor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get a specific advisor"""
    advisor = db.query(AdvisorModel).filter(AdvisorModel.id == advisor_id).first()
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor not found")
    return advisor

@router.post("/", response_model=Advisor)
async def create_advisor(
    advisor: AdvisorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Create a new advisor"""
    db_advisor = AdvisorModel(**advisor.dict())
    db.add(db_advisor)
    db.commit()
    db.refresh(db_advisor)
    return db_advisor

@router.put("/{advisor_id}", response_model=Advisor)
async def update_advisor(
    advisor_id: str,
    advisor: AdvisorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Update an existing advisor"""
    db_advisor = db.query(AdvisorModel).filter(AdvisorModel.id == advisor_id).first()
    if not db_advisor:
        raise HTTPException(status_code=404, detail="Advisor not found")
        
    # Update fields
    for field, value in advisor.dict().items():
        setattr(db_advisor, field, value)
        
    db.commit()
    db.refresh(db_advisor)
    return db_advisor

@router.delete("/{advisor_id}")
async def delete_advisor(
    advisor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Delete an advisor"""
    advisor = db.query(AdvisorModel).filter(AdvisorModel.id == advisor_id).first()
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor not found")
        
    db.delete(advisor)
    db.commit()
    
    return {"status": "success"} 