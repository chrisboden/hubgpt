# tools/get_research.py
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from utils.search_utils import perform_search
from utils.scrape_utils import ResilientScraper
from utils.ui_utils import update_spinner_status
import os


def process_scrape_with_llm(scrape_path, llm_client):
    if not os.path.exists(scrape_path):
        print(f"❌ ERROR: Scrape file does not exist at {scrape_path}")
        return "Error: Scrape file not found"
    
    # Verify file is readable
    try:
        with open(scrape_path, 'r', encoding='utf-8') as f:
            scrape_content = f.read()
        
        # Debug: Verify scrape content
        print(f"Scrape content length: {len(scrape_content)} characters")
        if not scrape_content:
            print("❌ ERROR: Scrape content is empty!")
            return "Error: No content to process"
        
        # Truncate content if it's extremely long
        if len(scrape_content) > 50000:
            scrape_content = scrape_content[:50000]
        
        # Define LLM messages
        faq_messages = [
            {"role": "system", "content": "You are an expert summariser. For a given body of content on a topic, you are able to analyse that content and generate a comprehensive FAQ that helps a reader understand the topic in detail."},
            {"role": "user", "content": f"Please generate a comprehensive FAQ for the following content:\n\n{scrape_content}"}
        ]
        
        # Attempt LLM call
        response = llm_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=faq_messages,
            max_tokens=4000,
            temperature=0.7
        )
        
        # Extract message content
        first_choice = response.choices[0]
        message = first_choice.message
        
        # Extract content
        if hasattr(message, 'content'):
            result = message.content
        else:
            print("❌ Could not find 'content' attribute in message")
            return "Error: Unable to extract LLM response content"
        
        # Return result
        return result
    
    except Exception as e:
        # Comprehensive error logging
        print(f"Comprehensive research error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Research process failed: {str(e)}"

def get_base_url(url):
    """Extract the base URL (domain only) from a full URL."""
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        print(f"🤖: I am now extracting the base URL from {url}")  
        update_spinner_status("🔗 Extracting base URL...")
        return base_url
    except Exception as e:
        print(f"Error extracting base URL from {url}: {str(e)}")
        return url  # Fall back to the original URL if parsing fails
    


def execute(research_brief, llm_client=None):
    print("The get_research tool has been called. Starting get_research function")

    try:
        # Modify the initial search to be an objective-based search
        print(f"🤖: I am performing a search for the objective:\n\n {research_brief}")
        update_spinner_status("🔎 Preparing search query")
        search_results = perform_search(
            objective=f"The brief from the user was:\n\n {research_brief}.\n\nTo help us answer this brief, your objective is to design a search query that helps find the definitive website for this topic", 
            llm_client=llm_client
        )
        
        if not search_results:
            print("No results found")
            return "No results found for the query"
            
        # Format results for LLM processing
        formatted_web_search_results = "\n".join(
            f"Title: {res['title']}\nURL: {res['url']}\nDescription: {res['description']}\n"
            for res in search_results
        ).strip()
        
        print(f"These are the search results for the top urls for the search term:\n{formatted_web_search_results}")
        update_spinner_status("🔎 Got first search results")
        # First LLM call to rank results
        web_search_messages = [
            {"role": "system", "content": "You are an expert URL Analysis Agent specialising in identifying official company websites from search results. Your expertise includes understanding URL structures, domain naming conventions, and digital business presence patterns, with particular insight into Australian and technology sector websites.\n\nCONTEXT FOR DISAMBIGUATION:\nThere are many organisations that share the same name so a key part of your role is to disambiguate the search results to determine which url most likely matches our intent. The following context should assist you:\n\n\nThis app is an AI Agent in service of the Peregian Digital Hub, a startup and technology Hub on the Sunshine Coast of Queensland Australia.\n\nTASK:\nAnalyse the provided search results and re-rank them based on their likelihood of being the official website for our target organization. For each result, examine the URL structure, domain name patterns, and page indicators to determine authenticity and relevance.\n\nConsider these ranking factors:\n1. Domain authenticity indicators (e.g., .com.au for Australian businesses, clean domains without excessive subdomains, domains that may use ai domain extensions)\n2. URL structure professionalism (avoiding sites like medium.com/company-name or facebook.com/company-name)\n3. Technology sector indicators\n4. Startup ecosystem relevance\n\nFor each search result, provide:\n1. A detailed analysis of why the URL might or might not be the official website\n2. Confidence indicators based on URL structure and domain patterns\n3. Red flags or positive signals in the URL composition\n\nOUTPUT FORMAT:\nRespond with a JSON array of objects, ordered by likelihood (most likely first), as follows:\n {\n 'results':[\n    {\n        'url': 'the url of the search result',\n        'description': 'the description from the search result',\n        'title': 'the title from the search result',\n        'rationale': 'Detailed reasoning for this ranking, including analysis of:\n            - Domain authenticity\n            - URL structure\n            - Geographical/sector relevance\n            - Any red flags or positive signals'\n    }\n]\n}\n\nEXAMPLE:\n\n{\n 'results': [\n {\n 'url': 'https://evenlabs.com/',\n 'title': 'EVEN Labs | Custom Training Plans',\n 'rationale': 'Home page with comprehensive overview of services'\n },\n {\n 'url': 'https://evenlabs.com/why',\n 'title': 'Why EVEN?',\n 'rationale': 'Provides insight into company mission and community'\n }\n // More results...\n ]\n}\n\n SPECIAL CONSIDERATIONS:\n- Be skeptical of social media profiles or third-party hosting platforms\n- Consider startup ecosystem platforms (e.g., crunchbase, angel.list) as secondary sources\n- Give weight to technology sector indicators in the URL structure\n\nFor ambiguous cases, explain your reasoning process for ranking decisions, particularly when distinguishing between similar company names or branches of the same organization."},
            {
                "role": "user",
                "content": f"The query is:\n\n {research_brief} \n\nAnalyse these search results and return the 5 most relevant results ranked by importance:\n\n{formatted_web_search_results}"
            }
        ]

        print("Sending search results to LLM for analysis")
        update_spinner_status("🔎 Sending search results to LLM")
        initial_response = llm_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=web_search_messages,
            max_tokens=4000,
            temperature=1,
            response_format={"type": "json_object"}
        )
        
        response_content = initial_response.choices[0].message.content.strip()
        print(f"LLM response received successfully with these results:\n{response_content}")
        update_spinner_status("🔎 LLM response received")
        # Clean up JSON string
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            response_content = response_content.split("```")[1].strip()
            
        reranked_websearch_results = json.loads(response_content)
        
        if isinstance(reranked_websearch_results, dict):
            if "results" in reranked_websearch_results:
                reranked_websearch_results = reranked_websearch_results["results"]
                print(f"These are the ranked results:\n{reranked_websearch_results}")
            else:
                reranked_websearch_results = [reranked_websearch_results]
        
        if isinstance(reranked_websearch_results, list) and len(reranked_websearch_results) > 0:
            first_result = reranked_websearch_results[0]
            top_url = first_result.get('url')
            
            # Extract the base URL
            base_url = get_base_url(top_url)
            print(f"🤖: I have completed extraction of the base URL: {base_url}")
            update_spinner_status("🔎 Completed extraction of base URL")
            
            print(f"STARTING SITE-SPECIFIC SEARCH FOR: site:{base_url}")

            site_search_results = perform_search(
                objective=f"The user's original request was:\n\n {research_brief}. We have done a first round of research and determined that the key website url is: {base_url}.\n\n Your job is to construct a site-specific search query limited to that website url to produce a search result which lists as many useful pages on that website, as possible. Aside from limiting the search to the site url, don't be too narrow with your criteria because the resulting search results will then be ranked in a subsequent step and then scraped to gather data that could help build a comprehensive knowledge base on the topic. Use your judgement about how many results to provide - max of 30 results", 
                llm_client=llm_client
            )
            
            if not site_search_results:
                print("No site-specific results found")
                return "No site-specific results found"
                
            # Format site-specific results for LLM
            formatted_site_search_results = "\n".join(
                f"Title: {res['title']}\nURL: {res['url']}\nDescription: {res['description']}\n"
                for res in site_search_results
            ).strip()
            print(f"🤖: I now have received the site-specific search results:\n{formatted_site_search_results}")
            update_spinner_status("🔎 Site-specific search complete")

            print(f"🤖: I will now have the site-specific search results re-ranked")

            site_search_messages = [
                {"role": "system", "content": "You are an expert search result analyser specialised in identifying web pages that contain potentially detailed context about a topic. Your task is to analyze a set of site-specific search results from a website and identify the pages from that site that are most likely to contain valuable contextual information about the organisation.\n\nOBJECTIVE:\nAnalyze and re-rank the search results based on the likelihood of the corresponding web page containing key organisational information such as:\n- Company overview and mission\n- Products and services offered\n- Value proposition\n- Leadership team and key personnel\n- Location and contact information\n- Pricing and cost structures\n- Social media urls and channels\n\nANALYSIS CRITERIA:\nFor each search result, evaluate:\n1. URL structure (e.g., /about-us, /company, /team, /contact)\n2. Page title relevance\n3. Description content signals\n4. Likelihood of containing multiple context data points\n\nRANKING METHODOLOGY:\n- Prioritize pages that typically contain comprehensive organizational information\n- Higher rank for pages likely to contain multiple information categories\n- Consider standard website architecture patterns\n- Value main section pages over deep subsidiary pages\n\nCommon high-value pages include:\n- About/Company pages\n- Home pages\n- Contact pages\n- Team/Leadership pages\n- Services/Products overview pages\n\nOUTPUT REQUIREMENTS:\nRespond with a JSON array of the top 5 most promising URLs, structured as follows:\n\n{\n 'results':[\n{\n        'url': 'page URL',\n        'title': 'page title',\n        'rationale': 'clear explanation for why this page is likely to contain valuable organizational context'\n    }\n]\n}\n\nRANKING RATIONALE GUIDELINES:\n- Explain specific signals in the URL, title, or description that suggest valuable content\n- Identify which types of organizational information the page is likely to contain\n- Note any patterns or conventions that inform your ranking decision\n\nFor each result, think step-by-step:\n1. What does the URL structure suggest about the page's content?\n2. What organizational information is this page likely to contain?\n3. Is this a primary/overview page or a subsidiary/detail page?\n4. How many different types of valuable context might this page contain?"},
                {
                    "role": "user",
                    "content": f"Analyze these search results from the url:\n\n{top_url}. \n\n Please identify which results are likely to contain the most informative content to help meet the user's brief, which was:\n\n ({research_brief}):\n\nThese are the search results to rank:\n\n{formatted_site_search_results}"
                }
            ]
            
            print(f"These are the messages sent to the llm:\n{site_search_messages}")
            
            final_response = llm_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=site_search_messages,
                max_tokens=4000,
                temperature=1,
                response_format={"type": "json_object"}
            )
            
        response_content = final_response.choices[0].message.content
        
        try:
            # Robust parsing of LLM response
            results = json.loads(response_content)
            
            # Explicit URL extraction with multiple fallback strategies
            urls = []
            
            # Try different possible keys and structures
            if isinstance(results, dict):
                # Check for 'results' key with URLs
                if 'results' in results:
                    if isinstance(results['results'], list):
                        # If results is a list of dictionaries with 'url' key
                        urls = [
                            item['url'] if isinstance(item, dict) and 'url' in item 
                            else item 
                            for item in results['results'] 
                            if item
                        ]
                
                # Check for direct 'urls' key
                if not urls and 'urls' in results:
                    urls = results['urls']
            
            # If no URLs found, fallback to search results
            if not urls:
                urls = [result['url'] for result in search_results[:5]]
            
            # Ensure unique URLs and limit to 5
            urls = list(dict.fromkeys(urls))[:5]
            
            print(f"Selected URLs for scraping: {urls}")
            update_spinner_status("🔎 Selected urls to scrape")
            
            # Scraping process (rest of the existing code remains the same)
            scraper = ResilientScraper()
            markdown_path = 'scrape.md'
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(f"# Scrape Results for: {research_brief}\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for i, url in enumerate(urls, 1):
                    print(f"Scraping URL {i} of {len(urls)}: {url}")
                    try:
                        content = scraper.scrape(url)
                        f.write(f"## URL {i}: {url}\n\n{content}\n\n")
                        print("🤖: I have written content to scrape.md")
                    except Exception as e:
                        print(f"Error scraping {url}: {e}")
            
            # Process scraped content
            final_output = process_scrape_with_llm(markdown_path, llm_client)
            
            return final_output
        
        except json.JSONDecodeError:
            print("Failed to parse LLM response")
            return "Error in URL selection process"
    
    except Exception as e:
        print(f"Comprehensive research error: {str(e)}")
        return f"Research process failed: {str(e)}"
    

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_research",
        "description": "This tool is a very intelligent web research agent that can search, find, gather and synthesise highly relevant information for a given topic. Use this tool whenever you are asked to perform research on topic. You simply give the agent a research_brief in natural language, eg 'please research the spacex starship launch schedule'. It will return a comprehensive research dossier for you to use in your answers.",
        "parameters": {
            "type": "object",
            "properties": {
                "research_brief": {
                    "type": "string",
                    "description": "The initial research brief query to use for the research, based on the user's message. Determine the intent and rephrase to get the best possible results. Be careful not to change key terms for example don't assume a given term is a typo when the user may have meant to use that term. Eg if the user mentions an org name, be careful not to change the org name in your research brief."
                }
            },
            "required": ["research_brief"]
        }
    },
    "direct_stream": True
}