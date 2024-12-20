# advisors.py
import os
import json
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard
import logging
from openai import OpenAI
from utils.prompt_utils import load_advisor_data, get_available_advisors, load_prompt
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

class LLMClient:
    """Handles LLM-related operations"""
    def __init__(self):
        self.client = self._initialize_client()
    
    @staticmethod
    def _initialize_client():
        return OpenAI(
            base_url=os.getenv('API_BASE_URL'),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def extract_params(self, advisor_data):
        llm_params_keys = [
            'model', 'temperature', 'max_tokens', 'top_p', 
            'frequency_penalty', 'presence_penalty', 'stream'
        ]
        return {
            key: advisor_data[key] 
            for key in llm_params_keys 
            if key in advisor_data
        }

    def process_response(self, advisor_data, messages, chat_history_path, selected_advisor, spinner_placeholder):
        llm_params = self.extract_params(advisor_data)
        tools = advisor_data.get('tools', [])
        tool_choice = advisor_data.get('tool_choice', 'auto')

        try:
            get_llm_response(
                client=self.client,
                messages=messages,
                initial_messages=messages,
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
            raise RuntimeError(f"LLM Response Error: {e}")

class ChatHistory:
    """Manages chat history operations"""
    def __init__(self, selected_advisor):
        self.selected_advisor = selected_advisor
        self.chat_history_path = self._get_history_path()
        
    def _get_history_path(self):
        return os.path.join(
            "advisors", 
            "chats", 
            f"{self.selected_advisor.replace(' ', '_')}.json"
        )

    def load(self):
        return load_chat_history(self.chat_history_path)

    def save(self, messages):
        save_chat_history(messages, self.chat_history_path)

    def clear(self):
        archive_chat_history(
            self.chat_history_path,
            os.path.join("advisors"),
            f"{self.selected_advisor.replace(' ', '_')}.json"
        )
        try:
            os.remove(self.chat_history_path)
        except FileNotFoundError:
            pass
        save_chat_history([], self.chat_history_path)

class SidebarManager:
    """Manages sidebar UI elements"""
    def setup(self):
        advisor_names = get_available_advisors()
        selected_advisor = st.sidebar.selectbox("Choose an advisor", advisor_names)
        clear_button = st.sidebar.button("Clear Chat")
        return selected_advisor, clear_button

class SnippetManager:
    """Manages saving and deleting message snippets"""
    @staticmethod
    def save_snippet(message_content, selected_advisor):
        snippets_dir = os.path.join("snippets")
        source_type = "advisor"
        source_name = selected_advisor
        save_snippet(message_content, source_type, source_name, snippets_dir)
        st.session_state.save_success = True

    @staticmethod
    def delete_message(chat_history, index, selected_advisor):
        delete_message(chat_history, index)
        chat_history_path = os.path.join(
            "advisors", 
            "chats", 
            f"{selected_advisor.replace(' ', '_')}.json"
        )
        save_chat_history(chat_history, chat_history_path)
        st.rerun()

class ChatInterface:
    """Manages the main chat interface"""
    def __init__(self, selected_advisor):
        self.selected_advisor = selected_advisor
        self.container = None
        self.snippet_manager = SnippetManager()

    def setup(self):
        st.title(f"Chat with {self.selected_advisor}")
        self.container = st.container()
        return self.container

    def display_messages(self, messages, context_id):
        with self.container:
            display_messages(
                messages=messages,
                save_callback=lambda msg: self.snippet_manager.save_snippet(
                    msg, self.selected_advisor
                ),
                delete_callback=lambda idx: self.snippet_manager.delete_message(
                    st.session_state.chat_history, 
                    idx, 
                    self.selected_advisor
                ),
                context_id=context_id
            )

    def display_error(self, error_message):
        with self.container:
            st.error(f"An error occurred: {error_message}")

class AdvisorManager:
    """Orchestrates the advisor chat application"""
    def __init__(self):
        self.llm_client = LLMClient()
        self.sidebar = SidebarManager()
        self.selected_advisor = None
        self.chat_history = None
        self.interface = None
        
    def initialize(self):
        self.selected_advisor, clear_button = self.sidebar.setup()
        self.chat_history = ChatHistory(self.selected_advisor)
        self.interface = ChatInterface(self.selected_advisor)
        
        if clear_button:
            self.chat_history.clear()
            st.rerun()

        return load_advisor_data(self.selected_advisor)

    def process_message(self, prompt, advisor_data):
        if st.session_state.get('follow_on_instruction'):
            prompt = st.session_state.follow_on_instruction
            del st.session_state.follow_on_instruction

        if not st.session_state.get('process_follow_on'):
            user_message = {"role": "user", "content": prompt}
            st.session_state.chat_history.append(user_message)
            
            with self.interface.container:
                with st.chat_message("user"):
                    st.markdown(prompt)

        self.chat_history.save(st.session_state.chat_history)
        
        initial_messages = load_prompt(advisor_data, st.session_state.chat_history)
        messages = initial_messages + st.session_state.chat_history

        with self.interface.container:
            spinner_placeholder = st.empty()
            
        try:
            self.llm_client.process_response(
                advisor_data, 
                messages, 
                self.chat_history.chat_history_path,
                self.selected_advisor,
                spinner_placeholder
            )
        except Exception as e:
            self.interface.display_error(str(e))
            logging.error(str(e))

def main():
    st.cache_data.clear()
    st.cache_resource.clear()

    # Initialize tools
    tools_directory = os.path.join(os.getcwd(), "tools")
    load_tools(tools_directory)
    initialize_session_state()
    
    # Initialize manager
    manager = AdvisorManager()
    advisor_data = manager.initialize()
    
    # Load chat history
    st.session_state.chat_history = manager.chat_history.load()
    st.session_state.selected_advisor = manager.selected_advisor

    # Setup chat interface
    manager.interface.setup()
    manager.interface.display_messages(
        st.session_state.chat_history,
        manager.selected_advisor.replace(' ', '_')
    )

    # Handle success message
    if st.session_state.get('save_success'):
        st.success("Snippet saved successfully!")
        st.session_state.save_success = False

    # Handle user input
    if prompt := st.chat_input(f"Chat with {manager.selected_advisor}") or st.session_state.get('follow_on_instruction'):
        manager.process_message(prompt, advisor_data)
        
        if st.session_state.get('process_follow_on'):
            del st.session_state.process_follow_on

if __name__ == "__main__":
    main()