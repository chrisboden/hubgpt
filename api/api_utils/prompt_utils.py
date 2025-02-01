# api/utils/prompt_utils.py

import os
import re
import glob
import json
from datetime import datetime
import frontmatter
from typing import Dict, List, Any, Optional
from .. import config
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.advisors import AdvisorModel
from ..models.users import User
from .user_file_utils import get_user_file_content
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def get_workspace_root():
    """Get the workspace root directory."""
    return os.getcwd()

def get_full_path(file_path):
    """
    Convert a relative file path to an absolute path based on the current working directory.
    
    Args:
        file_path (str): Relative file path to convert
    
    Returns:
        str: Absolute file path
    """
    # Join the current working directory with the relative file path to get the absolute path
    return os.path.join(os.getcwd(), file_path)

def include_directory_content(match, depth=5, file_delimiter=None):
    """
    Recursively include contents of files matching a directory pattern.
    """
    if depth <= 0:
        return "[ERROR: Maximum inclusion depth reached]"
    
    dir_pattern = match.group(1).strip()
    full_dir_pattern = get_full_path(dir_pattern)
    
    try:
        matching_files = glob.glob(full_dir_pattern)
        if not matching_files:
            return f"[ERROR: No files found matching {dir_pattern}]"
        
        contents = []
        for file_path in matching_files:
            with open(file_path, 'r') as f:
                content = f.read()
            content = process_inclusions(content, depth - 1)
            
            # Simple consistent delimiter format
            filename = os.path.basename(file_path)
            delimiter = f"\n\n---------- {filename} ------------\n\n"
            contents.append(f"{delimiter}{content}")
        
        return "\n".join(contents)
    except Exception as e:
        return f"[ERROR: Failed to process directory {dir_pattern}: {str(e)}]"

def include_file_content(match, depth=5):
    """
    Include contents of a specific file with support for nested inclusions.
    
    Args:
        match (re.Match): Regex match object containing file path
        depth (int): Maximum recursion depth for nested inclusions
    
    Returns:
        str: File contents or error message
    """
    # Check if the maximum depth has been reached
    if depth <= 0:
        return "[ERROR: Maximum inclusion depth reached]"
    
    # Extract and convert the file path to an absolute path
    file_to_include = match.group(1).strip()
    full_file_path = get_full_path(file_to_include)
    try:
        # Read the content of the file
        with open(full_file_path, 'r') as f:
            content = f.read()
        # Process any nested inclusions in the file content
        return process_inclusions(content, depth - 1)
    except FileNotFoundError:
        # Return an error message if the file is not found
        return f"[ERROR: File {file_to_include} not found]"

def get_current_datetime(match):
    """
    Generate current datetime string with optional custom formatting.
    
    Args:
        match (re.Match): Regex match object containing optional format string
    
    Returns:
        str: Formatted current datetime or error message
    """
    # Extract the format string from the match object, default to "%Y-%m-%d %H:%M:%S" if not provided
    format_string = match.group(1).strip() if match.group(1) else "%Y-%m-%d %H:%M:%S"
    try:
        # Return the current datetime formatted according to the format string
        return datetime.now().strftime(format_string)
    except Exception as e:
        # Return an error message if the format string is invalid
        return f"[ERROR: Invalid datetime format: {format_string}]"

def process_file_tag(match: re.Match, user: Optional[User] = None, db: Optional[Session] = None) -> str:
    """Process a file inclusion tag, handling both legacy file paths and user-specific files."""
    file_path = match.group(1)
    logger.info(f"Processing file inclusion: path={file_path}, user={user.id if user else None}")
    
    try:
        # First try user-specific file access
        if user and db:
            logger.info("Attempting user-specific file access")
            try:
                content = get_user_file_content(file_path, user, db)
                logger.info(f"Successfully read user file: length={len(content)}")
                return content
            except Exception as e:
                logger.warning(f"User file access failed: {str(e)}")
                # Fall through to legacy path handling
        
        # Legacy path handling
        logger.info("Attempting legacy file access")
        abs_path = os.path.join(get_workspace_root(), file_path)
        if not os.path.exists(abs_path):
            logger.error(f"File not found: path={abs_path}")
            return f"[Error: File not found: {file_path}]"
            
        with open(abs_path, 'r') as f:
            content = f.read().strip()
            logger.info(f"Successfully read legacy file: length={len(content)}")
            return content
            
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return f"[Error reading file {file_path}: {str(e)}]"

