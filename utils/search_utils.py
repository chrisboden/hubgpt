# utils/search_utils.py

import os
from typing import List, Dict, Optional, Union
from duckduckgo_search import DDGS
import requests
import json
from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError, BadRequestError
import openai

# Represents a structured search result with title, URL, and description
class SearchResult:
    def __init__(self, title: str, url: str, description: str):
        """
        Initialize a search result with key metadata.
        
        Args:
            title (str): The title of the search result
            url (str): The web URL of the result
            description (str): A brief description or snippet of the result
        """
        self.title = title
        self.url = url
        self.description = description


# Abstract base class defining the interface for search providers
class SearchProvider:
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Abstract method to be implemented by concrete search providers.
        
        Args:
            query (str): The search query string
            max_results (int): Maximum number of results to return
        
        Raises:
            NotImplementedError: If not overridden by subclass
        """
        raise NotImplementedError


# Concrete search provider using the Brave Search API
class BraveSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Brave Search provider with an API key.
        
        Args:
            api_key (Optional[str]): Brave API key, defaults to environment variable
        
        Raises:
            ValueError: If no API key is provided
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("Brave API key is required")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the Brave Search API.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            headers = {"X-Subscription-Token": self.api_key}
            params = {"q": query, "count": max_results}
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            return [
                SearchResult(
                    title=result.get("title", "No title"),
                    url=result.get("url", ""),
                    description=result.get("description", "No description")
                ) for result in data.get("results", [])[:max_results]
            ]
        except Exception as e:
            print(f"Brave search failed: {str(e)}")
            return []


# Concrete search provider using the Serper API
class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Serper provider with an API key.
        
        Args:
            api_key (Optional[str]): Serper API key, defaults to environment variable
        
        Raises:
            ValueError: If no API key is provided
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key is required")
        self.base_url = "https://google.serper.dev/search"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the Serper API.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            headers = {"X-API-KEY": self.api_key}
            payload = {"q": query, "num": max_results}
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return [
                SearchResult(
                    title=result.get("title", "No title"),
                    url=result.get("link", ""),
                    description=result.get("snippet", "No description")
                ) for result in data.get("organic", [])[:max_results]
            ]
        except Exception as e:
            print(f"Serper search failed: {str(e)}")
            return []


# Concrete search provider using the Jina API
class JinaSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Jina provider with an API key.
        
        Args:
            api_key (Optional[str]): Jina API key, defaults to environment variable
        
        Raises:
            ValueError: If no API key is provided
        """
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key is required")
        self.base_url = "https://api.jina.ai/v1/search"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the Jina API.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"query": query, "limit": max_results}
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return [
                SearchResult(
                    title=result.get("title", "No title"),
                    url=result.get("url", ""),
                    description=result.get("snippet", "No description")
                ) for result in data.get("results", [])[:max_results]
            ]
        except Exception as e:
            print(f"Jina search failed: {str(e)}")
            return []


# Concrete search provider using the DuckDuckGo API
class DDGSearchProvider(SearchProvider):
    def __init__(self):
        """
        Initialize the DuckDuckGo search provider.
        """
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the DuckDuckGo API.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            return [
                SearchResult(
                    title=result.get("title", "No title"),
                    url=result.get("link", ""),
                    description=result.get("body", "No description")
                ) for result in results[:max_results]
            ]
        except Exception as e:
            print(f"DuckDuckGo search failed: {str(e)}")
            return []


# Concrete search provider using the SerpApi
class SerpApiSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the SerpApi provider with an API key.
        
        Args:
            api_key (Optional[str]): SerpApi API key, defaults to environment variable
        
        Raises:
            ValueError: If no API key is provided
        """
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SerpApi API key is required")
        self.base_url = "https://serpapi.com/search"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the SerpApi.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            params = {
                "q": query,
                "num": max_results,
                "api_key": self.api_key,
                "engine": "google"
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return [
                SearchResult(
                    title=result.get("title", "No title"),
                    url=result.get("link", ""),
                    description=result.get("snippet", "No description")
                ) for result in data.get("organic_results", [])[:max_results]
            ]
        except Exception as e:
            print(f"SerpApi search failed: {str(e)}")
            return []


# Concrete search provider using the Tavily API
class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Tavily search provider with an API key.
        
        Args:
            api_key (Optional[str]): Tavily API key, defaults to environment variable
        
        Raises:
            MissingAPIKeyError: If no API key is provided
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise MissingAPIKeyError("Tavily API key is required")
        self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the Tavily API.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        try:
            response = self.client.search(query, max_results=max_results)
            return [
                SearchResult(
                    title=r.get("title", "No title"),
                    url=r.get("url", ""),
                    description=r.get("content", "No description")
                ) for r in response.get("results", [])[:max_results]
            ]
        except (InvalidAPIKeyError, UsageLimitExceededError, BadRequestError) as e:
            print(f"Tavily search failed: {str(e)}")
            return []


# Resilient search mechanism that tries multiple search providers
class ResilientSearcher:
    def __init__(self):
        """
        Initialize search providers based on available API keys.
        
        Dynamically creates search providers using environment variables,
        allowing fallback and flexibility in search strategies.
        """
        # Debug logging to understand provider initialization
        print("🕵️ Initializing Search Providers:")
        print(f"BRAVE_API_KEY present: {bool(os.getenv('BRAVE_API_KEY'))}")
        print(f"TAVILY_API_KEY present: {bool(os.getenv('TAVILY_API_KEY'))}")

        # Ordered list of search providers with conditional initialization
        self.providers = [
            BraveSearchProvider() if os.getenv("BRAVE_API_KEY") else None,
            TavilySearchProvider() if os.getenv("TAVILY_API_KEY") else None,
            SerperSearchProvider() if os.getenv("SERPER_API_KEY") else None,
            JinaSearchProvider() if os.getenv("JINA_API_KEY") else None,
            DDGSearchProvider(),  # Always available as a fallback
            SerpApiSearchProvider() if os.getenv("SERPAPI_API_KEY") else None,
        ]
        
        # Additional debug logging to show active providers
        print("🔍 Active Providers:")
        for provider in self.providers:
            if provider:
                print(f" - {type(provider).__name__}")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Attempt to search using multiple providers in a resilient manner.
        
        Tries each configured search provider sequentially, returning 
        results from the first successful provider.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Search results from the first successful provider
        """
        print(f"🔎 Attempting to search with query: {query}")
        
        for provider in self.providers:
            if provider is not None:
                print(f"Trying provider: {type(provider).__name__}")
                try:
                    results = provider.search(query, max_results)
                    if results:
                        print(f"✅ Successfully retrieved results from {type(provider).__name__}")
                        return results
                except Exception as e:
                    print(f"❌ {type(provider).__name__} failed: {str(e)}")
        
        return []


