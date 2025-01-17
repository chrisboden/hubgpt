import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials for the remote project
supabase_url = "https://vbqcmspqteqpfbhffebu.supabase.co"
supabase_key = os.getenv('SUPABASE_ANON_KEY')

print(f"\nUsing Supabase URL: {supabase_url}")
print(f"Using Supabase Key: {supabase_key[:10]}..." if supabase_key else "No key found")

def list_bucket_contents(bucket_name: str):
    """List all files in a Supabase Storage bucket."""
    try:
        print(f"\nListing contents of Supabase bucket '{bucket_name}':")
        
        # First, try to list files using the REST API
        list_url = f"{supabase_url}/rest/v1/storage/objects?select=*&bucket_id=eq.{bucket_name}"
        headers = {
            'Authorization': f'Bearer {supabase_key}',
            'apikey': supabase_key,
            'Content-Type': 'application/json'
        }
        
        print(f"Trying to list files using REST API: {list_url}")
        response = requests.get(list_url, headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            files = response.json()
            if files:
                print("\nFound files:")
                for file in files:
                    print(f"- {file}")
            else:
                print("No files found in bucket")
                
            # Try to access good2great.json directly since we know it exists
            if bucket_name == 'content':
                file_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/good2great.json"
                print(f"\nTrying to access known file: {file_url}")
                response = requests.get(file_url, headers=headers)
                print(f"File access response status: {response.status_code}")
                if response.status_code == 200:
                    print(f"File content preview: {response.text[:200]}...")
        else:
            print(f"Error listing files: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error accessing bucket: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("\nChecking 'content' bucket:")
    list_bucket_contents('content')
    
    print("\n---\n")
    
    print("Checking 'me' bucket:")
    list_bucket_contents('me') 