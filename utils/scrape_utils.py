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
            # Configure retry strategy to handle transient errors
            retry_strategy = Retry(
                total=3,  # Total number of retries
                backoff_factor=0.1,  # Exponential backoff factor
                status_forcelist=[500, 502, 503, 504],  # Retry on these HTTP status codes
                allowed_methods=["HEAD", "GET", "OPTIONS"]  # Methods to which retries are applied
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            
            # Create a session with the retry adapter to manage HTTP connections
            session = requests.Session()
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            # Enhanced headers to mimic a browser, improving the chances of successful scraping
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            # Increased timeout to allow more time for the server to respond and SSL verification to ensure secure connections
            response = session.get(
                url, 
                headers=headers, 
                timeout=15,  # Timeout in seconds
                verify=True  # Enable SSL verification
            )
            response.raise_for_status()  # Raise an exception for HTTP error responses

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract and clean text from the parsed HTML
            text = soup.get_text(separator='\n', strip=True)
            markdown_content = clean_text(text)

            return markdown_content

        except requests.exceptions.RequestException as e:
            # Print an error message if a request exception occurs
            cprint(f"Comprehensive scraping error for {url}: {str(e)}", "red")
            return f"Failed to scrape {url}: {str(e)}\n\n"


class ResilientScraper:
    def __init__(self):
        # Initialize a list of scraper providers, starting with BasicScraper
        self.providers: List[Scraper] = [BasicScraper()]  # Add more scraper classes as needed

    def scrape(self, url: str) -> str:
        """Try scraping with each provider until one succeeds."""
        for provider in self.providers:
            try:
                # Attempt to scrape the URL using the current provider
                return provider.scrape(url)
            except Exception as e:
                # Print an error message if the current provider fails
                cprint(f"Provider {provider.__class__.__name__} failed: {str(e)}", "yellow")
        # Return a failure message if all providers fail
        return f"All scraping methods failed for {url}"
