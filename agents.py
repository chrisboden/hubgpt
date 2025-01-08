import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import streamlit as st
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from termcolor import cprint
from utils.ui_utils import update_spinner_status
from utils.tool_utils import load_tools
from utils.chat_utils import (
    initialize_session_state,
    load_chat_history,
    save_chat_history,
    archive_chat_history,
    clear_chat_history
)
from utils.log_utils import get_helicone_config
import importlib.util
import sys
from pathlib import Path
import logging
from utils.log_utils import log_llm_request, log_llm_response
from utils.prompt_utils import process_inclusions

# Default LLM parameters - easy to tweak
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_STEPS = 10

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    execute_fn: callable
    
    def to_tool_schema(self):
        """Convert to OpenAI tool schema format"""
        # Ensure tool name contains no dots
        clean_name = self.name.split('.')[0]
        return {
            "type": "function",
            "function": {
                "name": clean_name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class SmlAgent:
    def __init__(
        self,
        system_prompt: str,
        tools: List[Tool],
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_steps: int = DEFAULT_MAX_STEPS
    ):
        logging.info(f"Initializing SmlAgent with {len(tools)} tools")
        logging.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Enhance system prompt with tool usage guidance
        tool_guidance = """When using tools:
1. Use the exact tool name as provided (e.g., 'use_notion' not 'use_notion.create_page')
2. Put operations in the arguments (e.g., {"operation": "create_page"})
3. Include all required parameters as specified in the tool schema"""
        
        self.system_prompt = f"{system_prompt}\n\n{tool_guidance}"
        
        # Get Helicone configuration
        helicone_config = get_helicone_config()
        
        # Initialize OpenAI client with appropriate configuration
        self.client = OpenAI(
            base_url=helicone_config['base_url'],
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers=helicone_config['headers']
        )
        
        self.tools = tools
        self.model = model
        self.temperature = temperature
        self.max_steps = max_steps
        self.tool_map = {tool.name: tool for tool in tools}
        
        # Initialize messages list with system prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
            
    def reset(self):
        """Reset conversation history"""
        logging.info("Resetting agent conversation history")
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _process_llm_response(self, completion: ChatCompletion) -> Tuple[Optional[ChatCompletionMessage], str]:
        """Process LLM response and handle potential errors"""
        try:
            if not completion:
                error_msg = "Empty response from LLM"
                logging.error(error_msg)
                return None, error_msg
                
            if not hasattr(completion, 'choices') or not completion.choices:
                error_msg = f"Invalid response structure from LLM: {completion}"
                logging.error(error_msg)
                return None, error_msg
                
            response = completion.choices[0].message
            if not response:
                error_msg = f"No message in LLM response. Full response: {completion}"
                logging.error(error_msg)
                return None, error_msg
                
            return response, ""
            
        except Exception as e:
            error_msg = f"Error processing LLM response: {str(e)}"
            logging.error(error_msg)
            logging.error(f"Raw completion: {completion}")
            logging.exception("Full traceback:")
            return None, error_msg

    def _make_llm_request(self, params: Dict[str, Any]) -> Tuple[Optional[ChatCompletion], str]:
        """Make LLM API request with error handling"""
        try:
            # Ensure stream is False for non-streaming responses
            params["stream"] = False
            
            log_llm_request(params)
            response = self.client.chat.completions.create(**params)
            
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

    def _handle_tool_call(self, tool_call) -> str:
        """Execute a tool call and return the result"""
        try:
            # Debug log the raw tool call
            logging.info(f"Raw tool call: {tool_call}")
            logging.info(f"Tool call function name: {tool_call.function.name}")
            logging.info(f"Tool call function arguments: {tool_call.function.arguments}")
            
            tool_name = tool_call.function.name
            if tool_name not in self.tool_map:
                error_msg = f"Error: Unknown tool '{tool_name}'"
                logging.error(error_msg)
                return error_msg
                
            tool = self.tool_map[tool_name]
            arguments = json.loads(tool_call.function.arguments)
            
            logging.info(f"Executing tool: {tool_name}")
            logging.info(f"Tool arguments: {json.dumps(arguments, indent=2)}")
            
            # Add LLM client to arguments if tool accepts it
            if 'client' in tool.execute_fn.__code__.co_varnames:
                arguments['client'] = self.client
            elif 'llm_client' in tool.execute_fn.__code__.co_varnames:
                arguments['llm_client'] = self.client
                
            update_spinner_status(f"🔧 Using tool: {tool_name}")
            result = tool.execute_fn(**arguments)
            
            # Handle tool execution results
            if isinstance(result, dict):
                # First check if this is a direct stream response
                if result.get('direct_stream', False):
                    stream = result.get('result')
                    if stream is None:
                        return "No result from stream"
                        
                    # Handle OpenRouter streaming response
                    if hasattr(stream, '__iter__'):
                        accumulated_response = ""
                        for chunk in stream:
                            if hasattr(chunk, 'choices') and chunk.choices:
                                delta = chunk.choices[0].delta
                                if hasattr(delta, 'content') and delta.content:
                                    accumulated_response += delta.content
                        return accumulated_response
                    return str(stream)
                
                # For non-streaming dict responses, just get the result
                return str(result.get('result', result))
            
            # For string or other responses, convert to string
            return str(result)
            
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            return error_msg

    def chat(self, user_input: str) -> str:
        """Single turn chat with tool use"""
        logging.info(f"Processing user input: {user_input}")
        
        # Add user message
        self.messages.append({"role": "user", "content": user_input})
        
        step = 0
        while step < self.max_steps:
            step += 1
            update_spinner_status(f"🤔 Step {step}/{self.max_steps}: Thinking...")
            logging.info(f"Step {step}/{self.max_steps}")
            
            try:
                # Prepare request parameters
                params = {
                    "model": self.model,
                    "messages": self.messages,
                    "tools": [t.to_tool_schema() for t in self.tools],
                    "tool_choice": "auto",
                    "temperature": self.temperature
                }
                
                # Make LLM request
                completion, error = self._make_llm_request(params)
                if error:
                    return f"Error occurred: {error}"
                    
                # Process response
                response, error = self._process_llm_response(completion)
                if error:
                    return f"Error occurred: {error}"
                
                # Log response details for debugging
                logging.debug(f"Response content: {response.content if hasattr(response, 'content') else 'No content'}")
                logging.debug(f"Response tool_calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'No tool_calls'}")
                
                # Handle tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    tool_call = response.tool_calls[0]
                    logging.info(f"Tool call requested: {tool_call.function.name}")
                    
                    # Execute tool call
                    result = self._handle_tool_call(tool_call)
                    
                    # Check if tool execution failed
                    if isinstance(result, str) and ('error' in result.lower() or 'failed' in result.lower()):
                        # Add error response to messages and return
                        error_message = {
                            "role": "assistant",
                            "content": f"I apologize, but I encountered an error: {result}"
                        }
                        self.messages.append(error_message)
                        return error_message["content"]
                    
                    # Add assistant and tool response messages
                    self.messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": result
                    })
                    
                    # Continue to next step if there are more tool calls
                    continue
                
                # If no tool calls, return the response content and add to messages
                if hasattr(response, 'content') and response.content:
                    self.messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    return response.content
                    
                # If we get here without returning, something went wrong
                return "Error: No valid response from assistant"
                
            except Exception as e:
                error_msg = f"Error in chat: {str(e)}"
                logging.error(error_msg)
                logging.exception("Full traceback:")
                update_spinner_status(f"❌ {error_msg}")
                return error_msg
                
        return "Maximum conversation steps reached"

