# tools/get_news.py

def execute(llm_client=None, search_query=None):
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

    # Make the completion call
    try:
        response = llm_client.chat.completions.create(
            model="perplexity/llama-3.1-sonar-huge-128k-online",
            messages=messages,
            temperature=1.15,
            max_tokens=8092,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stream=False  # Set to false to get full response
        )
        
        # Return a serializable dictionary with the content and metadata
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "total_tokens": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get news analysis: {str(e)}"
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
    }
}