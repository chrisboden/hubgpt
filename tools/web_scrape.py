# tools/web_scrape.py

import os
from termcolor import cprint
from utils.file_utils import get_safe_filepath
from utils.scrape_utils import ResilientScraper
from urllib.parse import urlparse
import json  # Add this import

def process_scraped_content(content, llm_client):
    """
    Process scraped content using an LLM to clean, structure, or enhance it.
    
    Args:
        content (str): Raw scraped content
        llm_client: LLM client for processing

    Returns:
        str: Processed content
    """
    try:
        # Truncate content if it's extremely long
        if len(content) > 50000:
            content = content[:50000]
        
        # Define LLM messages for initial content processing
        processing_messages = [
            {"role": "system", "content": "You are an expert content processor. Clean and structure the given web scraped content, removing any irrelevant information, ads, or boilerplate text. Your cleaned output should be an information-dense and comprehensive summary that loses none of the key information. This summary will be used as context by an AI agent"},
            {"role": "user", "content": f"Here is the content:\n\n{content}"}
        ]
        
        # Attempt LLM call
        response = llm_client.chat.completions.create(
            model="google/gemini-flash-1.5-8b",
            messages=processing_messages,
            max_tokens=4000,
            temperature=0.2
        )
        
        # Extract processed content
        processed_content = response.choices[0].message.content
        return processed_content
    
    except Exception as e:
        cprint(f"Error processing scraped content: {str(e)}", "red")
        return content  # Return original content if processing fails

def execute(url, filename, llm_client=None):
    """
    Scrapes content from a URL and saves it to a specified file.

    Args:
        url (str): The URL to scrape
        filename (str): The name of the file to save the content to
        llm_client (optional): LLM client for content processing

    Returns:
        dict: A dictionary containing status, message, and additional metadata
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                "status": "error",
                "message": "Error: Invalid URL. Must be a complete URL with http:// or https://",
                "url": url
            }

        # Get safe filepath
        filepath, error = get_safe_filepath(filename, create_dirs=True)
        if error:
            return {
                "status": "error",
                "message": error,
                "url": url
            }

        # Log the scraping attempt
        cprint(f"Attempting to scrape URL: {url}", "blue")
        cprint(f"Will save to: {filepath}", "blue")

        # Use the ResilientScraper to get content
        scraper = ResilientScraper()
        content = scraper.scrape(url)

        if content.startswith("Failed to scrape") or content.startswith("All scraping methods failed"):
            return {
                "status": "error",
                "message": content,
                "url": url
            }

        # Optional: Process content with LLM if client is provided
        if llm_client:
            try:
                content = process_scraped_content(content, llm_client)
            except Exception as e:
                cprint(f"LLM content processing failed: {str(e)}", "yellow")
                # Continue with original content if processing fails

        # Save the scraped content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        cprint(f"Successfully scraped content and saved to: {filename}", "green")
        return {
            "status": "success",
            "message": f"Content scraped and saved to '{filename}'",
            "bytes_written": len(content),
            "url": url
        }

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        cprint(error_msg, "red")
        return {
            "status": "error",
            "message": error_msg,
            "url": url
        }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "web_scrape",
        "description": (
            "Fetches and extracts textual content from a specified URL and saves it to a file. "
            "The content is saved in markdown format with proper formatting and structure. "
            "Use this tool to gather information from web pages for learning, data analysis, "
            "or incorporating external knowledge into your responses. "
            "This is helpful when you need to access the latest information or data not available "
            "in your existing knowledge base."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "The full URL of the website to scrape content from. "
                        "Must include the protocol (e.g., 'http://' or 'https://'). "
                        "Ensure the URL is correct and accessible."
                    )
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "The name of the file to save the scraped content to. "
                        "Can include subdirectories, e.g., 'scraped_data/webpage.txt'. "
                        "Directories will be created if they don't exist. "
                        "Content will be saved in markdown format."
                    )
                }
            },
            "required": ["url", "filename"]
        }
    }
}