# api/utils/file_utils.py

import os
from pathlib import Path

def sanitize_filename(filename):
    """
    Ensure filename is safe and contained within current directory.
    
    Args:
        filename (str): The filename or path to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Get just the basename, removing any path components
    safe_name = os.path.basename(filename)
    return safe_name

def sanitize_path(path):
    """
    Sanitize a file path to prevent directory traversal.
    Removes leading/trailing dots and slashes, and any parent directory references.
    
    Args:
        path (str): The path to sanitize
        
    Returns:
        str: Sanitized path
    """
    # Remove leading/trailing dots and slashes
    path = path.strip('./\\')
    
    # Split path into components and filter out dangerous parts
    parts = path.split(os.sep)
    safe_parts = [part for part in parts 
                 if part and part != '..' and not part.startswith('.')]
    
    # Rejoin path components
    return os.path.join(*safe_parts) if safe_parts else ''

def is_safe_path(filepath, base_dir):
    """
    Check if the file path is safe (within base directory).
    
    Args:
        filepath (str): Path to check
        base_dir (str): Base directory that should contain filepath
        
    Returns:
        bool: True if path is safe, False otherwise
    """
    try:
        # Get the absolute path of the requested file
        file_path = os.path.abspath(filepath)
        # Get the absolute path of the base directory
        base_path = os.path.abspath(base_dir)
        # Check if the file's path starts with the base path
        return file_path.startswith(base_path)
    except Exception:
        return False

def get_safe_filepath(filename, create_dirs=False):
    """
    Get a safe filepath and optionally create directories.
    
    Args:
        filename (str): The filename or path
        create_dirs (bool): Whether to create intermediate directories
        
    Returns:
        tuple: (filepath, error_message)
            filepath will be None if there's an error
            error_message will be None if successful
    """
    try:
        current_dir = os.getcwd()
        
        # Handle potential directory creation
        dir_path = os.path.dirname(filename)
        if dir_path:
            full_dir_path = os.path.join(current_dir, sanitize_path(dir_path))
            if create_dirs:
                if not is_safe_path(full_dir_path, current_dir):
                    return None, "Error: Cannot create directories outside the current directory."
                os.makedirs(full_dir_path, exist_ok=True)
            elif not os.path.exists(full_dir_path):
                return None, f"Error: Directory '{dir_path}' does not exist. Set create_dirs=true to create it."

        safe_filename = os.path.join(sanitize_path(dir_path) if dir_path else "", 
                                   os.path.basename(filename))
        filepath = os.path.join(current_dir, safe_filename)

        if not is_safe_path(filepath, current_dir):
            return None, "Error: Cannot access files outside the current directory."

        return filepath, None

    except Exception as e:
        return None, f"Error processing filepath: {str(e)}"