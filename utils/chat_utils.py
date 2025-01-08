# utils/chat_utils.py

import os
import json
import logging
import uuid
from datetime import datetime
import streamlit as st
import shutil

def initialize_session_state():
    """
    Initialize Streamlit session state variables for chat management.
    
    This function ensures that essential session state variables are 
    set up before starting a chat session. It provides default values 
    for tracking chat history, tool calls, and save status.
    
    Key Session State Variables:
    - chat_history: Stores the conversation messages
    - tool_call_args: Stores arguments for the most recent tool call
    - last_tool_call_id: Tracks the ID of the last tool call
    - last_tool_name: Stores the name of the last tool used
    - save_success: Indicates whether the last save operation was successful
    """
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'tool_call_args' not in st.session_state:
        st.session_state.tool_call_args = ""
    if 'last_tool_call_id' not in st.session_state:
        st.session_state.last_tool_call_id = ""
    if 'last_tool_name' not in st.session_state:
        st.session_state.last_tool_name = ""
    if 'save_success' not in st.session_state:
        st.session_state.save_success = False
    if 'follow_on_instruction' not in st.session_state:
        st.session_state.follow_on_instruction = None
    if 'process_follow_on' not in st.session_state:
        st.session_state.process_follow_on = False
    if 'spinner_placeholder' not in st.session_state:
        st.session_state.spinner_placeholder = st.empty()

def load_chat_history(chat_history_path):
    """
    Load chat history from a JSON file.
    
    Args:
        chat_history_path (str): File path to the chat history JSON file
    
    Returns:
        list: Loaded chat history or an empty list if file doesn't exist
    
    Handles potential file reading errors by returning an empty list
    if the specified file path does not exist.
    """
    if os.path.exists(chat_history_path):
        with open(chat_history_path, 'r') as chat_file:
            return json.load(chat_file)
    else:
        return []

def save_chat_history(chat_history, chat_history_path):
    """
    Save chat history to a JSON file.
    
    Args:
        chat_history (list): List of chat messages to save
        chat_history_path (str): Destination file path for saving chat history
    
    Writes the chat history with indentation for improved readability.
    """
    with open(chat_history_path, 'w') as chat_file:
        json.dump(chat_history, chat_file, indent=2)

def archive_chat_history(chat_history_path, advisors_dir, advisor_filename):
    """
    Archive the current chat history with a unique identifier.
    
    Args:
        chat_history_path (str): Path to the current chat history file
        advisors_dir (str): Directory containing advisor files
        advisor_filename (str): Name of the current advisor file
    
    Creates an archive of the chat history with:
    - A dedicated archive subdirectory
    - A unique filename using advisor name and short UUID
    - Error handling for archiving process
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
            st.success(f"Chat history archived as {archived_filename}.")
        except Exception as e:
            st.error(f"Failed to archive chat history: {e}")

def clear_chat_history(chat_history_path):
    """
    Clear the contents of the chat history file.
    
    Args:
        chat_history_path (str): Path to the chat history file to clear
    
    Resets the chat history file to an empty JSON array if the file exists.
    """
    if os.path.exists(chat_history_path):
        with open(chat_history_path, 'w') as chat_file:
            json.dump([], chat_file, indent=2)