def load_tool(tool_module) -> Tool:
    """Load a HubGPT tool module into Tool format"""
    try:
        metadata = tool_module.TOOL_METADATA["function"]
        logging.info(f"Loading tool: {metadata['name']}")
        return Tool(
            name=metadata["name"],
            description=metadata["description"],
            parameters=metadata["parameters"],
            execute_fn=tool_module.execute
        )
    except Exception as e:
        logging.error(f"Error loading tool module: {str(e)}")
        raise

@st.cache_resource
def load_available_tools(tools_dir: str) -> List[Tool]:
    """Load all available tools from the tools directory - cached to prevent reloading"""
    logging.info(f"Loading tools from directory: {tools_dir}")
    tools = []
    
    # Get all Python files in tools directory
    tool_files = Path(tools_dir).glob("*.py")
    
    for tool_file in tool_files:
        if tool_file.name.startswith("__"):
            continue
            
        try:
            # Import the module
            module_name = tool_file.stem
            spec = importlib.util.spec_from_file_location(module_name, str(tool_file))
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Check if it's a valid tool module
            if hasattr(module, "TOOL_METADATA") and hasattr(module, "execute"):
                tools.append(load_tool(module))
                logging.debug(f"Loaded tool: {module_name}")
                
        except Exception as e:
            logging.error(f"Error loading tool {tool_file.name}: {str(e)}")
            
    logging.info(f"Loaded {len(tools)} tools")
    return tools

