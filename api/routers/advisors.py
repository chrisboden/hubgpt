from fastapi import APIRouter, HTTPException, Depends
from typing import List
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

router = APIRouter(tags=["advisors"])
logger = logging.getLogger(__name__)

@router.get("", response_model=List[AdvisorSummary])
async def list_advisors(db: Session = Depends(get_db)):
    """List all available advisors"""
    try:
        advisors = db.query(AdvisorModel).all()
        return [
            AdvisorSummary(
                name=advisor.name,
                description=advisor.description,
                model=advisor.model
            ) for advisor in advisors
        ]
    except Exception as e:
        logger.error(f"Error listing advisors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{advisor_id}", response_model=Advisor)
async def get_advisor(advisor_id: str, db: Session = Depends(get_db)):
    """Get a specific advisor by ID"""
    advisor = db.query(AdvisorModel).filter(
        AdvisorModel.name == advisor_id
    ).first()
    
    if not advisor:
        raise HTTPException(status_code=404, detail="Advisor not found")
        
    return Advisor(
        name=advisor.name,
        description=advisor.description,
        model=advisor.model,
        temperature=advisor.temperature,
        max_tokens=advisor.max_tokens,
        stream=advisor.stream,
        messages=advisor.messages,
        gateway=advisor.gateway,
        tools=advisor.tools,
        top_p=advisor.top_p,
        frequency_penalty=advisor.frequency_penalty,
        presence_penalty=advisor.presence_penalty
    )

@router.post("", response_model=Advisor)
async def create_advisor(advisor: AdvisorCreate, db: Session = Depends(get_db)):
    """Create a new advisor"""
    try:
        # Check if advisor already exists
        existing = db.query(AdvisorModel).filter(
            AdvisorModel.name == advisor.name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Advisor already exists")
            
        # Create new advisor
        new_advisor = AdvisorModel(
            name=advisor.name,
            description=advisor.description,
            model=advisor.model,
            temperature=advisor.temperature,
            max_tokens=advisor.max_tokens,
            stream=advisor.stream,
            messages=advisor.messages,
            gateway=advisor.gateway,
            tools=advisor.tools,
            top_p=advisor.top_p,
            frequency_penalty=advisor.frequency_penalty,
            presence_penalty=advisor.presence_penalty,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_advisor)
        db.commit()
        db.refresh(new_advisor)
        
        return Advisor(
            name=new_advisor.name,
            description=new_advisor.description,
            model=new_advisor.model,
            temperature=new_advisor.temperature,
            max_tokens=new_advisor.max_tokens,
            stream=new_advisor.stream,
            messages=new_advisor.messages,
            gateway=new_advisor.gateway,
            tools=new_advisor.tools,
            top_p=new_advisor.top_p,
            frequency_penalty=new_advisor.frequency_penalty,
            presence_penalty=new_advisor.presence_penalty
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating advisor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{advisor_id}", response_model=Advisor)
async def update_advisor(advisor_id: str, advisor: AdvisorCreate, db: Session = Depends(get_db)):
    """Update an existing advisor"""
    try:
        # Get existing advisor
        existing = db.query(AdvisorModel).filter(
            AdvisorModel.name == advisor_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Advisor not found")
            
        # Update fields
        existing.name = advisor.name
        existing.description = advisor.description
        existing.model = advisor.model
        existing.temperature = advisor.temperature
        existing.max_tokens = advisor.max_tokens
        existing.stream = advisor.stream
        existing.messages = advisor.messages
        existing.gateway = advisor.gateway
        existing.tools = advisor.tools
        existing.top_p = advisor.top_p
        existing.frequency_penalty = advisor.frequency_penalty
        existing.presence_penalty = advisor.presence_penalty
        existing.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing)
        
        return Advisor(
            name=existing.name,
            description=existing.description,
            model=existing.model,
            temperature=existing.temperature,
            max_tokens=existing.max_tokens,
            stream=existing.stream,
            messages=existing.messages,
            gateway=existing.gateway,
            tools=existing.tools,
            top_p=existing.top_p,
            frequency_penalty=existing.frequency_penalty,
            presence_penalty=existing.presence_penalty
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating advisor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{advisor_id}")
async def delete_advisor(advisor_id: str, db: Session = Depends(get_db)):
    """Delete an advisor"""
    try:
        advisor = db.query(AdvisorModel).filter(
            AdvisorModel.name == advisor_id
        ).first()
        
        if not advisor:
            raise HTTPException(status_code=404, detail="Advisor not found")
            
        db.delete(advisor)
        db.commit()
        
        return {"status": "success", "message": f"Advisor {advisor_id} deleted"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting advisor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 