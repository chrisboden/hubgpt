# utils/llm_utils.py

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import streamlit as st
from termcolor import colored
from openai.types.chat import ChatCompletion
from utils.tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from utils.chat_utils import save_chat_history
from utils.log_utils import log_llm_request, log_llm_response, toggle_detailed_llm_logging

# Configure logging
LOGGING_ENABLED = True

class LLMParams:
    """Manages LLM API parameters and configuration"""
    @staticmethod
    def get_default():
        return {
            'model': 'gpt-4o-mini',
            'temperature': 1.0,
            'max_tokens': 8092,
            'top_p': 1,
            'frequency_penalty': 0,
            'presence_penalty': 0,
            'stream': True
        }

    @staticmethod
    def build_api_params(default_params: Dict, overrides: Dict, messages: List, tools: List) -> Dict:
        api_params = {**default_params}
        for key, value in overrides.items():
            if key not in ['spinner_placeholder', 'status_placeholder']:
                api_params[key] = value
        
        api_params['messages'] = messages
        if tools:
            api_params['tools'] = tools
            api_params['tool_choice'] = 'auto'
        
        return api_params

class ToolManager:
    """Handles tool resolution and execution"""
    @staticmethod
    def resolve_tools(tool_names: List[str]) -> List[Dict]:
        resolved_tools = []
        for tool_name in tool_names:
            metadata = TOOL_METADATA_REGISTRY.get(tool_name)
            if metadata:
                resolved_tools.append(metadata)
            else:
                logging.warning(f"Tool '{tool_name}' metadata not found. Skipping tool.")
        return resolved_tools

    @staticmethod
    def execute_tool_call(tool_name: str, function_call_data: Dict, llm_client) -> Dict:
        return execute_tool(tool_name, function_call_data, llm_client=llm_client)

