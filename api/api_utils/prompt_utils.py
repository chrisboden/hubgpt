# api/utils/prompt_utils.py

import os
import re
import glob
import json
from datetime import datetime
import frontmatter
from typing import Dict, List, Any
from .. import config
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.advisors import AdvisorModel

logger = logging.getLogger(__name__)

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

def process_inclusions(content, depth, file_delimiter=None):
    """
    Process file and directory inclusions in text content.
    
    Handles multiple types of inclusions:
    - Datetime generation
    - Directory content inclusion
    - Individual file inclusion
    
    Args:
        content (str): Text content to process
        depth (int): Maximum recursion depth
        file_delimiter (str, optional): Delimiter for multiple file contents
    
    Returns:
        str: Processed content with inclusions resolved
    """
    # Replace datetime placeholders with the current datetime
    content = re.sub(r'<\$datetime:(.*?)\$>', get_current_datetime, content)
    # Replace directory inclusion placeholders with the directory content
    content = re.sub(r'<\$dir:(.*?)\$>', lambda m: include_directory_content(m, depth, file_delimiter), content)
    # Replace file inclusion placeholders with the file content
    content = re.sub(r'<\$(.*?)\$>', lambda m: include_file_content(m, depth), content)
    return content

def parse_markdown_messages(content: str) -> List[Dict[str, Any]]:
    """
    Parse markdown content into a structured list of messages.
    
    Key Features:
    - Supports explicit role markers (::role::)
    - First content block treated as system message
    - Handles metadata in blockquote format
    - Processes file inclusions within message content
    
    Args:
        content (str): Markdown content to parse
    
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
            "content": process_inclusions(message_blocks[0].strip(), depth=5)
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
        message["content"] = process_inclusions(content, depth=5)
        messages.append(message)
    
    return messages

def load_advisor_data(advisor_id: str) -> dict:
    """Load advisor data from database"""
    try:
        # Get database session
        db = next(get_db())
        
        # Query advisor
        advisor = db.query(AdvisorModel).filter(
            AdvisorModel.name == advisor_id
        ).first()
        
        if not advisor:
            raise FileNotFoundError(f"Advisor {advisor_id} not found")
            
        # Convert to dict
        return {
            "name": advisor.name,
            "description": advisor.description,
            "model": advisor.model,
            "temperature": advisor.temperature,
            "max_tokens": advisor.max_tokens,
            "stream": advisor.stream,
            "messages": advisor.messages,
            "gateway": advisor.gateway,
            "tools": advisor.tools,
            "top_p": advisor.top_p,
            "frequency_penalty": advisor.frequency_penalty,
            "presence_penalty": advisor.presence_penalty
        }
            
    except Exception as e:
        logger.error(f"Error loading advisor data: {str(e)}")
        raise

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