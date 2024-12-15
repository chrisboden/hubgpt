# tools/file_delete.py

import os
from utils.file_utils import get_safe_filepath

def execute(filename):
    """
    Deletes a specified file from the filesystem.
    
    Args:
        filename (str): Name of the file to delete
        
    Returns:
        str: Success or error message
    """
    try:
        filepath, error = get_safe_filepath(filename)
        if error:
            return error

        os.remove(filepath)
        return f"{os.path.basename(filename)} deleted successfully."
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except PermissionError:
        return f"Error: Permission denied to delete '{filename}'."
    except Exception as e:
        return f"Error deleting file: {str(e)}"

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_delete",
        "description": (
            "Deletes a specified file from the filesystem. "
            "Use this tool when you need to remove files that are no longer needed, manage storage space, or clean up temporary files created during operations. "
            "Exercise caution to avoid deleting important files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Name of the file to delete, including its extension. "
                        "Be certain that the file is safe to delete to prevent data loss."
                    )
                }
            },
            "required": ["filename"]
        }
    }
}