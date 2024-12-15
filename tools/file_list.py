# tools/file_list.py

import os
import json
import re
from datetime import datetime
from termcolor import cprint
from utils.file_utils import is_safe_path, sanitize_filename

def extract_word_count_from_filename(filename):
    """
    Extract word count from filename if present in [wc_X] format.
    
    Args:
        filename (str): Filename to extract word count from
    
    Returns:
        int or None: Word count if found, otherwise None
    """
    match = re.search(r'\[wc_(\d+)\]', filename)
    return int(match.group(1)) if match else None

def get_file_metadata(filepath):
    """
    Get detailed metadata for a file.
    
    Args:
        filepath (str): Full path to the file
    
    Returns:
        dict: File metadata including size, creation time, word count
    """
    try:
        # Get file stats
        stat = os.stat(filepath)
        
        # Get file creation time
        creation_time = datetime.fromtimestamp(stat.st_ctime).isoformat()
        
        # Get file size in bytes
        file_size = stat.st_size
        
        # Extract filename and word count from filename
        filename = os.path.basename(filepath)
        word_count = extract_word_count_from_filename(filename)
        
        return {
            "filename": filename,
            "size_bytes": file_size,
            "created_at": creation_time,
            "word_count": word_count
        }
    except Exception as e:
        cprint(f"Error getting file metadata: {e}", "red")
        return {
            "filename": os.path.basename(filepath),
            "size_bytes": None,
            "created_at": None,
            "word_count": None
        }

def execute(directory=None):
    """
    Lists files in the specified directory with enhanced metadata.
    
    Args:
        directory (str, optional): Directory path to list files from. 
                                 If None, uses current working directory.
    
    Returns:
        str: JSON string containing list of files with metadata
    """
    try:
        # Get the current working directory
        current_dir = os.getcwd()
        cprint(f"Current working directory: {current_dir}", "blue")
        
        # Determine target directory
        if directory is None:
            dir_path = current_dir
        else:
            # Sanitize and join paths
            safe_dir = sanitize_filename(directory)
            dir_path = os.path.join(current_dir, safe_dir)
            cprint(f"Requested directory: {directory}", "blue")
            cprint(f"Sanitized path: {dir_path}", "blue")

        # Security check
        if not is_safe_path(dir_path, current_dir):
            cprint(f"Security check failed for path: {dir_path}", "red")
            return "Error: Cannot list files outside the current directory."

        # Verify directory exists
        if not os.path.exists(dir_path):
            cprint(f"Directory does not exist: {dir_path}", "red")
            return f"Error: Directory '{directory}' does not exist."

        # Verify it's actually a directory
        if not os.path.isdir(dir_path):
            cprint(f"Path is not a directory: {dir_path}", "red")
            return f"Error: '{directory}' is not a directory."

        # List files with metadata
        file_metadata = []
        for filename in os.listdir(dir_path):
            filepath = os.path.join(dir_path, filename)
            
            # Only process files, not directories
            if os.path.isfile(filepath):
                file_info = get_file_metadata(filepath)
                file_metadata.append(file_info)
        
        cprint(f"Successfully listed {len(file_metadata)} files", "green")
        
        # Return JSON string with files list and metadata
        return json.dumps({
            "status": "success",
            "directory": dir_path,
            "files": file_metadata
        }, indent=2)

    except PermissionError as e:
        error_msg = f"Permission denied accessing directory: {str(e)}"
        cprint(error_msg, "red")
        return json.dumps({"status": "error", "message": error_msg})
    except Exception as e:
        error_msg = f"Error listing files: {str(e)}"
        cprint(error_msg, "red")
        return json.dumps({"status": "error", "message": error_msg})


# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_list",
        "description": (
            "Lists all files and directories within a specified directory. "
            "Use this tool to explore the filesystem, check for the existence of files, or organize files and directories. "
            "When the user's instruction is fuzzy, you should follow your curiosity to see whether there are any files "
            "that could help you learn more about the task. This can help in decision-making processes, such as determining "
            "whether a file needs to be created or modified."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": (
                        "The directory path to list files from. "
                        "Can be relative to the current working directory or an absolute path. "
                        "If omitted, the current directory is used."
                    )
                }
            },
            "required": []
        }
    }
}