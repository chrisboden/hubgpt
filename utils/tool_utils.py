# utils/tool_utils.py

import os
import sys
import importlib
import logging
import json
import streamlit as st
from typing import Dict, Any
from inspect import signature

# Global dictionaries to store registered tools and their metadata
# TOOL_REGISTRY maps tool names to their executable functions
# TOOL_METADATA_REGISTRY stores additional information about each tool
TOOL_REGISTRY: Dict[str, Any] = {}
TOOL_METADATA_REGISTRY: Dict[str, Any] = {}

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
    - Requires each tool module to have an 'execute' function
    - Optionally supports 'TOOL_METADATA' for additional tool information
    
    Args:
        tools_dir (str): Path to the directory containing tool modules
    """
    global TOOL_REGISTRY, TOOL_METADATA_REGISTRY
    
    # Validate tools directory existence
    if not os.path.exists(tools_dir):
        st.error(f"Tools directory '{tools_dir}' not found.")
        logging.error(f"Tools directory '{tools_dir}' not found.")
        st.stop()

    # Add tools directory to Python's module search path
    sys.path.insert(0, tools_dir)  

    # Iterate through Python files in the tools directory
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = os.path.splitext(filename)[0]
            try:
                # Dynamically import the module
                module = importlib.import_module(module_name)
                
                # Register tool's execute function if available
                if hasattr(module, 'execute') and callable(getattr(module, 'execute')):
                    TOOL_REGISTRY[module_name] = module.execute
                else:
                    logging.warning(f"Module '{module_name}' does not have an 'execute' function. Skipping.")
                    continue

                # Register tool metadata if available
                if hasattr(module, 'TOOL_METADATA'):
                    TOOL_METADATA_REGISTRY[module_name] = module.TOOL_METADATA
                else:
                    logging.warning(f"Module '{module_name}' does not have 'TOOL_METADATA'. Skipping metadata.")
            except Exception as e:
                # Comprehensive error logging for module import failures
                logging.error(f"Error loading module '{module_name}': {e}")


def execute_tool(tool_name: str, args: Dict[str, Any], llm_client=None) -> Dict[str, Any]:
    """
    Execute a specified tool with given arguments and standardize its response.
    
    This function handles complex tool execution scenarios:
    - Validates tool availability
    - Supports optional LLM client injection
    - Handles various response formats (JSON, string)
    - Provides robust error handling and logging
    
    Key Features:
    - Dynamically determines tool function signature
    - Injects LLM client if the tool's function supports it
    - Attempts to parse responses as JSON
    - Returns a standardized response dictionary
    - Supports follow_on_instructions parameter for chaining tool calls
    - Returns both tool result and any follow-on instructions for further processing
    
    Args:
        tool_name (str): Name of the tool to execute
        args (Dict[str, Any]): Arguments for the tool
        llm_client (optional): Language model client for advanced tools
    
    Returns:
        Dict[str, Any]: Standardized tool execution result
    """
    # Check if the specified tool is available in the registry
    if tool_name not in TOOL_REGISTRY:
        st.error(f"Tool '{tool_name}' is not available.")
        logging.error(f"Tool '{tool_name}' is not available.")
        return {}

    try:
        logging.info(f"Executing tool '{tool_name}' with arguments: {args}")
        
        # Extract follow_on_instructions if present
        follow_on_instructions = args.pop("follow_on_instructions", [])
        
        tool_func = TOOL_REGISTRY[tool_name]
        tool_metadata = TOOL_METADATA_REGISTRY.get(tool_name, {})
        tool_signature = signature(tool_func)
        
        # Execute tool
        if llm_client and 'llm_client' in tool_signature.parameters:
            response = tool_func(llm_client=llm_client, **args)
        else:
            response = tool_func(**args)

        # Handle string responses
        if isinstance(response, str):
            if "```json" in response:
                response = response.split("```json")[1]
                if "```" in response:
                    response = response.split("```")[0]
            response = response.strip()
            
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                response = {"result": response}

        # Add follow-on instructions to response if present
        if follow_on_instructions:
            response["follow_on_instructions"] = follow_on_instructions

        return {
            **response,
            "direct_stream": tool_metadata.get("direct_stream", False)
        }

    except Exception as e:
        st.error(f"Error executing tool '{tool_name}': {e}")
        logging.error(f"Error executing tool '{tool_name}': {e}")
        return {}