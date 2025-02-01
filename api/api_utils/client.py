import os
import logging
from openai import OpenAI
from .log_utils import get_helicone_config
from .llm_utils import LLMParams

def get_llm_client(gateway: str = 'openrouter') -> OpenAI:
    """
    Get an initialized OpenAI client with appropriate configuration.
    
    Args:
        gateway (str): The gateway to use (openrouter, google, openai, etc.)
    
    Returns:
        OpenAI: Configured OpenAI client instance
    """
    try:
        # Get gateway configuration
        base_url, api_key = LLMParams.get_gateway_credentials(gateway)
        
        # Get Helicone configuration if using OpenRouter
        headers = {}
        if gateway == 'openrouter':
            helicone_config = get_helicone_config()
            base_url = helicone_config['base_url']
            headers.update(helicone_config['headers'])
            headers.update({
                "HTTP-Referer": "https://github.com/chrisb34/hubgpt",
                "X-Title": "HubGPT"
            })
        
        # Initialize client with configuration
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers=headers
        )
        
        logging.info(f"OpenAI client initialized successfully for gateway: {gateway}")
        return client
        
    except Exception as e:
        error_msg = f"Error initializing OpenAI client for gateway {gateway}: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg) 