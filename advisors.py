import os
import json
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard
import logging
from openai import OpenAI
from utils.prompt_utils import load_advisor_data, get_available_advisors
from utils.prompt_utils import load_prompt
from utils.tool_utils import load_tools
from utils.llm_utils import get_llm_response
from utils.chat_utils import (
    initialize_session_state,
    load_chat_history,
    save_chat_history,
    archive_chat_history,
    clear_chat_history
)
from utils.message_utils import save_snippet, delete_message, display_messages

def initialize_openai_client():
    return OpenAI(
        base_url=os.getenv('API_BASE_URL'),
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

def sidebar_controls():
    # Get available advisors
    advisor_names = get_available_advisors()
    
    # Advisor selection
    selected_advisor = st.sidebar.selectbox("Choose an advisor", advisor_names)
    
    # Clear conversation button
    clear_button = st.sidebar.button("Clear Conversation")
    
    return selected_advisor, clear_button

def save_advisor_snippet(message_content):
    snippets_dir = os.path.join("snippets")
    source_type = "advisor"
    source_name = st.session_state.selected_advisor
    save_snippet(message_content, source_type, source_name, snippets_dir)
    st.session_state.save_success = True  # Trigger confirmation message

def delete_advisor_message(index):
    delete_message(st.session_state.chat_history, index)
    selected_advisor = st.session_state.selected_advisor
    chat_history_path = os.path.join("advisors", "chats", f"{selected_advisor.replace(' ', '_')}.json")
    save_chat_history(st.session_state.chat_history, chat_history_path)
    st.rerun()

# advisors.py
def main():
    # Initialize OpenAI client
    client = initialize_openai_client()

    # Load tools
    tools_directory = os.path.join(os.getcwd(), "tools")
    load_tools(tools_directory)

    # Initialize session state
    initialize_session_state()

    # Sidebar controls
    selected_advisor, clear_button = sidebar_controls()

    # Load advisor data
    advisor_data = load_advisor_data(selected_advisor)
    
    # Set chat history path
    chat_history_path = os.path.join(
        "advisors", 
        "chats", 
        f"{selected_advisor.replace(' ', '_')}.json"
    )

    # Load or initialize chat history
    st.session_state.chat_history = load_chat_history(chat_history_path)
    st.session_state.selected_advisor = selected_advisor

    # Clear conversation logic
    if clear_button:
        # Explicitly clear the chat history
        st.session_state.chat_history = []
        
        # Remove the chat history file
        try:
            os.remove(chat_history_path)
        except FileNotFoundError:
            pass
        
        # Reinitialize the chat history file
        save_chat_history([], chat_history_path)
        
        st.rerun()

    # Main chat area
    st.title(f"Chat with {selected_advisor}")
    
    # Display previous messages
    display_messages(
        messages=st.session_state.chat_history,
        save_callback=save_advisor_snippet,
        delete_callback=delete_advisor_message,
        context_id=selected_advisor.replace(' ', '_')
    )

    # Handle success message
    if st.session_state.get('save_success'):
        st.success("Snippet saved successfully!")
        st.session_state.save_success = False  # Reset after displaying

    # Handle user input
    if prompt := st.chat_input(f"Chat with {selected_advisor}"):
        # Initialize spinner status in session state
        st.session_state.spinner_status = f"Preparing response with {selected_advisor}..."
        
        # Create a more robust spinner placeholder
        st.session_state.spinner_placeholder = st.empty()
        st.session_state.spinner_placeholder.markdown(f"*{st.session_state.spinner_status}*")
        # User message handling
        user_message = {"role": "user", "content": prompt}
        st.session_state.chat_history.append(user_message)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Logging
        logging.info(f"User input: {prompt}")

        # Save chat history
        save_chat_history(st.session_state.chat_history, chat_history_path)

        # Process messages
        initial_messages = load_prompt(advisor_data, st.session_state.chat_history)
        messages = initial_messages + st.session_state.chat_history
        #print(messages)
        # Extract LLM parameters
        llm_params_keys = [
            'model', 'temperature', 'max_tokens', 'top_p', 
            'frequency_penalty', 'presence_penalty', 'stream'
        ]
        llm_params = {
            key: advisor_data[key] 
            for key in llm_params_keys 
            if key in advisor_data
        }

        # Extract tools configuration
        tools = advisor_data.get('tools', [])
        print(tools)
        tool_choice = advisor_data.get('tool_choice', 'auto')
        print(tool_choice)
        
        # Prepare for assistant response
        try:
            # Spinner placeholder
            spinner_placeholder = st.session_state.spinner_placeholder
            
            # Get LLM response
            get_llm_response(
                client=client,
                messages=messages,
                initial_messages=initial_messages,
                chat_history=st.session_state.chat_history,
                chat_history_path=chat_history_path,
                advisor_data=advisor_data,
                selected_advisor=selected_advisor,
                tools=tools,
                tool_choice=tool_choice,
                spinner_placeholder=spinner_placeholder,
                **llm_params
            )
            #print(tools)
        except Exception as e:
            # Error handling
            st.error(f"An error occurred: {e}")
            logging.error(f"LLM Response Error: {e}")
        
        # Rerun to refresh the page
        st.rerun()

if __name__ == "__main__":
    main()