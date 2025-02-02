from fastapi import APIRouter, HTTPException, Depends, Request, status, Body, UploadFile, File
from fastapi import File  # Import these separately to avoid global application
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
from ..services.file_service import save_file, get_files, get_file_content
from .. import config as app_config  # Import the config module as app_config

router = APIRouter(
    tags=["files"],
    redirect_slashes=False  # Prevent automatic slash redirection
)
logger = logging.getLogger(__name__)

# Create a separate router for file operations
file_router = APIRouter(tags=["file_operations"])

class FileResponse(BaseModel):
    name: str
    type: str = "file"
    content_type: Optional[str] = None
    is_public: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = {}

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

@router.get("/", response_model=List[FileResponse])
async def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
) -> List[FileResponse]:
    """List all files for the current user"""
    try:
        logger.info(f"Listing files for user: {current_user.id} ({current_user.username})")
        user_files = []
        
        # User's personal files directory
        user_files_dir = app_config.USERS_ROOT / str(current_user.id) / "files"
        logger.info(f"Looking for files in: {user_files_dir} (exists: {user_files_dir.exists()})")
        
        if user_files_dir.exists():
            logger.info(f"Directory exists and is directory: {user_files_dir.is_dir()}")
            for file_path in user_files_dir.rglob('*'):
                logger.info(f"Found path: {file_path} (is_file: {file_path.is_file()})")
                if file_path.is_file():
                    relative_path = file_path.relative_to(user_files_dir)
                    stat = file_path.stat()
                    logger.info(f"Found file: {relative_path}")
                    user_files.append(FileResponse(
                        name=str(relative_path),
                        type="file",
                        content_type=None,
                        is_public=False,
                        created_at=str(stat.st_ctime),
                        updated_at=str(stat.st_mtime),
                        metadata={}
                    ))
        else:
            logger.warning(f"Directory does not exist: {user_files_dir}")
        
        # Shared files
        logger.info(f"Looking for shared files in: {app_config.SHARED_ROOT} (exists: {app_config.SHARED_ROOT.exists()})")
        
        if app_config.SHARED_ROOT.exists():
            logger.info(f"Shared directory exists and is directory: {app_config.SHARED_ROOT.is_dir()}")
            for file_path in app_config.SHARED_ROOT.rglob('*'):
                logger.info(f"Found shared path: {file_path} (is_file: {file_path.is_file()})")
                if file_path.is_file():
                    relative_path = file_path.relative_to(app_config.SHARED_ROOT)
                    stat = file_path.stat()
                    logger.info(f"Found shared file: {relative_path}")
                    user_files.append(FileResponse(
                        name=str(relative_path),
                        type="file",
                        content_type=None,
                        is_public=True,
                        created_at=str(stat.st_ctime),
                        updated_at=str(stat.st_mtime),
                        metadata={}
                    ))
        else:
            logger.warning(f"Shared directory does not exist: {app_config.SHARED_ROOT}")
        
        logger.info(f"Returning {len(user_files)} files: {[f.name for f in user_files]}")
        return user_files
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )

@router.post("/{filename}")
async def upload_file(
    filename: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Upload a file"""
    try:
        await save_file(filename, file, str(current_user.id))
        return {"filename": filename}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{filename}/content")
async def get_file_content_endpoint(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get file content"""
    try:
        content = await get_file_content(filename, str(current_user.id))
        return {"filename": filename, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{filename}")
async def delete_file_endpoint(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Delete a file"""
    try:
        file_path = app_config.USERS_ROOT / str(current_user.id) / "files" / filename
        if file_path.exists():
            file_path.unlink()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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