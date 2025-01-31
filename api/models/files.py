from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileInfo(BaseModel):
    """Model for file information"""
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: datetime
    content_type: Optional[str] = None

class FileList(BaseModel):
    """Model for list of files"""
    files: List[FileInfo]

class FileContent(BaseModel):
    """Model for file content"""
    content: str

class FileRename(BaseModel):
    """Model for file rename operation"""
    new_name: str 