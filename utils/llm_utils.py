# utils/llm_utils.py

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import streamlit as st
from termcolor import colored
from openai.types.chat import ChatCompletion
from utils.tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from utils.chat_utils import save_chat_history
from utils.log_utils import log_llm_request, log_llm_response, toggle_detailed_llm_logging, get_helicone_config
import openai

# Configure logging
LOGGING_ENABLED = True

class LLMParams:
    """Manages LLM API parameters and configuration"""
    @staticmethod
    def get_default():
        """
        Returns a dictionary of default parameters for the LLM API.

        Returns:
            Dict: Default parameters including model, temperature, max_tokens, etc.
        """
        return {
            'model': 'gpt-4o-mini',
            'temperature': 1.0,
            'max_tokens': 8092,
            'top_p': 1,
            'frequency_penalty': 0,
            'presence_penalty': 0,
            'stream': True,
            'response_format': None  # Default to None for natural language responses
        }

    @staticmethod
    def build_api_params(default_params: Dict, overrides: Dict, messages: List, tools: List) -> Dict:
        """
        Builds the final API parameters by merging default parameters with overrides.

        Args:
            default_params (Dict): Default parameters.
            overrides (Dict): Parameters to override the defaults.
            messages (List): List of messages to be sent to the LLM.
            tools (List): List of tools to be used.

        Returns:
            Dict: Final API parameters.
        """
        api_params = {**default_params}
        for key, value in overrides.items():
            if key not in ['spinner_placeholder', 'status_placeholder']:
                api_params[key] = value
        
        api_params['messages'] = messages
        if tools:
            api_params['tools'] = tools
            api_params['tool_choice'] = 'auto'
        
        # Handle response format if specified
        if 'response_format' in overrides:
            api_params['response_format'] = {
                'type': overrides['response_format']
            }
        
        return api_params

class ToolManager:
    """Handles tool resolution and execution"""
    @staticmethod
    def resolve_tools(tool_names: List[str]) -> List[Dict]:
        """
        Resolves tool metadata based on the provided tool names.

        Args:
            tool_names (List[str]): List of tool names.

        Returns:
            List[Dict]: List of resolved tool metadata.
        """
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
        """
        Executes a tool call with the provided function call data.

        Args:
            tool_name (str): Name of the tool to execute.
            function_call_data (Dict): Data containing the function call details.
            llm_client: Client to interact with the LLM.

        Returns:
            Dict: Result of the tool execution.
        """
        return execute_tool(tool_name, function_call_data, llm_client=llm_client)

