from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    """Basic file information"""
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: datetime
    content_type: Optional[str] = None

class FileList(BaseModel):
    """List of files"""
    files: list[FileInfo]

class FileContent(BaseModel):
    """File content for create/update operations"""
    content: str

class FileRename(BaseModel):
    """File rename operation"""
    new_name: str

# New models for user files

class UserFileCreate(BaseModel):
    """Create a new user file"""
    file_path: str = Field(..., description="Relative path within user's space")
    file_type: str = Field(..., description="File type (txt, md, json)")
    content_type: Optional[str] = Field(None, description="MIME type")
    is_public: bool = Field(False, description="Whether file is publicly accessible")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class UserFileUpdate(BaseModel):
    """Update user file metadata"""
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    content_type: Optional[str] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class UserFileResponse(BaseModel):
    """User file information"""
    id: str
    user_id: str
    file_path: str
    file_type: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    is_public: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class FileShare(BaseModel):
    """File sharing information"""
    shared_with_id: str
    permissions: Dict[str, Any] = Field(..., description="Share permissions (read, write)")

class FileShareResponse(BaseModel):
    """File share response"""
    id: str
    file_id: str
    shared_with_id: str
    permissions: Dict[str, Any]
    created_at: datetime 