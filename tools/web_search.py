# tools/web_search.py

from utils.search_utils import perform_search
from termcolor import cprint
import json

def execute(query, max_results=10, llm_client=None):
    """
    Performs a web search using multiple search providers and returns ranked results.
    
    Args:
        query (str): The search query or objective
        max_results (int): Maximum number of results to return
        llm_client: LLM client for query optimization
        
    Returns:
        dict: Search results and metadata
    """
    try:
        cprint(f"🔎 Starting web search for: {query}", "blue")
        
        # Perform the search using resilient searcher
        search_results = perform_search(
            objective=query,
            max_results=max_results,
            llm_client=llm_client
        )
        
        if not search_results:
            return {
                "status": "error",
                "message": "No search results found",
                "results": []
            }

        # Format results for better readability
        formatted_results = []
        for idx, result in enumerate(search_results, 1):
            formatted_results.append({
                "rank": idx,
                "title": result["title"],
                "url": result["url"],
                "description": result["description"]
            })

        cprint(f"✅ Found {len(formatted_results)} results", "green")
        
        return {
            "status": "success",
            "message": f"Found {len(formatted_results)} results",
            "results": formatted_results,
            "query": query
        }

    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        cprint(error_msg, "red")
        return {
            "status": "error",
            "message": error_msg,
            "results": []
        }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Performs a comprehensive web search using multiple search providers (Brave, Tavily, DuckDuckGo, etc.). "
            "The tool optimizes the search query using AI and returns ranked results. "
            "Use this tool when you need to find current information about any topic, "
            "verify facts, or gather data from multiple sources. "
            "Results include titles, URLs, and descriptions from various web pages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query or research objective. Can be a natural language question "
                        "or description of what you're looking for. The query will be optimized "
                        "automatically for best results."
                    )
                },
                "max_results": {
                    "type": "integer",
                    "description": (
                        "Maximum number of search results to return. Default is 10. "
                        "The actual number might be lower depending on available results."
                    ),
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}