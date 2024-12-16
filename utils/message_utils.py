# utils/message_utils.py

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

def display_messages(messages, save_callback, delete_callback, copy_enabled=True, context_id=""):
    """
    Renders messages in a Streamlit chat interface with interactive features.
    
    Handles different message types (assistant, tool, user) with specialized rendering:
    - Tool messages are displayed in expandable sections
    - Assistant messages get save and copy buttons
    - All messages can be deleted
    
    Key Features:
    - Dynamic styling for hover effects
    - Conditional button rendering based on message role
    - Unique key generation for Streamlit components
    
    Args:
        messages (list): Collection of message dictionaries
        save_callback (callable): Function to save a message
        delete_callback (callable): Function to delete a message
        copy_enabled (bool, optional): Toggle copy functionality. Defaults to True.
        context_id (str, optional): Unique identifier for message context
    """
    for idx, message in enumerate(messages):
        # Skip empty assistant messages to prevent clutter
        if message['role'] == 'assistant' and message.get('content') == 'null':
            continue
            
        # Special handling for tool response messages
        if message['role'] == 'tool':
            try:
                # Attempt to parse tool content as JSON for structured display
                tool_content = json.loads(message.get('content', '{}'))
                with st.expander(f"Tool Response: {message.get('name', 'Unknown Tool')}"):
                    st.json(tool_content)
                continue  # Skip further processing for tool messages
            except json.JSONDecodeError:
                # Fallback to plain text if JSON parsing fails
                with st.expander(f"Tool Response: {message.get('name', 'Unknown Tool')}"):
                    st.text(message.get('content', ''))
                continue

        # Render chat messages with role-based styling
        with st.chat_message(message['role']):
            st.markdown(message.get('content', ''))
            
            # Create flexible column layout for action buttons
            if message['role'] == 'assistant':
                col1, col2, col3 = st.columns([0.2, 0.2, 0.2])
            else:  # Simplified layout for user messages
                col1, col2, col3 = st.columns([0.1, 0.1, 0.2])

            # Inject CSS for subtle, hover-activated button interactions
            st.write(''' <style>
                    .stChatMessage [data-testid="stVerticalBlock"] {
                        gap: 8px;
                        width:10em;
                    }
                    .stChatMessage .element-container + div button{
                        opacity: 0.025;
                        margin:8px;
                    }
                    .stChatMessage .element-container + div iframe {
                        opacity: 0.025;
                        height:52px!important;
                        width: 56px!important;
                    }
                    .stChatMessage:hover .element-container + div button{
                        opacity: 1;
                     }
                    .stChatMessage:hover .element-container + div iframe {
                        opacity: 1;
                        height:52px!important;
                        width:56px!important
                    }
                    [data-testid="column"] {
                        height: 1.75em;
                        color-scheme: none !important;
                    }
                </style>''', unsafe_allow_html=True)

            # Contextual button rendering
            if message['role'] == 'assistant':
                with col1:
                    # Save button with unique key
                    if st.button("💾", key=f"save_{context_id}_{idx}"):
                        save_callback(message["content"])
                with col2:
                    # Conditional copy functionality
                    if copy_enabled:
                        st_copy_to_clipboard(
                            message['content'], 
                            key=f"copy_{context_id}_{idx}"  # Ensure unique key
                        )
            
            # Universal delete button
            with col3:
                if st.button("🗑️", key=f"delete_{context_id}_{idx}"):
                    delete_callback(idx)
                    st.rerun()  # Refresh UI after deletion