# utils/log_utils.py

import os
import json
import logging
from typing import Dict, Any
from termcolor import colored

# Global flag for detailed LLM logging
DETAILED_LLM_LOGGING = True

# Add these to explicitly declare what should be importable from this module
__all__ = ['setup_logging', 'toggle_detailed_llm_logging', 'log_llm_request', 'log_llm_response']

def setup_logging(project_root: str) -> logging.Logger:
    """Configure and setup logging for the application"""
    # Ensure the logs directory exists
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Remove any existing handlers to prevent conflicts
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, "app.log")),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

def toggle_detailed_llm_logging(enable: bool = True):
    """Toggle detailed LLM logging on/off"""
    global DETAILED_LLM_LOGGING
    DETAILED_LLM_LOGGING = enable
    print(colored(f"Detailed LLM logging {'enabled' if enable else 'disabled'}", "yellow"))

def log_llm_request(params: Dict[str, Any]):
    """Log LLM request parameters if detailed logging is enabled"""
    if not DETAILED_LLM_LOGGING:
        return
        
    try:
        # Only log if we have actual parameters
        if not params or not any(params.values()):
            return
            
        # Create a formatted version of the parameters
        formatted_params = {
            "model": params.get("model", "unknown"),
            "messages": params.get("messages", []),
            "temperature": params.get("temperature", None),
            "max_tokens": params.get("max_tokens", None),
            "tools": params.get("tools", []),
            "tool_choice": params.get("tool_choice", None)
        }
        
        # Only log if we have meaningful content
        if formatted_params["messages"] or formatted_params["tools"]:
            logging.info("\n" + "="*50 + "\nLLM REQUEST:\n" + "="*50 + "\n" + 
                        json.dumps(formatted_params, indent=2) + "\n" + "="*50)
        
    except Exception as e:
        logging.error(f"Error logging LLM request: {str(e)}")

def log_llm_response(response: Dict[str, Any]):
    """Log LLM response if detailed logging is enabled"""
    if not DETAILED_LLM_LOGGING:
        return
        
    try:
        # Skip empty responses
        if not response:
            return
            
        # Log the raw response first
        logging.info("\n" + "="*50 + "\nRAW LLM RESPONSE:\n" + "="*50)
        if isinstance(response, (str, dict)):
            logging.info(str(response))
        else:
            # For OpenAI response objects, try to get the raw data
            logging.info(str(getattr(response, 'model_dump', lambda: str(response))()))
        
        # Then log the formatted version if it's a dict
        if isinstance(response, dict):
            logging.info("\n" + "="*50 + "\nFORMATTED LLM RESPONSE:\n" + "="*50 + "\n" + 
                        json.dumps(response, indent=2) + "\n" + "="*50)
    except Exception as e:
        logging.error(f"Error logging LLM response: {str(e)}")