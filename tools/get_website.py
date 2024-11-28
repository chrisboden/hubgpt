# tools/get_website.py
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.search_utils import perform_search
import os

def clean_text(text):
    """Clean and format text for markdown"""
    if not text:
        return ""
    # Remove extra whitespace and newlines
    text = ' '.join(text.split())
    return text

def scrape_url(url):
    """Scrape content from a URL and return formatted markdown"""
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

        # Track unique content
        unique_text_blocks = set()

        # Extract content-rich divs
        for div in soup.find_all('div'):
            # Filter out common non-content areas
            class_or_id = ' '.join(div.get("class", [])) + ' ' + (div.get("id") or "")
            if any(term in class_or_id for term in ['header', 'footer', 'nav', 'sidebar', 'menu']):
                continue
            
            # Check if div has substantial unique text
            text = clean_text(div.get_text())
            if len(text) > 50 and text not in unique_text_blocks:
                unique_text_blocks.add(text)
                markdown_content += f"{text}\n\n"
        
        # Extract other tags like paragraphs and headings, avoiding duplicates
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

def process_scrape_with_llm(scrape_path, llm_client):
    """Send the contents of scrape.md to the LLM for FAQ generation"""
    try:
        # Read scrape content
        with open(scrape_path, 'r', encoding='utf-8') as f:
            scrape_content = f.read()
        
        # Define LLM messages
        faq_messages = [
            {"role": "system", "content": "You are an expert summariser. For a given body of content on a topic, you are able to analyse that content and generate a comprehensive FAQ that helps a reader understand the topic in detail."},
            {"role": "user", "content": f"Please generate FAQ for the content below:\n\n{scrape_content}"}
        ]
        
        print("Sending scrape content to LLM for FAQ generation")
        response = llm_client.chat.completions.create(
            model="google/gemini-flash-1.5-8b",
            messages=faq_messages,
            max_tokens=8000,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing scrape with LLM: {str(e)}")
        return f"An error occurred while generating FAQ: {str(e)}"
    

def execute(query, llm_client=None):
    print("get website tool called")
    print("Starting get website function")

    try:
        print(f"Performing search for query: '{query}'")
        search_results = perform_search(query, max_results=10)
        
        if not search_results:
            print("No results found")
            return "No results found for the query"
            
        # Format results for LLM
        formatted_results = "\n".join(
            f"Title: {res['title']}\nURL: {res['url']}\nDescription: {res['description']}\n"
            for res in search_results
        ).strip()
        print(f"These are the search results for the top urls for the search term:\n{formatted_results}")
        # First LLM call to rank results
        initial_messages = [
            {"role": "system", "content": "You are an expert URL Analysis Agent specialising in identifying official company websites from search results. Your expertise includes understanding URL structures, domain naming conventions, and digital business presence patterns, with particular insight into Australian and technology sector websites.\n\nCONTEXT FOR DISAMBIGUATION:\nThere are many organisations that share the same name so a key part of your role is to disambiguate the search results to determine which url most likely matches our intent. The following context should assist you:\n\n\nThis app is an AI Agent in service of the Peregian Digital Hub, a startup and technology Hub on the Sunshine Coast of Queensland Australia.\n\nTASK:\nAnalyse the provided search results and re-rank them based on their likelihood of being the official website for our target organization. For each result, examine the URL structure, domain name patterns, and page indicators to determine authenticity and relevance.\n\nConsider these ranking factors:\n1. Domain authenticity indicators (e.g., .com.au for Australian businesses, clean domains without excessive subdomains, domains that may use ai domain extensions)\n2. URL structure professionalism (avoiding sites like medium.com/company-name or facebook.com/company-name)\n3. Technology sector indicators\n4. Startup ecosystem relevance\n\nFor each search result, provide:\n1. A detailed analysis of why the URL might or might not be the official website\n2. Confidence indicators based on URL structure and domain patterns\n3. Red flags or positive signals in the URL composition\n\nOUTPUT FORMAT:\nRespond with a JSON array of objects, ordered by likelihood (most likely first), as follows:\n 'results':[\n    {\n        'url': 'the url of the search result',\n        'description': 'the description from the search result',\n        'title': 'the title from the search result',\n        'rationale': 'Detailed reasoning for this ranking, including analysis of:\n            - Domain authenticity\n            - URL structure\n            - Geographical/sector relevance\n            - Any red flags or positive signals'\n    }\n]\n\nSPECIAL CONSIDERATIONS:\n- Be skeptical of social media profiles or third-party hosting platforms\n- Consider startup ecosystem platforms (e.g., crunchbase, angel.list) as secondary sources\n- Give weight to technology sector indicators in the URL structure\n\nFor ambiguous cases, explain your reasoning process for ranking decisions, particularly when distinguishing between similar company names or branches of the same organization."},
            {
                "role": "user",
                "content": f"The query is:\n\n {query} \n\nAnalyse these search results and return the 5 most relevant results ranked by importance:\n\n{formatted_results}"
            }
        ]

        print("Sending search results to LLM for analysis")
        initial_response = llm_client.chat.completions.create(
            model="openai/gpt-4o",
            messages=initial_messages,
            max_tokens=2000,
            temperature=1,
            response_format={"type": "json_object"}
        )
        
        response_content = initial_response.choices[0].message.content.strip()
        print(f"LLM response received successfully with these results:\n{response_content}")
        
        # Clean up JSON string
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            response_content = response_content.split("```")[1].strip()
            
        ranked_results = json.loads(response_content)
        
        if isinstance(ranked_results, dict):
            if "results" in ranked_results:
                ranked_results = ranked_results["results"]
                print(f"These are the ranked results:\n{ranked_results}")
            else:
                ranked_results = [ranked_results]
        
        if isinstance(ranked_results, list) and len(ranked_results) > 0:
            first_result = ranked_results[0]
            top_url = first_result.get('url')
            
            if not top_url:
                return "Could not extract URL from top result"
            
            print(f"STARTING SITE-SPECIFIC SEARCH FOR: site:{top_url}")
            site_results = perform_search(f"site:{top_url}", max_results=10)
            
            if not site_results:
                print("No site-specific results found")
                return "No site-specific results found"
                
            # Format site-specific results for LLM
            site_formatted_results = "\n".join(
                f"Title: {res['title']}\nURL: {res['url']}\nDescription: {res['description']}\n"
                for res in site_results
            ).strip()
            print(f"These are the site results{site_formatted_results}")
            site_messages = [
                {"role": "system", "content": "You are an expert search result analyzer specialized in identifying web pages that contain rich organizational context. Your task is to analyze a set of search results from a single organization's website and identify the 5 pages most likely to contain valuable contextual information about the organization.\n\nOBJECTIVE:\nAnalyze and re-rank search results based on their likelihood of containing key organizational information such as:\n- Company overview and mission\n- Products and services offered\n- Value proposition\n- Leadership team and key personnel\n- Location and contact information\n- Pricing and cost structures\n- Social media presence and channels\n\nANALYSIS CRITERIA:\nFor each search result, evaluate:\n1. URL structure (e.g., /about-us, /company, /team, /contact)\n2. Page title relevance\n3. Description content signals\n4. Likelihood of containing multiple context data points\n\nRANKING METHODOLOGY:\n- Prioritize pages that typically contain comprehensive organizational information\n- Higher rank for pages likely to contain multiple information categories\n- Consider standard website architecture patterns\n- Value main section pages over deep subsidiary pages\n\nCommon high-value pages include:\n- About/Company pages\n- Home pages\n- Contact pages\n- Team/Leadership pages\n- Services/Products overview pages\n\nOUTPUT REQUIREMENTS:\nRespond with a JSON array of the top 5 most promising URLs, structured as follows:\n\n'results':[\n    {\n        'url': 'page URL',\n        'title': 'page title',\n        'rationale': 'clear explanation of why this page is likely to contain valuable organizational context'\n    }\n]\n\nRANKING RATIONALE GUIDELINES:\n- Explain specific signals in the URL, title, or description that suggest valuable content\n- Identify which types of organizational information the page is likely to contain\n- Note any patterns or conventions that inform your ranking decision\n\nFor each result, think step-by-step:\n1. What does the URL structure suggest about the page's content?\n2. What organizational information is this page likely to contain?\n3. Is this a primary/overview page or a subsidiary/detail page?\n4. How many different types of valuable context might this page contain?"},
                {
                    "role": "user",
                    "content": f"Analyze these pages from {top_url} and identify the 5 most informative ones:\n\n{site_formatted_results}"
                }
            ]
            
            final_response = llm_client.chat.completions.create(
                model="openai/gpt-4o",
                messages=site_messages,
                max_tokens=2000,
                temperature=1,
                response_format={"type": "json_object"}
            )
            
            try:
                response_content = final_response.choices[0].message.content
                print(f"Raw response content: {response_content}")
                results = json.loads(response_content)
                print(f"Parsed results: {results}")
                
                urls = []
                # Handle different response formats
                if isinstance(results, dict):
                    if "results" in results:
                        # Extract URLs from results array
                        for result in results["results"]:
                            if isinstance(result, dict) and "url" in result:
                                urls.append(result["url"])
                    elif "url" in results:
                        # Single result case
                        urls.append(results["url"])
                elif isinstance(results, list):
                    # Direct array of results
                    for result in results:
                        if isinstance(result, dict) and "url" in result:
                            urls.append(result["url"])
                
                if not urls:
                    return "No valid URLs found in response"
                
                # Ensure we have up to 5 unique URLs
                urls = list(dict.fromkeys(urls))[:5]  # Remove duplicates and limit to 5
                print(f"Extracted URLs: {urls}")
                
                # Sort URLs by length (typically puts homepage first)
                urls = sorted(urls, key=len)
                
                markdown_path = 'scrape.md'
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Scrape Results for: {query}\n\n")
                    f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    # Scrape each URL
                    for i, url in enumerate(urls, 1):
                        print(f"Scraping URL {i} of {len(urls)}: {url}")
                        content = scrape_url(url)
                        f.write(f"---\n\n{content}\n")
                
                print(f"Scrape results saved to {markdown_path}")


                # Process scrape content with LLM
                final_output = process_scrape_with_llm(markdown_path, llm_client)
                
                return final_output
                
            except Exception as e:
                print(f"Error processing results: {str(e)}")
                print(f"Response content: {response_content}")
                return f"Error processing results: {str(e)}"
        
        return "No valid results found"
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_website",
        "description": "Get the website url for a given term",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute, based on the user's message. Determine the intent and rephrase to get the best possible results."
                }
            },
            "required": ["query"]
        }
    }
}