class ResponseHandler:
    """Manages LLM response processing and UI updates"""
    def __init__(self, client, status_placeholder, response_placeholder):
        print(colored("Initializing ResponseHandler", "cyan"))
        self.client = client
        self.status_placeholder = status_placeholder
        self.response_placeholder = response_placeholder
        self.full_response = ""

    def handle_non_streamed_response(self, completion: ChatCompletion) -> tuple[str, Optional[Dict]]:
        """Handle non-streamed responses with tool call support"""
        print(colored("Starting handle_non_streamed_response", "yellow"))
        
        function_call_data = None
        full_response = ""
        
        if not completion.choices:
            return full_response, function_call_data
            
        message = completion.choices[0].message
        
        # Handle tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            print(colored(f"Tool call detected: {tool_call.function.name}", "cyan"))
            st.session_state.last_tool_name = tool_call.function.name
            st.session_state.last_tool_call_id = tool_call.id
            
            try:
                args = json.loads(tool_call.function.arguments)
                function_call_data = args
                print(colored(f"Tool arguments: {args}", "green"))
            except json.JSONDecodeError as e:
                print(colored(f"Error decoding tool arguments: {e}", "red"))
        
        # Handle content
        if message.content:
            full_response = message.content
            self.response_placeholder.markdown(full_response)
            print(colored("Response displayed", "green"))
        
        return full_response, function_call_data


    def handle_streamed_response(self, stream) -> tuple[str, Optional[Dict]]:
        """Handle streamed responses with improved tool call handling"""
        print(colored("Starting handle_streamed_response", "yellow"))
        
        function_call_data = None
        current_tool_args = ""
        tool_name = None
        tool_call_id = None  # Add this to track the tool call ID
        
        for chunk in stream:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            # Handle tool calls
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                tool_call = delta.tool_calls[0]
                
                # Capture tool call ID
                if hasattr(tool_call, 'id') and tool_call.id:
                    tool_call_id = tool_call.id
                    st.session_state.last_tool_call_id = tool_call_id
                    print(colored(f"Tool call ID captured: {tool_call_id}", "cyan"))
                
                # Handle function name
                if hasattr(tool_call, 'function'):
                    if hasattr(tool_call.function, 'name') and tool_call.function.name:
                        tool_name = tool_call.function.name
                        print(colored(f"Tool call detected: {tool_name}", "cyan"))
                        st.session_state.last_tool_name = tool_name
                        # Update status for tool usage
                        self.status_placeholder.markdown(f"*🔧 Using tool: {tool_name}*")
                    
                    # Accumulate arguments
                    if hasattr(tool_call.function, 'arguments'):
                        current_tool_args += tool_call.function.arguments
                
                # When we have complete arguments, process them
                if current_tool_args and not function_call_data:
                    try:
                        args = json.loads(current_tool_args)
                        function_call_data = {
                            'name': tool_name,
                            'arguments': args,
                            'id': tool_call_id  # Include the tool call ID
                        }
                        print(colored(f"Complete tool arguments for {tool_name} (ID: {tool_call_id}): {args}", "green"))
                    except json.JSONDecodeError:
                        # Still accumulating arguments
                        pass
            
            # Handle content
            chunk_text = delta.content or ""
            if chunk_text:
                self.full_response += chunk_text
                # Update response with thinking indicator when processing
                self.response_placeholder.markdown(f"{self.full_response}{'▌' if not function_call_data else ''}")
        
        return self.full_response, function_call_data


    def _process_tool_call(self, tool_call) -> Optional[Dict]:
        """Process tool calls with better argument handling"""
        print(colored(f"Processing tool call: {tool_call.function.name}", "yellow"))
        
        # Store tool info in session state
        st.session_state.last_tool_call_id = tool_call.id
        st.session_state.last_tool_name = tool_call.function.name
        self.status_placeholder.markdown(f"*🔧 Using tool: {tool_call.function.name}*")
        
        # Handle arguments
        try:
            # Ensure we have complete arguments
            if not hasattr(tool_call.function, 'arguments') or not tool_call.function.arguments:
                print(colored("No arguments provided", "red"))
                return None
                
            # Clean the arguments string
            args_str = tool_call.function.arguments.strip()
            if not args_str:
                print(colored("Empty arguments string", "red"))
                return None
                
            print(colored(f"Raw arguments: {args_str}", "cyan"))
            
            # Parse JSON
            args = json.loads(args_str)
            print(colored(f"Parsed arguments: {args}", "green"))
            return args
            
        except json.JSONDecodeError as e:
            print(colored(f"Error decoding tool arguments: {e}", "red"))
            print(colored(f"Problematic arguments string: {tool_call.function.arguments}", "red"))
            return None
        except Exception as e:
            print(colored(f"Unexpected error processing tool call: {e}", "red"))
            return None

    def handle_tool_execution(
        self,
        tool_name: str, 
        function_data: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        chat_history_path: str
    ) -> Optional[Dict[str, Any]]:
        """Handle tool execution with support for artifacts and structured responses."""
        print(colored(f"\nStarting tool execution for: {tool_name}", "cyan"))
        print(colored(f"Function data: {function_data}", "cyan"))
        
        try:
            # Set up spinner placeholder for tool updates
            st.session_state.spinner_placeholder = self.status_placeholder
            
            # Handle nested function data structure from LLM
            if isinstance(function_data, str):
                try:
                    function_data = json.loads(function_data)
                except json.JSONDecodeError:
                    pass
                    
            # Extract actual arguments, handling potential double nesting
            if 'arguments' in function_data:
                args = function_data['arguments']
                # Handle double nesting case
                if isinstance(args, dict) and 'arguments' in args:
                    function_data = args['arguments']
                else:
                    function_data = args
            
            print(colored(f"Cleaned function data: {function_data}", "yellow"))
            
            tool_response = execute_tool(
                tool_name, 
                function_data,
                llm_client=self.client
            )
            
            print(colored(f"Tool response received: {tool_response}", "green"))
            
            if not tool_response:
                print(colored("No tool response received", "red"))
                return None

            # Handle direct streaming tools
            if tool_response.get('direct_stream'):
                print(colored("Processing direct stream response", "yellow"))
                stream = tool_response.get('result')
                if stream:
                    full_response = ""
                    logging.info("\n" + "="*50 + "\nPROCESSING DIRECT STREAM:\n" + "="*50)
                    
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        chunk_text = delta.content or ""
                        full_response += chunk_text
                        self.response_placeholder.markdown(full_response)
                    
                    logging.info(f"\nFinal streamed response length: {len(full_response)} characters")
                    logging.info("="*50)
                    
                    return {
                        "result": full_response,
                        "direct_stream": True
                    }
            
            # Handle artifact generation tool specifically
            if tool_name == 'make_artifact' and 'artifact_html' in tool_response:
                print(colored("Processing artifact response", "yellow"))
                return {
                    "result": tool_response.get('result', ''),
                    "artifact_html": tool_response['artifact_html'],
                    "artifact_id": tool_response['artifact_id']
                }
            
            return tool_response

        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            print(colored(error_msg, "red"))
            print(colored(f"Full error: {str(e)}", "red"))
            logging.error(error_msg)
            logging.exception(e)
            self.response_placeholder.markdown(f"❌ {error_msg}")
            return None

