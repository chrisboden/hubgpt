# tools/get_hub_co_updates.py

import os
from dotenv import load_dotenv
import requests
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser
from termcolor import cprint

# Load environment variables at the start of the script
load_dotenv()

# Number of days to look back for posts
POST_AGE_DAYS = 30

def fetch_company_urls() -> List[str]:
    """Fetch company LinkedIn URLs from the published Google Sheet CSV."""
    try:
        csv_url = os.getenv("HUB_COMPANIES_CSV_URL")
        cprint(f"This is CSV url:{csv_url}", "green")
        if not csv_url:
            raise ValueError("HUB_COMPANIES_CSV_URL not found in environment variables")
        
        cprint(f"Fetching companies from CSV...", "blue")
        df = pd.read_csv(csv_url)
        company_urls = df['Linkedin URL'].tolist()
        cprint(f"Successfully fetched {len(company_urls)} company URLs", "green")
        return company_urls
    except Exception as e:
        cprint(f"Error fetching CSV: {e}", "red")
        return []   

def parse_linkedin_response(response_data: Dict, max_age_days: int) -> List[Dict]:
    """
    Parse and filter the LinkedIn API response.
    
    Args:
        response_data: Raw API response
        max_age_days: Maximum age of posts to include (in days)
    
    Returns:
        List of parsed and filtered company updates
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    parsed_data = []
    
    for company_data in response_data.get('data', []):
        posts = company_data.get('posts', [])
        if not posts:
            continue
            
        filtered_posts = []
        for post in posts:
            post_date = parser.parse(post['postedAt'])
            if post_date > cutoff_date:
                filtered_posts.append({
                    "post_text": post['postText'],
                    "post_date": post['postedAt']
                })
                
        if filtered_posts:  # Only include companies with posts after filtering
            parsed_data.append({
                "company": post['actor']['actorName'],
                "posts": filtered_posts
            })
    
    return parsed_data

def execute(llm_client=None, post_count: int = 5) -> Dict:
    """
    Fetch LinkedIn updates for hub companies.
    
    Args:
        llm_client: Optional LLM client for additional processing
        post_count: Number of recent posts to fetch per company (default: 5)
    
    Returns:
        Dict containing filtered company updates and metadata
    """
    company_urls = fetch_company_urls()
    
    url = "https://linkedin-bulk-data-scraper.p.rapidapi.com/company_posts"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "linkedin-bulk-data-scraper.p.rapidapi.com",
        "Content-Type": "application/json",
        "x-rapidapi-user": os.getenv("RAPIDAPI_USER", "")
    }
    
    payload = {
        "links": company_urls,
        "count": post_count
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        raw_updates = response.json()
        
        # Parse and filter the response
        filtered_updates = parse_linkedin_response(raw_updates, POST_AGE_DAYS)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "post_age_days": POST_AGE_DAYS,
            "updates": filtered_updates
        }
        
        # Only add summary if llm_client is provided
        if llm_client is not None:
            try:
                prompt = f"Summarize the key updates from the hub companies from the past {POST_AGE_DAYS} days:"
                response = llm_client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[{"role": "user", "content": prompt}]
                )
                result["summary"] = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error generating summary: {e}")
                # Continue without summary if LLM fails
                
        return result
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_hub_co_updates",
        "description": "Fetch recent LinkedIn updates from hub companies within the last 30 days",
        "parameters": {
            "type": "object",
            "properties": {
                "post_count": {
                    "type": "integer",
                    "description": "Number of recent posts to fetch per company. Always use 5",
                }
            },
            "required": []
        }
    }
}