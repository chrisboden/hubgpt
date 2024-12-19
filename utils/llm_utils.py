# utils/llm_utils.py

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import streamlit as st
from termcolor import colored
from openai.types.chat import ChatCompletion
from utils.tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from utils.chat_utils import save_chat_history

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
        """Handle tool execution with support for direct streaming and structured responses."""
        print(colored(f"\nStarting tool execution for: {tool_name}", "cyan"))
        print(colored(f"Function data: {function_data}", "cyan"))
        
        try:
            # Set up spinner placeholder for tool updates
            st.session_state.spinner_placeholder = self.status_placeholder
            
            print(colored("Executing tool...", "yellow"))
            tool_response = execute_tool(
                tool_name, 
                function_data,
                llm_client=self.client
            )
            
            # Clear spinner placeholder after tool execution
            if hasattr(st.session_state, 'spinner_placeholder'):
                delattr(st.session_state, 'spinner_placeholder')
            
            print(colored(f"Tool response received: {tool_response}", "green"))
            
            if not tool_response:
                print(colored("No tool response received", "red"))
                return None
                
            # Handle direct output tools
            if tool_response.get('direct_stream', False):
                print(colored("Processing direct stream response", "yellow"))
                result = tool_response.get('result', '')
                
                # Handle error responses
                if isinstance(result, dict) and 'error' in result:
                    error_msg = f"❌ Error: {result['error']}"
                    print(colored(error_msg, "red"))
                    self.response_placeholder.markdown(error_msg)
                    return None
                
                # Handle streaming responses
                if hasattr(result, 'choices'):
                    print(colored("Processing streaming response", "yellow"))
                    full_response = ""
                    for chunk in result:
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            chunk_text = delta.content
                            full_response += chunk_text
                            self.response_placeholder.markdown(full_response)
                            print(colored("Streaming chunk displayed", "green"))
                
                # Handle markdown or structured responses
                else:
                    print(colored("Processing non-streaming response", "yellow"))
                    if isinstance(result, str):
                        print(colored("Rendering markdown string", "yellow"))
                        self.response_placeholder.markdown(result)
                    else:
                        print(colored("Rendering structured data", "yellow"))
                        self.response_placeholder.markdown(f"```json\n{json.dumps(result, indent=2)}\n```")
                    
                    chat_history.append({
                        "role": "assistant",
                        "content": result if isinstance(result, str) else json.dumps(result, indent=2),
                        "tool_name": tool_name
                    })
                    print(colored("Response added to chat history", "green"))
                
                save_chat_history(chat_history, chat_history_path)
                print(colored("Chat history saved", "green"))
                return None
                
            # Return tool response for standard flow
            print(colored("Returning standard tool response", "yellow"))
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
    """Main orchestrator function using the refactored components"""
    try:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            
            with st.spinner(f"{selected_advisor} is thinking..."):
                # Initialize components
                params = LLMParams.get_default()
                resolved_tools = ToolManager.resolve_tools(tools)
                api_params = LLMParams.build_api_params(params, overrides, messages, resolved_tools)
                
                response_placeholder = st.empty()
                response_handler = ResponseHandler(client, status_placeholder, response_placeholder)
                history_manager = ChatHistoryManager(chat_history, chat_history_path)

                try:
                    # Get initial LLM response
                    if api_params.get('stream', True):
                        stream = client.chat.completions.create(**api_params)
                        full_response, function_call_data = response_handler.handle_streamed_response(stream)
                    else:
                        completion = client.chat.completions.create(**api_params)
                        full_response, function_call_data = response_handler.handle_non_streamed_response(completion)

                    # Add response to history if it's not a pure tool call
                    if full_response.strip():
                        history_manager.add_assistant_response(full_response)

                    # Handle tool calls if present
                    if function_call_data:
                        tool_name = function_call_data['name']  # Get tool name from function_call_data
                        tool_args = function_call_data['arguments']
                        print(colored(f"Executing tool: {tool_name}", "yellow"))
                        tool_result = response_handler.handle_tool_execution(
                            tool_name,
                            tool_args,
                            chat_history,
                            chat_history_path
                        )
                        
                        print(colored(f"Tool result: {tool_result}", "green"))
                        
                        # Only proceed with synthesis if tool_result is not None
                        # (None indicates direct streaming was handled)
                        if tool_result is not None:
                            # Add tool interaction to history
                            history_manager.add_tool_interaction(
                                tool_name,
                                st.session_state.last_tool_call_id,
                                function_call_data,
                                tool_result
                            )
                            
                            # Get final response from LLM
                            api_params['messages'] = initial_messages + chat_history
                            if api_params.get('stream', True):
                                stream = client.chat.completions.create(**api_params)
                                final_response = response_handler.handle_streamed_response(stream)[0]
                            else:
                                completion = client.chat.completions.create(**api_params)
                                final_response = response_handler.handle_non_streamed_response(completion)[0]
                            
                            history_manager.add_assistant_response(final_response)

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logging.error(f"LLM Response Error: {e}")
                    logging.exception(e)
                
                finally:
                    status_placeholder.empty()
                    history_manager.save()

    except Exception as main_e:
        st.error(f"An unexpected error occurred: {main_e}")
        logging.error(f"Unexpected error in get_llm_response: {main_e}")
        logging.exception(main_e)

    return chat_history