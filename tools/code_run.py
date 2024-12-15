# tools/code_run.py
import sys
import subprocess
import os
from pathlib import Path
from termcolor import cprint

def execute(filename, client=None):
    """
    Executes a Python script and returns its output.
    Passes through OpenAI client for tool access.
    """
    try:
        # Set environment variables for the subprocess
        env = os.environ.copy()
        if client:
            # Pass API configuration to subprocess
            env["OPENROUTER_API_KEY"] = client.api_key
            env["API_BASE_URL"] = client.base_url

        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            error_msg = f"Error: {result.stderr}"
            cprint(error_msg, "red")
            return error_msg
            
        cprint(f"✅ Code executed successfully", "green")
        return result.stdout or result.stderr
    except Exception as e:
        error_msg = f"Error executing file: {str(e)}"
        cprint(error_msg, "red")
        return error_msg

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "code_run",
        "description": "Executes a Python script file and returns its output. The script will have access to all agent tools.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the Python script file to execute (must end in .py)"
                }
            },
            "required": ["filename"]
        }
    }
}