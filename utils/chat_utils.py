# utils/chat_utils.py

import os
import json
import logging
import uuid
from datetime import datetime
import streamlit as st
import shutil

def initialize_session_state():
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

def load_chat_history(chat_history_path):
    if os.path.exists(chat_history_path):
        with open(chat_history_path, 'r') as chat_file:
            return json.load(chat_file)
    else:
        return []

def save_chat_history(chat_history, chat_history_path):
    with open(chat_history_path, 'w') as chat_file:
        json.dump(chat_history, chat_file, indent=2)

def archive_chat_history(chat_history_path, advisors_dir, advisor_filename):
    archive_dir = os.path.join(advisors_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    if os.path.exists(chat_history_path):
        try:
            short_uuid = uuid.uuid4().hex[:6]
            advisor_base = os.path.splitext(advisor_filename)[0]
            archived_filename = f"{advisor_base}_{short_uuid}.json"
            archived_path = os.path.join(archive_dir, archived_filename)

            shutil.copy2(chat_history_path, archived_path)
            st.success(f"Chat history archived as {archived_filename}.")
        except Exception as e:
            st.error(f"Failed to archive chat history: {e}")

def clear_chat_history(chat_history_path):
    if os.path.exists(chat_history_path):
        with open(chat_history_path, 'w') as chat_file:
            json.dump([], chat_file, indent=2)
