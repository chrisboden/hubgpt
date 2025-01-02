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
from utils.prompt_utils import process_inclusions

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
            # Strip any method names from tool call (e.g. use_notion.create_page -> use_notion)
            tool_name = tool_call.function.name.split('.')[0]
            
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
                
                # Debug logging
                logging.debug(f"Raw completion: {completion}")
                logging.debug(f"Response object: {response}")
                logging.debug(f"Response content: {response.content if hasattr(response, 'content') else 'No content'}")
                logging.debug(f"Response tool_calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'No tool_calls'}")
                
                # Log response safely with error handling
                try:
                    log_data = {
                        "content": response.content if hasattr(response, 'content') else None
                    }
                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        log_data["tool_calls"] = [
                            {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            } for tc in response.tool_calls
                        ]
                    log_llm_response(log_data)
                except Exception as e:
                    logging.error(f"Error in response logging: {str(e)}")
                    logging.error(f"Response state: content={hasattr(response, 'content')}, tool_calls={hasattr(response, 'tool_calls')}")
                
                # Handle tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    tool_results = []
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
                        tool_results.append(result)
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": result
                        })
                    
                    # Check for errors and continue if successful
                    if not all(not str(r).startswith("Error") for r in tool_results):
                        error_msg = "One or more tools reported errors"
                        logging.error(error_msg)
                        return error_msg
                    continue  # Continue to next step with tool results
                    
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

def auto_select_tools(user_input: str, available_tools: List[Tool], llm_client: OpenAI) -> List[Tool]:
    """Use LLM to automatically select appropriate tools based on user input"""
    logging.info("Auto-selecting tools for input: %s", user_input)
    
    try:
        # Prepare the prompt with tools README content
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

User request: """ + user_input

        # Process the prompt to include README content
        prompt = process_inclusions(prompt_template, depth=5)
        logging.debug("Processed prompt with README content")

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
        #st.subheader("Agent Settings")
        model = st.selectbox(
            "Model",
            ["openai/gpt-4o-mini", "deepseek/deepseek-chat", "google/gemini-2.0-flash-exp:free"]
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
        max_steps = st.slider("Max Steps", 1, 20, 10)
        
        # Tool selection
        #st.subheader("Available Tools")
        tool_options = ["Auto"] + [tool.name for tool in tools]
        selected_tool_names = []
        auto_selected = False
        
        for tool_name in tool_options:
            if st.checkbox(tool_name, False):
                if tool_name == "Auto":
                    auto_selected = True
                else:
                    selected_tool_names.append(tool_name)
        
        # Initialize OpenAI client for auto tool selection
        client = OpenAI(
            base_url=os.getenv('API_BASE_URL', 'https://openrouter.ai/api/v1'),
            api_key=os.getenv('OPENROUTER_API_KEY')
        )
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            logging.info("Chat history cleared")
            st.rerun()
    
    # Hidden system prompt - not shown in UI but used by agent
    system_prompt = """You are a helpful assistant that can use tools to accomplish tasks.
Follow these guidelines:
1. Use appropriate tools to find information and perform actions
2. Provide clear, concise responses
3. Cite sources when possible"""

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
        
        # Handle tool selection
        selected_tools = []
        if auto_selected:
            with st.spinner("Auto-selecting tools..."):
                selected_tools = auto_select_tools(prompt, tools, client)
                if not selected_tools:
                    st.error("Failed to auto-select tools. Please select tools manually.")
                    return
        else:
            selected_tools = [t for t in tools if t.name in selected_tool_names]
            
        if not selected_tools:
            st.error("No tools selected. Please select at least one tool.")
            return
            
        logging.info(f"Using tools: {[t.name for t in selected_tools]}")
        
        # Initialize agent with selected tools
        agent = SmlAgent(
            system_prompt=system_prompt,
            tools=selected_tools,
            model=model,
            temperature=temperature,
            max_steps=max_steps
        )
        
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