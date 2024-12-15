# utils/scrape_utils.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from typing import Optional, List
from urllib.parse import urlparse

def clean_text(text: str) -> str:
    """Clean and format text for markdown."""
    if not text:
        return ""
    return ' '.join(text.split())


class Scraper:
    def scrape(self, url: str) -> str:
        """Scrape content from a URL and return markdown content."""
        raise NotImplementedError


class BasicScraper(Scraper):
    def scrape(self, url: str) -> str:
        """Scrape content using requests and BeautifulSoup with enhanced resilience."""
        try:
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,  # Total number of retries
                backoff_factor=0.1,  # Exponential backoff
                status_forcelist=[500, 502, 503, 504],  # Retry on these status codes
                allowed_methods=["HEAD", "GET", "OPTIONS"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            
            # Create a session with the retry adapter
            session = requests.Session()
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            # Enhanced headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            # Increased timeout and verify SSL
            response = session.get(
                url, 
                headers=headers, 
                timeout=15,  # Increased timeout
                verify=True  # Ensure SSL verification
            )
            response.raise_for_status()

            # Rest of the scraping logic remains the same...
            # (previous BeautifulSoup parsing code)

        except requests.exceptions.RequestException as e:
            print(f"Comprehensive scraping error for {url}: {str(e)}")
            return f"Failed to scrape {url}: {str(e)}\n\n"


class ResilientScraper:
    def __init__(self):
        self.providers: List[Scraper] = [BasicScraper()]  # Add more scraper classes as needed

    def scrape(self, url: str) -> str:
        """Try scraping with each provider until one succeeds."""
        for provider in self.providers:
            try:
                return provider.scrape(url)
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed: {str(e)}")
        return f"All scraping methods failed for {url}"