def process_dir_tag(match: str, user: Optional[User] = None, db: Optional[Session] = None) -> str:
    """Process a directory inclusion tag, handling user-specific paths"""
    # Extract directory pattern from tag
    dir_pattern = match.group(1)
    
    if not user or not db:
        # If no user context, use legacy directory handling
        try:
            base_dir = Path("files")
            if not Path(dir_pattern).is_absolute():
                pattern_path = base_dir / dir_pattern
            else:
                pattern_path = Path(dir_pattern)
                
            # Get all matching files
            matching_files = []
            for file_path in Path(pattern_path.parent).glob(pattern_path.name):
                if file_path.is_file():
                    matching_files.append(file_path)
                    
            if not matching_files:
                return f"[No files found matching pattern {dir_pattern}]"
                
            # Combine contents of all matching files
            contents = []
            for file_path in sorted(matching_files):
                try:
                    contents.append(f"=== {file_path.name} ===\n{file_path.read_text()}")
                except Exception as e:
                    contents.append(f"[Error reading {file_path.name}: {str(e)}]")
                    
            return "\n\n".join(contents)
            
        except Exception as e:
            return f"[Error processing directory {dir_pattern}: {str(e)}]"
            
    try:
        # Query database for matching files
        from ..models.user_files import UserFile
        files = db.query(UserFile).filter(
            UserFile.user_id == user.id,
            UserFile.file_path.like(dir_pattern.replace('*', '%'))
        ).all()
        
        if not files:
            return f"[No files found matching pattern {dir_pattern}]"
            
        # Combine contents of all matching files
        contents = []
        for file in sorted(files, key=lambda f: f.file_path):
            try:
                content = get_user_file_content(db, user.id, file.file_path, check_access=True)
                contents.append(f"=== {file.file_path} ===\n{content}")
            except Exception as e:
                contents.append(f"[Error reading {file.file_path}: {str(e)}]")
                
        return "\n\n".join(contents)
        
    except Exception as e:
        return f"[Error processing directory {dir_pattern}: {str(e)}]"

def process_inclusions(content: str, user: Optional[User] = None, db: Optional[Session] = None) -> str:
    """Process all file and directory inclusion tags in content"""
    # Process datetime inclusions
    content = re.sub(
        r'<\$datetime(?:\:(.*?))?\$>',
        get_current_datetime,
        content
    )
    
    # Process file inclusions
    content = re.sub(
        r'<\$file:(.*?)\$>',
        lambda m: process_file_tag(m, user, db),
        content
    )
    
    # Process directory inclusions
    content = re.sub(
        r'<\$dir:(.*?)\$>',
        lambda m: process_dir_tag(m, user, db),
        content
    )
    
    return content