class ResponseHandler:
    """Manages LLM response processing and UI updates"""
    def __init__(self, client, status_placeholder, response_placeholder):
        """
        Initializes the ResponseHandler.

        Args:
            client: Client to interact with the LLM.
            status_placeholder: Placeholder for status messages.
            response_placeholder: Placeholder for response messages.
        """
        print(colored("Initializing ResponseHandler", "cyan"))
        self.client = client
        self.status_placeholder = status_placeholder
        self.response_placeholder = response_placeholder
        self.full_response = ""

    def _make_llm_request(self, params: Dict[str, Any]) -> Tuple[Optional[ChatCompletion], str]:
        """Make LLM API request with error handling"""
        try:
            # Ensure stream is False for non-streaming responses
            params["stream"] = False
            
            # Get Helicone configuration
            helicone_config = get_helicone_config()
            
            # Add Helicone headers if enabled
            headers = {**helicone_config['headers']}
            if 'selected_advisor' in params:
                headers["Helicone-Property-Advisor"] = params['selected_advisor']
            if 'tools' in params:
                headers["Helicone-Property-Tools"] = ",".join(str(t) for t in params['tools'])
            
            # Make the API request
            log_llm_request(params)
            response = self.client.chat.completions.create(
                **params,
                extra_headers=headers
            )
            
            # Log response for debugging
            logging.info("LLM Response received")
            logging.debug(f"Response model: {response.model}")
            logging.debug(f"Response id: {response.id}")
            
            # Verify response is valid before processing
            if not response or not hasattr(response, 'choices'):
                error_msg = f"Invalid API response structure: {response}"
                logging.error(error_msg)
                return None, error_msg
            
            return response, ""
            
        except Exception as e:
            error_msg = f"LLM API request failed: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            return None, error_msg

    def _make_streaming_request(self, params: Dict[str, Any]):
        """Make streaming LLM API request with error handling"""
        try:
            # Ensure streaming is enabled
            params["stream"] = True
            
            # Get Helicone configuration
            helicone_config = get_helicone_config()
            
            # Add Helicone headers if enabled
            headers = {**helicone_config['headers']}
            if 'selected_advisor' in params:
                headers["Helicone-Property-Advisor"] = params['selected_advisor']
            if 'tools' in params:
                headers["Helicone-Property-Tools"] = ",".join(str(t) for t in params['tools'])
            
            # Make the streaming request
            log_llm_request(params)
            return self.client.chat.completions.create(
                **params,
                extra_headers=headers
            )
            
        except Exception as e:
            error_msg = f"Streaming LLM request failed: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            raise RuntimeError(error_msg)

    def handle_non_streamed_response(self, completion: ChatCompletion) -> tuple[str, Optional[Dict]]:
        """
        Handles non-streamed responses with support for tool calls.

        Args:
            completion (ChatCompletion): Completion object from the LLM.

        Returns:
            tuple[str, Optional[Dict]]: Full response and function call data.
        """
        print(colored("Starting handle_non_streamed_response", "yellow"))
        
        function_call_data = None
        full_response = ""
        
        # Return early if no choices in completion
        if not completion.choices:
            return full_response, function_call_data
            
        message = completion.choices[0].message
        
        # Handle tool calls if present in the message
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            print(colored(f"Tool call detected: {tool_call.function.name}", "cyan"))
            
            # Store tool info in session state for tracking
            st.session_state.last_tool_name = tool_call.function.name
            st.session_state.last_tool_call_id = tool_call.id
            
            # Parse tool arguments from JSON
            try:
                args = json.loads(tool_call.function.arguments)
                function_call_data = args
                print(colored(f"Tool arguments: {args}", "green"))
            except json.JSONDecodeError as e:
                print(colored(f"Error decoding tool arguments: {e}", "red"))
        
        # Handle and display message content if present
        if message.content:
            full_response = message.content
            self.response_placeholder.markdown(full_response)
            print(colored("Response displayed", "green"))
        
        return full_response, function_call_data


    def handle_streamed_response(self, stream) -> tuple[str, Optional[Dict]]:
        """
        Processes streamed responses chunk by chunk, handling both content and tool calls.
        
        Args:
            stream: Iterator of response chunks from the LLM
            
        Returns:
            tuple[str, Optional[Dict]]: Accumulated response text and tool call data if present
        """
        print(colored("Starting handle_streamed_response", "yellow"))
        
        # Initialize tracking variables
        function_call_data = None
        current_tool_args = ""  # Buffer for accumulating tool arguments
        tool_name = None
        tool_call_id = None
        
        try:
            # Get stream from API if not provided
            if isinstance(stream, dict):
                stream = self._make_streaming_request(stream)
            
            # Process each chunk in the stream
            for chunk in stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # Handle tool calls in the chunk
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    
                    # Track tool call ID when present
                    if hasattr(tool_call, 'id') and tool_call.id:
                        tool_call_id = tool_call.id
                        st.session_state.last_tool_call_id = tool_call_id
                        print(colored(f"Tool call ID captured: {tool_call_id}", "cyan"))
                    
                    # Process function information if present
                    if hasattr(tool_call, 'function'):
                        # Handle function name
                        if hasattr(tool_call.function, 'name') and tool_call.function.name:
                            tool_name = tool_call.function.name
                            print(colored(f"Tool call detected: {tool_name}", "cyan"))
                            st.session_state.last_tool_name = tool_name
                            self.status_placeholder.markdown(f"*🔧 Using tool: {tool_name}*")
                        
                        # Accumulate function arguments
                        if hasattr(tool_call.function, 'arguments'):
                            current_tool_args += tool_call.function.arguments
                        
                    # Try to parse complete arguments when available
                    if current_tool_args and not function_call_data:
                        try:
                            args = json.loads(current_tool_args)
                            # Return clean arguments structure without nesting
                            function_call_data = {
                                'name': tool_name,
                                'arguments': args,
                                'id': tool_call_id
                            }
                            print(colored(f"Complete tool arguments for {tool_name} (ID: {tool_call_id}): {args}", "green"))
                        except json.JSONDecodeError:
                            # Continue accumulating if arguments are incomplete
                            pass
                
                # Handle content updates
                chunk_text = delta.content or ""
                if chunk_text:
                    self.full_response += chunk_text
                    # Show typing indicator (▌) while processing
                    self.response_placeholder.markdown(f"{self.full_response}{'▌' if not function_call_data else ''}")
            
            return self.full_response, function_call_data
            
        except openai.APIError as e:
            error_msg = f"OpenRouter API Error: {str(e)}"
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "status_code": getattr(e, 'status_code', None),
                "response": getattr(e, 'response', None),
                "headers": getattr(e, 'headers', None),
                "body": getattr(e, 'body', None)
            }
            logging.error(error_msg)
            logging.error("Detailed error information:")
            logging.error(json.dumps(error_details, indent=2))
            self.response_placeholder.markdown(f"❌ {error_msg}")
            return self.full_response, function_call_data
        except Exception as e:
            error_msg = f"Error processing stream: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            self.response_placeholder.markdown(f"❌ {error_msg}")
            return self.full_response, function_call_data


    def _process_tool_call(self, tool_call) -> Optional[Dict]:
        """
        Helper method to process and validate tool calls.
        
        Args:
            tool_call: Tool call object from LLM response
            
        Returns:
            Optional[Dict]: Parsed tool arguments if valid, None if invalid
        """
        print(colored(f"Processing tool call: {tool_call.function.name}", "yellow"))
        
        # Update session state with tool tracking info
        st.session_state.last_tool_call_id = tool_call.id
        st.session_state.last_tool_name = tool_call.function.name
        self.status_placeholder.markdown(f"*🔧 Using tool: {tool_call.function.name}*")
        
        # Validate and parse tool arguments
        try:
            # Verify arguments exist
            if not hasattr(tool_call.function, 'arguments') or not tool_call.function.arguments:
                print(colored("No arguments provided", "red"))
                return None
                
            # Clean and validate arguments string
            args_str = tool_call.function.arguments.strip()
            if not args_str:
                print(colored("Empty arguments string", "red"))
                return None
                
            print(colored(f"Raw arguments: {args_str}", "cyan"))
            
            # Parse and return JSON arguments
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
        """
        Handles tool execution with support for artifacts and structured responses.

        Args:
            tool_name (str): Name of the tool to execute.
            function_data (Dict[str, Any]): Data containing the function call details.
            chat_history (List[Dict[str, Any]]): Current chat history.
            chat_history_path (str): Path to save the chat history.

        Returns:
            Optional[Dict[str, Any]]: Result of the tool execution.
        """
        print(colored(f"\nStarting tool execution for: {tool_name}", "cyan"))
        print(colored(f"Function data: {function_data}", "cyan"))
        
        try:
            # Set up spinner placeholder for tool updates
            st.session_state.spinner_placeholder = self.status_placeholder
            
            # Unwrap nested function data structure from LLM
            if isinstance(function_data, str):
                try:
                    function_data = json.loads(function_data)
                except json.JSONDecodeError:
                    pass
                    
            # Extract actual arguments, handling potential double nesting
            if isinstance(function_data, dict):
                # Case 1: Nested under 'arguments' key
                if 'arguments' in function_data:
                    function_data = function_data['arguments']
                # Case 2: Double nested with tool name
                if isinstance(function_data, dict) and function_data.get('name') == tool_name and 'arguments' in function_data:
                    function_data = function_data['arguments']
            
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
                    
                    # Return only the result, excluding direct_stream flag
                    return {
                        "result": full_response
                    }
            
            # Handle artifact generation tool specifically
            if tool_name == 'make_artifact' and 'artifact_html' in tool_response:
                print(colored("Processing artifact response", "yellow"))
                return {
                    "result": tool_response.get('result', ''),
                    "artifact_html": tool_response['artifact_html'],
                    "artifact_id": tool_response['artifact_id']
                }
            
            # Remove direct_stream flag from response if present
            if isinstance(tool_response, dict):
                tool_response.pop('direct_stream', None)
            
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
        """
        Initializes the ChatHistoryManager.

        Args:
            chat_history (List): Current chat history.
            chat_history_path (str): Path to save the chat history.
        """
        self.chat_history = chat_history
        self.chat_history_path = chat_history_path

    def add_assistant_response(self, content: str):
        """
        Adds an assistant's response to the chat history.

        Args:
            content (str): Content of the assistant's response.
        """
        if content.strip():
            self.chat_history.append({"role": "assistant", "content": content})

    def add_tool_interaction(self, tool_name: str, tool_call_id: str, function_call_data: Dict, tool_response: Dict):
        """
        Adds a tool interaction to the chat history.

        Args:
            tool_name (str): Name of the tool used.
            tool_call_id (str): ID of the tool call.
            function_call_data (Dict): Data containing the function call details.
            tool_response (Dict): Response from the tool execution.
        """
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
        """Saves the chat history to a file."""
        save_chat_history(self.chat_history, self.chat_history_path)