# Function to generate an optimized search query using an LLM
def generate_search_query(objective: str, llm_client=None) -> Dict[str, Union[str, int]]:
    """
    Generate an optimized search query using an LLM.
    
    Uses an LLM to intelligently craft a search query and determine 
    the optimal number of results based on the given objective.
    
    Args:
        objective (str): The fuzzy search objective
        llm_client (optional): Language model client for query generation
    
    Returns:
        Dict containing refined search query and result count
        - 'query': Optimized search query string
        - 'max_results': Recommended number of results
    
    Raises:
        ValueError: If no LLM client is provided
    """
    print(f"🔍 Generating search query for objective: {objective}")
    
    # Validate LLM client availability
    if llm_client is None:
        raise ValueError("LLM client is required for search query generation")

    # Prepare structured prompt for LLM to generate search query
    query_generation_messages = [
        {
            "role": "system", 
            "content": """You are the Google search world champion. Your task is to evaluate the objective you have been given and think step by step to:
1. Craft an effective search query that is likely to generate the most useful results
2. Determine the optimal number of search results that are required for performing the task at hand

You will respond with a JSON object containing two keys:
- 'query': A suggested search query string
- 'max_results': An integer representing the ideal number of search results.

You know when to keep a search broad and when to narrow it. For example, when trying to find the definitive url for a particular organisation, person or concept, you tend to keep the query very broad. When searching for a person by name like Bob Smylie you know to use quotes to search on their name like this "Bob Smylie" and when you are need to find pages on a given site you know to use the "site: url" search filter. You only use other operands or narrowing search terms when you need to filter for very specific results.

Your goal is to design a query that best matches the objective you have been given."""
        },
        {
            "role": "user", 
            "content": f"This is the objective of the search query:\n\n {objective}"
        }
    ]
   
    try:
        # Generate search query using LLM
        response = llm_client.chat.completions.create(
            model="openai/gpt-4o",  # Use the model from the passed client
            messages=query_generation_messages,
            max_tokens=200,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Extract and parse the LLM's response
        response_content = response.choices[0].message.content.strip()
        
        # Clean up potential JSON formatting issues
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        
        # Parse the JSON response
        parsed_response = json.loads(response_content)

        print(f"🤖: The llm has designed the search query as follows:{parsed_response}")
        
        # Validate and set defaults, ensuring reasonable result count
        return {
            "query": parsed_response.get('query', objective),
            "max_results": max(5, min(parsed_response.get('max_results', 10), 15))  # Clamp between 5 and 15
        }
    
    except Exception as e:
        # Fallback mechanism if query generation fails
        print(f"Error generating search query: {e}")
        return {
            "query": objective,
            "max_results": 10  # Default fallback
        }
    
def perform_search(objective: str, max_results: int = 10, llm_client=None) -> List[Dict[str, str]]:
    """
    High-level search function that combines query generation and execution.
    
    Generates an optimized search query using an LLM, then performs 
    a resilient search across multiple providers.
    
    Args:
        objective (str): The fuzzy search objective
        max_results (int): Override for maximum number of results
        llm_client (optional): Language model client for query generation
    
    Returns:
        List of search results as dictionaries with title, URL, and description
    """
    # Generate optimized search query and parameters
    search_params = generate_search_query(objective, llm_client)
    
    # Determine final result count, respecting optional override
    final_max_results = max_results if max_results != 10 else search_params['max_results']
    
    # Perform the search using the generated query
    print(f"🤖: Now performing the search as follows:{search_params}")
    searcher = ResilientSearcher()
    results = searcher.search(search_params['query'], final_max_results)
    
    print(f"🤖: These are the (unranked) search results:{results}")
    return [
        {
            "title": result.title,
            "url": result.url,
            "description": result.description
        } for result in results
    ]