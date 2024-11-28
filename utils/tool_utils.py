# utils/tool_utils.py

import os
import sys
import importlib
import logging
import json
import streamlit as st
from typing import Dict, Any
from inspect import signature

TOOL_REGISTRY: Dict[str, Any] = {}
TOOL_METADATA_REGISTRY: Dict[str, Any] = {}

def load_tools(tools_dir: str):
    """
    Dynamically load all tool modules from the specified directory,
    and register their execute functions and metadata.
    """
    global TOOL_REGISTRY, TOOL_METADATA_REGISTRY
    if not os.path.exists(tools_dir):
        st.error(f"Tools directory '{tools_dir}' not found.")
        logging.error(f"Tools directory '{tools_dir}' not found.")
        st.stop()

    sys.path.insert(0, tools_dir)  # Add tools_dir to sys.path for module discovery

    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = os.path.splitext(filename)[0]
            try:
                module = importlib.import_module(module_name)
                # Register execute function
                if hasattr(module, 'execute') and callable(getattr(module, 'execute')):
                    TOOL_REGISTRY[module_name] = module.execute
                    logging.info(f"Loaded tool: {module_name}")
                else:
                    logging.warning(f"Module '{module_name}' does not have an 'execute' function. Skipping.")
                    continue

                # Register tool metadata
                if hasattr(module, 'TOOL_METADATA'):
                    TOOL_METADATA_REGISTRY[module_name] = module.TOOL_METADATA
                    logging.info(f"Loaded metadata for tool: {module_name}")
                else:
                    logging.warning(f"Module '{module_name}' does not have 'TOOL_METADATA'. Skipping metadata.")
            except Exception as e:
                logging.error(f"Error loading module '{module_name}': {e}")


def execute_tool(tool_name: str, args: Dict[str, Any], llm_client=None) -> Dict[str, Any]:
    """
    Executes the specified tool with given arguments and ensures proper JSON formatting of the response.
    """
    if tool_name not in TOOL_REGISTRY:
        st.error(f"Tool '{tool_name}' is not available.")
        logging.error(f"Tool '{tool_name}' is not available.")
        return {}

    try:
        logging.info(f"Executing tool '{tool_name}' with arguments: {args}")
        
        # Get the execute function for the specified tool
        tool_func = TOOL_REGISTRY[tool_name]
        tool_signature = signature(tool_func)
        
        # Execute the tool and get response
        if llm_client and 'llm_client' in tool_signature.parameters:
            response = tool_func(llm_client=llm_client, **args)
        else:
            response = tool_func(**args)

        # Clean up the response if it's a string containing JSON
        if isinstance(response, str):
            # Remove markdown formatting if present
            if "```json" in response:
                response = response.split("```json")[1]
                if "```" in response:
                    response = response.split("```")[0]
            response = response.strip()
            
            # Try to parse the string as JSON
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                logging.warning(f"Could not parse tool response as JSON: {response}")
                # If parsing fails, return the cleaned string
                return {"result": response}

        return response
    except Exception as e:
        st.error(f"Error executing tool '{tool_name}': {e}")
        logging.error(f"Error executing tool '{tool_name}': {e}")
        return {}