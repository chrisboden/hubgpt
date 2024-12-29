# file_tool.py

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


def expand_home(filepath: str) -> str:
    """Expand user home directory."""
    if filepath.startswith('~/') or filepath == '~':
        return os.path.expanduser(filepath)
    return filepath


# Constants
FILESYSTEM_PERMISSIONS = 0o644  # -rw-r--r--
DIRECTORY_PERMISSIONS = 0o755   # drwxr-xr-x
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Initialize base and data directories - FIXED THE ISSUE HERE
BASE_DIRECTORY = os.path.abspath(
    os.path.expanduser(os.environ.get('BASE_DIRECTORY', '.')))
DATA_DIRECTORY = os.path.join(BASE_DIRECTORY, 'data')
FILES_DIRECTORY = os.path.join(DATA_DIRECTORY, 'files')

# Create necessary directories
os.makedirs(DATA_DIRECTORY, mode=DIRECTORY_PERMISSIONS, exist_ok=True)
os.makedirs(FILES_DIRECTORY, mode=DIRECTORY_PERMISSIONS, exist_ok=True)

# The issue was here - we need to include the root directory for absolute paths
allowed_directories = [
    '/',  # Add root directory to allow absolute paths
    BASE_DIRECTORY,
    DATA_DIRECTORY,
    FILES_DIRECTORY
]

# Add any additional directories from environment variable
env_dirs = os.environ.get('ALLOWED_DIRECTORIES', '').split(':')
allowed_directories.extend([
    os.path.abspath(expand_home(d))
    for d in env_dirs
    if d and d != '.'
])

# Remove duplicates while preserving order
allowed_directories = list(dict.fromkeys(allowed_directories))

print(colored("BASE_DIRECTORY: " + BASE_DIRECTORY, "yellow"))
print(colored("DATA_DIRECTORY: " + DATA_DIRECTORY, "yellow"))
print(colored("FILES_DIRECTORY: " + FILES_DIRECTORY, "yellow"))
print(colored(f"Allowed directories: {allowed_directories}", "cyan"))

# Custom exceptions


class TimeoutError(Exception):
    pass

# Utility functions


@contextmanager
def timeout(seconds: int = 30):
    timer = threading.Timer(seconds, lambda: (_ for _ in ()).throw(
        TimeoutError(f"Operation timed out after {seconds} seconds")))
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def check_file_size(path: str) -> None:
    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        raise ValueError(
            f"File size ({size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)")


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


def resolve_path(path: str, allowed_directories: List[str]) -> str:
    """
    Resolve and validate a path against allowed directories.
    Handles path normalization and validation in one place.
    """
    try:
        # Strip BASE_DIRECTORY if it's included in the path
        if path.startswith(BASE_DIRECTORY):
            path = path[len(BASE_DIRECTORY):].lstrip('/')

        # Normalize path to ensure it's under /data/files
        if path.startswith('/'):
            path = path.lstrip('/')
            if not path.startswith('data/files/'):
                path = f"data/files/{path}"
        else:
            if not path.startswith('data/files/'):
                path = f"data/files/{path}"

        # Convert to absolute path relative to BASE_DIRECTORY
        full_path = os.path.join(BASE_DIRECTORY, path)
        
        # Normalize path (remove redundant separators, resolve .., etc.)
        normalized_path = os.path.abspath(full_path)

        # Validate against allowed directories
        if not any(
            os.path.commonpath([normalized_path, os.path.abspath(allowed_dir)]) == os.path.abspath(allowed_dir)
            for allowed_dir in allowed_directories
        ):
            raise ValueError(f"Access denied - path outside allowed directories: {normalized_path}")

        return normalized_path

    except Exception as e:
        raise ValueError(f"Error resolving path {path}: {str(e)}")


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
                modified_content = modified_content.replace(
                    normalized_old, normalized_new)
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
                    original_indent = re.match(
                        r'^\s*', content_lines[i]).group(0) if content_lines[i] else ''
                    new_lines = [
                        f"{original_indent}{line.lstrip()}" for line in normalized_new.split('\n')]

                    # For subsequent lines, try to preserve relative indentation
                    for j in range(1, len(new_lines)):
                        old_indent = re.match(
                            r'^\s*', old_lines[j]).group(0) if j < len(old_lines) else ''
                        new_indent = re.match(r'^\s*', new_lines[j]).group(0)
                        if old_indent and new_indent:
                            relative_indent = len(new_indent) - len(old_indent)
                            new_lines[j] = f"{original_indent}{' ' * max(0, relative_indent)}{new_lines[j].lstrip()}"

                    content_lines[i:i + len(old_lines)] = new_lines
                    modified_content = '\n'.join(content_lines)
                    match_found = True
                    break

            if not match_found:
                raise ValueError(
                    f"Could not find exact match for edit:\n{edit['oldText']}")

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


def read_file(llm_client, path: str) -> str:
    try:
        valid_path = resolve_path(path, allowed_directories)
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
        except Exception as e:
            results.append(f"{file_path}: Error - {str(e)}")
    return results


