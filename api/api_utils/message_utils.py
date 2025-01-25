# api/utils/message_utils.py

import os
import json
from datetime import datetime
import uuid
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard

def save_snippet(message_content, source_type, source_name, snippets_dir):
    """
    Saves a message snippet to a JSON file with structured metadata.

    This function handles:
    - Creating the snippets directory if it doesn't exist
    - Loading existing snippets 
    - Generating a unique identifier for each snippet
    - Storing snippet details including source, content, and timestamp
    
    Args:
        message_content (str): The text content to be saved
        source_type (str): Origin type (e.g., 'advisor', 'notepad', 'team')
        source_name (str): Specific name of the source
        snippets_dir (str): Directory path for storing snippets
    
    Returns:
        dict: The newly created snippet with its metadata
    """
    # Ensure snippets directory exists
    os.makedirs(snippets_dir, exist_ok=True)
    snippets_path = os.path.join(snippets_dir, "snippets.json")

    # Load existing snippets, or start with an empty list
    if os.path.exists(snippets_path):
        with open(snippets_path, 'r') as snippets_file:
            snippets = json.load(snippets_file)
    else:
        snippets = []

    # Create a new snippet with comprehensive metadata
    new_snippet = {
        "id": str(uuid.uuid4())[:8],  # Short unique identifier
        "source": {
            "type": source_type,
            "name": source_name
        },
        "content": message_content,
        "timestamp": datetime.now().isoformat()  # ISO 8601 formatted timestamp
    }

    # Add the new snippet to the collection
    snippets.append(new_snippet)

    # Persist updated snippets to file
    with open(snippets_path, 'w') as snippets_file:
        json.dump(snippets, snippets_file, indent=4)

    return new_snippet

def delete_message(messages, index):
    """
    Removes a specific message from the messages list by its index.
    
    Args:
        messages (list): The list of message dictionaries
        index (int): The index of the message to remove
    """
    messages.pop(index)


def display_messages(messages, save_callback, delete_callback, copy_enabled=True, context_id="", show_tool_messages=False):
    """
    Renders messages in a Streamlit chat interface with interactive features.
    
    Args:
        messages (list): List of message dictionaries
        save_callback (callable): Function to handle saving messages
        delete_callback (callable): Function to handle deleting messages
        copy_enabled (bool): Whether to show copy button
        context_id (str): Unique identifier for the chat context
        show_tool_messages (bool): Whether to display tool messages in expanders (default: False)
    """
    for idx, message in enumerate(messages):
        # Skip empty assistant messages
        if message['role'] == 'assistant' and message.get('content') == 'null':
            continue
            
        # Special handling for tool response messages
        if message['role'] == 'tool':
            if not show_tool_messages:
                continue
                
            try:
                tool_content = json.loads(message.get('content', '{}'))
                # Special handling for make_artifact tool
                if message.get('name') == 'make_artifact' and 'artifact_html' in tool_content:
                    with st.chat_message("assistant"):
                        st.components.v1.html(
                            tool_content['artifact_html'],
                            height=400,
                            scrolling=True
                        )
                else:
                    # Standard tool response display in expander
                    with st.expander(f"Tool Response: {message.get('name', 'Unknown Tool')}"):
                        st.json(tool_content)
                continue
            except json.JSONDecodeError:
                with st.expander(f"Tool Response: {message.get('name', 'Unknown Tool')}"):
                    st.text(message.get('content', ''))
                continue
        
        # Handle regular messages
        with st.chat_message(message['role']):
            st.markdown(message.get('content', ''))
            
            # Create flexible column layout for action buttons
            if message['role'] == 'assistant':
                col1, col2, col3 = st.columns([0.2, 0.2, 0.2])
            else:  # Simplified layout for user messages
                col1, col2, col3 = st.columns([0.1, 0.1, 0.2])

            # Contextual button rendering
            if message['role'] == 'assistant':
                with col1:
                    if st.button("💾", key=f"save_{context_id}_{idx}"):
                        save_callback(message["content"])
                with col2:
                    if copy_enabled:
                        st_copy_to_clipboard(
                            message['content'], 
                            key=f"copy_{context_id}_{idx}"
                        )
            
            # Universal delete button
            with col3:
                if st.button("🗑️", key=f"delete_{context_id}_{idx}"):
                    delete_callback(idx)
                    st.rerun()