# utils/chat_utils.py

import os
import json
import logging
import uuid
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

class ChatState:
    """Class to manage chat state without Streamlit dependencies"""
    def __init__(self):
        self.chat_history = []
        self.tool_call_args = ""
        self.last_tool_call_id = ""
        self.last_tool_name = ""
        self.save_success = False
        self.follow_on_instruction = None
        self.process_follow_on = False

# Global chat state instance
chat_state = ChatState()

def initialize_session_state():
    """
    Initialize chat state variables for chat management.
    Returns the chat state instance.
    """
    global chat_state
    chat_state = ChatState()
    return chat_state

def load_chat_history(chat_history_path):
    """
    Load chat history from a JSON file.
    
    Args:
        chat_history_path (str): File path to the chat history JSON file
    
    Returns:
        list: Loaded chat history or an empty list if file doesn't exist
    """
    if os.path.exists(chat_history_path):
        try:
            with open(chat_history_path, 'r') as chat_file:
                return json.load(chat_file)
        except Exception as e:
            logger.error(f"Error loading chat history: {e}")
            return []
    else:
        return []

def save_chat_history(chat_history, chat_history_path):
    """
    Save chat history to a JSON file.
    
    Args:
        chat_history (list): List of chat messages to save
        chat_history_path (str): Destination file path for saving chat history
    
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        with open(chat_history_path, 'w') as chat_file:
            json.dump(chat_history, chat_file, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving chat history: {e}")
        return False

def archive_chat_history(chat_history_path, advisors_dir, advisor_filename):
    """
    Archive the current chat history with a unique identifier.
    
    Args:
        chat_history_path (str): Path to the current chat history file
        advisors_dir (str): Directory containing advisor files
        advisor_filename (str): Name of the current advisor file
    
    Returns:
        tuple: (bool, str) - (success status, message)
    """
    archive_dir = os.path.join(advisors_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    if os.path.exists(chat_history_path):
        try:
            # Generate a unique short identifier for the archive
            short_uuid = uuid.uuid4().hex[:6]
            advisor_base = os.path.splitext(advisor_filename)[0]
            archived_filename = f"{advisor_base}_{short_uuid}.json"
            archived_path = os.path.join(archive_dir, archived_filename)

            # Copy the current chat history to the archive
            shutil.copy2(chat_history_path, archived_path)
            logger.info(f"Chat history archived as {archived_filename}")
            return True, f"Chat history archived as {archived_filename}"
        except Exception as e:
            error_msg = f"Failed to archive chat history: {e}"
            logger.error(error_msg)
            return False, error_msg
    return False, "No chat history to archive"

def clear_chat_history(chat_history_path):
    """
    Clear the contents of the chat history file.
    
    Args:
        chat_history_path (str): Path to the chat history file to clear
    
    Returns:
        bool: True if clear was successful, False otherwise
    """
    try:
        if os.path.exists(chat_history_path):
            with open(chat_history_path, 'w') as chat_file:
                json.dump([], chat_file, indent=2)
            return True
        return False
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return False
