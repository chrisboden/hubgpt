# utils/log_utils.py

import os
import json
import logging
from typing import Dict, Any
from termcolor import colored

# Global flags for logging control
DETAILED_LLM_LOGGING = True  # Controls whether detailed LLM logs are enabled
INCLUDE_RAW_RESPONSE = False  # Controls whether raw LLM responses are logged

# Exported functions for external use
__all__ = ['setup_logging', 'toggle_detailed_llm_logging', 'log_llm_request', 'log_llm_response']

def setup_logging(project_root: str) -> logging.Logger:
    """Configure and setup logging for the application
    
    Args:
        project_root: Root directory of the project where logs will be stored
        
    Returns:
        Configured logger instance
    """
    # Ensure the logs directory exists
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Remove any existing handlers to prevent duplicate logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure logging with both file and console handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, "app.log")),  # Log to file
            logging.StreamHandler()  # Log to console
        ]
    )

    return logging.getLogger(__name__)

def toggle_detailed_llm_logging(enable: bool = True):
    """Toggle detailed LLM logging on/off
    
    Args:
        enable: Boolean to enable/disable detailed logging
    """
    global DETAILED_LLM_LOGGING
    DETAILED_LLM_LOGGING = enable
    print(colored(f"Detailed LLM logging {'enabled' if enable else 'disabled'}", "yellow"))

def toggle_raw_response_logging(enable: bool = False):
    """Toggle raw response logging on/off
    
    Args:
        enable: Boolean to enable/disable raw response logging
    """
    global INCLUDE_RAW_RESPONSE
    INCLUDE_RAW_RESPONSE = enable
    print(colored(f"Raw response logging {'enabled' if enable else 'disabled'}", "yellow"))

def log_llm_request(params: Dict[str, Any]):
    """Log LLM request parameters if detailed logging is enabled
    
    Args:
        params: Dictionary containing LLM request parameters
    """
    if not DETAILED_LLM_LOGGING:
        return
        
    try:
        # Skip logging if parameters are empty or invalid
        if not params or not any(params.values()):
            return
            
        # Create a formatted version of the parameters for cleaner logging
        formatted_params = {
            "model": params.get("model", "unknown"),
            "messages": params.get("messages", []),
            "temperature": params.get("temperature", None),
            "max_tokens": params.get("max_tokens", None),
            "tools": params.get("tools", []),
            "tool_choice": params.get("tool_choice", None)
        }
        
        # Only log if we have meaningful content (messages or tools)
        if formatted_params["messages"] or formatted_params["tools"]:
            logging.info("\n" + "="*50 + "\nLLM REQUEST:\n" + "="*50 + "\n" + 
                        json.dumps(formatted_params, indent=2) + "\n" + "="*50)
        
    except Exception as e:
        logging.error(f"Error logging LLM request: {str(e)}")

def log_llm_response(response: Dict[str, Any]):
    """Log LLM response if detailed logging is enabled
    
    Args:
        response: Dictionary containing LLM response data
    """
    if not DETAILED_LLM_LOGGING:
        return
        
    try:
        # Skip empty responses
        if not response:
            return
            
        # Log raw response if enabled (useful for debugging)
        if INCLUDE_RAW_RESPONSE:
            logging.info("\n" + "="*50 + "\nRAW LLM RESPONSE:\n" + "="*50)
            if isinstance(response, (str, dict)):
                logging.info(str(response))
            else:
                # Handle OpenAI response objects by extracting raw data
                logging.info(str(getattr(response, 'model_dump', lambda: str(response))()))
        
        # Always log the formatted version for better readability
        if isinstance(response, dict):
            logging.info("\n" + "="*50 + "\nFORMATTED LLM RESPONSE:\n" + "="*50 + "\n" + 
                        json.dumps(response, indent=2) + "\n" + "="*50)
    except Exception as e:
        logging.error(f"Error logging LLM response: {str(e)}")