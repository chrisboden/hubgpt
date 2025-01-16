# utils/log_utils.py

import os
import json
import logging
from typing import Dict, Any
from termcolor import colored
from logging.handlers import RotatingFileHandler

# Global flags for logging control
DETAILED_LLM_LOGGING = True
INCLUDE_RAW_RESPONSE = True
USE_HELICONE = False  # Default to not using Helicone

__all__ = [
    'setup_logging', 
    'toggle_detailed_llm_logging', 
    'log_llm_request', 
    'log_llm_response',
    'toggle_helicone',
    'get_helicone_config'
]

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

class LineCountRotatingFileHandler(RotatingFileHandler):
    """A handler that rotates based on both size and line count"""
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, 
                 encoding=None, delay=False, max_lines=None):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.max_lines = max_lines
        
        # Initialize line count from existing file
        if os.path.exists(filename):
            with open(filename, 'r', encoding=encoding or 'utf-8') as f:
                self.line_count = sum(1 for _ in f)
        else:
            self.line_count = 0
    
    def doRollover(self):
        """Override doRollover to keep last N lines"""
        if self.stream:
            self.stream.close()
            self.stream = None
            
        if self.max_lines:
            try:
                # Read all lines from the current file
                with open(self.baseFilename, 'r', encoding=self.encoding) as f:
                    lines = f.readlines()
                
                # Keep only the last max_lines
                lines = lines[-self.max_lines:]
                
                # Write the last max_lines back to the file
                with open(self.baseFilename, 'w', encoding=self.encoding) as f:
                    f.writelines(lines)
                
                self.line_count = len(lines)
            except Exception as e:
                print(colored(f"Error during log rotation: {e}", "red"))
        
        if not self.delay:
            self.stream = self._open()

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

def setup_logging(project_root: str) -> None:
    """Configure and setup logging for the application"""
    
    # Check if logging is already configured
    if hasattr(setup_logging, '_initialized'):
        return
    
    # Ensure the logs directory exists
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        print(colored(f"Creating logs directory at {logs_dir}", "yellow"))
        os.makedirs(logs_dir)

    log_file = os.path.join(logs_dir, "app.log")
    print(colored(f"Setting up logging to {log_file}", "cyan"))

    # Remove any existing handlers from the root logger
    logging.root.handlers = []

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    try:
        # File handler with line count rotation
        file_handler = LineCountRotatingFileHandler(
            filename=log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5,
            encoding='utf-8',
            max_lines=1000  # Keep last 1000 lines
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Add console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s:%(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        print(colored(f"Successfully set up file logging to {log_file}", "green"))
        
        # Mark logging as initialized
        setup_logging._initialized = True
        
        # Test log write
        logging.info("Logging system initialized")
        
    except Exception as e:
        print(colored(f"Error setting up file logging: {e}", "red"))
        raise

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