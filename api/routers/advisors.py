from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from fastapi import status

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

router = APIRouter(
    tags=["advisors"],
    redirect_slashes=False  # Prevent automatic slash redirection
)
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

@router.get("", response_model=List[Advisor])  # Note: removed trailing slash
async def list_advisors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """List all available advisors"""
    advisors = db.query(AdvisorModel).all()
    return advisors

@router.get("/{advisor_id}", response_model=Advisor)  # This one is fine as it has a parameter
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

@router.post("", response_model=Advisor)  # Note: removed trailing slash
async def create_advisor(
    advisor: AdvisorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Create a new advisor"""
    try:
        # Check if advisor with this name already exists
        existing = db.query(AdvisorModel).filter(AdvisorModel.name == advisor.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Advisor with name '{advisor.name}' already exists"
            )
            
        db_advisor = AdvisorModel(**advisor.dict())
        db.add(db_advisor)
        db.commit()
        db.refresh(db_advisor)
        return db_advisor
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating advisor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating advisor: {str(e)}"
        )

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