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
    return os.path.join(os.getcwd(), file_path)

def include_directory_content(match, depth=5, file_delimiter=None):
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
            content = process_inclusions(content, depth - 1, file_delimiter)
            if file_delimiter is not None:
                contents.append(f"{file_delimiter.format(filename=os.path.basename(file_path))}\n{content}")
            else:
                contents.append(content)
        
        return "\n".join(contents)
    except Exception as e:
        return f"[ERROR: Failed to process directory {dir_pattern}: {str(e)}]"

def include_file_content(match, depth=5):
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
    format_string = match.group(1).strip() if match.group(1) else "%Y-%m-%d %H:%M:%S"
    try:
        return datetime.now().strftime(format_string)
    except Exception as e:
        return f"[ERROR: Invalid datetime format: {format_string}]"

def process_inclusions(content, depth, file_delimiter=None):
    content = re.sub(r'<\$datetime:(.*?)\$>', get_current_datetime, content)
    content = re.sub(r'<\$dir:(.*?)\$>', lambda m: include_directory_content(m, depth, file_delimiter), content)
    content = re.sub(r'<\$(.*?)\$>', lambda m: include_file_content(m, depth), content)
    return content

def parse_markdown_messages(content: str) -> List[Dict[str, Any]]:
    """Parse markdown content into messages array.
    - Content before any ::role:: marker is treated as system message
    - Other messages must be explicitly marked with ::role::
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
    """Load advisor data from either JSON or Markdown file"""
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
    """Load and process prompt with conversation history"""
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
    """Get list of available advisors from both .json and .md files"""
    advisors_dir = "advisors"
    advisor_files = [
        f for f in os.listdir(advisors_dir) 
        if f.endswith(('.json', '.md'))
    ]
    return [os.path.splitext(f)[0].replace('_', ' ') for f in advisor_files]