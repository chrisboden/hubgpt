from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileInfo(BaseModel):
    """Information about a file or directory"""
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: datetime
    content_type: Optional[str] = None

class FileList(BaseModel):
    """List of files/directories"""
    files: List[FileInfo]
    
class FileContent(BaseModel):
    """File content for creation/update"""
    content: str
    
class FileRename(BaseModel):
    """Request model for renaming a file/directory"""
    new_name: str 