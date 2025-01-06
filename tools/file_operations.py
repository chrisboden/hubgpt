# tools/file_operations.py

import os
import json
import shutil
import re
import requests
from urllib.parse import urlparse, unquote
import mimetypes
import threading
from typing import List, Dict, Union, Optional
from difflib import unified_diff
from termcolor import colored
from contextlib import contextmanager
from utils.ui_utils import update_spinner_status
import logging

def expand_home(filepath: str) -> str:
    """Expand user home directory."""
    if filepath.startswith('~/') or filepath == '~':
        return os.path.expanduser(filepath)
    return filepath

# Constants and globals
FILESYSTEM_PERMISSIONS = 0o644  # -rw-r--r--
DIRECTORY_PERMISSIONS = 0o755   # drwxr-xr-x
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

class DirectoryManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DirectoryManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._init_directories()
    
    def _init_directories(self):
        """Initialize file operation directories"""
        logging.info("Initializing file operation directories...")
        
        # Set up base directories
        self.ROOT_DIRECTORY = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.TEMP_DIRECTORY = os.path.join(self.ROOT_DIRECTORY, 'temp')
        self.DEMO_DIRECTORY = os.path.join(self.ROOT_DIRECTORY, 'demo')
        self.DATA_DIRECTORY = os.path.join(self.ROOT_DIRECTORY, 'data')
        
        # Create directories
        for directory in [self.TEMP_DIRECTORY, self.DEMO_DIRECTORY, self.DATA_DIRECTORY]:
            os.makedirs(directory, mode=DIRECTORY_PERMISSIONS, exist_ok=True)
        
        # Set up allowed directories
        self.allowed_directories = [
            self.ROOT_DIRECTORY,
            self.TEMP_DIRECTORY,
            self.DEMO_DIRECTORY,
            self.DATA_DIRECTORY
        ]
        
        # Add environment directories
        env_dirs = os.environ.get('ALLOWED_DIRECTORIES', '').split(':')
        self.allowed_directories.extend([
            os.path.abspath(expand_home(d))
            for d in env_dirs
            if d and d != '.'
        ])
        
        # Remove duplicates while preserving order
        self.allowed_directories = list(dict.fromkeys(self.allowed_directories))
        
        logging.debug(f"Initialized directories: {self.allowed_directories}")
        logging.info("File operation directories initialized successfully")

# Initialize the singleton
dir_manager = DirectoryManager()

# Export the directory paths and allowed directories
ROOT_DIRECTORY = dir_manager.ROOT_DIRECTORY
TEMP_DIRECTORY = dir_manager.TEMP_DIRECTORY
DEMO_DIRECTORY = dir_manager.DEMO_DIRECTORY
DATA_DIRECTORY = dir_manager.DATA_DIRECTORY
allowed_directories = dir_manager.allowed_directories

# Custom exceptions
class TimeoutError(Exception):
    pass

# Utility functions
@contextmanager
def timeout(seconds: int = 30):
    """Context manager to enforce a timeout on operations."""
    timer = threading.Timer(seconds, lambda: (_ for _ in ()).throw(
        TimeoutError(f"Operation timed out after {seconds} seconds")))
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def check_file_size(path: str) -> None:
    """Check if the file size exceeds the maximum allowed size."""
    update_spinner_status(f"Checking file size for {path}...")
    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        update_spinner_status(f"File size check failed - exceeds limit")
        raise ValueError(
            f"File size ({size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)")
    update_spinner_status("File size check passed")


def normalize_path(p: str) -> str:
    """
    Normalize path to a full, absolute path.

    Args:
        p (str): Input path

    Returns:
        str: Fully resolved, absolute path
    """
    update_spinner_status(f"Normalizing path: {p}")
    # Expand user home directory
    expanded_path = os.path.expanduser(p)

    # Convert to absolute path
    absolute_path = os.path.abspath(expanded_path)

    # Normalize path (remove redundant separators, resolve .., etc.)
    normalized_path = os.path.normpath(absolute_path)

    update_spinner_status(f"Path normalized to: {normalized_path}")
    return normalized_path


