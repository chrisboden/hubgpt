import os
import logging
from openai import OpenAI
from .log_utils import get_helicone_config

def get_llm_client() -> OpenAI:
    """
    Get an initialized OpenAI client with appropriate configuration.
    
    The client is configured with:
    - Base URL from environment or default OpenRouter URL
    - API key from environment
    - Helicone headers if enabled
    - Default headers for OpenRouter
    
    Returns:
        OpenAI: Configured OpenAI client instance
    """
    try:
        # Get Helicone configuration
        helicone_config = get_helicone_config()
        
        # Initialize client with base configuration
        client = OpenAI(
            base_url=helicone_config['base_url'],
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                **helicone_config['headers'],
                "HTTP-Referer": "https://github.com/chrisb34/hubgpt",  # Required for OpenRouter
                "X-Title": "HubGPT"  # Optional but recommended
            }
        )
        
        logging.info("OpenAI client initialized successfully")
        return client
        
    except Exception as e:
        error_msg = f"Error initializing OpenAI client: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg) 