# utils/search_utils.py

import os
from typing import List, Dict, Optional, Union, Tuple
from duckduckgo_search import DDGS
import requests
import json
from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError, BadRequestError
import openai
import uuid
from PIL import Image
from io import BytesIO
import time

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
        self.max_retries = 2
        self.retry_delay = 1  # seconds

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform a search using the Brave Search API with retries and validation.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Processed search results
        """
        # Validate query length per API requirements
        if not query or len(query) > 400 or len(query.split()) > 50:
            print("❌ Invalid query: Must be between 1-400 chars and max 50 words")
            return []

        for attempt in range(self.max_retries):
            try:
                headers = {
                    "X-Subscription-Token": self.api_key,
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip"
                }
                
                params = {
                    "q": query,
                    "count": min(max_results, 20),  # API max is 20
                    "offset": 0,
                    "search_lang": "en",
                    "country": "us",  # Lowercase as per API example
                    "safesearch": "moderate",
                    "text_decorations": False,
                    "spellcheck": True
                }
                
                print(f"🦁 Brave Search attempt {attempt + 1}/{self.max_retries}")
                print(f"Request URL: {self.base_url}")
                print(f"Request params: {params}")
                
                response = requests.get(self.base_url, headers=headers, params=params)
                
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 429:
                    print(f"⚠️ Brave Search rate limit hit on attempt {attempt + 1}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                
                response.raise_for_status()
                
                try:
                    data = response.json()
                    print(f"Response data keys: {data.keys()}")
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to decode JSON response: {str(e)}")
                    print(f"Raw response content: {response.text[:500]}...")
                    if attempt < self.max_retries - 1:
                        continue
                    return []
                
                # Check for error messages in response
                if "error" in data:
                    print(f"⚠️ Brave Search API error: {data['error']}")
                    if attempt < self.max_retries - 1:
                        continue
                    return []
                
                # Get web results from the correct location in response
                web_results = data.get("web", {}).get("results", [])
                if not web_results:
                    print("⚠️ No web results found in response")
                    print(f"Available data keys: {data.keys()}")
                    if attempt < self.max_retries - 1:
                        continue
                    return []
                
                results = []
                for result in web_results[:max_results]:
                    # Skip non-family-friendly results if present
                    if not result.get("family_friendly", True):
                        continue
                        
                    results.append(SearchResult(
                        title=result.get("title", "No title"),
                        url=result.get("url", ""),
                        description=result.get("description", "No description")
                    ))
                
                if not results:
                    print("⚠️ Failed to parse any valid results from response")
                    if attempt < self.max_retries - 1:
                        continue
                    return []
                
                print(f"✅ Brave Search succeeded with {len(results)} results")
                return results
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Brave Search request failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
            except Exception as e:
                print(f"❌ Brave Search unexpected error: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
        
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


class ImageSearchResult:
    def __init__(self, title: str, url: str, thumbnail_url: str, width: Optional[int] = None, height: Optional[int] = None):
        self.title = title
        self.url = url
        self.thumbnail_url = thumbnail_url
        self.width = width
        self.height = height
        self.uuid = str(uuid.uuid4())[:5]

# Add new abstract provider for image search
class ImageSearchProvider(SearchProvider):
    def image_search(self, query: str, max_results: int = 10) -> List[ImageSearchResult]:
        raise NotImplementedError

# Add Brave image search provider
class BraveImageSearchProvider(BraveSearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)  # Initialize parent with API key
    
    def image_search(self, query: str, max_results: int = 10) -> List[ImageSearchResult]:
        try:
            headers = {"X-Subscription-Token": self.api_key}
            params = {
                "q": query,
                "count": max_results,
                "search_lang": "en",
                "country": "us"
            }
            response = requests.get("https://api.search.brave.com/res/v1/images/search", 
                                 headers=headers, 
                                 params=params)
            response.raise_for_status()
            data = response.json()
            
            return [
                ImageSearchResult(
                    title=img.get("title", "No title"),
                    url=img["properties"]["url"],
                    thumbnail_url=img["thumbnail"]["src"],
                    width=img.get("width"),
                    height=img.get("height")
                ) for img in data.get("results", [])
            ]
        except Exception as e:
            print(f"Brave image search failed: {str(e)}")
            return []

class SerperImageSearchProvider(SerperSearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)  # Initialize parent with API key
    
    def image_search(self, query: str, max_results: int = 10) -> List[ImageSearchResult]:
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "q": query,
                "num": max_results
            }
            
            response = requests.post(
                "https://google.serper.dev/images",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                ImageSearchResult(
                    title=img.get("title", "No title"),
                    url=img["imageUrl"],
                    thumbnail_url=img["thumbnailUrl"],
                    width=img.get("imageWidth"),
                    height=img.get("imageHeight")
                ) for img in data.get("images", [])
            ]
        except Exception as e:
            print(f"Serper image search failed: {str(e)}")
            return []

# Resilient search mechanism that tries multiple search providers
class ResilientSearcher:
    def __init__(self):
        """
        Initialize search providers based on available API keys.
        Prioritizes Brave search with multiple attempts before falling back.
        """
        # Debug logging to understand provider initialization
        print("🕵️ Initializing Search Providers:")
        print(f"BRAVE_API_KEY present: {bool(os.getenv('BRAVE_API_KEY'))}")
        print(f"TAVILY_API_KEY present: {bool(os.getenv('TAVILY_API_KEY'))}")

        # Initialize Brave provider first if available
        self.brave_provider = BraveSearchProvider() if os.getenv("BRAVE_API_KEY") else None
        
        # Fallback providers
        self.fallback_providers = [
            TavilySearchProvider() if os.getenv("TAVILY_API_KEY") else None,
            SerperSearchProvider() if os.getenv("SERPER_API_KEY") else None,
            JinaSearchProvider() if os.getenv("JINA_API_KEY") else None,
            DDGSearchProvider(),  # Always available as a fallback
            SerpApiSearchProvider() if os.getenv("SERPAPI_API_KEY") else None,
        ]
        
        # Additional debug logging to show active providers
        print("🔍 Active Providers:")
        if self.brave_provider:
            print(" - BraveSearchProvider (Primary)")
        print("Fallback Providers:")
        for provider in self.fallback_providers:
            if provider:
                print(f" - {type(provider).__name__}")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Attempt to search using Brave first with multiple attempts before falling back.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
        
        Returns:
            List[SearchResult]: Search results from the first successful provider
        """
        print(f"🔎 Attempting to search with query: {query}")
        
        # Try Brave first if available
        if self.brave_provider:
            print("🦁 Attempting Brave Search as primary provider")
            results = self.brave_provider.search(query, max_results)
            if results:
                return results
            print("⚠️ Brave Search returned no results, falling back to other providers")
        
        # Fall back to other providers
        for provider in self.fallback_providers:
            if provider is not None:
                print(f"Trying fallback provider: {type(provider).__name__}")
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
    
def perform_image_search(objective: str, max_results: int = 10, llm_client=None) -> List[ImageSearchResult]:
    """High-level image search function with query optimization"""
    search_params = generate_search_query(objective, llm_client)
    searcher = ResilientSearcher()
    return searcher.image_search(search_params['query'], max_results)


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