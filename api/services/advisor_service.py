from pathlib import Path
import json
import yaml
import logging
import re
from typing import Dict, Any, Optional, List
from ..models.advisors import AdvisorCreate

logger = logging.getLogger(__name__)

def get_advisors_dir() -> Path:
    """Get the path to the advisors directory"""
    return Path("advisors")

def parse_markdown_advisor(content: str) -> Optional[Dict[str, Any]]:
    """Parse a markdown file with YAML frontmatter into advisor data"""
    try:
        # Split content into frontmatter and markdown
        parts = content.split('---', 2)
        if len(parts) >= 3:
            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(parts[1])
            markdown_content = parts[2].strip()
            
            # Convert frontmatter to advisor format
            advisor_data = {
                'model': frontmatter.get('model'),
                'temperature': float(frontmatter.get('temperature', 1.0)),
                'max_tokens': int(frontmatter.get('max_output_tokens', frontmatter.get('max_tokens', 1000))),
                'stream': bool(frontmatter.get('stream', True)),
                'top_p': float(frontmatter.get('top_p', 1.0)),
                'frequency_penalty': float(frontmatter.get('frequency_penalty', 0)),
                'presence_penalty': float(frontmatter.get('presence_penalty', 0)),
                'tools': frontmatter.get('tools', []),
                'messages': [
                    {
                        'role': 'system',
                        'content': markdown_content
                    }
                ]
            }
            return advisor_data
    except Exception as e:
        logger.error(f"Error parsing markdown advisor: {str(e)}")
    return None

def create_markdown_content(advisor: AdvisorCreate) -> str:
    """Create markdown content with YAML frontmatter from advisor data"""
    frontmatter = {
        'model': advisor.model,
        'temperature': advisor.temperature,
        'max_output_tokens': advisor.max_tokens,
        'top_p': advisor.top_p,
        'frequency_penalty': advisor.frequency_penalty,
        'presence_penalty': advisor.presence_penalty,
        'stream': advisor.stream,
        'tools': advisor.tools or []
    }
    
    # Remove None values
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
    
    # Get system message from messages array
    system_message = next((msg.content for msg in advisor.messages if msg.role == 'system'), '')
    
    return f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

{system_message}
"""

def create_json_content(advisor: AdvisorCreate) -> Dict[str, Any]:
    """Create JSON content from advisor data"""
    return {
        'model': advisor.model,
        'temperature': advisor.temperature,
        'max_tokens': advisor.max_tokens,
        'stream': advisor.stream,
        'top_p': advisor.top_p,
        'frequency_penalty': advisor.frequency_penalty,
        'presence_penalty': advisor.presence_penalty,
        'tools': advisor.tools,
        'messages': [msg.dict() for msg in advisor.messages]  # Convert Message objects to dicts
    }

def load_advisor(advisor_path: Path) -> Optional[Dict[str, Any]]:
    """Load an advisor from a file"""
    try:
        if advisor_path.suffix == '.json':
            with open(advisor_path, 'r') as f:
                try:
                    data = json.load(f)
                    # Validate required fields
                    required_fields = ['model', 'temperature', 'messages']
                    if not all(field in data for field in required_fields):
                        logger.error(f"Missing required fields in {advisor_path}")
                        return None
                    
                    # Ensure messages is a list with at least one system message
                    if not isinstance(data['messages'], list) or not any(
                        msg.get('role') == 'system' for msg in data['messages']
                    ):
                        logger.error(f"Invalid messages format in {advisor_path}")
                        return None
                    
                    # Add name from filename
                    data['name'] = advisor_path.stem
                    
                    # Ensure numeric fields are proper types
                    data['temperature'] = float(data['temperature'])
                    data['max_tokens'] = int(data.get('max_tokens', 1000))
                    data['stream'] = bool(data.get('stream', True))
                    
                    # Handle optional numeric fields
                    for field in ['top_p', 'frequency_penalty', 'presence_penalty']:
                        if field in data and data[field] is not None:
                            data[field] = float(data[field])
                    
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {advisor_path}: {str(e)}")
                    # Try to repair the file
                    try:
                        with open(advisor_path, 'r') as f:
                            content = f.read()
                        # Create a backup
                        backup_path = advisor_path.with_suffix('.json.bak')
                        with open(backup_path, 'w') as f:
                            f.write(content)
                        logger.info(f"Created backup of corrupted file: {backup_path}")
                        
                        # Try to fix common JSON issues
                        fixed_content = content.replace("'", '"')  # Replace single quotes
                        fixed_content = re.sub(r',\s*}', '}', fixed_content)  # Remove trailing commas
                        fixed_content = re.sub(r',\s*]', ']', fixed_content)
                        
                        # Try to parse the fixed content
                        data = json.loads(fixed_content)
                        logger.info(f"Successfully repaired JSON in {advisor_path}")
                        
                        # Save the fixed content
                        with open(advisor_path, 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        return data
                    except Exception as repair_error:
                        logger.error(f"Failed to repair JSON in {advisor_path}: {str(repair_error)}")
                        return None
                    
        elif advisor_path.suffix == '.md':
            with open(advisor_path, 'r') as f:
                content = f.read()
            data = parse_markdown_advisor(content)
            if data:
                data['name'] = advisor_path.stem
                return data
            
    except Exception as e:
        logger.error(f"Error loading advisor from {advisor_path}: {str(e)}")
    return None 