from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pathlib import Path
import logging
from ..models.advisors import Advisor, AdvisorSummary, AdvisorCreate
from ..services.advisor_service import (
    get_advisors_dir,
    load_advisor,
    create_json_content,
    create_markdown_content
)
from ..services.storage_service import ensure_directory, write_json_file

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[AdvisorSummary])
async def list_advisors():
    """List all available advisors"""
    advisors_dir = get_advisors_dir()
    advisors = []
    
    if not advisors_dir.exists():
        return []
        
    for file_path in advisors_dir.glob("*.json"):
        advisor_data = load_advisor(file_path)
        if advisor_data:
            advisors.append(AdvisorSummary(
                name=advisor_data["name"],
                model=advisor_data["model"]
            ))
            
    for file_path in advisors_dir.glob("*.md"):
        advisor_data = load_advisor(file_path)
        if advisor_data:
            advisors.append(AdvisorSummary(
                name=advisor_data["name"],
                model=advisor_data["model"]
            ))
            
    return advisors

@router.get("/{advisor_id}", response_model=Advisor)
async def get_advisor(advisor_id: str):
    """Get a specific advisor by ID"""
    advisors_dir = get_advisors_dir()
    
    # Try JSON file first
    json_path = advisors_dir / f"{advisor_id}.json"
    if json_path.exists():
        advisor_data = load_advisor(json_path)
        if advisor_data:
            return Advisor(**advisor_data)
            
    # Try markdown file
    md_path = advisors_dir / f"{advisor_id}.md"
    if md_path.exists():
        advisor_data = load_advisor(md_path)
        if advisor_data:
            return Advisor(**advisor_data)
            
    raise HTTPException(status_code=404, detail="Advisor not found")

@router.post("/", response_model=Advisor)
async def create_advisor(advisor: AdvisorCreate):
    """Create a new advisor"""
    advisors_dir = get_advisors_dir()
    ensure_directory(advisors_dir)
    
    # Check if advisor already exists
    json_path = advisors_dir / f"{advisor.name}.json"
    md_path = advisors_dir / f"{advisor.name}.md"
    if json_path.exists() or md_path.exists():
        raise HTTPException(status_code=400, detail="Advisor already exists")
        
    # Create advisor file
    if advisor.format == "json":
        content = create_json_content(advisor)
        file_path = json_path
        success = write_json_file(file_path, content)
    else:  # markdown
        content = create_markdown_content(advisor)
        file_path = md_path
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            success = True
        except Exception as e:
            logger.error(f"Error creating markdown advisor: {str(e)}")
            success = False
            
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create advisor")
        
    # Load and return the created advisor
    advisor_data = load_advisor(file_path)
    if not advisor_data:
        raise HTTPException(status_code=500, detail="Failed to load created advisor")
        
    return Advisor(**advisor_data)

@router.put("/{advisor_id}", response_model=Advisor)
async def update_advisor(advisor_id: str, advisor: AdvisorCreate):
    """Update an existing advisor"""
    advisors_dir = get_advisors_dir()
    
    # Check if advisor exists and get its current format
    json_path = advisors_dir / f"{advisor_id}.json"
    md_path = advisors_dir / f"{advisor_id}.md"
    
    existing_path = None
    is_json = False
    if json_path.exists():
        existing_path = json_path
        is_json = True
    elif md_path.exists():
        existing_path = md_path
        is_json = False
    else:
        raise HTTPException(status_code=404, detail="Advisor not found")
    
    # Create new content in original format
    if is_json:
        content = create_json_content(advisor)
        success = write_json_file(existing_path, content)
    else:  # markdown
        content = create_markdown_content(advisor)
        try:
            with open(existing_path, 'w') as f:
                f.write(content)
            success = True
        except Exception as e:
            logger.error(f"Error updating markdown advisor: {str(e)}")
            success = False
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update advisor")
    
    # Load and return the updated advisor
    advisor_data = load_advisor(existing_path)
    if not advisor_data:
        raise HTTPException(status_code=500, detail="Failed to load updated advisor")
    
    return Advisor(**advisor_data) 