from fastapi import APIRouter, HTTPException, Depends, Request, status, Body
from fastapi import File, UploadFile  # Import these separately to avoid global application
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import json
from pathlib import Path

from ..database import get_db
from ..models.users import User
from ..models.user_files import UserFile, FileShare as DBFileShare
from ..api_utils.user_file_utils import save_user_file, get_user_file_content, delete_user_file, get_user_file_path
from ..services.auth_service import get_current_user_from_request
from ..api_utils.prompt_utils import process_inclusions
from pydantic import BaseModel, Field
from ..models.files import FileRename

router = APIRouter(tags=["files"])
logger = logging.getLogger(__name__)

# Create a separate router for file operations
file_router = APIRouter(tags=["file_operations"])

class FileResponse(BaseModel):
    id: str
    user_id: str
    file_path: str
    file_type: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    is_public: bool
    metadata: dict = {}
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Convert metadata field name
        if hasattr(obj, 'file_metadata'):
            obj.metadata = obj.file_metadata
        # Convert datetime fields to strings
        if hasattr(obj, 'created_at'):
            obj.created_at = obj.created_at.isoformat()
        if hasattr(obj, 'updated_at'):
            obj.updated_at = obj.updated_at.isoformat()
        return super().from_orm(obj)

class FileShare(BaseModel):
    """File share request model"""
    shared_with_id: str = Field(..., description="ID of the user to share with")
    permissions: Dict[str, Any] = Field(..., description="Share permissions (read, write)")

class FileShareResponse(BaseModel):
    """File share response model"""
    id: str
    file_id: str
    shared_with_id: str
    permissions: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Convert datetime fields to strings
        if hasattr(obj, 'created_at'):
            obj.created_at = obj.created_at.isoformat()
        return super().from_orm(obj)

class ShareRequest(BaseModel):
    shared_with_id: str
    permissions: Dict[str, Any]

@router.post("/{file_path:path}", response_model=FileResponse)
async def upload_file(
    file_path: str,
    file: UploadFile = File(...),
    file_type: str = None,
    is_public: bool = False,
    metadata: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Upload a file to user's storage"""
    try:
        if not file_type:
            file_type = file_path.split('.')[-1] if '.' in file_path else 'txt'
            
        # Read file content
        content = await file.read()
            
        db_file = await save_user_file(
            db=db,
            user=current_user,
            file=content,
            file_path=file_path,
            file_type=file_type,
            content_type=file.content_type,
            is_public=is_public,
            metadata=metadata
        )
        
        return FileResponse.from_orm(db_file)
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_path:path}/content")
async def get_file_content(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get file content"""
    return get_user_file_content(db, current_user.id, file_path)

@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Delete a file"""
    if delete_user_file(db, current_user.id, file_path):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="File not found")

@router.get("/", response_model=List[FileResponse])
async def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """List user's files"""
    files = db.query(UserFile).filter(
        UserFile.user_id == current_user.id
    ).all()
    return [FileResponse.from_orm(f) for f in files]

@router.post("/{file_path:path}/share", response_model=FileShareResponse)
async def share_file(
    file_path: str,
    share_data: Dict[str, Any] = Body(..., embed=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Share a file with another user"""
    # Get file record
    file = db.query(UserFile).filter(
        UserFile.user_id == current_user.id,
        UserFile.file_path == file_path
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Check if user exists
    shared_with = db.query(User).filter(User.id == share_data["shared_with_id"]).first()
    if not shared_with:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Create share record
    share = DBFileShare(
        file_id=file.id,
        shared_with_id=share_data["shared_with_id"],
        permissions=share_data["permissions"]
    )
    
    db.add(share)
    db.commit()
    db.refresh(share)
    
    return FileShareResponse.from_orm(share)

@router.delete("/files/{file_path:path}/share/{user_id}")
async def unshare_file(
    file_path: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Remove file share"""
    # Get file record
    file = db.query(UserFile).filter(
        UserFile.user_id == current_user.id,
        UserFile.file_path == file_path
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Delete share record
    share = db.query(DBFileShare).filter(
        DBFileShare.file_id == file.id,
        DBFileShare.shared_with_id == user_id
    ).first()
    
    if share:
        db.delete(share)
        db.commit()
        return {"status": "success"}
        
    raise HTTPException(status_code=404, detail="Share not found")

@router.get("/")
async def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
) -> List[dict]:
    """List all files for the current user"""
    try:
        files = db.query(UserFile).filter(
            UserFile.user_id == current_user.id
        ).all()
        
        return [
            {
                "id": str(file.id),
                "name": file.file_path,
                "type": "file",
                "content_type": file.content_type,
                "is_public": file.is_public,
                "created_at": file.created_at.isoformat(),
                "updated_at": file.updated_at.isoformat() if file.updated_at else None,
                "metadata": file.metadata
            }
            for file in files
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )

@router.patch("/{file_path:path}", response_model=FileResponse)
async def rename_file(
    file_path: str,
    data: FileRename = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Rename a file"""
    # Debug logging
    logger.info(f"Received rename request for file: {file_path}")
    logger.info(f"Rename data: {data}")
    
    # Get file record
    db_file = db.query(UserFile).filter(
        UserFile.user_id == current_user.id,
        UserFile.file_path == file_path
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get the directory path and construct new file path
    dir_path = str(Path(file_path).parent)
    new_file_path = str(Path(dir_path) / data.new_name) if dir_path != '.' else data.new_name
    
    # Check if target path already exists
    existing_file = db.query(UserFile).filter(
        UserFile.user_id == current_user.id,
        UserFile.file_path == new_file_path
    ).first()
    
    if existing_file:
        raise HTTPException(status_code=409, detail="File with new name already exists")
    
    try:
        # Get absolute paths
        old_abs_path = get_user_file_path(current_user.id, file_path)
        new_abs_path = get_user_file_path(current_user.id, new_file_path, create_dirs=True)
        
        # Move the file
        old_abs_path.rename(new_abs_path)
        
        # Update database record
        db_file.file_path = new_file_path
        db.commit()
        db.refresh(db_file)
        
        return FileResponse.from_orm(db_file)
    except Exception as e:
        logger.error(f"Error renaming file: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Include the file operations router
router.include_router(file_router, prefix="/files") 