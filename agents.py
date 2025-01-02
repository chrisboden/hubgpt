import os
import json
from typing import List, Dict, Any
from dataclasses import dataclass
import streamlit as st
from openai import OpenAI
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
import importlib.util
import sys
from pathlib import Path
import logging
from utils.log_utils import log_llm_request, log_llm_response

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    execute_fn: callable
    
    def to_tool_schema(self):
        """Convert to OpenAI tool schema format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class SmlAgent:
    def __init__(
        self,
        system_prompt: str,
        tools: List[Tool],
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.7,
        max_steps: int = 10
    ):
        logging.info(f"Initializing SmlAgent with {len(tools)} tools")
        logging.info(f"Available tools: {[tool.name for tool in tools]}")
        
        self.client = OpenAI(
            base_url=os.getenv('API_BASE_URL', 'https://openrouter.ai/api/v1'),
            api_key=os.getenv('OPENROUTER_API_KEY')
        )
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = model
        self.temperature = temperature
        self.max_steps = max_steps
        self.messages = []
        self.tool_map = {tool.name: tool for tool in tools}
        
    def reset(self):
        """Reset conversation history"""
        logging.info("Resetting agent conversation history")
        self.messages = []
            
    def _handle_tool_call(self, tool_call) -> str:
        """Execute a tool call and return the result"""
        try:
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
            
            # Handle direct streaming responses
            if isinstance(result, dict) and result.get('direct_stream'):
                stream = result.get('result')
                if stream:
                    accumulated_response = ""
                    for chunk in stream:
                        if hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                accumulated_response += content
                    logging.info(f"Accumulated streaming response from {tool_name}")
                    return accumulated_response
                    
            logging.info(f"Tool {tool_name} execution completed")
            return str(result)
            
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            logging.error(error_msg)
            update_spinner_status(f"❌ {error_msg}")
            return f"Error: {str(e)}"
            
    def chat(self, user_input: str) -> str:
        """Single turn chat with tool use"""
        logging.info(f"Processing user input: {user_input}")
        
        # Add user message
        self.messages.append({"role": "system", "content": self.system_prompt})
        self.messages.append({"role": "user", "content": user_input})
        
        step = 0
        while step < self.max_steps:
            step += 1
            update_spinner_status(f"🤔 Step {step}/{self.max_steps}: Thinking...")
            logging.info(f"Step {step}/{self.max_steps}")
            
            try:
                # Get model response
                params = {
                    "model": self.model,
                    "messages": self.messages,
                    "tools": [t.to_tool_schema() for t in self.tools],
                    "tool_choice": "auto",
                    "temperature": self.temperature
                }
                log_llm_request(params)
                
                completion = self.client.chat.completions.create(**params)
                response = completion.choices[0].message
                log_llm_response({"content": response.content, "function_call": response.tool_calls[0] if response.tool_calls else None})
                
                # Handle tool calls if present
                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        logging.info(f"Tool call requested: {tool_call.function.name}")
                        
                        # Add assistant message with tool call
                        self.messages.append({
                            "role": "assistant",
                            "content": response.content,
                            "tool_calls": [tool_call.model_dump()]
                        })
                        
                        # Execute tool and add result
                        result = self._handle_tool_call(tool_call)
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": result
                        })
                        
                else:
                    # Regular response - no tool call
                    update_spinner_status("✍️ Generating response...")
                    logging.info("No tool call, returning direct response")
                    self.messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    return response.content
                    
            except Exception as e:
                error_msg = f"Error in chat: {str(e)}"
                logging.error(error_msg)
                update_spinner_status(f"❌ {error_msg}")
                return f"Error occurred: {str(e)}"
                
        logging.warning("Max steps reached without resolution")
        return "Max steps reached without resolution"

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
        st.subheader("Agent Settings")
        model = st.selectbox(
            "Model",
            ["openai/gpt-4o-mini", "deepseek/deepseek-chat", "google/gemini-2.0-flash-exp:free"]
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
        max_steps = st.slider("Max Steps", 1, 20, 10)
        
        # Tool selection
        st.subheader("Available Tools")
        selected_tools = []
        for tool in tools:
            if st.checkbox(tool.name, False):  # Default to False - tools start unchecked
                selected_tools.append(tool)
                
        logging.debug(f"Selected tools: {[tool.name for tool in selected_tools]}")
                
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            logging.info("Chat history cleared")
            st.rerun()
    
    # System prompt configuration
    system_prompt = st.text_area(
        "System Prompt",
        """You are a helpful assistant that can use tools to accomplish tasks.
Follow these guidelines:
1. Use appropriate tools to find information and perform actions
2. Provide clear, concise responses
3. Cite sources when possible""",
        height=150
    )
    
    # Initialize agent
    agent = SmlAgent(
        system_prompt=system_prompt,
        tools=selected_tools,
        model=model,
        temperature=temperature,
        max_steps=max_steps
    )
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        logging.info("Initialized new chat session")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Message the agent..."):
        logging.info(f"New user message: {prompt}")
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Agent is working..."):
                response = agent.chat(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                logging.info("Agent response completed")

if __name__ == "__main__":
    main() 