def parse_markdown_messages(content: str, user: Optional[User] = None, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Parse markdown content into a structured list of messages.
    
    Key Features:
    - Supports explicit role markers (::role::)
    - First content block treated as system message
    - Handles metadata in blockquote format
    - Processes file inclusions within message content
    
    Args:
        content (str): Markdown content to parse
        user (Optional[User]): User context for file access
        db (Optional[Session]): Database session
    
    Returns:
        List[Dict[str, Any]]: Parsed messages with roles and content
    """
    # Split the content by role markers
    message_pattern = r'\n::([\w-]+)::\n'
    message_blocks = re.split(message_pattern, content.strip())
    messages = []
    
    # If the first block has content, treat it as a system message
    if message_blocks[0].strip():
        messages.append({
            "role": "system",
            "content": process_inclusions(message_blocks[0].strip(), user, db)
        })
        message_blocks = message_blocks[1:]
    
    # Process each pair of role and content
    for i in range(0, len(message_blocks), 2):
        if i + 1 >= len(message_blocks):
            break
            
        role = message_blocks[i].strip().lower()
        content = message_blocks[i + 1].strip()
        
        message = {"role": role}
        
        # Look for metadata in blockquote format
        metadata_pattern = r'^>\s*(.+?)\s*\n\n'
        metadata_match = re.match(metadata_pattern, content, re.DOTALL)
        
        if metadata_match:
            metadata_lines = metadata_match.group(1).split('\n')
            metadata = {}
            # Parse each line of metadata
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            # Update the message with the parsed metadata
            message.update(metadata)
            # Remove the metadata from the content
            content = content[metadata_match.end():].strip()
        
        # Process any file inclusions in the content
        message["content"] = process_inclusions(content, user, db)
        messages.append(message)
    
    return messages

def load_advisor_data(advisor_id: str, user: Optional[User] = None, db: Optional[Session] = None) -> dict:
    """
    Load advisor data from the database and process any inclusions in the messages.
    
    Args:
        advisor_id (str): The ID of the advisor to load
        user (Optional[User]): User context for file access
        db (Optional[Session]): Database session
        
    Returns:
        dict: The processed advisor data
        
    Raises:
        HTTPException: If advisor not found or error processing data
    """
    logger.info(f"Loading advisor data: advisor_id={advisor_id}, user={user.id if user else None}")
    
    # Get database session if not provided
    if not db:
        db = next(get_db())
        
    # Load advisor from database
    advisor = db.query(AdvisorModel).filter(AdvisorModel.id == advisor_id).first()
    if not advisor:
        logger.error(f"Advisor not found: advisor_id={advisor_id}")
        raise HTTPException(status_code=404, detail="Advisor not found")
        
    logger.info(f"Found advisor: name={advisor.name}")
        
    # Convert to dict for modification
    advisor_data = {
        "id": advisor.id,
        "name": advisor.name,
        "description": advisor.description,
        "model": advisor.model,
        "temperature": advisor.temperature,
        "max_tokens": advisor.max_tokens,
        "stream": advisor.stream,
        "gateway": advisor.gateway,
        "tools": advisor.tools or [],
        "top_p": advisor.top_p,
        "frequency_penalty": advisor.frequency_penalty,
        "presence_penalty": advisor.presence_penalty,
        "messages": []
    }
    
    # Process inclusions in each message with database session
    for message in advisor.messages:
        logger.info(f"Processing message: role={message['role']}")
        try:
            processed_content = process_inclusions(message["content"], user=user, db=db)
            logger.info(f"Successfully processed message content: length={len(processed_content)}")
            processed_message = {
                "role": message["role"],
                "content": processed_content
            }
            if "name" in message:
                processed_message["name"] = message["name"]
            advisor_data["messages"].append(processed_message)
        except Exception as e:
            logger.error(f"Error processing message inclusions: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing message inclusions: {str(e)}")
        
    return advisor_data

def load_prompt(advisor_data: Dict[str, Any], conversation_history: List[Dict[str, str]], 
               max_depth: int = 5, file_delimiter: str = None) -> List[Dict[str, str]]:
    """
    Prepare prompt messages by incorporating conversation history.
    
    Key Features:
    - Replaces conversation history placeholder in messages
    - Supports dynamic message content generation
    
    Args:
        advisor_data (Dict[str, Any]): Advisor configuration
        conversation_history (List[Dict[str, str]]): Previous conversation messages
        max_depth (int, optional): Maximum recursion depth for inclusions
        file_delimiter (str, optional): Delimiter for multiple file contents
    
    Returns:
        List[Dict[str, str]]: Processed messages ready for LLM
    """
    # Convert the conversation history to a string
    conversation_history_str = "\n".join([f"{msg['role']}: {msg['content']}" 
                                        for msg in conversation_history])

    messages = advisor_data["messages"]
    # Replace the conversation history placeholder in each message
    for message in messages:
        if '<$conversation_history$>' in message["content"]:
            message["content"] = message["content"].replace(
                '<$conversation_history$>', 
                conversation_history_str
            )

    return messages

def get_available_advisors() -> List[str]:
    """
    Retrieve a list of available advisors from the advisors directory.
    
    Scans for both JSON and Markdown files, converting filenames to readable advisor names.
    
    Returns:
        List[str]: Names of available advisors
    """
    advisors_dir = "advisors"
    # List all files in the advisors directory that end with .json or .md
    advisor_files = [
        f for f in os.listdir(advisors_dir) 
        if f.endswith(('.json', '.md'))
    ]
    # Convert filenames to advisor names by replacing underscores with spaces
    return [os.path.splitext(f)[0].replace('_', ' ') for f in advisor_files]