def resolve_path(path: str, allowed_directories: List[str]) -> str:
    """
    Resolve and validate a path against allowed directories.
    Handles path normalization and validation in one place.
    """
    try:
        update_spinner_status(f"Resolving path: {path}")
        print(colored(f"Resolving path: {path}", "yellow"))
        
        # Special handling for paths starting with /data or /temp
        if path.startswith('/data/'):
            relative_path = path[6:]  # Remove '/data/' prefix
            full_path = os.path.join(DATA_DIRECTORY, relative_path)
            normalized_path = os.path.abspath(full_path)
            print(colored(f"Converted /data path to: {normalized_path}", "yellow"))
            
            # Validate it's within DATA_DIRECTORY
            if os.path.commonpath([normalized_path, DATA_DIRECTORY]) == DATA_DIRECTORY:
                update_spinner_status(f"Path resolved successfully to: {normalized_path}")
                return normalized_path
        elif path.startswith('/temp/'):
            relative_path = path[6:]  # Remove '/temp/' prefix
            full_path = os.path.join(TEMP_DIRECTORY, relative_path)
            normalized_path = os.path.abspath(full_path)
            print(colored(f"Converted /temp path to: {normalized_path}", "yellow"))
            
            # Validate it's within TEMP_DIRECTORY
            if os.path.commonpath([normalized_path, TEMP_DIRECTORY]) == TEMP_DIRECTORY:
                update_spinner_status(f"Path resolved successfully to: {normalized_path}")
                return normalized_path
        
        # If path is relative, try to resolve against each allowed directory
        if not os.path.isabs(path):
            for base_dir in allowed_directories:
                full_path = os.path.join(base_dir, path)
                normalized_path = os.path.abspath(full_path)
                
                # Check if the normalized path is under any allowed directory
                if any(
                    os.path.commonpath([normalized_path, os.path.abspath(allowed_dir)]) == os.path.abspath(allowed_dir)
                    for allowed_dir in allowed_directories
                ):
                    update_spinner_status(f"Path resolved successfully to: {normalized_path}")
                    return normalized_path
        else:
            # For absolute paths, just normalize and validate
            normalized_path = os.path.abspath(path)
            if any(
                os.path.commonpath([normalized_path, os.path.abspath(allowed_dir)]) == os.path.abspath(allowed_dir)
                for allowed_dir in allowed_directories
            ):
                update_spinner_status(f"Path resolved successfully to: {normalized_path}")
                return normalized_path

        update_spinner_status("Path resolution failed - access denied")
        raise ValueError(f"Access denied - path outside allowed directories: {path}")

    except Exception as e:
        update_spinner_status(f"Path resolution failed: {str(e)}")
        raise ValueError(f"Error resolving path {path}: {str(e)}")

def normalize_line_endings(text: str) -> str:
    """Normalize line endings to Unix style."""
    return text.replace('\r\n', '\n')


def create_unified_diff(original_content: str, new_content: str, filepath: str = 'file') -> str:
    """Create a unified diff between original and new content."""
    update_spinner_status("Generating unified diff...")
    # Ensure consistent line endings for diff
    normalized_original = normalize_line_endings(original_content)
    normalized_new = normalize_line_endings(new_content)

    diff = '\n'.join(unified_diff(
        normalized_original.splitlines(keepends=True),
        normalized_new.splitlines(keepends=True),
        fromfile=f'{filepath} (original)',
        tofile=f'{filepath} (modified)'
    ))
    update_spinner_status("Diff generated successfully")
    return diff