class LLMResponseManager:
    """
    Manages the entire LLM response workflow, handling complex interactions 
    between the language model, tools, and chat history.
    
    This class orchestrates the process of:
    - Initializing LLM parameters
    - Setting up UI components
    - Making LLM API calls
    - Executing tools
    - Managing chat history
    """
    
    def __init__(self, client, messages, chat_history, chat_history_path, advisor_data, selected_advisor, tools=[], **overrides):
        """
        Initialize the LLM response management system with comprehensive configuration.
        
        Key responsibilities in initialization:
        - Set up client and communication parameters
        - Prepare chat history tracking
        - Resolve and configure available tools
        - Build API parameters with flexible overrides
        
        Args:
            client: The LLM API client for making requests
            messages: Initial conversation context
            chat_history: Running record of conversation interactions
            chat_history_path: File path for persistent chat history storage
            advisor_data: Metadata about the current AI advisor
            selected_advisor: Name of the active advisor
            tools: List of tools available for the advisor
            **overrides: Flexible parameter overrides for fine-tuned control
        """
        # Core communication and context attributes
        self.client = client
        self.messages = messages
        self.chat_history = chat_history
        self.chat_history_path = chat_history_path
        self.advisor_data = advisor_data
        self.selected_advisor = selected_advisor
        self.tools = tools
        self.overrides = overrides
        
        # UI and interaction tracking components (initially None)
        self.status_placeholder = None
        self.response_placeholder = None
        self.response_handler = None
        self.history_manager = None
        
        # Configure LLM parameters with flexible defaults and overrides
        self.params = LLMParams.get_default()
        self.resolved_tools = ToolManager.resolve_tools(tools)
        self.api_params = LLMParams.build_api_params(self.params, overrides, messages, self.resolved_tools)

    def setup_ui_components(self):
        """
        Dynamically set up Streamlit UI components for real-time interaction.
        
        This method:
        - Creates placeholders for status and response messages
        - Initializes response and history management handlers
        
        Returns:
            bool: Indicates successful UI component initialization
        """
        with st.chat_message("assistant"):
            self.status_placeholder = st.empty()
            self.response_placeholder = st.empty()
            self.response_handler = ResponseHandler(self.client, self.status_placeholder, self.response_placeholder)
            self.history_manager = ChatHistoryManager(self.chat_history, self.chat_history_path)
            return True

    def make_llm_call(self, messages=None):
        """
        Execute an LLM API call with robust error handling and logging.
        
        Handles both streamed and non-streamed response modes, allowing 
        flexible communication with the language model.
        
        Args:
            messages: Optional custom message set to override default messages
        
        Returns:
            tuple: Full text response and any associated function call data
        
        Raises:
            Exception: Captures and logs any API call failures
        """
        if messages:
            self.api_params['messages'] = messages
            
        # Add Helicone tracking headers
        helicone_headers = {
            "Helicone-Property-Advisor": self.selected_advisor,
            "Helicone-Property-Tools": ",".join(self.tools) if self.tools else "none",
            "Helicone-Request-Id": f"hubgpt-{self.selected_advisor}-{id(self)}"
        }
            
        log_llm_request(self.api_params)
        
        try:
            # Dynamically choose between streaming and non-streaming modes
            if self.api_params.get('stream', True):
                stream = self.client.chat.completions.create(
                    **self.api_params,
                    extra_headers=helicone_headers
                )
                response, function_call_data = self.response_handler.handle_streamed_response(stream)
            else:
                completion = self.client.chat.completions.create(
                    **self.api_params,
                    extra_headers=helicone_headers
                )
                response, function_call_data = self.response_handler.handle_non_streamed_response(completion)
                
            # Add response logging here
            log_llm_response({
                "content": response,
                "function_call": function_call_data
            })
                
            return response, function_call_data
            
        except Exception as e:
            print(colored(f"LLM call failed: {e}", "red"))
            raise


    def handle_tool_response(self, tool_name, function_call_data):
        """
        Process tool execution and prepare follow-up conversation context.
        
        Workflow:
        1. Execute the specified tool
        2. Record the tool interaction in chat history
        3. Prepare follow-up messages for potential additional processing
        
        Args:
            tool_name: Name of the tool to execute
            function_call_data: Detailed parameters for tool execution
        
        Returns:
            tuple: Tool execution result and prepared follow-up messages
        """
        # Execute tool and capture its result
        tool_result = self.response_handler.handle_tool_execution(
            tool_name,
            function_call_data,
            self.chat_history,
            self.chat_history_path
        )
        
        if tool_result is None:
            return None, None
            
        # Log tool result
        log_llm_response({
            "tool_name": tool_name,
            "tool_result": tool_result
        })
            
        # Record tool interaction in chat history
        self.history_manager.add_tool_interaction(
            tool_name,
            st.session_state.last_tool_call_id,
            function_call_data,
            tool_result
        )
        
        # Prepare context for potential follow-up LLM interaction
        follow_up_messages = self._construct_follow_up_messages(
            tool_name, 
            function_call_data, 
            tool_result
        )
        
        return tool_result, follow_up_messages

    def _construct_follow_up_messages(self, tool_name, function_call_data, tool_result):
        """
        Construct a conversation context that includes the tool execution details.
        
        Transforms tool results into a format suitable for continued LLM interaction,
        maintaining the conversation's context and flow.
        
        Args:
            tool_name: Name of the executed tool
            function_call_data: Original tool call parameters
            tool_result: Result returned by the tool
        
        Returns:
            list: Augmented message list with tool execution context
        """
        # Flexible serialization of tool result
        tool_content = (
            json.dumps(tool_result) if isinstance(tool_result, dict) 
            else str(tool_result)
        )
        
        # Append static weather question to tool content
        #tool_content = tool_content + "\n\n\nThe user also asked what the current weather is in milan"
        
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
                "content": tool_content
            }
        ]

    def process_response(self):
        """
        Central method orchestrating the entire LLM interaction workflow.
        
        Comprehensive process handling:
        - UI setup
        - Initial LLM call
        - Tool execution (if applicable)
        - Response generation
        - Chat history management
        - Error handling
        
        Returns:
            list: Updated chat history after processing
        """
        try:
            with st.spinner(f"{self.selected_advisor} is thinking..."):
                if not self.setup_ui_components():
                    return self.chat_history
                    
                # Initial language model interaction
                full_response, function_call_data = self.make_llm_call()
                
                # Handle potential tool invocation
                if function_call_data and 'name' in function_call_data:
                    tool_name = function_call_data['name']
                    tool_result, follow_up_messages = self.handle_tool_response(tool_name, function_call_data)
                    
                    if tool_result is not None:
                        # Special handling for artifact creation
                        if tool_name == 'make_artifact':
                            self.history_manager.save()
                            st.rerun()
                        
                        # Direct streaming for certain tools
                        if tool_result.get('direct_stream'):
                            self.history_manager.add_assistant_response(tool_result['result'])
                            self.history_manager.save()
                            st.rerun()
                            return self.chat_history
                            
                        # Follow-up LLM call for complex tool interactions
                        final_response, _ = self.make_llm_call(follow_up_messages)
                        self.history_manager.add_assistant_response(final_response)
                else:
                    # Standard response handling without tools
                    if full_response.strip():
                        self.history_manager.add_assistant_response(full_response)
                        
        except Exception as e:
            # Comprehensive error management
            st.error(f"An error occurred: {e}")
            logging.error(f"LLM Response Error: {e}")
            logging.exception(e)
            
        finally:
            # Cleanup and state management
            self.status_placeholder.empty()
            self.history_manager.save()
            
            # Conditional UI refresh
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
    """
    Main entry point for LLM interactions.
    
    Initializes an LLMResponseManager to handle the complete lifecycle of:
    - Making API calls to the language model
    - Processing responses and tool calls
    - Managing chat history
    - Handling errors and exceptions
    
    Returns:
        List[Dict[str, Any]]: Updated chat history after processing
    """
    try:
        # Initialize response manager with all required components
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
        # Process the response and return updated chat history
        return manager.process_response()
        
    except Exception as e:
        # Handle any unexpected errors
        st.error(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error in get_llm_response: {e}")
        logging.exception(e)
        return chat_history