from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import re

logger = logging.getLogger(__name__)

def get_chats_dir() -> Path:
    """Get the path to the chats directory"""
    return Path("advisors/chats")

def get_archive_dir() -> Path:
    """Get the path to the archive directory"""
    return Path("advisors/archive")

def load_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load a conversation from file"""
    try:
        # Check if this is an archived conversation
        if re.search(r'_[a-f0-9]{6}$', conversation_id):
            file_path = get_archive_dir() / f"{conversation_id}.json"
        else:
            file_path = get_chats_dir() / f"{conversation_id}.json"
            
        if not file_path.exists():
            return None
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Handle both formats: array of messages or conversation object
            if isinstance(data, list):
                # Convert array of messages to conversation object
                return {
                    "id": conversation_id,
                    "advisor_id": conversation_id.split('_')[0],
                    "messages": data,
                    "created_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            return data
    except Exception as e:
        logger.error(f"Error loading conversation {conversation_id}: {str(e)}")
        return None

def save_conversation(conversation_id: str, data: Dict[str, Any]) -> bool:
    """Save a conversation to file"""
    try:
        # Ensure required directories exist
        chats_dir = get_chats_dir()
        chats_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = chats_dir / f"{conversation_id}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving conversation {conversation_id}: {str(e)}")
        return False

def archive_conversation(conversation_id: str) -> Optional[str]:
    """Archive a conversation and return the new conversation ID"""
    try:
        # Load the current conversation
        data = load_conversation(conversation_id)
        if not data:
            return None
            
        # Generate a unique suffix
        suffix = uuid.uuid4().hex[:6]
        archive_id = f"{conversation_id}_{suffix}"
        
        # Ensure archive directory exists
        archive_dir = get_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to archive
        archive_path = archive_dir / f"{archive_id}.json"
        with open(archive_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        # Delete the current conversation file
        current_path = get_chats_dir() / f"{conversation_id}.json"
        if current_path.exists():
            current_path.unlink()
            
        return archive_id
    except Exception as e:
        logger.error(f"Error archiving conversation {conversation_id}: {str(e)}")
        return None

def create_blank_chat(advisor_id: str) -> Dict[str, Any]:
    """Create a new blank chat for an advisor"""
    return {
        "id": advisor_id,
        "advisor_id": advisor_id,
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation"""
    try:
        # Check if this is an archived conversation
        if re.search(r'_[a-f0-9]{6}$', conversation_id):
            # For archived chats, simply delete the file
            file_path = get_archive_dir() / f"{conversation_id}.json"
            if file_path.exists():
                file_path.unlink()
                return True
        else:
            # For current chats, delete and create a new blank one
            file_path = get_chats_dir() / f"{conversation_id}.json"
            if file_path.exists():
                file_path.unlink()
                # Create a new blank chat
                blank_chat = create_blank_chat(conversation_id)
                save_conversation(conversation_id, blank_chat)
                return True
        return False
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        return False 