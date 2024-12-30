# tools/get_news.py

import logging
from termcolor import colored
from utils.log_utils import log_llm_request, log_llm_response

def execute(llm_client=None, search_query=None):
    print(colored("Starting get_news tool execution", "cyan"))
    
    if not llm_client:
        raise ValueError("LLM client is required for this tool")
    
    if not search_query:
        raise ValueError("Subject is required")

    # Define messages for the completion
    messages = [
        {
            "role": "system",
            "content": "You are a highly reliable source of web search content"
        },
        {
            "role": "user",
            "content": f"{search_query}"
        }
    ]

    # Prepare API parameters
    api_params = {
        "model": "perplexity/llama-3.1-sonar-huge-128k-online",
        "messages": messages,
        "temperature": 1.15,
        "max_tokens": 8092,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stream": True
    }

    print(colored(f"Preparing news search with query: {search_query}", "yellow"))
    
    # Log the API request parameters
    log_llm_request(api_params)

    # Make the completion call
    try:
        print(colored("Making LLM API call for news search", "yellow"))
        stream = llm_client.chat.completions.create(**api_params)
        
        print(colored("Successfully received stream response", "green"))
        
        # Log that we're returning a direct stream
        logging.info("\n" + "="*50 + "\nDIRECT STREAM RESPONSE:\n" + "="*50 + 
                    "\nReturning stream object for direct UI updates\n" + "="*50)
        
        return {
            "result": stream,
            "direct_stream": True
        }
        
    except Exception as e:
        error_msg = f"Failed to get news analysis: {str(e)}"
        print(colored(error_msg, "red"))
        logging.error(error_msg)
        return {
            "error": error_msg
        }

# Tool metadata remains the same
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_news",
        "description": "Use this tool if you need to get up to date news from the web about a specific subject or topic. This tool provides the latest news and works best with a detailed search query. Make sure to rephrase the user's question as a detailed search_query",
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "A detailed search query to use for the news search, e.g. 'provide the current major news updates about artificial intelligence'"
                }
            },
            "required": [
                "search_query"
            ]
        }
    },
    "direct_stream": True
}