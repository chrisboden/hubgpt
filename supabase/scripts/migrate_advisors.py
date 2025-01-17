import asyncio
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

def get_advisor_description(name: str) -> str:
    """Get a description for an advisor based on their name."""
    descriptions = {
        "Elon_Musk": "AI advisor that emulates Elon Musk's thinking and communication style",
        "Naval_Ravikant": "AI advisor embodying Naval Ravikant's philosophical and entrepreneurial insights",
        "Charlie_Munger": "AI advisor channeling Charlie Munger's wisdom and mental models",
        "Peter_Thiel": "AI advisor representing Peter Thiel's contrarian thinking and strategic insights",
        "Steve_Jobs": "AI advisor embodying Steve Jobs' product vision and innovation philosophy",
        "Daniel_Kahneman": "AI advisor based on Daniel Kahneman's behavioral economics expertise",
        "Nassim_Taleb": "AI advisor incorporating Nassim Taleb's ideas on uncertainty and antifragility",
        "David_Deutsch": "AI advisor based on David Deutsch's perspectives on physics and knowledge",
        "Yuval_Harari": "AI advisor drawing from Yuval Harari's historical and futuristic insights",
        "Jim_Collins": "AI advisor applying Jim Collins' research on great companies and leadership",
        "Shane_Parrish": "AI advisor incorporating mental models and decision-making frameworks",
        "Chris_Voss": "AI advisor applying negotiation techniques and communication strategies",
        "Mr_Promptmaker": "AI advisor specialized in crafting effective prompts for AI systems",
        "Mr_Member": "AI advisor for managing Hub membership and community interactions",
        "Mr_Searcher": "AI advisor specialized in research and information gathering",
        "Mr_Repo": "AI advisor for managing and working with code repositories",
        "Mr_Linkedin": "AI advisor for LinkedIn content and professional networking",
        "Mr_Feedreader": "AI advisor for processing and analyzing RSS feeds",
        "Mr_Gangster": "AI advisor with a unique and entertaining communication style"
    }
    return descriptions.get(name, f"AI advisor based on {name.replace('_', ' ')}'s expertise and insights")

async def load_advisor_file(file_path: Path) -> Dict:
    """Load and parse an advisor JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Extract advisor name from filename
        name = file_path.stem
        
        # Get system message from messages array
        system_message = next(
            (msg["content"] for msg in data.get("messages", []) 
             if msg.get("role") == "system"),
            ""
        )
        
        # Create advisor record matching the schema
        advisor = {
            "name": name,
            "description": get_advisor_description(name),
            "model": data.get("model", ""),
            "temperature": clamp(float(data.get("temperature", 1.0)), 0, 1),
            "max_tokens": int(data.get("max_tokens", 4096)),
            "top_p": clamp(float(data.get("top_p", 1)), 0, 1),
            "frequency_penalty": clamp(float(data.get("frequency_penalty", 0)), -2, 2),
            "presence_penalty": clamp(float(data.get("presence_penalty", 0)), -2, 2),
            "stream": bool(data.get("stream", True)),
            "system_message": system_message,
            "tools": json.dumps(data.get("tools", []))  # Convert tools list to JSON string
        }
        
        # Print the adjusted values
        print("\nAdjusted values to meet constraints:")
        print(f"temperature: {data.get('temperature', 1.0)} -> {advisor['temperature']}")
        print(f"top_p: {data.get('top_p', 1)} -> {advisor['top_p']}")
        print(f"frequency_penalty: {data.get('frequency_penalty', 0)} -> {advisor['frequency_penalty']}")
        print(f"presence_penalty: {data.get('presence_penalty', 0)} -> {advisor['presence_penalty']}")
        
        return advisor
    except Exception as e:
        print(f"Error loading advisor {file_path}: {str(e)}")
        return None

async def migrate_advisors(specific_advisor: str = None):
    """Migrate advisors to Supabase.
    
    Args:
        specific_advisor: Optional name of specific advisor to migrate (e.g., 'Elon_Musk')
    """
    try:
        # Get database connection
        db_url = urlparse(os.getenv('dbpoolrconnxn'))
        conn = psycopg2.connect(
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
        
        # Get advisor files
        advisors_dir = Path("advisors")
        if specific_advisor:
            advisor_files = [advisors_dir / f"{specific_advisor}.json"]
            if not advisor_files[0].exists():
                print(f"Error: {advisor_files[0]} not found")
                return
        else:
            advisor_files = list(advisors_dir.glob("*.json"))
            print(f"\nFound {len(advisor_files)} advisor files to migrate")
        
        # Track results
        successful = []
        failed = []
        
        # Migrate each advisor
        for file_path in advisor_files:
            try:
                print(f"\nMigrating {file_path.name}...")
                
                # Load advisor data
                advisor_data = await load_advisor_file(file_path)
                if not advisor_data:
                    failed.append(file_path.name)
                    continue
                    
                # Create advisor using direct SQL
                cur = conn.cursor(cursor_factory=RealDictCursor)
                
                columns = ', '.join(advisor_data.keys())
                values = ', '.join([f"%s" for _ in advisor_data])
                query = f"INSERT INTO public.advisors ({columns}) VALUES ({values}) RETURNING id"
                
                cur.execute(query, list(advisor_data.values()))
                conn.commit()
                
                result = cur.fetchone()
                if result:
                    print(f"Successfully migrated {file_path.name} (ID: {result['id']})")
                    successful.append(file_path.name)
                else:
                    print(f"Failed to migrate {file_path.name}")
                    failed.append(file_path.name)
                    
                cur.close()
                
            except Exception as e:
                print(f"Error migrating {file_path.name}: {str(e)}")
                failed.append(file_path.name)
        
        # Print summary
        print("\nMigration Summary:")
        print(f"Successfully migrated: {len(successful)}")
        print(f"Failed to migrate: {len(failed)}")
        
        if successful:
            print("\nSuccessful migrations:")
            for name in successful:
                print(f"✓ {name}")
                
        if failed:
            print("\nFailed migrations:")
            for name in failed:
                print(f"✗ {name}")
        
        conn.close()
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Migrate specific advisor
        asyncio.run(migrate_advisors(sys.argv[1]))
    else:
        # Migrate all advisors
        asyncio.run(migrate_advisors()) 