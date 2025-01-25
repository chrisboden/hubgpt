import os
import pandas as pd
import requests
from io import StringIO
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_member_data(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch member data from Google Sheets and return as list of dicts"""
    try:
        # Get URL from environment variable
        sheet_url = os.getenv('MEMBER_SHEET_URL')
        print(f"Attempting to access sheet URL: {sheet_url}")
        
        if not sheet_url:
            raise ValueError("MEMBER_SHEET_URL not found in environment variables")
            
        # Fetch data directly from URL
        print("Fetching data from Google Sheets...")
        response = requests.get(sheet_url)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            raise ValueError(f"Failed to fetch sheet data. Status code: {response.status_code}")
            
        # Load into pandas
        print("Loading data into pandas...")
        df = pd.read_csv(StringIO(response.text))
        print(f"Columns found: {df.columns.tolist()}")
        
        # Convert to list of dicts
        records = df.to_dict('records')
        print(f"Found {len(records)} records")
        
        # Apply limit if specified
        if limit:
            records = records[:limit]
            
        return records
    except Exception as e:
        print(f"Error fetching member data: {str(e)}")
        return []

def get_member_emails(limit: Optional[int] = None) -> List[str]:
    """Get list of member email addresses"""
    members = get_member_data(limit)
    return [m['email'] for m in members if 'email' in m and m['email']]



def execute(limit: Optional[int] = None):
    """Tool execution function"""
    return get_member_data(limit) 

# Tool metadata for the framework
TOOL_METADATA = {
    "function": {
        "name": "use_crm",
        "description": "Access Hub member data from Google Sheets CRM",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional limit on number of records to return"
                }
            }
        }
    }
}