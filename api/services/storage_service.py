from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional, List
import shutil

logger = logging.getLogger(__name__)

def ensure_directory(path: Path) -> None:
    """Ensure a directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Read and parse a JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {str(e)}")
        return None

def write_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """Write data to a JSON file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {file_path}: {str(e)}")
        return False

def backup_file(file_path: Path) -> Optional[Path]:
    """Create a backup of a file"""
    try:
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {str(e)}")
        return None

def delete_file(file_path: Path) -> bool:
    """Delete a file"""
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False

def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """List files in a directory matching a pattern"""
    try:
        return list(directory.glob(pattern))
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {str(e)}")
        return [] 