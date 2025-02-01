import os
import shutil
from pathlib import Path
from typing import Optional, Union
from fastapi import UploadFile, HTTPException
import logging
from sqlalchemy.orm import Session
from ..models.user_files import UserFile, FileShare
from ..models.users import User

logger = logging.getLogger(__name__)

def get_user_file_path(user_id: str, file_path: str, create_dirs: bool = False) -> Path:
    """
    Get the absolute path for a user file.
    
    Args:
        user_id (str): User ID
        file_path (str): Relative file path within user's space
        create_dirs (bool): Whether to create parent directories
        
    Returns:
        Path: Absolute path to the file
    """
    # Handle shared files
    if file_path.startswith('shared/'):
        base_path = Path("storage") / file_path
    else:
        base_path = Path("storage") / "users" / user_id / "files" / file_path
        
    if create_dirs:
        base_path.parent.mkdir(parents=True, exist_ok=True)
        
    return base_path

def check_file_access(db: Session, user_id: str, file_path: str) -> bool:
    """
    Check if user has access to file.
    
    Args:
        db (Session): Database session
        user_id (str): User ID
        file_path (str): File path to check
        
    Returns:
        bool: Whether user has access
    """
    # Shared files are accessible to all
    if file_path.startswith('shared/'):
        return True
        
    # Query the file record
    file = db.query(UserFile).filter(
        UserFile.user_id == user_id,
        UserFile.file_path == file_path
    ).first()
    
    if not file:
        return False
        
    # Owner has access
    if file.user_id == user_id:
        return True
        
    # Check if file is public
    if file.is_public:
        return True
        
    # Check if file is shared with user
    share = db.query(FileShare).filter(
        FileShare.file_id == file.id,
        FileShare.shared_with_id == user_id
    ).first()
    
    return share is not None

async def save_user_file(
    db: Session,
    user: User,
    file: Union[UploadFile, bytes, str],
    file_path: str,
    file_type: str,
    content_type: Optional[str] = None,
    is_public: bool = False,
    metadata: dict = None
) -> UserFile:
    """
    Save a file to user's storage and create/update database record.
    
    Args:
        db (Session): Database session
        user (User): User model instance
        file (Union[UploadFile, bytes, str]): File content
        file_path (str): Relative path within user's space
        file_type (str): File type (txt, md, json)
        content_type (str, optional): MIME type
        is_public (bool): Whether file is publicly accessible
        metadata (dict, optional): Additional metadata
        
    Returns:
        UserFile: Created/updated file record
    """
    try:
        # Get absolute path
        abs_path = get_user_file_path(user.id, file_path, create_dirs=True)
        
        # Save file content
        if isinstance(file, UploadFile):
            with abs_path.open('wb') as f:
                shutil.copyfileobj(file.file, f)
        elif isinstance(file, bytes):
            abs_path.write_bytes(file)
        else:
            abs_path.write_text(str(file))
            
        # Get file size
        size_bytes = abs_path.stat().st_size
        
        # Check if file already exists
        db_file = db.query(UserFile).filter(
            UserFile.user_id == user.id,
            UserFile.file_path == file_path
        ).first()
        
        if db_file:
            # Update existing record
            db_file.file_type = file_type
            db_file.content_type = content_type
            db_file.size_bytes = size_bytes
            db_file.is_public = is_public
            if metadata is not None:
                db_file.file_metadata = metadata
        else:
            # Create new record
            db_file = UserFile(
                user_id=user.id,
                file_path=file_path,
                file_type=file_type,
                content_type=content_type,
                size_bytes=size_bytes,
                is_public=is_public,
                file_metadata=metadata or {}
            )
            db.add(db_file)
            
        db.commit()
        db.refresh(db_file)
        
        return db_file
        
    except Exception as e:
        logger.error(f"Error saving user file: {e}")
        if abs_path.exists():
            abs_path.unlink()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_user_file_content(
    db: Session,
    user_id: str,
    file_path: str,
    check_access: bool = True
) -> str:
    """
    Get content of a user file.
    
    Args:
        db (Session): Database session
        user_id (str): User ID
        file_path (str): File path
        check_access (bool): Whether to check access permissions
        
    Returns:
        str: File content
    """
    logger.info(f"Getting user file content: user_id={user_id}, path={file_path}, check_access={check_access}")
    
    if check_access:
        has_access = check_file_access(db, user_id, file_path)
        logger.info(f"Access check result: {has_access}")
        if not has_access:
            logger.warning(f"Access denied: user_id={user_id}, path={file_path}")
            raise HTTPException(status_code=403, detail="Access denied")
        
    abs_path = get_user_file_path(user_id, file_path)
    logger.info(f"Resolved absolute path: {abs_path}")
    
    if not abs_path.exists():
        logger.warning(f"File not found: {abs_path}")
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        content = abs_path.read_text()
        logger.info(f"Successfully read file: length={len(content)}")
        return content
    except Exception as e:
        logger.error(f"Error reading file {abs_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def delete_user_file(
    db: Session,
    user_id: str,
    file_path: str,
    check_access: bool = True
) -> bool:
    """
    Delete a user file.
    
    Args:
        db (Session): Database session
        user_id (str): User ID
        file_path (str): File path
        check_access (bool): Whether to check access permissions
        
    Returns:
        bool: Whether file was deleted
    """
    logger.info(f"Deleting file: user_id={user_id}, file_path={file_path}")
    
    if check_access and not check_file_access(db, user_id, file_path):
        logger.warning(f"Access denied: user_id={user_id}, file_path={file_path}")
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Get file record
    file = db.query(UserFile).filter(
        UserFile.user_id == user_id,
        UserFile.file_path == file_path
    ).first()
    
    if not file:
        logger.warning(f"File not found: user_id={user_id}, file_path={file_path}")
        return False
        
    try:
        # Delete file from storage
        abs_path = get_user_file_path(user_id, file_path)
        logger.info(f"Deleting file from disk: {abs_path}")
        if abs_path.exists():
            abs_path.unlink()
            
        # Delete database record (cascade will handle shares)
        logger.info(f"Deleting database record: id={file.id}")
        db.delete(file)
        db.commit()
        
        # Verify deletion
        check = db.query(UserFile).filter(
            UserFile.id == file.id
        ).first()
        if check:
            logger.error(f"File record still exists after deletion: id={file.id}")
        else:
            logger.info(f"File record deleted successfully: id={file.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 