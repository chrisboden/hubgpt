import os
import json
import logging
from typing import Dict, Any
from termcolor import colored

# Global flags for logging control
DETAILED_LLM_LOGGING = True
INCLUDE_RAW_RESPONSE = False
USE_HELICONE = False  # Default to not using Helicone

def toggle_helicone(enable: bool = False):
    """Toggle Helicone logging on/off"""
    global USE_HELICONE
    USE_HELICONE = enable
    print(colored(f"Helicone logging {'enabled' if enable else 'disabled'}", "yellow"))

def get_helicone_config() -> Dict[str, Any]:
    """Get Helicone configuration if enabled"""
    if not USE_HELICONE:
        return {
            "use_helicone": False,
            "base_url": os.getenv('API_BASE_URL', 'https://openrouter.ai/api/v1'),
            "headers": {}
        }
        
    helicone_key = os.getenv("HELICONE_API_KEY")
    if not helicone_key:
        return {
            "use_helicone": False,
            "base_url": os.getenv('API_BASE_URL', 'https://openrouter.ai/api/v1'),
            "headers": {}
        }
        
    return {
        "use_helicone": True,
        "base_url": "https://openrouter.helicone.ai/api/v1",
        "headers": {
            "Helicone-Auth": f"Bearer {helicone_key}",
            "Helicone-Cache-Enabled": "true",
            "Helicone-Property-App": "hubgpt"
        }
    }

def toggle_detailed_llm_logging(enable: bool = True):
    """Toggle detailed LLM logging on/off"""
    global DETAILED_LLM_LOGGING
    DETAILED_LLM_LOGGING = enable
    print(colored(f"Detailed LLM logging {'enabled' if enable else 'disabled'}", "yellow"))

def toggle_raw_response_logging(enable: bool = False):
    """Toggle raw response logging on/off"""
    global INCLUDE_RAW_RESPONSE
    INCLUDE_RAW_RESPONSE = enable
    print(colored(f"Raw response logging {'enabled' if enable else 'disabled'}", "yellow"))

def log_llm_request(params: Dict[str, Any]):
    """Log LLM request parameters if detailed logging is enabled"""
    if not DETAILED_LLM_LOGGING:
        return
        
    try:
        if not params or not any(params.values()):
            return
            
        def make_serializable(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, '__dict__'):
                return {k: make_serializable(v) for k, v in obj.__dict__.items() 
                       if not k.startswith('_')}
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(x) for x in obj]
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            return obj
            
        formatted_params = make_serializable({
            "model": params.get("model", "unknown"),
            "messages": params.get("messages", []),
            "temperature": params.get("temperature", None),
            "max_tokens": params.get("max_tokens", None),
            "tools": params.get("tools", []),
            "tool_choice": params.get("tool_choice", None)
        })
        
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
        if not response:
            return
            
        def make_serializable(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, '__dict__'):
                return {k: make_serializable(v) for k, v in obj.__dict__.items() 
                       if not k.startswith('_')}
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(x) for x in obj]
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            return obj
            
        if INCLUDE_RAW_RESPONSE:
            logging.info("\n" + "="*50 + "\nRAW LLM RESPONSE:\n" + "="*50)
            logging.info(str(response))
        
        formatted_response = make_serializable(response)
        if isinstance(formatted_response, dict):
            logging.info("\n" + "="*50 + "\nFORMATTED LLM RESPONSE:\n" + "="*50 + "\n" + 
                        json.dumps(formatted_response, indent=2) + "\n" + "="*50)
    except Exception as e:
        logging.error(f"Error logging LLM response: {str(e)}") 