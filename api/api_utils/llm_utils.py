# api/utils/llm_utils.py

import json
import logging
import os
from typing import Dict, Any, List, Optional, Union, Tuple
from termcolor import colored
from openai.types.chat import ChatCompletion
from .tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from .chat_utils import save_chat_history
from .log_utils import log_llm_request, log_llm_response, toggle_detailed_llm_logging, get_helicone_config
import openai

# Configure logging
LOGGING_ENABLED = True

class LLMParams:
    """Manages LLM API parameters and configuration"""
    
    # Gateway configurations
    GATEWAY_CONFIG = {
        'openrouter': {
            'base_url_env': 'OPENROUTER_BASE_URL',
            'api_key_env': 'OPENROUTER_API_KEY'
        },
        'openai': {
            'base_url_env': 'OPENAI_BASE_URL',
            'api_key_env': 'OPENAI_API_KEY'
        },
        'google': {
            'base_url_env': 'GOOGLE_BASE_URL',
            'api_key_env': 'GEMINI_API_KEY'
        },
        'groq': {
            'base_url_env': 'GROQ_BASE_URL',
            'api_key_env': 'GROQ_API_KEY'
        },
        'deepseek': {
            'base_url_env': 'DEEPSEEK_BASE_URL',
            'api_key_env': 'DEEPSEEK_API_KEY'
        }
    }
    
    @staticmethod
    def get_gateway_credentials(gateway: str = 'openrouter') -> tuple[str, str]:
        """
        Get the base URL and API key for the specified gateway.
        Falls back to OpenRouter if gateway not found.

        Args:
            gateway (str): The gateway identifier (e.g., 'openrouter', 'openai', etc.)

        Returns:
            tuple[str, str]: (base_url, api_key) for the gateway
        """
        # Default to openrouter if gateway not found
        gateway = gateway.lower()
        if gateway not in LLMParams.GATEWAY_CONFIG:
            logging.warning(f"Gateway {gateway} not found, falling back to openrouter")
            gateway = 'openrouter'
            
        config = LLMParams.GATEWAY_CONFIG[gateway]
        base_url = os.getenv(config['base_url_env'])
        api_key = os.getenv(config['api_key_env'])

        # Special handling for OpenAI gateway
        if gateway == 'openai':
            base_url = base_url or "https://api.openai.com/v1"
        
        # Validate credentials
        if not base_url or not api_key:
            missing = []
            if not base_url:
                missing.append(config['base_url_env'])
            if not api_key:
                missing.append(config['api_key_env'])
            error_msg = f"Missing environment variables for {gateway} gateway: {', '.join(missing)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        logging.info(f"Using gateway: {gateway} with base_url: {base_url}")
        return base_url, api_key

    @staticmethod
    def get_default():
        """
        Returns a dictionary of default parameters for the LLM API.
        """
        return {
            'model': 'gpt-4o-mini',
            'temperature': 1.0,
            'max_tokens': 8092,
            'top_p': 1,
            'frequency_penalty': 0,
            'presence_penalty': 0,
            'stream': True,
            'response_format': None,
            'gateway': 'openrouter'  # Default gateway
        }

    @staticmethod
    def build_api_params(default_params: Dict, overrides: Dict, messages: List, tools: List) -> Dict:
        """
        Builds the final API parameters by merging default parameters with overrides.
        """
        # Get gateway from overrides or default to openrouter
        gateway = overrides.get('gateway', 'openrouter').lower()
        
        # Define valid parameters based on gateway
        base_params = {'model', 'temperature', 'max_tokens', 'stream', 'messages', 'tools', 'tool_choice', 'gateway'}
        
        # Add gateway-specific parameters
        if gateway in ['openrouter', 'openai']:
            base_params.update({
                'top_p', 'frequency_penalty', 'presence_penalty',
                'response_format'
            })
        
        # Start with default params
        api_params = {**default_params}
        
        # Add valid overrides
        for key, value in overrides.items():
            if key not in ['spinner_placeholder', 'status_placeholder', 'provider']:
                api_params[key] = value
        
        # Add messages
        api_params['messages'] = messages
        
        # Add tools if provided
        if tools:
            api_params['tools'] = tools
            api_params['tool_choice'] = overrides.get('tool_choice', 'auto')
            logging.info(f"Added tools to API params: {json.dumps(tools, indent=2)}")
        
        # Handle response format if specified
        if 'response_format' in overrides and gateway in ['openrouter', 'openai']:
            api_params['response_format'] = {
                'type': overrides['response_format']
            }
        
        # Handle model names for different gateways
        if gateway == 'google':
            # For Gemini, ensure model name starts with 'gemini-'
            model = api_params.get('model', '')
            if not model:  # Only set default if no model specified
                api_params['model'] = 'gemini-1.5-flash'  # Default to flash model if not specified
            elif not model.startswith('gemini-'):
                logging.warning(f"Using non-Gemini model name with Google gateway: {model}")
        
        # Make sure gateway is included in params
        api_params['gateway'] = gateway
        
        # Final validation - only return valid parameters for the gateway
        filtered_params = {
            k: v for k, v in api_params.items()
            if k in base_params and v is not None
        }
        
        logging.debug(f"Final API params after filtering for {gateway}: {filtered_params}")
        return filtered_params

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
    """Manages LLM response processing"""
    def __init__(self, client=None, messages=None):
        """
        Initializes the ResponseHandler.

        Args:
            client: Optional OpenAI client instance
            messages: Optional list of messages for context
        """
        logging.info("Initializing ResponseHandler")
        self.client = client
        self.messages = messages or []
        self.full_response = ""
        self._cancelled = False
        self._current_stream = None

    @property
    def chat_messages(self):
        """Returns the current chat messages"""
        return self.messages

    def cancel(self):
        """Cancels the current stream if one exists"""
        logging.info("Cancelling stream")
        self._cancelled = True
        if self._current_stream:
            try:
                # Close the stream if it has a close method
                if hasattr(self._current_stream, 'close'):
                    self._current_stream.close()
                # For OpenAI streams, we can also try to cancel the response
                if hasattr(self._current_stream, 'response'):
                    self._current_stream.response.close()
            except Exception as e:
                logging.error(f"Error closing stream: {e}")

    def _make_llm_request(self, params: Dict[str, Any]) -> Tuple[Optional[ChatCompletion], str]:
        """Make LLM API request with error handling"""
        try:
            # Ensure stream is False for non-streaming responses
            params["stream"] = False
            
            # Get Helicone configuration
            helicone_config = get_helicone_config()
            
            # Add Helicone headers if enabled
            headers = {**helicone_config['headers']}
            if 'tools' in params:
                headers["Helicone-Property-Tools"] = ",".join(str(t) for t in params['tools'])
            
            # Get gateway configuration if specified
            gateway = params.pop('gateway', 'openrouter')  # Remove gateway param before API call
            base_url, api_key = LLMParams.get_gateway_credentials(gateway)
            
            # Create a new client with the gateway configuration
            client = openai.OpenAI(
                base_url=base_url,
                api_key=api_key
            )
            
            # Make the API request
            log_llm_request(params)
            response = client.chat.completions.create(
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
            # Reset cancelled flag
            self._cancelled = False
            
            # Ensure streaming is enabled
            params["stream"] = True
            
            # Get Helicone configuration
            helicone_config = get_helicone_config()
            
            # Add Helicone headers if enabled
            headers = {**helicone_config['headers']}
            if 'tools' in params:
                headers["Helicone-Property-Tools"] = ",".join(str(t) for t in params['tools'])
            
            # Get gateway configuration if specified
            gateway = params.pop('gateway', 'openrouter')  # Remove gateway param before API call
            base_url, api_key = LLMParams.get_gateway_credentials(gateway)
            
            # Create a new client with the gateway configuration
            client = openai.OpenAI(
                base_url=base_url,
                api_key=api_key,
                default_headers={
                    **headers,
                    "HTTP-Referer": "https://github.com/chrisb34/hubgpt",  # Required for OpenRouter
                    "X-Title": "HubGPT"  # Optional but recommended
                }
            )
            
            # Make the streaming request
            log_llm_request(params)
            self._current_stream = client.chat.completions.create(**params)
            logging.debug("Streaming response created successfully")
            return self._current_stream
            
        except Exception as e:
            error_msg = f"Streaming LLM request failed: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            raise RuntimeError(error_msg)

    async def handle_streamed_response(self, stream):
        """
        Processes streamed responses chunk by chunk, handling both content and tool calls.
        
        Args:
            stream: Iterator of response chunks from the LLM
            
        Yields:
            object: The raw chunk object from the stream
        
        Returns:
            List: Updated messages array including tool calls and responses
        """
        logging.info("Starting handle_streamed_response")
        
        self.full_response = ""
        current_tool_call = None
        assistant_message = {"role": "assistant", "content": ""}
        
        try:
            # Process each chunk as it arrives
            async for chunk in self._aiter(stream):
                # Check if stream was cancelled
                if self._cancelled:
                    logging.info("Stream cancelled, stopping processing")
                    break
                    
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Handle content updates
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    self.full_response += content
                    assistant_message["content"] += content
                    # Log chunk in green
                    print(colored(content, 'green'), end='', flush=True)
                    # Yield the raw chunk immediately
                    yield chunk
                    
                # Handle tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    
                    # Initialize tool call if new
                    if not current_tool_call:
                        current_tool_call = {
                            'id': tool_call.id,
                            'name': tool_call.function.name,
                            'arguments': ''
                        }
                        # Log tool call start in yellow
                        print(colored(f"\nTool call started: {current_tool_call['name']}\n", 'yellow'), flush=True)
                    
                    # Append arguments if present
                    if hasattr(tool_call.function, 'arguments'):
                        current_tool_call['arguments'] += tool_call.function.arguments
            
            # Process completed tool call if present and not cancelled
            if current_tool_call and not self._cancelled:
                try:
                    args = json.loads(current_tool_call['arguments'])
                    # Log tool arguments in cyan
                    print(colored(f"\nTool arguments: {json.dumps(args, indent=2)}\n", 'cyan'), flush=True)
                    
                    # Add assistant's tool call message to history
                    assistant_message["tool_calls"] = [{
                        "id": current_tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": current_tool_call["name"],
                            "arguments": current_tool_call["arguments"]
                        }
                    }]
                    self.messages.append(assistant_message)
                    
                    # Execute the tool
                    tool_result = ToolManager.execute_tool_call(
                        current_tool_call['name'],
                        args,
                        self.client
                    )
                    
                    # Check if tool uses direct streaming
                    if isinstance(tool_result, dict) and tool_result.get('direct_stream'):
                        # For direct streaming tools, yield their stream directly
                        stream_result = tool_result.get('result')
                        if stream_result:
                            # Process the direct stream similar to main stream
                            async for chunk in self._aiter(stream_result):
                                # Check if stream was cancelled
                                if self._cancelled:
                                    logging.info("Stream cancelled during tool execution")
                                    break
                                    
                                if chunk.choices:
                                    delta = chunk.choices[0].delta
                                    if hasattr(delta, 'content') and delta.content:
                                        content = delta.content
                                        self.full_response += content
                                        # Log chunk in blue to differentiate tool stream
                                        print(colored(content, 'blue'), end='', flush=True)
                                        # Yield the raw chunk immediately
                                        yield chunk
                    else:
                        # For regular tools, follow the tool call flow:
                        # 1. Log tool result
                        print(colored(f"\nTool result: {json.dumps(tool_result, indent=2)}\n", 'magenta'), flush=True)
                        
                        # 2. Create tool response message
                        tool_message = {
                            "role": "tool",
                            "name": current_tool_call['name'],
                            "tool_call_id": current_tool_call['id'],
                            "content": json.dumps(tool_result)
                        }
                        
                        # 3. Add tool response to messages
                        self.messages.append(tool_message)
                        
                        # Only proceed with final response if not cancelled
                        if not self._cancelled:
                            # 4. Get LLM's response to tool result
                            tool_response = self.client.chat.completions.create(
                                messages=self.messages,
                                stream=True,
                                model=self.messages[0].get('model', 'gpt-4o-mini'),  # Use original model
                                temperature=1.0
                            )
                            
                            # 5. Stream LLM's final response
                            assistant_message = {"role": "assistant", "content": ""}
                            async for chunk in self._aiter(tool_response):
                                # Check if stream was cancelled
                                if self._cancelled:
                                    logging.info("Stream cancelled during final response")
                                    break
                                    
                                if chunk.choices:
                                    delta = chunk.choices[0].delta
                                    if hasattr(delta, 'content') and delta.content:
                                        content = delta.content
                                        self.full_response += content
                                        assistant_message["content"] += content
                                        print(colored(content, 'green'), end='', flush=True)
                                        # Yield the raw chunk immediately
                                        yield chunk
                            
                            # 6. Add final assistant response to messages if not cancelled
                            if assistant_message["content"] and not self._cancelled:
                                self.messages.append(assistant_message)
                    
                except json.JSONDecodeError as e:
                    logging.error(f"Error decoding tool arguments: {e}")
                except Exception as e:
                    logging.error(f"Error executing tool: {e}")
                    yield f"I apologize, but I encountered an error: {str(e)}"
            
            # Add newline after completion
            print()
            
        except Exception as e:
            error_msg = f"Error processing stream: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
        finally:
            # Clean up stream reference
            self._current_stream = None

    async def _aiter(self, iterator):
        """Helper method to convert a regular iterator to an async iterator"""
        for item in iterator:
            yield item

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
        Adds an assistant response to the chat history and saves it.

        Args:
            content (str): Content of the assistant's response.
        """
        message = {
            "role": "assistant",
            "content": content
        }
        self.chat_history.append(message)
        save_chat_history(self.chat_history, self.chat_history_path)

    def add_tool_response(self, tool_name: str, tool_response: Dict):
        """
        Adds a tool response to the chat history and saves it.

        Args:
            tool_name (str): Name of the tool used.
            tool_response (Dict): Response from the tool.
        """
        message = {
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(tool_response)
        }
        self.chat_history.append(message)
        save_chat_history(self.chat_history, self.chat_history_path)