def auto_select_tools(user_input: str, available_tools: List[Tool], llm_client: OpenAI) -> List[Tool]:
    """Use LLM to automatically select appropriate tools based on user input"""
    logging.info("Auto-selecting tools for input: %s", user_input)
    
    try:
        # Get chat history from session state
        chat_history = st.session_state.get('messages', [])
        
        # Format chat history as string
        history_str = ""
        if chat_history:
            history_str = "\n\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in chat_history 
                if msg['content'] is not None  # Skip messages without content
            ])
            history_str = f"\n\nNote that the previous chat history with the user:\n\n{history_str}"
        
        # Prepare the prompt with tools README content and chat history
        prompt_template = """You are a tool selection agent. Given a user brief and a list of potential tools, you select all of the tools that might be required to complete the job.

Here are the available tools:

<$tools/README.md$>

IMPORTANT: You must respond with a valid JSON object using this exact structure:
{
    "selected_tools": ["tool_name1", "tool_name2"],
    "rationale": "Brief explanation of why these tools were selected"
}

Do not include any other text in your response, only the JSON object.

For the user request below, analyze what tools would be needed and return them in a JSON response:

User request: """ + user_input + history_str

        # Process the prompt to include README content
        prompt = process_inclusions(prompt_template, depth=5)
        logging.debug("Processed prompt with README content and chat history")

        # Use deepseek model for tool selection
        update_spinner_status("Analyzing request with Deepseek...")
        response = llm_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a tool selection specialist. Always respond with valid JSON only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        # Parse response
        try:
            content = response.choices[0].message.content
            # Remove markdown code blocks if present
            content = content.replace('```json\n', '').replace('\n```', '').strip()
            
            selection = json.loads(content)
            if not isinstance(selection, dict) or 'selected_tools' not in selection:
                raise ValueError("Invalid response format")
                
            selected_tool_names = selection["selected_tools"]
            logging.info("Auto-selected tools: %s", selected_tool_names)
            logging.info("Selection rationale: %s", selection.get("rationale", "No rationale provided"))
            
            # Map selected names to actual tool objects
            selected_tools = [
                tool for tool in available_tools 
                if tool.name in selected_tool_names
            ]
            
            if not selected_tools:
                logging.warning("No matching tools were found")
                return []
                
            update_spinner_status(f"Selected tools: {', '.join(selected_tool_names)}")
            return selected_tools
            
        except json.JSONDecodeError as e:
            logging.error("Failed to parse JSON response: %s", str(e))
            logging.error("Raw response: %s", response.choices[0].message.content)
            return []
            
    except Exception as e:
        logging.error("Error in auto tool selection: %s", str(e))
        return []

