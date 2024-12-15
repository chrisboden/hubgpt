# utils/prompt_utils.py

import os
import re
import glob
import json
from datetime import datetime
import frontmatter
from datetime import datetime
from typing import Dict, List, Any

def get_full_path(file_path):
    """
    Convert a relative file path to an absolute path based on the current working directory.
    
    Args:
        file_path (str): Relative file path to convert
    
    Returns:
        str: Absolute file path
    """
    return os.path.join(os.getcwd(), file_path)

def include_directory_content(match, depth=5, file_delimiter=None):
    """
    Recursively include contents of files matching a directory pattern.
    
    Key Features:
    - Supports nested file inclusions with depth control
    - Handles potential errors in file reading
    - Optional file delimiter for separating multiple file contents
    
    Args:
        match (re.Match): Regex match object containing directory pattern
        depth (int): Maximum recursion depth for nested inclusions
        file_delimiter (str, optional): Format string for file name headers
    
    Returns:
        str: Concatenated file contents or error message
    """
    if depth <= 0:
        return "[ERROR: Maximum inclusion depth reached]"
    
    dir_pattern = match.group(1).strip()
    full_dir_pattern = get_full_path(dir_pattern)
    
    try:
        # Find all files matching the pattern
        matching_files = glob.glob(full_dir_pattern)
        if not matching_files:
            return f"[ERROR: No files found matching {dir_pattern}]"
        
        contents = []
        for file_path in matching_files:
            with open(file_path, 'r') as f:
                content = f.read()
            # Process any nested inclusions in the file content
            content = process_inclusions(content, depth - 1, file_delimiter)
            
            # Optionally add file delimiter
            if file_delimiter is not None:
                contents.append(f"{file_delimiter.format(filename=os.path.basename(file_path))}\n{content}")
            else:
                contents.append(content)
        
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
    if depth <= 0:
        return "[ERROR: Maximum inclusion depth reached]"
    
    file_to_include = match.group(1).strip()
    full_file_path = get_full_path(file_to_include)
    try:
        with open(full_file_path, 'r') as f:
            content = f.read()
        return process_inclusions(content, depth - 1)
    except FileNotFoundError:
        return f"[ERROR: File {file_to_include} not found]"

def get_current_datetime(match):
    """
    Generate current datetime string with optional custom formatting.
    
    Args:
        match (re.Match): Regex match object containing optional format string
    
    Returns:
        str: Formatted current datetime or error message
    """
    format_string = match.group(1).strip() if match.group(1) else "%Y-%m-%d %H:%M:%S"
    try:
        return datetime.now().strftime(format_string)
    except Exception as e:
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
    content = re.sub(r'<\$datetime:(.*?)\$>', get_current_datetime, content)
    content = re.sub(r'<\$dir:(.*?)\$>', lambda m: include_directory_content(m, depth, file_delimiter), content)
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
    # Split content by ::role:: markers
    message_pattern = r'\n::([\w-]+)::\n'
    message_blocks = re.split(message_pattern, content.strip())
    messages = []
    
    # First block is always treated as system message if it has content
    if message_blocks[0].strip():
        messages.append({
            "role": "system",
            "content": process_inclusions(message_blocks[0].strip(), depth=5)
        })
        message_blocks = message_blocks[1:]
    
    # Process remaining pairs of role and content
    for i in range(0, len(message_blocks), 2):
        if i + 1 >= len(message_blocks):
            break
            
        role = message_blocks[i].strip().lower()
        content = message_blocks[i + 1].strip()
        
        message = {"role": role}
        
        # Look for metadata in markdown blockquote format
        metadata_pattern = r'^>\s*(.+?)\s*\n\n'
        metadata_match = re.match(metadata_pattern, content, re.DOTALL)
        
        if metadata_match:
            metadata_lines = metadata_match.group(1).split('\n')
            metadata = {}
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            message.update(metadata)
            content = content[metadata_match.end():].strip()
        
        # Process any file inclusions in the content
        message["content"] = process_inclusions(content, depth=5)
        messages.append(message)
    
    return messages

def load_advisor_data(selected_advisor: str) -> Dict[str, Any]:
    """
    Load advisor configuration from either Markdown or JSON file.
    
    Supports two file formats:
    1. Markdown with frontmatter (preferred)
    2. JSON fallback
    
    Args:
        selected_advisor (str): Name of the advisor to load
    
    Returns:
        Dict[str, Any]: Advisor configuration with messages
    
    Raises:
        FileNotFoundError: If no advisor file is found
    """
    base_name = selected_advisor.replace(' ', '_')
    advisors_dir = "advisors"
    
    # Try markdown first
    md_path = os.path.join(advisors_dir, f"{base_name}.md")
    if os.path.exists(md_path):
        with open(md_path, 'r') as advisor_file:
            post = frontmatter.load(advisor_file)
            return {
                **post.metadata,
                "messages": parse_markdown_messages(post.content)
            }
    
    # Fall back to JSON
    json_path = os.path.join(advisors_dir, f"{base_name}.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as advisor_file:
            advisor_data = json.load(advisor_file)
            # Process any file inclusions in message content
            for message in advisor_data["messages"]:
                message["content"] = process_inclusions(message["content"], depth=5)
            return advisor_data
            
    raise FileNotFoundError(f"No advisor file found for {selected_advisor}")

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
    conversation_history_str = "\n".join([f"{msg['role']}: {msg['content']}" 
                                        for msg in conversation_history])

    messages = advisor_data["messages"]
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
    advisor_files = [
        f for f in os.listdir(advisors_dir) 
        if f.endswith(('.json', '.md'))
    ]
    return [os.path.splitext(f)[0].replace('_', ' ') for f in advisor_files]