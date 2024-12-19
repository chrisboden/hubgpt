# file_tool.py

import os
import json
import shutil
import re
import threading
from typing import List, Dict, Union, Optional
from difflib import unified_diff
from termcolor import colored
from contextlib import contextmanager

def expand_home(filepath: str) -> str:
    """Expand user home directory."""
    if filepath.startswith('~/') or filepath == '~':
        return os.path.expanduser(filepath)
    return filepath

# Constants
FILESYSTEM_PERMISSIONS = 0o644  # -rw-r--r--
DIRECTORY_PERMISSIONS = 0o755   # drwxr-xr-x
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Initialize allowed directories from environment variable or default to current directory
allowed_directories = os.environ.get('ALLOWED_DIRECTORIES', '.').split(':')
allowed_directories = [os.path.abspath(expand_home(d)) for d in allowed_directories]

# Custom exceptions
class TimeoutError(Exception):
    pass

# Utility functions

@contextmanager
def timeout(seconds: int = 30):
    timer = threading.Timer(seconds, lambda: (_ for _ in ()).throw(TimeoutError(f"Operation timed out after {seconds} seconds")))
    timer.start()
    try:
        yield
    finally:
        timer.cancel()

def check_file_size(path: str) -> None:
    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File size ({size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)")

def normalize_path(p: str) -> str:
    """
    Normalize path to a full, absolute path.
    
    Args:
        p (str): Input path
    
    Returns:
        str: Fully resolved, absolute path
    """
    # Expand user home directory
    expanded_path = os.path.expanduser(p)
    
    # Convert to absolute path
    absolute_path = os.path.abspath(expanded_path)
    
    # Normalize path (remove redundant separators, resolve .., etc.)
    normalized_path = os.path.normpath(absolute_path)
    
    return normalized_path

def validate_path(requested_path: str, allowed_directories: List[str]) -> str:
    """
    Validate that the requested path is within allowed directories.
    
    Args:
        requested_path (str): Path to validate
        allowed_directories (List[str]): List of allowed base directories
    
    Returns:
        str: Validated absolute path
    """
    # If a relative path is provided, prepend the first allowed directory
    if not os.path.isabs(requested_path):
        requested_path = os.path.join(allowed_directories[0], requested_path)
    
    expanded_path = expand_home(requested_path)
    absolute_path = os.path.abspath(expanded_path)

    # Check if path is within allowed directories
    is_allowed = any(
        absolute_path.startswith(os.path.abspath(dir)) 
        for dir in allowed_directories
    )

    if not is_allowed:
        raise ValueError(f"Access denied - path outside allowed directories: {absolute_path} not in {allowed_directories}")

    return absolute_path

def normalize_line_endings(text: str) -> str:
    return text.replace('\r\n', '\n')

def create_unified_diff(original_content: str, new_content: str, filepath: str = 'file') -> str:
    # Ensure consistent line endings for diff
    normalized_original = normalize_line_endings(original_content)
    normalized_new = normalize_line_endings(new_content)

    diff = '\n'.join(unified_diff(
        normalized_original.splitlines(keepends=True),
        normalized_new.splitlines(keepends=True),
        fromfile=f'{filepath} (original)',
        tofile=f'{filepath} (modified)'
    ))
    return diff

# file_operations.py

def apply_file_edits(filePath: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    try:
        # Check file size before processing
        check_file_size(filePath)
        
        # Read file content and normalize line endings
        with timeout(30):
            with open(filePath, 'r', encoding='utf-8') as file:
                content = normalize_line_endings(file.read())

        # Apply edits sequentially
        modified_content = content
        for edit in edits:
            normalized_old = normalize_line_endings(edit['oldText'])
            normalized_new = normalize_line_endings(edit['newText'])

            # If exact match exists, use it
            if normalized_old in modified_content:
                modified_content = modified_content.replace(normalized_old, normalized_new)
                continue

            # Otherwise, try line-by-line matching with flexibility for whitespace
            old_lines = normalized_old.split('\n')
            content_lines = modified_content.split('\n')
            match_found = False

            for i in range(len(content_lines) - len(old_lines) + 1):
                potential_match = content_lines[i:i + len(old_lines)]

                # Compare lines with normalized whitespace
                is_match = all(
                    old_line.strip() == content_line.strip() 
                    for old_line, content_line in zip(old_lines, potential_match)
                )

                if is_match:
                    # Preserve original indentation of first line
                    original_indent = re.match(r'^\s*', content_lines[i]).group(0) if content_lines[i] else ''
                    new_lines = [f"{original_indent}{line.lstrip()}" for line in normalized_new.split('\n')]

                    # For subsequent lines, try to preserve relative indentation
                    for j in range(1, len(new_lines)):
                        old_indent = re.match(r'^\s*', old_lines[j]).group(0) if j < len(old_lines) else ''
                        new_indent = re.match(r'^\s*', new_lines[j]).group(0)
                        if old_indent and new_indent:
                            relative_indent = len(new_indent) - len(old_indent)
                            new_lines[j] = f"{original_indent}{' ' * max(0, relative_indent)}{new_lines[j].lstrip()}"

                    content_lines[i:i + len(old_lines)] = new_lines
                    modified_content = '\n'.join(content_lines)
                    match_found = True
                    break

            if not match_found:
                raise ValueError(f"Could not find exact match for edit:\n{edit['oldText']}")

        # Create unified diff
        diff = create_unified_diff(content, modified_content, filePath)

        # Format diff with appropriate number of backticks
        num_backticks = 3
        while diff in ('`' * num_backticks):
            num_backticks += 1
        formatted_diff = f"{'`' * num_backticks}\ndiff\n{diff}\n{'`' * num_backticks}\n\n"

        if not dry_run:
            with timeout(30):
                with open(filePath, 'w', encoding='utf-8') as file:
                    file.write(modified_content)

        return formatted_diff
    
    except Exception as e:
        raise ValueError(f"Error applying edits to {filePath}: {str(e)}")

def search_files(root_path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
    exclude_patterns = exclude_patterns or []
    results = []

    def search(current_path: str):
        try:
            with timeout(5):  # Short timeout for directory listing
                entries = os.listdir(current_path)
        except (PermissionError, OSError, TimeoutError) as e:
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
                    validate_path(full_path, allowed_directories)
                except ValueError as e:
                    print(colored(str(e), "red"))
                    continue

                # Check if path matches any exclude pattern
                relative_path = os.path.relpath(full_path, root_path)
                should_exclude = any(
                    re.match(pattern.replace('*', '.*'), relative_path, re.IGNORECASE) 
                    for pattern in exclude_patterns
                )

                if should_exclude:
                    continue

                if pattern.lower() in entry.lower():
                    results.append(full_path)

                if os.path.isdir(full_path):
                    search(full_path)
            except Exception as e:
                print(colored(f"Error processing {entry}: {str(e)}", "red"))
                continue

    search(root_path)
    return results

def get_file_stats(filePath: str) -> Dict[str, Union[int, str, bool]]:
    try:
        with timeout(5):
            stats = os.stat(filePath)
            return {
                "size": stats.st_size,
                "created": stats.st_ctime,
                "modified": stats.st_mtime,
                "accessed": stats.st_atime,
                "is_directory": os.path.isdir(filePath),
                "is_file": os.path.isfile(filePath),
                "permissions": oct(stats.st_mode)[-3:]
            }
    except TimeoutError:
        raise ValueError(f"Timeout getting file stats for {filePath}")
    except Exception as e:
        raise ValueError(f"Error getting file stats: {str(e)}")

# Tool implementations
def read_file(llm_client, path: str) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)
        check_file_size(valid_path)
        
        with timeout(30):
            try:
                with open(valid_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except UnicodeDecodeError:
                # Fallback to binary mode for non-UTF-8 files
                with open(valid_path, 'rb') as file:
                    return file.read().decode('utf-8', errors='replace')
    except TimeoutError:
        raise ValueError(f"Timeout reading file {path}")
    except Exception as e:
        raise ValueError(f"Error reading file {path}: {str(e)}")

def read_multiple_files(llm_client, paths: List[str]) -> List[str]:
    results = []
    for file_path in paths:
        try:
            valid_path = validate_path(file_path, allowed_directories)
            check_file_size(valid_path)
            
            with timeout(30):
                try:
                    with open(valid_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except UnicodeDecodeError:
                    with open(valid_path, 'rb') as file:
                        content = file.read().decode('utf-8', errors='replace')
                results.append(f"{file_path}:\n{content}\n")
        except Exception as e:
            results.append(f"{file_path}: Error - {str(e)}")
    return results

def write_file(llm_client, path: str, content: str) -> str:
    """Thread-safe implementation of write_file."""
    try:
        valid_path = validate_path(path, allowed_directories)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(valid_path)), exist_ok=True)
        
        try:
            with timeout(30):
                with open(valid_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                # Set file permissions
                os.chmod(valid_path, FILESYSTEM_PERMISSIONS)
            return f"Successfully wrote to {path}"
        except TimeoutError:
            raise ValueError(f"Timeout writing to file {path}")
        except Exception as e:
            raise ValueError(f"Error writing to file {path}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error writing to file {path}: {str(e)}")

def edit_file(llm_client, path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)
        return apply_file_edits(valid_path, edits, dry_run)
    except Exception as e:
        raise ValueError(f"Error editing file {path}: {str(e)}")

def create_directory(llm_client, path: str) -> str:
    """Create a directory at the specified path."""
    try:
        # If path is relative, make it relative to the first allowed directory
        if not os.path.isabs(path):
            full_path = os.path.join(allowed_directories[0], path)
        else:
            full_path = path
            
        # Validate the path
        valid_path = validate_path(full_path, allowed_directories)
        
        print(f"Creating directory at: {valid_path}")  # Debug print
        
        with timeout(10):
            os.makedirs(valid_path, mode=DIRECTORY_PERMISSIONS, exist_ok=True)
        return f"Successfully created directory {valid_path}"
    except TimeoutError:
        raise ValueError(f"Timeout creating directory {path}")
    except Exception as e:
        raise ValueError(f"Error creating directory {path}: {str(e)}")

def list_directory(llm_client, path: str) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)
        with timeout(10):
            entries = os.listdir(valid_path)
            formatted = '\n'.join(
                f"[DIR]  {entry}" if os.path.isdir(os.path.join(valid_path, entry)) 
                else f"[FILE] {entry}"
                for entry in sorted(entries)  # Sort entries for consistent output
            )
        return formatted
    except TimeoutError:
        raise ValueError(f"Timeout listing directory {path}")
    except Exception as e:
        raise ValueError(f"Error listing directory {path}: {str(e)}")
    
def directory_tree(llm_client, path: str, max_depth: int = 20) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)

        def build_tree(current_path: str, current_depth: int = 0) -> Union[Dict[str, Union[str, List]], str]:
            if current_depth >= max_depth:
                return "[MAX DEPTH REACHED]"
            
            with timeout(5):  # Short timeout for each directory
                entries = os.listdir(current_path)
                result = []

                for entry in entries:
                    try:
                        full_path = os.path.join(current_path, entry)
                        entry_data = {
                            "name": entry,
                            "type": "directory" if os.path.isdir(full_path) else "file"
                        }

                        if entry_data["type"] == "directory":
                            entry_data["children"] = build_tree(full_path, current_depth + 1)

                        result.append(entry_data)
                    except Exception as e:
                        print(colored(f"Error processing {entry}: {str(e)}", "yellow"))
                        continue

                return result

        tree_data = build_tree(valid_path)
        return json.dumps(tree_data, indent=2)
    except TimeoutError:
        raise ValueError(f"Timeout building directory tree for {path}")
    except Exception as e:
        raise ValueError(f"Error building directory tree for {path}: {str(e)}")


def move_file(llm_client, source: str, destination: str) -> str:
    """Move a file from source to destination."""
    try:
        # Always use the first allowed directory as base for relative paths
        base_dir = allowed_directories[0]  # This will be root/temp
        
        # Resolve relative paths against base_dir
        full_source = os.path.join(base_dir, source) if not os.path.isabs(source) else source
        full_destination = os.path.join(base_dir, destination) if not os.path.isabs(destination) else destination
        
        print(f"Base directory: {base_dir}")  # Debug print
        print(f"Moving from: {full_source}")  # Debug print
        print(f"Moving to: {full_destination}")  # Debug print
        
        # Validate paths
        valid_source_path = validate_path(full_source, allowed_directories)
        valid_dest_path = validate_path(full_destination, allowed_directories)
        
        with timeout(30):
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(valid_dest_path), exist_ok=True)
            
            # Move the file
            shutil.move(valid_source_path, valid_dest_path)
            
        return f"Successfully moved {valid_source_path} to {valid_dest_path}"
    except TimeoutError:
        raise ValueError(f"Timeout moving file from {source} to {destination}")
    except Exception as e:
        raise ValueError(f"Error moving file from {source} to {destination}: {str(e)}")
    

