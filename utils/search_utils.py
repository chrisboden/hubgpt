# utils/search_utils.py

import os
from typing import List, Dict, Optional, Union
from duckduckgo_search import DDGS
import requests
import json
from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError, BadRequestError
import openai


class SearchResult:
    def __init__(self, title: str, url: str, description: str):
        self.title = title
        self.url = url
        self.description = description


class SearchProvider:
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        raise NotImplementedError


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise MissingAPIKeyError("Tavily API key is required")
        self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
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


class JinaSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        if not self.api_key:
            raise ValueError("Jina API key is required")
        self.base_url = "https://s.jina.ai"

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            url = f"{self.base_url}/{query}"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-Retain-Images": "none"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return [
                SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("url", ""),
                    description=item.get("description", "No description")
                ) for item in data.get("data", [])[:max_results]
            ]
        except Exception as e:
            print(f"Jina search failed: {str(e)}")
            return []


class DDGSearchProvider(SearchProvider):
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [
                    SearchResult(
                        title=r.get("title", "No title"),
                        url=r.get("href", ""),
                        description=r.get("body", "No description")
                    ) for r in results
                ]
        except Exception as e:
            print(f"DDG search failed: {str(e)}")
            return []


class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("Serper API key is required")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            url = "https://google.serper.dev/search"
            payload = json.dumps({
                "q": query,
                "num": max_results
            })
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("link", ""),
                    description=item.get("snippet", "No description")
                ))
            return results
        except Exception as e:
            print(f"Serper search failed: {str(e)}")
            return []


class SerpApiSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SerpAPI key is required")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": max_results
            }
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic_results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("link", ""),
                    description=item.get("snippet", "No description")
                ))
            return results
        except Exception as e:
            print(f"SerpAPI search failed: {str(e)}")
            return []


class BraveSearchProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("Brave Search API key is required")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip", 
                "X-Subscription-Token": self.api_key
            }
            params = {
                "q": query,
                "count": max_results
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("web", {}).get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", "No title"),
                    url=item.get("url", ""),
                    description=item.get("description", "No description")
                ))
            return results
        except Exception as e:
            print(f"Brave Search failed: {str(e)}")
            return []



class ResilientSearcher:
    def __init__(self):
        # Debug logging to understand provider initialization
        print("🕵️ Initializing Search Providers:")
        print(f"BRAVE_API_KEY present: {bool(os.getenv('BRAVE_API_KEY'))}")
        print(f"TAVILY_API_KEY present: {bool(os.getenv('TAVILY_API_KEY'))}")

        self.providers = [
            BraveSearchProvider() if os.getenv("BRAVE_API_KEY") else None,
            TavilySearchProvider() if os.getenv("TAVILY_API_KEY") else None,
            SerperSearchProvider() if os.getenv("SERPER_API_KEY") else None,
            JinaSearchProvider() if os.getenv("JINA_API_KEY") else None,
            DDGSearchProvider(),
            SerpApiSearchProvider() if os.getenv("SERPAPI_API_KEY") else None,
        ]
        
        # Additional debug logging
        print("🔍 Active Providers:")
        for provider in self.providers:
            if provider:
                print(f" - {type(provider).__name__}")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
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


def generate_search_query(objective: str, llm_client=None) -> Dict[str, Union[str, int]]:
    """
    Generate an optimized search query and number of results using an LLM
    
    Args:
        objective (str): The fuzzy objective to search for
        llm_client (optional): The LLM client to use for query generation
    
    Returns:
        Dict with 'query' and 'max_results'
    """
    print(f"🔍 Generating search query for objective: {objective}")
    # Validate LLM client
    if llm_client is None:
        raise ValueError("LLM client is required for search query generation")

    # Prepare the LLM messages
    query_generation_messages = [
        {
            "role": "system", 
            "content": """You are the Google search world champion. Your task is to evaluate the objective you have been given and think step by step to:
1. Craft an effective search query that is likely to generate the most useful results
2. Determine the optimal number of search results that are required for performing the task at hand

You will respond with a JSON object contianing two keys:
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
        # Make LLM call to generate query
        response = llm_client.chat.completions.create(
            model="openai/gpt-4o",  # Use the model from the passed client
            messages=query_generation_messages,
            max_tokens=200,
            temperature=1,
            response_format={"type": "json_object"}
        )

        # Extract and parse the response
        response_content = response.choices[0].message.content.strip()
        
        # Clean up JSON string if needed
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        
        # Parse the JSON
        parsed_response = json.loads(response_content)

        print(f"🤖: The llm has designed the search query as follows:{parsed_response}")
        
        # Validate and set defaults
        return {
            "query": parsed_response.get('query', objective),
            "max_results": max(5, min(parsed_response.get('max_results', 10), 15))  # Clamp between 5 and 15
        }
    

    except Exception as e:
        print(f"Error generating search query: {e}")
        return {
            "query": objective,
            "max_results": 10  # Default fallback
        }
    
def perform_search(objective: str, max_results: int = 10, llm_client=None) -> List[Dict[str, str]]:
    """
    Perform a search with an LLM-generated query
    
    Args:
        objective (str): The fuzzy objective to search for
        max_results (int): Maximum number of search results to return (optional)
        llm_client (optional): The LLM client to use for query generation
    
    Returns:
        List of search result dictionaries
    """
    # Generate the optimized search query and max results
    search_params = generate_search_query(objective, llm_client)
    
    # Use LLM-suggested max_results, but allow override from function parameter
    final_max_results = max_results if max_results != 10 else search_params['max_results']
    
    # Perform the search using the generated query
    searcher = ResilientSearcher()
    print(f"🤖: Now performing the search as follows:{search_params}")
    results = searcher.search(search_params['query'], final_max_results)
    print(f"🤖: These are the (unranked) search results:{results}")
    return [
        {
            "title": result.title,
            "url": result.url,
            "description": result.description
        } for result in results
    ]