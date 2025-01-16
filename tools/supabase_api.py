import os
from typing import Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseAPI:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials. Please check your .env file.")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
    async def get_advisors(self) -> List[Dict]:
        """Get all advisors from the database."""
        try:
            response = await self.supabase.from_('advisors').select('*').execute()
            return response.data
        except Exception as e:
            print(f"Error fetching advisors: {str(e)}")
            return []
            
    async def get_advisor(self, advisor_id: int) -> Optional[Dict]:
        """Get a specific advisor by ID."""
        try:
            response = await self.supabase.from_('advisors').select('*').eq('id', advisor_id).single().execute()
            return response.data
        except Exception as e:
            print(f"Error fetching advisor {advisor_id}: {str(e)}")
            return None
            
    async def create_advisor(self, advisor_data: Dict) -> Optional[Dict]:
        """Create a new advisor.
        
        Required fields:
        - name: str
        - model: str
        - temperature: float
        - max_tokens: int
        - top_p: float
        - frequency_penalty: float
        - presence_penalty: float
        - stream: bool
        - system_message: str
        
        Optional fields:
        - description: str
        - tools: Dict
        """
        try:
            # Ensure required fields are present
            required_fields = [
                'name', 'model', 'temperature', 'max_tokens', 'top_p',
                'frequency_penalty', 'presence_penalty', 'stream', 'system_message'
            ]
            
            missing_fields = [field for field in required_fields if field not in advisor_data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
                
            response = await self.supabase.from_('advisors').insert(advisor_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating advisor: {str(e)}")
            return None
            
    async def update_advisor(self, advisor_id: int, advisor_data: Dict) -> Optional[Dict]:
        """Update an existing advisor."""
        try:
            response = await self.supabase.from_('advisors').update(advisor_data).eq('id', advisor_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating advisor {advisor_id}: {str(e)}")
            return None
            
    async def delete_advisor(self, advisor_id: int) -> bool:
        """Delete an advisor."""
        try:
            await self.supabase.from_('advisors').delete().eq('id', advisor_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting advisor {advisor_id}: {str(e)}")
            return False
            
    async def search_advisors(self, query: str) -> List[Dict]:
        """Search advisors by name or description."""
        try:
            response = await self.supabase.from_('advisors').select('*').or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            ).execute()
            return response.data
        except Exception as e:
            print(f"Error searching advisors: {str(e)}")
            return []

# Helper function to create a singleton instance
_instance = None

def get_supabase_client() -> SupabaseAPI:
    """Get or create a singleton instance of SupabaseAPI."""
    global _instance
    if _instance is None:
        _instance = SupabaseAPI()
    return _instance 