def main():
    st.title("Agent Playground")
    
    # Initialize session state
    initialize_session_state()
    
    # Show loading status
    with st.spinner("Loading tools..."):
        # Load all available tools - now cached
        tools_directory = os.path.join(os.getcwd(), "tools")
        tools = load_available_tools(tools_directory)
    
    if not tools:
        st.error("No tools were loaded. Please check the tools directory.")
        logging.error("No tools were loaded")
        return
    
    # Create agent with configurable settings
    with st.sidebar:
        # Tool selection
        selected_tool_names = []
        
        # Auto tool selection is default
        auto_selected = st.checkbox("Auto Tool Selection", value=True)
        
        # Expandable section for manual tool selection
        with st.expander("Manual Tool Selection", expanded=False):
            for tool in tools:
                if st.checkbox(tool.name, False):
                    selected_tool_names.append(tool.name)
        
        # Clear chat button
        if st.button("Clear Chat"):
            if 'agent' in st.session_state:
                st.session_state.agent.reset()
            st.session_state.messages = []
            logging.info("Chat history cleared")
            st.rerun()
    
    # Hidden system prompt - not shown in UI but used by agent
    system_prompt = """You are a helpful assistant that can use tools to accomplish tasks.
Follow these guidelines:
1. Use appropriate tools to find information and perform actions
2. Provide clear, concise responses
3. Cite sources when possible"""

    # Initialize message history and agent in session state if not present
    if "messages" not in st.session_state:
        st.session_state.messages = []
        logging.info("Initialized new chat session")
    
    if "agent" not in st.session_state:
        st.session_state.agent = None
    
    # Display chat history using message_utils display_messages
    from utils.message_utils import display_messages
    display_messages(
        messages=st.session_state.messages,
        save_callback=None,  # We could add snippet saving later if needed
        delete_callback=None,
        context_id="agent_playground"
    )
    
    # Chat input
    if prompt := st.chat_input("Message the agent..."):
        logging.info(f"New user message: {prompt}")
        
        # Immediately show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Initialize OpenAI client for auto tool selection
        helicone_config = get_helicone_config()
        client = OpenAI(
            base_url=helicone_config['base_url'],
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers=helicone_config['headers']
        )
        
        # Handle tool selection and agent response in assistant message block
        with st.chat_message("assistant"):
            # Create status placeholder for detailed updates
            status_placeholder = st.empty()
            # Store placeholder in session state for tool updates
            st.session_state.spinner_placeholder = status_placeholder
            
            # Handle tool selection
            selected_tools = []
            if auto_selected:
                status_placeholder.markdown("🤔 Selecting appropriate tools...")
                selected_tools = auto_select_tools(prompt, tools, client)
                if not selected_tools:
                    status_placeholder.error("Failed to auto-select tools. Please select tools manually.")
                    return
            else:
                selected_tools = [t for t in tools if t.name in selected_tool_names]
            
            if not selected_tools:
                status_placeholder.error("No tools selected. Please select at least one tool.")
                return
                
            logging.info(f"Using tools: {[t.name for t in selected_tools]}")
            
            # Initialize or reuse agent with selected tools
            if st.session_state.agent is None:
                st.session_state.agent = SmlAgent(
                    system_prompt=system_prompt,
                    tools=selected_tools
                )
            else:
                # Update tools if they've changed
                st.session_state.agent.tools = selected_tools
                st.session_state.agent.tool_map = {tool.name: tool for tool in selected_tools}
            
            # Get agent response
            try:
                response = st.session_state.agent.chat(prompt)
                # Clear status placeholder before showing final response
                status_placeholder.empty()
                # Clear from session state
                if 'spinner_placeholder' in st.session_state:
                    del st.session_state.spinner_placeholder
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                logging.info("Agent response completed")
            except Exception as e:
                status_placeholder.error(f"Error: {str(e)}")
                logging.error(f"Agent error: {str(e)}")
                return

if __name__ == "__main__":
    main() 