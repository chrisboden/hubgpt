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

@st.cache_resource
def initialize_openai_client():
    return OpenAI(
        base_url=os.getenv('API_BASE_URL'),
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

@st.cache_data
def load_cached_tools(tools_directory):
    return load_tools(tools_directory)

@st.cache_data
def get_cached_advisors():
    return get_available_advisors()

def sidebar_controls():
    # Get available advisors using cached function
    advisor_names = get_cached_advisors()
    
    # Advisor selection
    selected_advisor = st.sidebar.selectbox("Choose an advisor", advisor_names)
    
    # Clear conversation button
    clear_button = st.sidebar.button("Clear Chat")
    
    return selected_advisor, clear_button

def initialize_session_state():
    """Initialize all required session state variables"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'selected_advisor' not in st.session_state:
        st.session_state.selected_advisor = None
    if 'save_success' not in st.session_state:
        st.session_state.save_success = False
    if 'spinner_placeholder' not in st.session_state:
        st.session_state.spinner_placeholder = None
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False

def main():
    # Initialize OpenAI client (cached)
    client = initialize_openai_client()

    # Load tools (cached)
    tools_directory = os.path.join(os.getcwd(), "tools")
    load_cached_tools(tools_directory)

    # Initialize session state
    initialize_session_state()

    # Sidebar controls
    selected_advisor, clear_button = sidebar_controls()

    # Load advisor data with caching
    @st.cache_data
    def get_advisor_data(advisor_name):
        return load_advisor_data(advisor_name)

    advisor_data = get_advisor_data(selected_advisor)
    
    # Set chat history path
    chat_history_path = os.path.join(
        "advisors", 
        "chats", 
        f"{selected_advisor.replace(' ', '_')}.json"
    )

    # Load chat history only if needed
    if (st.session_state.selected_advisor != selected_advisor or 
        'chat_history' not in st.session_state):
        st.session_state.chat_history = load_chat_history(chat_history_path)
        st.session_state.selected_advisor = selected_advisor

    # Clear conversation logic
    if clear_button:
        archive_chat_history(
            chat_history_path,
            os.path.join("advisors"),
            f"{selected_advisor.replace(' ', '_')}.json"
        )
        st.session_state.chat_history = []
        try:
            os.remove(chat_history_path)
        except FileNotFoundError:
            pass
        save_chat_history([], chat_history_path)
        st.rerun()

    # Main chat area
    st.title(f"Chat with {selected_advisor}")
    
    # Create a container for messages
    chat_container = st.container()
    
    # Display messages in container
    with chat_container:
        display_messages(
            messages=st.session_state.chat_history,
            save_callback=save_snippet,
            delete_callback=delete_message,
            context_id=selected_advisor.replace(' ', '_')
        )

    # Handle success message
    if st.session_state.get('save_success'):
        st.success("Snippet saved successfully!")
        st.session_state.save_success = False

    # Handle user input
    if prompt := st.chat_input(f"Chat with {selected_advisor}"):
        if not st.session_state.is_processing:
            st.session_state.is_processing = True
            
            user_message = {"role": "user", "content": prompt}
            st.session_state.chat_history.append(user_message)
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            save_chat_history(st.session_state.chat_history, chat_history_path)

            initial_messages = load_prompt(advisor_data, st.session_state.chat_history)
            messages = initial_messages + st.session_state.chat_history

            llm_params_keys = [
                'model', 'temperature', 'max_tokens', 'top_p', 
                'frequency_penalty', 'presence_penalty', 'stream'
            ]
            llm_params = {
                key: advisor_data[key] 
                for key in llm_params_keys 
                if key in advisor_data
            }

            tools = advisor_data.get('tools', [])
            tool_choice = advisor_data.get('tool_choice', 'auto')
            
            try:
                with chat_container:
                    spinner_placeholder = st.empty()
                    st.session_state.spinner_placeholder = spinner_placeholder
                
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

            except Exception as e:
                with chat_container:
                    st.error(f"An error occurred: {e}")
                logging.error(f"LLM Response Error: {e}")
            
            finally:
                st.session_state.is_processing = False

if __name__ == "__main__":
    main()