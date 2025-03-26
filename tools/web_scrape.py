# tools/web_scrape.py

import os
from termcolor import cprint
from utils.file_utils import get_safe_filepath
from utils.scrape_utils import ResilientScraper
from urllib.parse import urlparse
import json  # Add this import

def process_scraped_content(content, llm_client):
    """
    Process scraped content using an LLM to clean and structure it while preserving links.
    
    Args:
        content (str): Raw scraped content
        llm_client: LLM client for processing

    Returns:
        str: Processed content with preserved links
    """
    try:
        # Truncate content if it's extremely long
        if len(content) > 50000:
            content = content[:50000]
        
        # Updated LLM messages to explicitly preserve links
        processing_messages = [
            {"role": "system", "content": """You are an expert content processor. Clean and structure the given web scraped content, removing irrelevant information, ads, or boilerplate text. 

IMPORTANT: You must preserve ALL links in markdown format [text](url). Convert any HTML links (<a href="url">text</a>) to markdown format.

Your output should:
1. Be in clean markdown format
2. Preserve all original links as [text](url)
3. Maintain the content's information hierarchy
4. Remove clutter while keeping all valuable information
5. Be comprehensive and well-structured"""},
            {"role": "user", "content": f"Process this content, ensuring all links are preserved:\n\n{content}"}
        ]
        
        # Attempt LLM call with higher max tokens to accommodate link preservation
        response = llm_client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=processing_messages,
            max_tokens=6000,  # Increased to handle longer content with links
            temperature=0.2
        )
        
        processed_content = response.choices[0].message.content
        
        # Verify link preservation with a warning if no links found
        if "[" not in processed_content or "](" not in processed_content:
            cprint("Warning: No markdown links found in processed content. Links may have been lost.", "yellow")
            
        return processed_content
    
    except Exception as e:
        cprint(f"Error processing scraped content: {str(e)}", "red")
        return content

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