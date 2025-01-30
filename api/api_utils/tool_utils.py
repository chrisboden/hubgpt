# utils/tool_utils.py

import os
import sys
import importlib
import logging
import json
from typing import Dict, Any, Optional
from inspect import signature

logger = logging.getLogger(__name__)

# Global dictionaries to store registered tools and their metadata
# TOOL_REGISTRY maps tool names to their executable functions
# TOOL_METADATA_REGISTRY stores additional information about each tool
TOOL_REGISTRY: Dict[str, Any] = {}
TOOL_METADATA_REGISTRY: Dict[str, Any] = {}

def load_tools(tools_dir: str) -> None:
    """
    Load all tools from the specified directory.
    
    Args:
        tools_dir (str): Directory containing tool modules
    """
    global TOOL_REGISTRY, TOOL_METADATA_REGISTRY
    
    # Get the absolute path of the tools directory
    if not os.path.isabs(tools_dir):
        tools_dir = os.path.abspath(tools_dir)
    
    # Add tools directory to Python path if not already there
    if tools_dir not in sys.path:
        sys.path.append(tools_dir)
    
    try:
        # Iterate through Python files in the tools directory
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]  # Remove .py extension
                try:
                    # Import the module
                    module = importlib.import_module(module_name)
                    
                    # Register the tool if it has the required attributes
                    if hasattr(module, 'execute') and hasattr(module, 'TOOL_METADATA'):
                        TOOL_REGISTRY[module_name] = module.execute
                        TOOL_METADATA_REGISTRY[module_name] = module.TOOL_METADATA
                        logger.info(f"Successfully loaded tool: {module_name}")
                    else:
                        logger.warning(f"Skipping {module_name}: missing required attributes")
                        
                except Exception as e:
                    logger.error(f"Error loading tool {module_name}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error loading tools from directory {tools_dir}: {str(e)}")
        raise

def execute_tool(tool_name: str, args: Dict[str, Any], llm_client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Execute a registered tool with the provided arguments.
    
    Args:
        tool_name (str): Name of the tool to execute
        args (Dict[str, Any]): Arguments to pass to the tool
        llm_client (Optional[Any]): LLM client instance if needed
        
    Returns:
        Dict[str, Any]: Result from the tool execution
        
    Raises:
        KeyError: If tool_name is not found in registry
        ValueError: If invalid arguments are provided
    """
    if tool_name not in TOOL_REGISTRY:
        error_msg = f"Tool '{tool_name}' not found in registry"
        logger.error(error_msg)
        raise KeyError(error_msg)
    
    tool_func = TOOL_REGISTRY[tool_name]
    
    try:
        # Get the function signature
        sig = signature(tool_func)
        
        # Prepare arguments
        valid_args = {}
        for param_name in sig.parameters:
            if param_name == 'llm_client':
                valid_args['llm_client'] = llm_client
            elif param_name in args:
                valid_args[param_name] = args[param_name]
        
        # Execute the tool
        result = tool_func(**valid_args)
        return {"result": result} if result is not None else {}
        
    except Exception as e:
        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)