# tools/code_write.py

import os
from pathlib import Path
from termcolor import cprint

def execute(filename, code):
    """Creates or overwrites a Python script with the provided code. Has access to existing tools and can import them for use in the code it writes."""
    try:
        # Add root directory to Python path in the generated code
        root_dir = str(Path(__file__).parent.parent)
        import_setup = f'''# Auto-generated imports for tool access
import sys
import os
from pathlib import Path

# Add project root to Python path
root_dir = "{root_dir}"
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Now you can import tools
from tools import use_ai, web_search, web_scrape, file_read, file_write

'''
        # Write the file with imports
        with open(filename, 'w') as f:
            f.write(import_setup + code)
        
        cprint(f"✅ Code written to {filename} with tool imports", "green")
        return f"Code written to {filename} with tool access setup."
    except Exception as e:
        error_msg = f"Error writing file: {str(e)}"
        cprint(error_msg, "red")
        return error_msg
    
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "code_write",
        "description": (
            "Creates or overwrites a Python script with the provided code. The script will automatically "
            "have access to all agent tools through pre-configured imports. "
            "\n\nExample usage patterns:"
            "\n1. Using the AI tool:"
            "\n   from tools import use_ai"
            "\n   result = use_ai.execute("
            "\n       messages=[{'role': 'user', 'content': 'Your prompt here'}]"
            "\n   )"
            "\n\n2. Using web search:"
            "\n   from tools import web_search"
            "\n   results = web_search.execute(query='Your search query')"
            "\n\n3. File operations:"
            "\n   from tools import file_read, file_write"
            "\n   content = file_read.execute('input.txt')"
            "\n   file_write.execute('output.txt', 'new content')"
            "\n\n4. Web scraping:"
            "\n   from tools import web_scrape"
            "\n   content = web_scrape.execute(url='https://example.com', filename='scraped.txt')"
            "\n\nThe code will have access to all standard Python libraries plus the agent's tool suite."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Name of the file to write to, including the `.py` extension. "
                        "Example: 'analysis.py' or 'data_processor.py'"
                    )
                },
                "code": {
                    "type": "string",
                    "description": (
                        "The Python code to write into the file. Can import and use any of the agent's tools:\n"
                        "- use_ai: For making AI API calls\n"
                        "- web_search: For searching the web\n"
                        "- web_scrape: For scraping web content\n"
                        "- file_read/write/delete: For file operations\n"
                        "- file_list: For listing directory contents\n"
                        "\nThe code should be properly indented Python code."
                    )
                }
            },
            "required": ["filename", "code"]
        }
    }
}