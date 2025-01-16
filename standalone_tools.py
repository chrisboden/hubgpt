"""
Standalone tool execution script that provides a command-line interface for running individual tools.
This module allows tools to be tested and run independently of the main application, which is useful
for development and debugging purposes.

Key features:
- Loads environment variables and initializes OpenAI client with OpenRouter
- Provides a simple CLI interface for tool execution
- Handles both regular and streaming responses from tools
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from utils.tool_utils import load_tools, execute_tool
from termcolor import colored
import sys
import json

def init_tools():
    """
    Initialize the tools environment and OpenAI client.
    
    Sets up the necessary environment for tool execution by:
    1. Loading environment variables (including API keys)
    2. Initializing OpenAI client with OpenRouter configuration
    3. Loading all available tools from the tools directory
    
    Returns:
        tuple: (OpenAI client instance, dict of loaded tools)
    """
    load_dotenv()
    
    # OpenRouter is used instead of direct OpenAI API for model flexibility
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    
    # Load all tools from the tools directory
    tools_dir = os.path.join(os.path.dirname(__file__), "tools")
    tools = load_tools(tools_dir)
    
    return client, tools

def get_tool_params(tool_name: str, tools: dict) -> dict:
    """
    Get the expected parameters for a specific tool.
    
    Args:
        tool_name (str): Name of the tool
        tools (dict): Dictionary of loaded tools
    
    Returns:
        dict: Dictionary of parameter names and their default values
    """
    tool = tools.get(tool_name)
    if not tool or not hasattr(tool, 'execute'):
        return {}
    
    import inspect
    sig = inspect.signature(tool.execute)
    params = {}
    for name, param in sig.parameters.items():
        if name != 'self' and name != 'llm_client':
            params[name] = param.default if param.default != inspect.Parameter.empty else None
    return params

def run_tool(tool_name: str, **args):
    """
    Execute a specific tool with provided arguments and handle its response.
    
    This function handles both regular tool responses and streaming responses
    (like those from LLM interactions). For streaming responses, it prints
    the content in real-time and collects the full response.
    
    Args:
        tool_name (str): Name of the tool to execute
        **args: Variable keyword arguments passed to the tool
    
    Returns:
        dict: Tool execution results or None if execution fails
    """
    try:
        client, tools = init_tools()
        print(colored(f"Executing tool: {tool_name}", "blue"))
        
        # Get expected parameters for the tool
        tool_params = get_tool_params(tool_name, tools)
        
        # Map generic search_query to appropriate parameter if needed
        if 'search_query' in args and args['search_query']:
            query = args.pop('search_query')
            # Map to first available parameter if none match exactly
            if tool_params and not any(k in args for k in tool_params):
                first_param = next(iter(tool_params))
                args[first_param] = query
        
        result = execute_tool(tool_name, args, client)
        print(colored("Tool execution completed", "green"))
        
        # Special handling for streaming responses (e.g., from LLM tools)
        if isinstance(result, dict) and result.get('direct_stream') and 'result' in result:
            stream = result['result']
            full_response = ""
            print("\nStreaming response:")
            for chunk in stream:
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        print(content, end='', flush=True)
                        full_response += content
            print("\n")
            return {"result": full_response}
            
        return result
    except Exception as e:
        print(colored(f"Error running tool: {str(e)}", "red"))
        return None

# CLI interface
if __name__ == "__main__":
    # Validate command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 standalone_tools.py <tool_name> [parameters_json]")
        print("Example: python3 standalone_tools.py get_hacker_news '{\"limit\": 5}'")
        print("Or: python3 standalone_tools.py <tool_name> <search_query>")
        sys.exit(1)
    
    tool_name = sys.argv[1]
    args = {}
    
    # Handle both JSON parameters and simple search query
    if len(sys.argv) > 2:
        try:
            # Try to parse as JSON first
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            # If not JSON, treat as search query
            args = {"search_query": sys.argv[2]}
    
    print(f"\nExecuting {tool_name} with args: {args}")
    result = run_tool(tool_name, **args)
    if isinstance(result, dict) and 'result' in result:
        print("Result:", result['result']) 