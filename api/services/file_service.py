from pathlib import Path
import aiofiles
import logging
from typing import List
from fastapi import UploadFile
from .. import config

logger = logging.getLogger(__name__)

async def save_file(filename: str, file: UploadFile, user_id: str) -> None:
    """Save an uploaded file to the user's storage directory."""
    try:
        # Create user-specific path
        file_path = config.USERS_ROOT / str(user_id) / "files" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
            
        logger.info(f"File saved successfully: {filename} for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving file {filename} for user {user_id}: {e}")
        raise

def get_files(user_id: str) -> List[str]:
    """Get a list of all files in the user's storage directory."""
    try:
        files = []
        user_dir = config.USERS_ROOT / str(user_id) / "files"
        if user_dir.exists():
            for file_path in user_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(user_dir)
                    files.append(str(relative_path))
        return sorted(files)
    except Exception as e:
        logger.error(f"Error listing files for user {user_id}: {e}")
        raise

async def get_file_content(filename: str, user_id: str) -> str:
    """Get the content of a file from the user's directory."""
    try:
        file_path = config.USERS_ROOT / str(user_id) / "files" / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
            
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            return content
    except Exception as e:
        logger.error(f"Error reading file {filename} for user {user_id}: {e}")
        raise 