def write_file(llm_client, path: str, content: str) -> str:
    """Write content to a file, handling both absolute and relative paths."""
    try:
        print(colored(f"Writing file - Original path: {path}", "yellow"))

        # If path starts with /data, make it relative to BASE_DIRECTORY
        if path.startswith('/data'):
            relative_path = path[1:]  # Remove leading slash
            full_path = os.path.join(BASE_DIRECTORY, relative_path)
        else:
            full_path = resolve_path(path, allowed_directories)

        print(colored(f"Full resolved path: {full_path}", "yellow"))
        print(colored(
            f"Directory exists? {os.path.exists(os.path.dirname(full_path))}", "yellow"))

        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        print(colored(f"Directory created/verified", "yellow"))
        print(colored(f"Attempting to write file...", "yellow"))

        # Write the file
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)

        print(colored(f"File written successfully", "yellow"))
        print(colored(f"File exists? {os.path.exists(full_path)}", "yellow"))
        print(colored(
            f"File size: {os.path.getsize(full_path) if os.path.exists(full_path) else 'N/A'}", "yellow"))

        return f"Successfully wrote to {full_path}"
    except Exception as e:
        print(colored(f"Error in write_file: {str(e)}", "red"))
        raise ValueError(f"Error writing to file {path}: {str(e)}")


def edit_file(llm_client, path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    try:
        valid_path = resolve_path(path, allowed_directories)
        return apply_file_edits(valid_path, edits, dry_run)
    except Exception as e:
        raise ValueError(f"Error editing file {path}: {str(e)}")


def create_directory(llm_client, path: str) -> str:
    """Create a directory at the specified path."""
    try:
        # Resolve and validate the path
        valid_path = resolve_path(path, allowed_directories)

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
        valid_path = resolve_path(path, allowed_directories)
        with timeout(10):
            entries = os.listdir(valid_path)
            formatted = '\n'.join(
                f"[DIR]  {entry}" if os.path.isdir(os.path.join(valid_path, entry))
                else f"[FILE] {entry}"
                # Sort entries for consistent output
                for entry in sorted(entries)
            )
        return formatted
    except TimeoutError:
        raise ValueError(f"Timeout listing directory {path}")
    except Exception as e:
        raise ValueError(f"Error listing directory {path}: {str(e)}")


def directory_tree(llm_client, path: str, max_depth: int = 20) -> str:
    try:
        valid_path = resolve_path(path, allowed_directories)

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
                            entry_data["children"] = build_tree(
                                full_path, current_depth + 1)

                        result.append(entry_data)
                    except Exception as e:
                        print(
                            colored(f"Error processing {entry}: {str(e)}", "yellow"))

                return result

        return json.dumps(build_tree(valid_path), indent=2)
    except TimeoutError:
        raise ValueError(f"Timeout building directory tree for {path}")
    except Exception as e:
        raise ValueError(f"Error building directory tree for {path}: {str(e)}")


def move_file(llm_client, source: str, destination: str) -> str:
    try:
        # Resolve and validate both source and destination paths
        full_source = resolve_path(source, allowed_directories)
        full_destination = resolve_path(destination, allowed_directories)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(full_destination), exist_ok=True)

        # Move the file
        shutil.move(full_source, full_destination)

        return f"Successfully moved {full_source} to {full_destination}"
    except Exception as e:
        raise ValueError(
            f"Error moving file from {source} to {destination}: {str(e)}")


def search_files(root_path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
    # Resolve the root path
    valid_root_path = resolve_path(root_path, allowed_directories)

    exclude_patterns = exclude_patterns or []
    results = []

    def search(current_path: str):
        try:
            with timeout(5):  # Short timeout for directory listing
                entries = os.listdir(current_path)
        except (PermissionError, OSError, TimeoutError) as e:
            print(
                colored(f"Access error for {current_path}: {str(e)}", "yellow"))
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
                    results.append(full_path)

                if os.path.isdir(full_path):
                    search(full_path)
            except Exception as e:
                print(colored(f"Error processing {entry}: {str(e)}", "red"))
                continue

    search(valid_root_path)
    return results


def get_file_stats(filePath: str, format: str = 'dict') -> Union[Dict, str]:
    """
    Get file statistics in either dict or string format.
    Combines previous get_file_stats and get_file_info functions.
    """
    try:
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

            return info if format == 'dict' else '\n'.join(f"{k}: {v}" for k, v in info.items())
    except Exception as e:
        raise ValueError(f"Error getting file stats: {str(e)}")


def search_files_tool(llm_client, path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    try:
        valid_path = resolve_path(path, allowed_directories)
        results = search_files(valid_path, pattern, exclude_patterns)
        return '\n'.join(results) if results else "No matches found"
    except Exception as e:
        raise ValueError(f"Error searching files in {path}: {str(e)}")


def get_default_download_directory() -> str:
    """Get the default directory for downloaded files."""
    download_dir = os.path.join(BASE_DIRECTORY, 'data', 'files')
    os.makedirs(download_dir, exist_ok=True)
    return download_dir


def download_file(llm_client, url: str, filename: Optional[str] = None) -> str:
    try:
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

        # Download the file with timeout to get Content-Type
        with timeout(60):
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Get file extension from Content-Type header
            content_type = response.headers.get('Content-Type', '')
            extension = ''
            if content_type:
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

            # Write file in chunks to handle large files
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Set file permissions
        os.chmod(save_path, FILESYSTEM_PERMISSIONS)

        return f"The file `{filename}` has been successfully downloaded to {save_path}"

    except TimeoutError:
        raise ValueError("Download timed out after 60 seconds")
    except requests.RequestException as e:
        raise ValueError(f"Error downloading file: {str(e)}")
    except Exception as e:
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
        for op in operations:
            try:
                operation = op.get('operation')
                if not operation:
                    raise ValueError("Operation parameter is required")

                rationale = op.get('rationale', 'No rationale provided')
                print(
                    colored(f"Executing {operation} with rationale: {rationale}", "cyan"))

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
                results.append({
                    "operation": operation,
                    "result": result,
                    "success": True,
                    "rationale": rationale
                })

            except Exception as e:
                error_message = f"Error in {op.get('operation', 'unknown')}: {str(e)}"
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