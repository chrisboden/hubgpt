# tools/web_read_page.py

import os
import requests
from termcolor import colored
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def execute(url: str, **kwargs):
    """
    Fetches and returns a clean markdown version of a webpage using Jina API.
    
    Parameters:
    - url (str): The URL to read and convert to markdown
    
    Returns:
    - dict: Contains the markdown content or error message
    """
    try:
        # Get Jina API key from environment
        jina_api_key = os.getenv('JINA_API_KEY')
        if not jina_api_key:
            return {"error": "JINA_API_KEY not found in environment variables"}
        
        # Prepare the Jina API request
        jina_url = f'https://r.jina.ai/{url}'
        headers = {
            'Authorization': f'Bearer {jina_api_key}'
        }
        
        print(colored(f"Fetching content from: {url}", "blue"))
        
        # Make the API request
        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()
        
        print(colored("Successfully fetched and converted content", "green"))
        
        return {
            "result": response.text,
            "follow_on_instructions": []
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(colored(error_msg, "red"))
        return {"error": error_msg}

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "web_read_page",
        "description": "Fetches and returns a clean markdown version of a webpage.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to read and convert to markdown"
                }
            },
            "required": ["url"]
        }
    }
}