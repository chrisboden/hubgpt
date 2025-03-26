# tools/get_company_updates.py

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
    """
    Fetch company LinkedIn URLs from the published Google Sheet CSV.
    
    Returns:
        List of LinkedIn URLs for companies.
    """
    try:
        # Retrieve the CSV URL from environment variables
        csv_url = os.getenv("COMPANIES_CSV_URL")
        cprint(f"\n🔍 Fetching companies from CSV:", "blue")
        cprint(f"  URL: {csv_url}", "blue")
        
        # Raise an error if the URL is not found
        if not csv_url:
            error_msg = "COMPANIES_CSV_URL not found in environment variables"
            cprint(f"❌ Error: {error_msg}", "red")
            raise ValueError(error_msg)
        
        # Read the CSV file into a DataFrame
        cprint(f"\n📥 Reading CSV data...", "blue")
        df = pd.read_csv(csv_url)
        
        # Log DataFrame info
        cprint(f"\n📊 CSV Data Info:", "yellow")
        cprint(f"  - Number of rows: {len(df)}", "yellow")
        cprint(f"  - Columns: {', '.join(df.columns)}", "yellow")
        
        # Check if 'Linkedin URL' column exists
        if 'Linkedin URL' not in df.columns:
            error_msg = "CSV is missing 'Linkedin URL' column. Available columns: " + ", ".join(df.columns)
            cprint(f"❌ Error: {error_msg}", "red")
            raise ValueError(error_msg)
        
        # Extract the LinkedIn URLs into a list
        company_urls = df['Linkedin URL'].dropna().tolist()
        
        # Log results
        cprint(f"\n✅ Successfully loaded company URLs:", "green")
        cprint(f"  - Total URLs found: {len(company_urls)}", "green")
        if company_urls:
            cprint("\n📝 First few URLs:", "cyan")
            for url in company_urls[:3]:
                cprint(f"  - {url}", "cyan")
            if len(company_urls) > 3:
                cprint(f"  - ... and {len(company_urls)-3} more", "cyan")
        else:
            cprint("⚠️ Warning: No URLs found in the CSV", "yellow")
        
        return company_urls
        
    except pd.errors.EmptyDataError:
        error_msg = "CSV file is empty"
        cprint(f"❌ Error: {error_msg}", "red")
        return []
    except Exception as e:
        # Print error message if fetching fails
        cprint(f"\n❌ Error fetching CSV:", "red")
        cprint(f"  - Error type: {type(e).__name__}", "red")
        cprint(f"  - Error message: {str(e)}", "red")
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
    # Calculate the cutoff date for filtering posts
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cprint(f"\n📅 Filtering posts older than: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}", "blue")
    
    parsed_data = []
    
    # Iterate over each company's data in the response
    company_count = len(response_data.get('data', []))
    cprint(f"🏢 Processing {company_count} companies", "blue")
    
    for company_data in response_data.get('data', []):
        posts = company_data.get('posts', [])
        
        # Skip companies with no posts
        if not posts:
            continue
            
        filtered_posts = []
        company_name = posts[0]['actor']['actorName'] if posts else "Unknown Company"
        cprint(f"\n📊 Processing {company_name}:", "yellow")
        cprint(f"  - Total posts found: {len(posts)}", "yellow")
        
        # Filter posts based on the cutoff date
        for post in posts:
            post_date = parser.parse(post['postedAt'])
            if post_date > cutoff_date:
                filtered_posts.append({
                    "post_text": post['postText'],
                    "post_date": post['postedAt']
                })
                cprint(f"  ✅ Including post from {post_date.strftime('%Y-%m-%d')}", "green")
            else:
                cprint(f"  ❌ Skipping post from {post_date.strftime('%Y-%m-%d')} (too old)", "red")
                
        # Only include companies with posts after filtering
        if filtered_posts:
            parsed_data.append({
                "company": company_name,
                "posts": filtered_posts
            })
            cprint(f"  📝 Kept {len(filtered_posts)} posts within date range", "cyan")
        else:
            cprint(f"  ℹ️ No posts within date range", "yellow")
    
    cprint(f"\n🎯 Final results:", "green")
    cprint(f"  - Companies processed: {company_count}", "green")
    cprint(f"  - Companies with recent posts: {len(parsed_data)}", "green")
    
    return parsed_data

