# utils/scrape_utils.py

import requests
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
        """Scrape content using requests and BeautifulSoup."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract title
            title = soup.title.string if soup.title else url

            # Start markdown with the title and source
            markdown_content = f"## {clean_text(title)}\n\n"
            markdown_content += f"Source: {url}\n\n"

            # Extract content-rich divs
            unique_text_blocks = set()
            for div in soup.find_all('div'):
                class_or_id = ' '.join(div.get("class", [])) + ' ' + (div.get("id") or "")
                if any(term in class_or_id for term in ['header', 'footer', 'nav', 'sidebar', 'menu']):
                    continue
                text = clean_text(div.get_text())
                if len(text) > 50 and text not in unique_text_blocks:
                    unique_text_blocks.add(text)
                    markdown_content += f"{text}\n\n"

            # Extract other tags like paragraphs and headings
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = clean_text(tag.get_text())
                if text and text not in unique_text_blocks:
                    unique_text_blocks.add(text)
                    if tag.name.startswith('h'):
                        level = int(tag.name[1])
                        markdown_content += f"{'#' * (level + 1)} {text}\n\n"
                    else:
                        markdown_content += f"{text}\n\n"

            return markdown_content
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
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
