from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
import markdown
import logging

from ..database import get_db
from ..models.snippets import (
    Snippet,
    SnippetCreate,
    SnippetUpdate,
    SnippetResponse
)
from ..models.users import User
from ..services.auth_service import get_current_user_from_request
from ..services.markdown_service import extract_title_and_tags, render_markdown

router = APIRouter(prefix="/api/v1/snippets", tags=["snippets"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[SnippetResponse])
async def list_snippets(
    source_type: Optional[str] = None,
    source_name: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """List all snippets for the current user with optional filtering"""
    query = db.query(Snippet).filter(Snippet.user_id == current_user.id)
    
    # Apply filters
    if source_type:
        query = query.filter(Snippet.source_type == source_type)
    if source_name:
        query = query.filter(Snippet.source_name == source_name)
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        for tag in tag_list:
            # For SQLite JSON, we need to check if the tag is in the JSON array
            query = query.filter(Snippet.tags.like(f'%"{tag}"%'))
    if q:
        query = query.filter(
            or_(
                Snippet.content.ilike(f"%{q}%"),
                Snippet.title.ilike(f"%{q}%")
            )
        )
    
    return query.all()

@router.get("/{snippet_id}", response_model=SnippetResponse)
async def get_snippet(
    snippet_id: str,
    format: str = Query("md", regex="^(md|html|text)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get a specific snippet"""
    snippet = db.query(Snippet).filter(
        Snippet.id == snippet_id,
        Snippet.user_id == current_user.id
    ).first()
    
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    
    # Handle format
    if format == "html" and not snippet.content_html:
        snippet.content_html = render_markdown(snippet.content)
        db.commit()
    elif format == "text":
        snippet.content = markdown.markdown(snippet.content)
    
    return snippet

@router.post("/", response_model=SnippetResponse)
async def create_snippet(
    snippet: SnippetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Create a new snippet"""
    try:
        # Extract title and tags from content
        title, extracted_tags = extract_title_and_tags(snippet.content)
        logger.info(f"Extracted title: {title}, tags: {extracted_tags}")
        
        # Combine extracted and provided tags
        tags = list(set(extracted_tags + (snippet.tags or [])))
        logger.info(f"Combined tags: {tags}")
        
        # Create snippet
        db_snippet = Snippet(
            user_id=current_user.id,
            source_type=snippet.source_type,
            source_name=snippet.source_name,
            content=snippet.content,
            content_html=render_markdown(snippet.content),
            title=title,
            tags=tags,
            snippet_metadata=snippet.snippet_metadata
        )
        
        db.add(db_snippet)
        db.commit()
        db.refresh(db_snippet)
        return db_snippet
    except Exception as e:
        logger.error(f"Error creating snippet: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{snippet_id}")
async def delete_snippet(
    snippet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Delete a snippet"""
    snippet = db.query(Snippet).filter(
        Snippet.id == snippet_id,
        Snippet.user_id == current_user.id
    ).first()
    
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    
    db.delete(snippet)
    db.commit()
    return {"message": "Snippet deleted successfully"}

@router.get("/export", response_model=List[SnippetResponse])
async def export_snippets(
    format: str = Query("md", regex="^(md|html|pdf)$"),
    ids: Optional[str] = Query(None, description="Comma-separated list of snippet IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Export snippets in bulk"""
    query = db.query(Snippet).filter(Snippet.user_id == current_user.id)
    
    if ids:
        id_list = [id.strip() for id in ids.split(",")]
        query = query.filter(Snippet.id.in_(id_list))
    
    snippets = query.all()
    
    # TODO: Implement PDF export
    if format == "pdf":
        raise HTTPException(status_code=501, detail="PDF export not yet implemented")
    
    return snippets 