def search_files_tool(llm_client, path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)
        results = search_files(valid_path, pattern, exclude_patterns)
        return '\n'.join(results) if results else "No matches found"
    except Exception as e:
        raise ValueError(f"Error searching files in {path}: {str(e)}")

def get_file_info(llm_client, path: str) -> str:
    try:
        valid_path = validate_path(path, allowed_directories)
        info = get_file_stats(valid_path)
        return '\n'.join(f"{key}: {value}" for key, value in info.items())
    except Exception as e:
        raise ValueError(f"Error getting file info for {path}: {str(e)}")


# Main execute function
def execute(llm_client=None, **kwargs):
    """
    Execute the file tool with the given parameters.
    
    Args:
        llm_client: Optional OpenAI client for LLM operations
        **kwargs: Operation-specific parameters
    
    Returns:
        dict: Result of the operation
    """

    try:
        global allowed_directories
        
        # Override allowed directories if provided in kwargs
        if 'allowed_directories' in kwargs:
            allowed_directories = [
                os.path.abspath(expand_home(dir)) 
                for dir in kwargs['allowed_directories']
            ]
        operation = kwargs.get('operation')
        if not operation:
            raise ValueError("Operation parameter is required")

        # Map operations to functions
        operations = {
            'read_file': lambda: read_file(llm_client, kwargs['path']),
            'read_multiple_files': lambda: read_multiple_files(llm_client, kwargs['paths']),
            'write_file': lambda: write_file(llm_client, kwargs['path'], kwargs['content']),
            'edit_file': lambda: edit_file(llm_client, kwargs['path'], kwargs['edits'], kwargs.get('dryRun', False)),
            'create_directory': lambda: create_directory(llm_client, kwargs['path']),
            'list_directory': lambda: list_directory(llm_client, kwargs['path']),
            'directory_tree': lambda: directory_tree(llm_client, kwargs['path']),
            'move_file': lambda: move_file(llm_client, kwargs['source'], kwargs['destination']),
            'search_files': lambda: search_files_tool(llm_client, kwargs['path'], kwargs['pattern'], kwargs.get('excludePatterns')),
            'get_file_info': lambda: get_file_info(llm_client, kwargs['path'])
        }

        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")

        # Extract rationale from kwargs
        rationale = kwargs.get('rationale')
        if not rationale:
            raise ValueError("Rationale parameter is required")

        print(colored(f"Executing {operation}...", "cyan"))
        print(colored(f"Rationale: {rationale}", "cyan"))

        result = operations[operation]()
        print(colored("Operation completed successfully", "green"))

        return {
            "result": result,
            "follow_on_instructions": [],
            "rationale": rationale  # Include rationale in the response
        }

    except Exception as e:
        error_message = f"Error in file_tool: {str(e)}"
        print(colored(error_message, "red"))
        return {
            "result": error_message,
            "follow_on_instructions": [],
            "error": True,
            "direct_stream": False
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_operations",
        "description": "A secure tool for performing various file system operations with timeout protection and size limits. ",
        "parameters": {
            "type": "object",
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": "A short comment explaining you rationale and intent for using this operation, eg using write_file to create new.txt as instructed by user"
                },
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
                        "search_files",
                        "get_file_info"
                    ],
                    "description": "The file operation to perform."
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
