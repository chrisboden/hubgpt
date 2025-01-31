import os
import json
from pathlib import Path
import logging
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)

def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path (Union[str, Path]): Directory path to ensure exists
        
    Returns:
        Path: Path object of the ensured directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def write_json_file(path: Union[str, Path], data: Dict[str, Any]) -> bool:
    """
    Write data to a JSON file.
    
    Args:
        path (Union[str, Path]): Path to write the JSON file
        data (Dict[str, Any]): Data to write to the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        path = Path(path)
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file with pretty formatting
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {path}: {e}")
        return False

def read_json_file(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Read data from a JSON file.
    
    Args:
        path (Union[str, Path]): Path to read the JSON file from
        
    Returns:
        Dict[str, Any]: Data from the JSON file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
    """
    path = Path(path)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_file(path: Union[str, Path]) -> bool:
    """
    Delete a file if it exists.
    
    Args:
        path (Union[str, Path]): Path to the file to delete
        
    Returns:
        bool: True if file was deleted, False if it didn't exist
    """
    try:
        path = Path(path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {path}: {e}")
        return False 