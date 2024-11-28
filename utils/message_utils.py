# utils/message_utils.py

import os
import json
from datetime import datetime
import uuid
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard

def save_snippet(message_content, source_type, source_name, snippets_dir):
    """
    Saves the provided message content as a snippet.

    Parameters:
    - message_content (str): The content of the message to save.
    - source_type (str): The type of the source ('advisor', 'notepad', or 'team').
    - source_name (str): The name of the advisor, notepad, or team.
    - snippets_dir (str): The directory where snippets.json is stored.
    """
    os.makedirs(snippets_dir, exist_ok=True)
    snippets_path = os.path.join(snippets_dir, "snippets.json")

    # Load existing snippets if they exist
    if os.path.exists(snippets_path):
        with open(snippets_path, 'r') as snippets_file:
            snippets = json.load(snippets_file)
    else:
        snippets = []

    # Create a new snippet according to the new JSON structure
    new_snippet = {
        "id": str(uuid.uuid4())[:8],  # Generate a short UUID
        "source": {
            "type": source_type,
            "name": source_name
        },
        "content": message_content,
        "timestamp": datetime.now().isoformat()
    }

    snippets.append(new_snippet)

    # Save updated snippets
    with open(snippets_path, 'w') as snippets_file:
        json.dump(snippets, snippets_file, indent=4)

    return new_snippet

def delete_message(messages, index):
    """Deletes a message from the messages list."""
    messages.pop(index)

def display_messages(messages, save_callback, delete_callback, copy_enabled=True, context_id=""):
    """Displays messages with optional save, copy, and delete buttons."""
    for idx, message in enumerate(messages):
        # Skip empty assistant messages
        if message['role'] == 'assistant' and message.get('content') == 'null':
            continue
            
        # Handle tool messages differently
        if message['role'] == 'tool':
            try:
                # Parse the content as JSON for better formatting
                tool_content = json.loads(message.get('content', '{}'))
                with st.expander(f"🔧 Tool Response: {message.get('name', 'Unknown Tool')}"):
                    st.json(tool_content)
                continue  # Skip the rest of the loop for tool messages
            except json.JSONDecodeError:
                # If content isn't JSON, display as regular text
                with st.expander(f"🔧 Tool Response: {message.get('name', 'Unknown Tool')}"):
                    st.text(message.get('content', ''))
                continue

        # Handle regular chat messages
        with st.chat_message(message['role']):
            st.markdown(message.get('content', ''))
            
            # Create columns for buttons
            if message['role'] == 'assistant':
                col1, col2, col3 = st.columns([0.2, 0.2, 0.2])
            else:  # user messages only get delete button
                col1, col2, col3 = st.columns([0.1, 0.1, 0.2])

            # Add styling
            st.write(''' <style>
                    .stChatMessage [data-testid="stVerticalBlock"] {
                        gap: 8px;
                        width:10em;
                    }
                    .stChatMessage .element-container + div button,
                    .stChatMessage .element-container + div iframe {
                        opacity: 0.025;
                    }
                    .stChatMessage:hover .element-container + div button,
                    .stChatMessage:hover .element-container + div iframe {
                        opacity: 1;
                    }
                    [data-testid="column"] {
                        height: 1.75em;
                        color-scheme: none !important;
                    }
                </style>''', unsafe_allow_html=True)

            # Show save and copy buttons only for assistant messages
            if message['role'] == 'assistant':
                with col1:
                    if st.button("💾", key=f"save_{context_id}_{idx}"):
                        save_callback(message["content"])
                with col2:
                    if copy_enabled:
                        st_copy_to_clipboard(message['content'])
            # Show delete button for all messages
            with col3:
                if st.button("🗑️", key=f"delete_{context_id}_{idx}"):
                    delete_callback(idx)
                    st.rerun()