def execute(llm_client=None, post_count: int = 5) -> Dict:
    """
    Fetch LinkedIn updates for list of companies.
    
    Args:
        llm_client: Optional LLM client for additional processing
        post_count: Number of recent posts to fetch per company (default: 5)
    
    Returns:
        Dict containing filtered company updates and metadata
    """
    # Fetch the list of company LinkedIn URLs
    company_urls = fetch_company_urls()
    
    # Define the API endpoint and headers for the request
    url = "https://linkedin-bulk-data-scraper.p.rapidapi.com/company_posts"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "linkedin-bulk-data-scraper.p.rapidapi.com",
        "Content-Type": "application/json",
        "x-rapidapi-user": os.getenv("RAPIDAPI_USER", "")
    }
    
    # Prepare the payload with company URLs and post count
    payload = {
        "links": company_urls,
        "count": post_count
    }
    
    try:
        # Log API request details
        cprint(f"\n🌐 Making LinkedIn API request to: {url}", "blue")
        cprint(f"📦 Payload:", "blue")
        cprint(f"  - Number of companies: {len(company_urls)}", "blue")
        cprint(f"  - Posts per company: {post_count}", "blue")
        
        # Make a POST request to the LinkedIn API
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Log API response
        cprint(f"\n✅ LinkedIn API response received", "green")
        cprint(f"📊 Response status code: {response.status_code}", "green")
        
        # Parse the raw API response
        raw_updates = response.json()
        
        # Log raw response details
        cprint(f"\n📝 Raw response details:", "yellow")
        cprint(f"  - Response type: {type(raw_updates)}", "yellow")
        if isinstance(raw_updates, dict):
            cprint(f"  - Keys in response: {', '.join(raw_updates.keys())}", "yellow")
            if 'data' in raw_updates:
                cprint(f"  - Number of companies with data: {len(raw_updates['data'])}", "yellow")
        
        # Parse and filter the response
        filtered_updates = parse_linkedin_response(raw_updates, POST_AGE_DAYS)
        
        # Log filtered results
        cprint(f"\n🔍 Filtered results:", "cyan")
        cprint(f"  - Companies with updates: {len(filtered_updates)}", "cyan")
        for company in filtered_updates:
            cprint(f"  - {company['company']}: {len(company['posts'])} posts", "cyan")
        
        # Prepare the result dictionary with metadata
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "post_age_days": POST_AGE_DAYS,
            "updates": filtered_updates
        }
        
        # Only add summary if llm_client is provided
        if llm_client is not None:
            try:
                # Generate a summary of the updates using the LLM client
                cprint("\n🤖 Generating summary using LLM...", "blue")
                prompt = f"Summarize the key updates from the list of companies from the past {POST_AGE_DAYS} days:"
                response = llm_client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{"role": "user", "content": prompt}]
                )
                result["summary"] = response.choices[0].message.content.strip()
                cprint("✅ Summary generated successfully", "green")
            except Exception as e:
                # Print error message if summary generation fails
                cprint(f"❌ Error generating summary: {e}", "red")
                # Continue without summary if LLM fails
                
        return result
        
    except Exception as e:
        # Log error details
        cprint(f"\n❌ Error during LinkedIn API request:", "red")
        cprint(f"  - Error type: {type(e).__name__}", "red")
        cprint(f"  - Error message: {str(e)}", "red")
        
        # Return an error result if the API request fails
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_company_updates",
        "description": "Fetch the recent LinkedIn updates posted by a the companies at the Peregian Digital Hub",
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