def apply_file_edits(filePath: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """Apply a series of text edits to a file."""
    try:
        update_spinner_status(f"Applying edits to {filePath}...")
        # Check file size before processing
        check_file_size(filePath)

        # Read file content and normalize line endings
        with timeout(30):
            with open(filePath, 'r', encoding='utf-8') as file:
                content = normalize_line_endings(file.read())

        # Apply edits sequentially
        modified_content = content
        for i, edit in enumerate(edits, 1):
            update_spinner_status(f"Applying edit {i} of {len(edits)}...")
            old_text = normalize_line_endings(edit['oldText'])
            new_text = normalize_line_endings(edit['newText'])

            # Special handling for prepending text
            if old_text == '':
                modified_content = new_text + modified_content
                continue

            # Exact replacement
            if old_text in modified_content:
                modified_content = modified_content.replace(old_text, new_text)
                continue

            # More robust line-by-line matching
            lines = modified_content.split('\n')
            for i, line in enumerate(lines):
                if old_text.strip() == line.strip():
                    lines[i] = new_text
                    modified_content = '\n'.join(lines)
                    break
            else:
                # If no match found, raise a more informative error
                update_spinner_status("Edit failed - text not found")
                raise ValueError(
                    f"Could not find match for edit:\nOld Text: '{old_text}'\n"
                    f"Current File Content (first 500 chars): '{content[:500]}'"
                )

        # Create unified diff
        diff = create_unified_diff(content, modified_content, filePath)

        if not dry_run:
            update_spinner_status("Writing modified content...")
            with timeout(30):
                with open(filePath, 'w', encoding='utf-8') as file:
                    file.write(modified_content)

        update_spinner_status("File edits applied successfully")
        return diff

    except Exception as e:
        update_spinner_status(f"Error applying edits: {str(e)}")
        raise ValueError(f"Error applying edits to {filePath}: {str(e)}")


def read_file(llm_client, path: str) -> str:
    """Read the content of a file."""
    try:
        update_spinner_status(f"Reading file: {path}")
        valid_path = resolve_path(path, allowed_directories)
        check_file_size(valid_path)

        with timeout(30):
            try:
                with open(valid_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    update_spinner_status("File read successfully")
                    return content
            except UnicodeDecodeError:
                update_spinner_status("Attempting binary read for non-UTF-8 file...")
                # Fallback to binary mode for non-UTF-8 files
                with open(valid_path, 'rb') as file:
                    content = file.read().decode('utf-8', errors='replace')
                    update_spinner_status("File read successfully in binary mode")
                    return content
    except TimeoutError:
        update_spinner_status("File read timed out")
        raise ValueError(f"Timeout reading file {path}")
    except Exception as e:
        update_spinner_status(f"Error reading file: {str(e)}")
        raise ValueError(f"Error reading file {path}: {str(e)}")


def read_multiple_files(llm_client, paths: List[str]) -> List[str]:
    """Read the content of multiple files."""
    results = []
    for i, file_path in enumerate(paths, 1):
        try:
            update_spinner_status(f"Reading file {i} of {len(paths)}: {file_path}")
            valid_path = resolve_path(file_path, allowed_directories)
            check_file_size(valid_path)

            with timeout(30):
                try:
                    with open(valid_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except UnicodeDecodeError:
                    with open(valid_path, 'rb') as file:
                        content = file.read().decode('utf-8', errors='replace')
                results.append(f"{file_path}:\n{content}\n")
                update_spinner_status(f"Successfully read file {i} of {len(paths)}")
        except Exception as e:
            update_spinner_status(f"Error reading file {file_path}: {str(e)}")
            results.append(f"{file_path}: Error - {str(e)}")
    return results


def write_file(llm_client, path: str, content: str) -> str:
    """Write content to a file, handling both absolute and relative paths."""
    try:
        update_spinner_status(f"Writing file: {path}")
        print(colored(f"Writing file - Original path: {path}", "yellow"))

        # Handle special paths
        if path.startswith('/data/'):
            relative_path = path[1:]  # Remove leading slash
            full_path = os.path.join(DATA_DIRECTORY, relative_path[5:])  # Remove 'data/' prefix
        elif path.startswith('/temp/'):
            relative_path = path[1:]  # Remove leading slash
            full_path = os.path.join(TEMP_DIRECTORY, relative_path[5:])  # Remove 'temp/' prefix
        else:
            full_path = resolve_path(path, allowed_directories)

        print(colored(f"Full resolved path: {full_path}", "yellow"))
        print(colored(f"Directory exists? {os.path.exists(os.path.dirname(full_path))}", "yellow"))

        # Ensure the directory exists
        update_spinner_status("Creating directory structure...")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        print(colored(f"Directory created/verified", "yellow"))
        print(colored(f"Attempting to write file...", "yellow"))

        # Write the file
        update_spinner_status("Writing file content...")
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)

        print(colored(f"File written successfully", "yellow"))
        print(colored(f"File exists? {os.path.exists(full_path)}", "yellow"))
        print(colored(f"File size: {os.path.getsize(full_path) if os.path.exists(full_path) else 'N/A'}", "yellow"))

        update_spinner_status("File written successfully")
        return f"Successfully wrote to {full_path}"
    except Exception as e:
        update_spinner_status(f"Error writing file: {str(e)}")
        print(colored(f"Error in write_file: {str(e)}", "red"))
        raise ValueError(f"Error writing to file {path}: {str(e)}")


def edit_file(llm_client, path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """Edit a file by applying a series of text edits."""
    try:
        update_spinner_status(f"Editing file: {path}")
        valid_path = resolve_path(path, allowed_directories)
        return apply_file_edits(valid_path, edits, dry_run)
    except Exception as e:
        update_spinner_status(f"Error editing file: {str(e)}")
        raise ValueError(f"Error editing file {path}: {str(e)}")


def create_directory(llm_client, path: str) -> str:
    """Create a directory at the specified path."""
    try:
        update_spinner_status(f"Creating directory: {path}")
        # Resolve and validate the path
        valid_path = resolve_path(path, allowed_directories)

        print(f"Creating directory at: {valid_path}")  # Debug print

        with timeout(10):
            os.makedirs(valid_path, mode=DIRECTORY_PERMISSIONS, exist_ok=True)
        update_spinner_status("Directory created successfully")
        return f"Successfully created directory {valid_path}"
    except TimeoutError:
        update_spinner_status("Directory creation timed out")
        raise ValueError(f"Timeout creating directory {path}")
    except Exception as e:
        update_spinner_status(f"Error creating directory: {str(e)}")
        raise ValueError(f"Error creating directory {path}: {str(e)}")


def list_directory(llm_client, path: str) -> str:
    """List the contents of a directory."""
    try:
        update_spinner_status(f"Listing directory: {path}")
        valid_path = resolve_path(path, allowed_directories)
        with timeout(10):
            entries = os.listdir(valid_path)
            formatted = '\n'.join(
                f"[DIR]  {entry}" if os.path.isdir(os.path.join(valid_path, entry))
                else f"[FILE] {entry}"
                # Sort entries for consistent output
                for entry in sorted(entries)
            )
        update_spinner_status("Directory listing complete")
        return formatted
    except TimeoutError:
        update_spinner_status("Directory listing timed out")
        raise ValueError(f"Timeout listing directory {path}")
    except Exception as e:
        raise ValueError(f"Error listing directory {path}: {str(e)}")


def directory_tree(llm_client, path: str, max_depth: int = 20) -> str:
    """Generate a JSON representation of the directory tree."""
    try:
        update_spinner_status(f"Building directory tree for: {path}")
        print(colored(f"Building directory tree for: {path}", "green"))
        
        valid_path = resolve_path(path, allowed_directories)

        def build_tree(current_path: str, current_depth: int = 0) -> Union[Dict[str, Union[str, List]], str]:
            if current_depth >= max_depth:
                return "[MAX DEPTH REACHED]"

            with timeout(5):  # Short timeout for each directory
                entries = os.listdir(current_path)
                result = []

                for entry in entries:
                    try:
                        update_spinner_status(f"Processing {entry}")
                        print(colored(f"Processing {entry}", "green"))
                        
                        full_path = os.path.join(current_path, entry)
                        entry_data = {
                            "name": entry,
                            "type": "directory" if os.path.isdir(full_path) else "file"
                        }

                        if entry_data["type"] == "directory":
                            entry_data["children"] = build_tree(
                                full_path, current_depth + 1)

                        result.append(entry_data)
                    except Exception as e:
                        update_spinner_status(f"Error processing {entry}: {str(e)}")
                        print(colored(f"Error processing {entry}: {str(e)}", "yellow"))

                return result

        tree = build_tree(valid_path)
        update_spinner_status("Directory tree built successfully")
        print(colored("Directory tree built successfully", "green"))
        return json.dumps(tree, indent=2)
        
    except TimeoutError:
        update_spinner_status(f"Timeout building directory tree for {path}")
        raise ValueError(f"Timeout building directory tree for {path}")
    except Exception as e:
        update_spinner_status(f"Error building directory tree: {str(e)}")
        raise ValueError(f"Error building directory tree for {path}: {str(e)}")


def move_file(llm_client, source: str, destination: str) -> str:
    """Move a file from source to destination."""
    try:
        update_spinner_status(f"Moving file from {source} to {destination}")
        print(colored(f"Moving file from {source} to {destination}", "green"))
        
        # Resolve and validate both source and destination paths
        full_source = resolve_path(source, allowed_directories)
        full_destination = resolve_path(destination, allowed_directories)

        # Ensure destination directory exists
        update_spinner_status("Creating destination directory if needed")
        os.makedirs(os.path.dirname(full_destination), exist_ok=True)

        # Move the file
        update_spinner_status("Moving file...")
        shutil.move(full_source, full_destination)

        update_spinner_status("File moved successfully")
        print(colored("File moved successfully", "green"))
        return f"Successfully moved {full_source} to {full_destination}"
        
    except Exception as e:
        update_spinner_status(f"Error moving file: {str(e)}")
        raise ValueError(
            f"Error moving file from {source} to {destination}: {str(e)}")


def search_files(root_path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
    """Search for files matching a pattern, excluding specified patterns."""
    # Resolve the root path
    valid_root_path = resolve_path(root_path, allowed_directories)

    exclude_patterns = exclude_patterns or []
    results = []

    def search(current_path: str):
        try:
            update_spinner_status(f"Searching in: {current_path}")
            print(colored(f"Searching in: {current_path}", "green"))
            
            with timeout(5):  # Short timeout for directory listing
                entries = os.listdir(current_path)
        except (PermissionError, OSError, TimeoutError) as e:
            update_spinner_status(f"Access error for {current_path}: {str(e)}")
            print(colored(f"Access error for {current_path}: {str(e)}", "yellow"))
            return

        for entry in entries:
            try:
                full_path = os.path.join(current_path, entry)

                # Skip if we can't access the file/directory
                try:
                    os.stat(full_path)
                except (PermissionError, OSError):
                    continue

                # Validate each path before processing
                try:
                    resolve_path(full_path, allowed_directories)
                except ValueError as e:
                    print(colored(str(e), "red"))
                    continue

                # Check if path matches any exclude pattern
                relative_path = os.path.relpath(full_path, valid_root_path)
                should_exclude = any(
                    re.match(pattern.replace('*', '.*'),
                             relative_path, re.IGNORECASE)
                    for pattern in exclude_patterns
                )

                if should_exclude:
                    continue

                if pattern.lower() in entry.lower():
                    update_spinner_status(f"Found match: {entry}")
                    results.append(full_path)

                if os.path.isdir(full_path):
                    search(full_path)
            except Exception as e:
                update_spinner_status(f"Error processing {entry}: {str(e)}")
                print(colored(f"Error processing {entry}: {str(e)}", "red"))
                continue

    search(valid_root_path)
    update_spinner_status(f"Search complete. Found {len(results)} matches")
    return results


def get_file_stats(filePath: str, format: str = 'dict') -> Union[Dict, str]:
    """
    Get file statistics in either dict or string format.
    Combines previous get_file_stats and get_file_info functions.
    """
    try:
        update_spinner_status(f"Getting stats for: {filePath}")
        print(colored(f"Getting stats for: {filePath}", "green"))
        
        valid_path = resolve_path(filePath, allowed_directories)
        with timeout(5):
            stats = os.stat(valid_path)
            info = {
                "size": stats.st_size,
                "created": stats.st_ctime,
                "modified": stats.st_mtime,
                "accessed": stats.st_atime,
                "is_directory": os.path.isdir(valid_path),
                "is_file": os.path.isfile(valid_path),
                "permissions": oct(stats.st_mode)[-3:]
            }

            update_spinner_status("File stats retrieved successfully")
            return info if format == 'dict' else '\n'.join(f"{k}: {v}" for k, v in info.items())
    except Exception as e:
        update_spinner_status(f"Error getting file stats: {str(e)}")
        raise ValueError(f"Error getting file stats: {str(e)}")


def search_files_tool(llm_client, path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """Tool to search files with a given pattern and exclusion list."""
    try:
        update_spinner_status(f"Searching files in {path} for pattern: {pattern}")
        print(colored(f"Searching files in {path} for pattern: {pattern}", "green"))
        
        valid_path = resolve_path(path, allowed_directories)
        results = search_files(valid_path, pattern, exclude_patterns)
        
        update_spinner_status(f"Search complete. Found {len(results)} matches")
        return '\n'.join(results) if results else "No matches found"
    except Exception as e:
        update_spinner_status(f"Error searching files: {str(e)}")
        raise ValueError(f"Error searching files in {path}: {str(e)}")


def get_default_download_directory() -> str:
    """Get the default directory for downloaded files."""
    download_dir = os.path.join(DATA_DIRECTORY, 'files')
    os.makedirs(download_dir, exist_ok=True)
    return download_dir


def download_file(llm_client, url: str, filename: Optional[str] = None) -> str:
    """Download a file from a URL to the default download directory."""
    try:
        update_spinner_status(f"Preparing to download from: {url}")
        print(colored(f"Preparing to download from: {url}", "green"))
        
        # Validate and create download directory
        download_dir = os.path.join(allowed_directories[0], 'data', 'files')
        os.makedirs(download_dir, exist_ok=True)

        # Parse the URL
        parsed_url = urlparse(url)

        # Get filename from URL if not provided
        if not filename:
            # Try to get filename from URL path
            path = unquote(parsed_url.path)  # Handle URL-encoded paths
            filename = os.path.basename(path)

            # If no filename in path, use a default name
            if not filename or filename == '/':
                filename = 'downloaded_file'

        update_spinner_status("Downloading file...")
        # Download the file with timeout to get Content-Type
        with timeout(60):
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Get file extension from Content-Type header
            content_type = response.headers.get('Content-Type', '')
            extension = ''
            if content_type:
                update_spinner_status("Determining file type...")
                # Use mimetypes to guess extension
                extension = mimetypes.guess_extension(
                    content_type.partition(';')[0].strip())
                if not extension:
                    # Fallback for common types
                    content_type_map = {
                        'application/pdf': '.pdf',
                        'application/json': '.json',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'application/zip': '.zip',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                        'application/vnd.ms-excel': '.xls',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                        'text/csv': '.csv'
                    }
                    extension = content_type_map.get(
                        content_type.partition(';')[0].strip(), '')

            # Handle filename and extension properly
            if extension:
                # Split filename into base and existing extension
                base_name, existing_ext = os.path.splitext(filename)

                # Only replace extension if:
                # 1. No existing extension, or
                # 2. Existing extension doesn't match the content type
                if not existing_ext or existing_ext.lower() != extension.lower():
                    filename = f"{base_name}{extension}"

            # Validate filename
            if not re.match(r'^[\w\-\. ]+$', filename):
                raise ValueError(
                    "Invalid filename - only alphanumeric, dash, dot and space characters allowed")

            # Full path to save file
            save_path = os.path.join(download_dir, filename)

            update_spinner_status(f"Saving file as: {filename}")
            # Write file in chunks to handle large files
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Set file permissions
        os.chmod(save_path, FILESYSTEM_PERMISSIONS)

        update_spinner_status("File downloaded successfully")
        print(colored("File downloaded successfully", "green"))
        return f"The file `{filename}` has been successfully downloaded to {save_path}"

    except TimeoutError:
        update_spinner_status("Download timed out")
        raise ValueError("Download timed out after 60 seconds")
    except requests.RequestException as e:
        update_spinner_status(f"Download error: {str(e)}")
        raise ValueError(f"Error downloading file: {str(e)}")
    except Exception as e:
        update_spinner_status(f"Error saving file: {str(e)}")
        raise ValueError(f"Error saving downloaded file: {str(e)}")


def execute(llm_client=None, **kwargs):
    """
    Execute file operations with consolidated functions and improved error handling.

    Args:
        llm_client: Optional OpenAI client for LLM operations
        **kwargs: Operation-specific parameters including:
            - operation: The file operation to perform
            - path/paths: File or directory path(s)
            - content: Content to write
            - edits: List of text edits
            - url: Download URL
            - pattern: Search pattern
            - source/destination: Paths for move operations

    Returns:
        dict: Operation result with success/failure status
    """
    try:
        update_spinner_status("Starting file operations...")
        print(colored("Starting file operations...", "green"))
        
        # Convert single operation to list format for unified handling
        operations = kwargs.get('operations', [])
        if not operations and 'operation' in kwargs:
            # Convert single operation to list format
            operations = [kwargs]

        if not operations:
            raise ValueError("No operations specified")

        results = []
        overall_success = True

        # Process each operation
        for i, op in enumerate(operations, 1):
            try:
                operation = op.get('operation')
                if not operation:
                    raise ValueError("Operation parameter is required")

                rationale = op.get('rationale', 'No rationale provided')
                update_spinner_status(f"Operation {i}/{len(operations)}: {operation}")
                print(colored(f"Executing {operation} with rationale: {rationale}", "cyan"))

                # Define operation handlers
                operation_handlers = {
                    'read_file': lambda: read_file(llm_client, op['path']),
                    'read_multiple_files': lambda: read_multiple_files(llm_client, op['paths']),
                    'write_file': lambda: write_file(llm_client, op['path'], op['content']),
                    'edit_file': lambda: edit_file(llm_client, op['path'], op['edits'], op.get('dryRun', False)),
                    'create_directory': lambda: create_directory(llm_client, op['path']),
                    'list_directory': lambda: list_directory(llm_client, op['path']),
                    'directory_tree': lambda: directory_tree(llm_client, op['path']),
                    'move_file': lambda: move_file(llm_client, op['source'], op['destination']),
                    'download_file': lambda: download_file(llm_client, op['url'], op.get('filename')),
                    'search_files': lambda: search_files(op['path'], op['pattern'], op.get('excludePatterns')),
                    'get_file_info': lambda: get_file_stats(op['path'], format='str')
                }

                if operation not in operation_handlers:
                    raise ValueError(f"Unknown operation: {operation}")

                result = operation_handlers[operation]()
                update_spinner_status(f"Operation {operation} completed successfully")
                results.append({
                    "operation": operation,
                    "result": result,
                    "success": True,
                    "rationale": rationale
                })

            except Exception as e:
                error_message = f"Error in {op.get('operation', 'unknown')}: {str(e)}"
                update_spinner_status(error_message)
                print(colored(error_message, "red"))
                results.append({
                    "operation": op.get('operation', 'unknown'),
                    "result": error_message,
                    "success": False,
                    "rationale": op.get('rationale', 'No rationale provided')
                })
                overall_success = False

        # Return single result for single operation, list for multiple
        if len(results) == 1:
            return {
                "result": results[0]["result"],
                "follow_on_instructions": [],
                "rationale": results[0]["rationale"],
                "success": results[0]["success"],
                "direct_stream": True
            }
        else:
            return {
                "result": results,
                "follow_on_instructions": [],
                "success": overall_success,
                "direct_stream": True
            }

    except Exception as e:
        error_message = f"Error in operation execution: {str(e)}"
        print(colored(error_message, "red"))
        return {
            "result": error_message,
            "follow_on_instructions": [],
            "error": True,
            "direct_stream": False,
            "success": False
        }


TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_operations",
        "description": "A secure tool for performing various file system operations including reading, writing, editing files, managing directories, and downloading files from the web.\n\n Important: Supports multiple operations in a single call for related tasks like create directory and move files. Eg \"operations\": [\n        {\n            \"operation\": \"create_directory\",\n            \"path\": \"/data/files/new_folder\"\n        },\n        {\n            \"operation\": \"move_file\",\n            \"source\": \"/data/files/document.md\",\n            \"destination\": \"/data/files/new_folder/renamed.md\"\n        }\n    ]",
        "parameters": {
            "type": "object",
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": "A short comment explaining you rationale and intent for using this operation, eg using write_file to create new.txt as instructed by user"
                },
                "operations": {
                    "type": "array",
                    "description": "List of operations to perform in sequence. Use this for related operations like creating a directory and moving files.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": [
                                    "read_file",
                                    "read_multiple_files",
                                    "write_file",
                                    "edit_file",
                                    "create_directory",
                                    "list_directory",
                                    "directory_tree",
                                    "move_file",
                                    "download_file",
                                    "search_files",
                                    "get_file_info"
                                ]
                            },
                            "path": {
                                "type": "string",
                                "description": "The path to the file or directory involved in the operation."
                            },
                            "paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of paths for operations that require multiple files."
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to write to a file."
                            },
                            "edits": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "oldText": {
                                            "type": "string",
                                            "description": "Text to search for - must match exactly."
                                        },
                                        "newText": {
                                            "type": "string",
                                            "description": "Text to replace with."
                                        }
                                    },
                                    "required": ["oldText", "newText"]
                                },
                                "description": "A list of edits to apply to a file."
                            },
                            "url": {
                                "type": "string",
                                "description": (
                                    "The full URL of the file to download. Must include the protocol (http/https)."
                                    "Example: 'https://example.com/report.pdf'. Files are saved to the /data/files/ directory. Use the `filename` parameter to rename the downloaded file."
                                )
                            },
                            "filename": {
                                "type": "string",
                                "description": (
                                    "Optional custom filename for the downloaded file. If not provided, the filename "
                                    "will be extracted from the URL. Must only contain alphanumeric characters, "
                                    "dashes, dots, and spaces. Example: 'annual_report_2023.pdf'"
                                )
                            },
                            "dryRun": {
                                "type": "boolean",
                                "default": False,
                                "description": "Preview changes using git-style diff format."
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern for file operations."
                            },
                            "excludePatterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude from search results."
                            },
                            "source": {
                                "type": "string",
                                "description": "Source path for move operations (absolute path)."
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination path for move operations (absolute path)."
                            }
                        },
                        "required": ["operation"]
                    }
                }
            }
        }
    },
    "direct_stream": False
}