class ChatHistoryManager:
    """Manages chat history updates and persistence"""
    def __init__(self, chat_history: List, chat_history_path: str):
        self.chat_history = chat_history
        self.chat_history_path = chat_history_path

    def add_assistant_response(self, content: str):
        if content.strip():
            self.chat_history.append({"role": "assistant", "content": content})

    def add_tool_interaction(self, tool_name: str, tool_call_id: str, function_call_data: Dict, tool_response: Dict):
        assistant_tool_message = {
            "role": "assistant",
            "content": "null",
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(function_call_data)
                }
            }]
        }
        self.chat_history.append(assistant_tool_message)
        
        tool_message = {
            "role": "tool",
            "name": tool_name,
            "tool_call_id": tool_call_id,
            "content": json.dumps(tool_response, indent=2)
        }
        self.chat_history.append(tool_message)

    def save(self):
        save_chat_history(self.chat_history, self.chat_history_path)


class LLMResponseManager:
    """Manages the entire LLM response flow including tool execution and chat history"""
    
    def __init__(self, client, messages, chat_history, chat_history_path, advisor_data, selected_advisor, tools=[], **overrides):
        self.client = client
        self.messages = messages
        self.chat_history = chat_history
        self.chat_history_path = chat_history_path
        self.advisor_data = advisor_data
        self.selected_advisor = selected_advisor
        self.tools = tools
        self.overrides = overrides
        
        # Initialize components
        self.status_placeholder = None
        self.response_placeholder = None
        self.response_handler = None
        self.history_manager = None
        
        # Set up params
        self.params = LLMParams.get_default()
        self.resolved_tools = ToolManager.resolve_tools(tools)
        self.api_params = LLMParams.build_api_params(self.params, overrides, messages, self.resolved_tools)

    def setup_ui_components(self):
        """Initialize Streamlit UI components"""
        with st.chat_message("assistant"):
            self.status_placeholder = st.empty()
            self.response_placeholder = st.empty()
            self.response_handler = ResponseHandler(self.client, self.status_placeholder, self.response_placeholder)
            self.history_manager = ChatHistoryManager(self.chat_history, self.chat_history_path)
            return True

    def make_llm_call(self, messages=None):
        """Make LLM API call and handle response"""
        if messages:
            self.api_params['messages'] = messages
            
        log_llm_request(self.api_params)
        
        try:
            if self.api_params.get('stream', True):
                stream = self.client.chat.completions.create(**self.api_params)
                response, function_call_data = self.response_handler.handle_streamed_response(stream)
            else:
                completion = self.client.chat.completions.create(**self.api_params)
                response, function_call_data = self.response_handler.handle_non_streamed_response(completion)
                
            return response, function_call_data
            
        except Exception as e:
            print(colored(f"LLM call failed: {e}", "red"))
            raise

    def handle_tool_response(self, tool_name, function_call_data):
        """Process tool execution and prepare follow-up messages"""
        tool_result = self.response_handler.handle_tool_execution(
            tool_name,
            function_call_data,
            self.chat_history,
            self.chat_history_path
        )
        
        if tool_result is None:
            return None, None
            
        self.history_manager.add_tool_interaction(
            tool_name,
            st.session_state.last_tool_call_id,
            function_call_data,
            tool_result
        )
        
        follow_up_messages = self._construct_follow_up_messages(
            tool_name, 
            function_call_data, 
            tool_result
        )
        
        return tool_result, follow_up_messages

    def _construct_follow_up_messages(self, tool_name, function_call_data, tool_result):
        """Construct messages for follow-up LLM call after tool execution"""
        # Convert tool result to string representation
        tool_content = (
            json.dumps(tool_result) if isinstance(tool_result, dict) 
            else str(tool_result)
        )
        
        return [
            *self.messages,
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": st.session_state.last_tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(function_call_data)
                    }
                }]
            },
            {
                "role": "tool",
                "name": tool_name,
                "tool_call_id": st.session_state.last_tool_call_id,
                "content": tool_content  # Use the properly formatted tool content
            }
        ]

    def process_response(self):
        """Main method to process LLM response flow"""
        try:
            with st.spinner(f"{self.selected_advisor} is thinking..."):
                if not self.setup_ui_components():
                    return self.chat_history
                    
                # Initial LLM call
                full_response, function_call_data = self.make_llm_call()
                
                # Handle tool execution if present
                if function_call_data and 'name' in function_call_data:
                    tool_name = function_call_data['name']
                    tool_result, follow_up_messages = self.handle_tool_response(tool_name, function_call_data)
                    
                    if tool_result is not None:
                        if tool_name == 'make_artifact':
                            self.history_manager.save()
                            st.rerun()
                        
                        # Handle direct stream responses differently
                        if tool_result.get('direct_stream'):
                            self.history_manager.add_assistant_response(tool_result['result'])
                            self.history_manager.save()
                            st.rerun()
                            return self.chat_history
                            
                        # Make follow-up LLM call for non-direct stream responses
                        final_response, _ = self.make_llm_call(follow_up_messages)
                        self.history_manager.add_assistant_response(final_response)
                else:
                    # Handle non-tool responses
                    if full_response.strip():
                        self.history_manager.add_assistant_response(full_response)
                        
        except Exception as e:
            st.error(f"An error occurred: {e}")
            logging.error(f"LLM Response Error: {e}")
            logging.exception(e)
            
        finally:
            self.status_placeholder.empty()
            self.history_manager.save()
            
            if not (function_call_data and function_call_data.get('name') == 'make_artifact'):
                if not function_call_data or (function_call_data and tool_result is not None):
                    st.rerun()
                    
        return self.chat_history

def get_llm_response(
    client: Any,
    messages: List[Dict[str, Any]],
    initial_messages: List[Dict[str, Any]],
    chat_history: List[Dict[str, Any]],
    chat_history_path: str,
    advisor_data: Dict[str, Any],
    selected_advisor: str,
    tools: List[str] = [],
    tool_choice: str = 'auto',
    **overrides
) -> List[Dict[str, Any]]:
    """Main entry point for LLM interactions"""
    try:
        manager = LLMResponseManager(
            client=client,
            messages=messages,
            chat_history=chat_history,
            chat_history_path=chat_history_path,
            advisor_data=advisor_data,
            selected_advisor=selected_advisor,
            tools=tools,
            **overrides
        )
        return manager.process_response()
        
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error in get_llm_response: {e}")
        logging.exception(e)
        return chat_history