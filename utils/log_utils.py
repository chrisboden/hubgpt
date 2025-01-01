# utils/log_utils.py

import os
import json
import logging
from typing import Dict, Any
from termcolor import colored
from logging.handlers import RotatingFileHandler

# Global flags for logging control
DETAILED_LLM_LOGGING = True
INCLUDE_RAW_RESPONSE = False

__all__ = ['setup_logging', 'toggle_detailed_llm_logging', 'log_llm_request', 'log_llm_response']

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
    
    def emit(self, record):
        """Emit a record and check line count"""
        if self.max_lines and self.line_count >= self.max_lines:
            self.doRollover()
            
        super().emit(record)
        self.line_count += 1

def setup_logging(project_root: str) -> logging.Logger:
    """Configure and setup logging for the application"""
    # Ensure the logs directory exists
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with line count rotation
    file_handler = LineCountRotatingFileHandler(
        filename=os.path.join(logs_dir, "app.log"),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
        encoding='utf-8',
        max_lines=1000  # Keep last 1000 lines
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    print(colored("Logging configured with line count rotation", "green"))
    return logger

# Rest of the functions remain unchanged
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
            
        formatted_params = {
            "model": params.get("model", "unknown"),
            "messages": params.get("messages", []),
            "temperature": params.get("temperature", None),
            "max_tokens": params.get("max_tokens", None),
            "tools": params.get("tools", []),
            "tool_choice": params.get("tool_choice", None)
        }
        
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
            
        if INCLUDE_RAW_RESPONSE:
            logging.info("\n" + "="*50 + "\nRAW LLM RESPONSE:\n" + "="*50)
            if isinstance(response, (str, dict)):
                logging.info(str(response))
            else:
                logging.info(str(getattr(response, 'model_dump', lambda: str(response))()))
        
        if isinstance(response, dict):
            logging.info("\n" + "="*50 + "\nFORMATTED LLM RESPONSE:\n" + "="*50 + "\n" + 
                        json.dumps(response, indent=2) + "\n" + "="*50)
    except Exception as e:
        logging.error(f"Error logging LLM response: {str(e)}")