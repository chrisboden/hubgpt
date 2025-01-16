# utils/tool_utils.py

import os
import sys
import importlib
import logging
import json
from typing import Dict, Any, Optional
from inspect import signature

# Check if streamlit is available
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Global dictionaries to store registered tools and their metadata
TOOL_REGISTRY: Dict[str, Any] = {}
TOOL_METADATA_REGISTRY: Dict[str, Any] = {}

def handle_error(message: str, error_type: str = "error"):
    """Unified error handling for both Streamlit and non-Streamlit environments"""
    logging.error(message)
    if STREAMLIT_AVAILABLE:
        if error_type == "error":
            st.error(message)
        elif error_type == "warning":
            st.warning(message)
        if error_type == "error":
            st.stop()
    else:
        if error_type == "error":
            raise RuntimeError(message)
        elif error_type == "warning":
            print(f"Warning: {message}")

def load_tools(tools_dir: str):
    """
    Dynamically load and register tool modules from a specified directory.
    
    This function performs several critical tasks:
    - Validates the existence of the tools directory
    - Adds the directory to Python's module search path
    - Discovers and imports Python files as potential tools
    - Registers tools with executable functions
    - Captures and logs any loading errors
    
    Key Considerations:
    - Skips files starting with '__' (like __init__.py)
    - Validates tool modules have required attributes
    - Handles import and registration errors gracefully
    
    Args:
        tools_dir (str): Path to directory containing tool modules
        
    Returns:
        Dict[str, Any]: Dictionary of loaded tools
    """
    if not os.path.exists(tools_dir):
        handle_error(f"Tools directory not found: {tools_dir}")
        return TOOL_REGISTRY

    # Add tools directory to Python path if not already there
    if tools_dir not in sys.path:
        sys.path.append(tools_dir)
    
    # Clear existing registries
    TOOL_REGISTRY.clear()
    TOOL_METADATA_REGISTRY.clear()
    
    # Load each Python file in the tools directory
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Register if module has execute function
                if hasattr(module, 'execute'):
                    TOOL_REGISTRY[module_name] = module
                    
                    # Register metadata if available
                    if hasattr(module, 'TOOL_METADATA'):
                        TOOL_METADATA_REGISTRY[module_name] = module.TOOL_METADATA
                    
            except Exception as e:
                handle_error(f"Error loading tool {module_name}: {str(e)}", "warning")
    
    return TOOL_REGISTRY

def execute_tool(tool_name: str, args: Dict[str, Any], llm_client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Execute a registered tool with provided arguments.
    
    This function:
    1. Validates the tool exists
    2. Validates and processes the arguments
    3. Executes the tool with proper error handling
    4. Returns the tool's result
    
    Args:
        tool_name (str): Name of the tool to execute
        args (Dict[str, Any]): Arguments to pass to the tool
        llm_client (Optional[Any]): LLM client instance if needed
        
    Returns:
        Dict[str, Any]: Tool execution results
        
    Raises:
        RuntimeError: If tool execution fails
    """
    if tool_name not in TOOL_REGISTRY:
        handle_error(f"Tool '{tool_name}' not found in registry.")
    
    tool = TOOL_REGISTRY[tool_name]
    
    try:
        # Get the execute function from the module
        execute_func = tool.execute
        
        # Get the function signature
        sig = signature(execute_func)
        
        # Prepare arguments
        valid_args = {}
        for param_name in sig.parameters:
            if param_name == 'llm_client':
                valid_args['llm_client'] = llm_client
            elif param_name in args:
                valid_args[param_name] = args[param_name]
        
        # Execute the tool
        result = execute_func(**valid_args)
        return {"result": result} if result is not None else {}
        
    except Exception as e:
        handle_error(f"Error executing tool '{tool_name}': {str(e)}")
        return {}