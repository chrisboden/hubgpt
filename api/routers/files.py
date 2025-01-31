from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime
import shutil
import os

from ..models.files import FileInfo, FileList, FileContent, FileRename

router = APIRouter(tags=["files"])

# Get base files directory from environment or use default
FILES_DIR = Path(os.getenv("FILES_DIR", "files"))

def ensure_files_dir():
    """Ensure the files directory exists"""
    FILES_DIR.mkdir(parents=True, exist_ok=True)

def get_file_info(path: Path) -> FileInfo:
    """Get file information for a path"""
    stat = path.stat()
    # Handle root directory case
    try:
        rel_path = str(path.relative_to(FILES_DIR))
        # If this is the root directory, use empty string as path
        if rel_path == '.':
            rel_path = ''
    except ValueError:
        # If path is the root directory itself
        rel_path = ''
    
    return FileInfo(
        name=path.name if path != FILES_DIR else '',
        path=rel_path,
        is_dir=path.is_dir(),
        size=stat.st_size if not path.is_dir() else None,
        modified=datetime.fromtimestamp(stat.st_mtime),
        content_type="application/x-directory" if path.is_dir() else None
    )

@router.get("", response_model=FileList)
async def list_files():
    """List all files and folders in the files directory recursively"""
    ensure_files_dir()
    files = []
    try:
        # Add root directory
        root_info = FileInfo(
            name="",
            path="",
            is_dir=True,
            size=None,
            modified=datetime.fromtimestamp(FILES_DIR.stat().st_mtime),
            content_type="application/x-directory"
        )
        files.append(root_info)
        
        # Recursively walk through all files and directories
        for root, dirs, filenames in os.walk(FILES_DIR):
            root_path = Path(root)
            
            # Add directories
            for dir_name in dirs:
                dir_path = root_path / dir_name
                try:
                    files.append(get_file_info(dir_path))
                except Exception as e:
                    continue  # Skip directories that can't be accessed
            
            # Add files
            for filename in filenames:
                file_path = root_path / filename
                try:
                    files.append(get_file_info(file_path))
                except Exception as e:
                    continue  # Skip files that can't be accessed
                    
    except Exception as e:
        # If there's an error, just return empty list with root
        pass
    
    # Sort directories first, then files, both alphabetically
    return FileList(files=sorted(files, key=lambda x: (not x.is_dir, x.path.lower() if x.path else "")))

@router.get("/{path:path}")
async def get_file(path: str):
    """Get contents of a specific file"""
    file_path = FILES_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory")
    return Response(content=file_path.read_text(), media_type="text/plain")

@router.post("/{path:path}")
async def create_file(path: str, content: FileContent = None):
    """Create a new file or directory"""
    ensure_files_dir()
    file_path = FILES_DIR / path
    
    # Create all parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)
        
    # Check if path already exists
    if file_path.exists():
        raise HTTPException(status_code=409, detail="Path already exists")
    
    # Create directory if content is None
    if content is None:
        file_path.mkdir(parents=True)
        return JSONResponse(content={"message": "Directory created"})
    
    # Create file with content
    file_path.write_text(content.content)
    return JSONResponse(content={"message": "File created"})

@router.put("/{path:path}")
async def update_file(path: str, content: FileContent):
    """Update an existing file's contents"""
    file_path = FILES_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="Cannot update directory content")
    
    file_path.write_text(content.content)
    return JSONResponse(content={"message": "File updated"})

@router.patch("/{path:path}")
async def rename_file(path: str, rename: FileRename):
    """Rename a file or directory"""
    file_path = FILES_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")
        
    new_path = file_path.parent / rename.new_name
    if new_path.exists():
        raise HTTPException(status_code=409, detail="New path already exists")
        
    file_path.rename(new_path)
    return JSONResponse(content={"message": "Path renamed"})

@router.delete("/{path:path}")
async def delete_file(path: str):
    """Delete a file or directory"""
    file_path = FILES_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")
        
    if file_path.is_dir():
        shutil.rmtree(file_path)
    else:
        file_path.unlink()
        
    return JSONResponse(content={"message": "Path deleted"}) 