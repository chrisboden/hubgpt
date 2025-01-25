import os
from openai import OpenAI
from .log_utils import get_helicone_config

def get_llm_client() -> OpenAI:
    """
    Initialize and return an OpenAI client configured for OpenRouter.
    Uses environment variables for API key and Helicone configuration.
    """
    helicone_config = get_helicone_config()
    
    client = OpenAI(
        base_url=helicone_config['base_url'],
        api_key=os.getenv("OPENROUTER_API_KEY"),
        default_headers=helicone_config['headers']
    )
    
    return client 