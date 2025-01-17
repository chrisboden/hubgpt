import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def migrate_includes():
    """Migrate content and me includes from database to storage."""
    try:
        # Connect to database
        db_url = urlparse(os.getenv('dbpoolrconnxn'))
        conn = psycopg2.connect(
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
        
        # Initialize Supabase client
        supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        
        # Get content and me includes from database
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT path, content::text as content
            FROM prompt_includes 
            WHERE path LIKE 'content/%' OR path LIKE 'me/%'
        """)
        includes = cur.fetchall()
        
        print(f"Found {len(includes)} includes to migrate")
        
        # Create directories if they don't exist
        try:
            supabase.storage.from_('includes').list('content')
        except:
            print("Creating content directory...")
        
        try:
            supabase.storage.from_('includes').list('me')
        except:
            print("Creating me directory...")
        
        # Migrate each include to storage
        success_count = 0
        for include in includes:
            try:
                path = include['path']
                content = include['content']
                
                if not content:
                    print(f"Skipping {path} - no content")
                    continue
                
                print(f"Migrating {path}...")
                
                # For JSON files, try to parse and extract content
                if path.endswith('.json'):
                    try:
                        data = json.loads(content)
                        if isinstance(data, list) and len(data) > 0 and 'content' in data[0]:
                            content = data[0]['content']
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse JSON for {path}")
                
                # Convert content to bytes
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                else:
                    content_bytes = str(content).encode('utf-8')
                
                # Upload to storage
                result = supabase.storage.from_('includes').upload(
                    path,
                    content_bytes,
                    {'content-type': 'text/plain', 'upsert': True}
                )
                
                if hasattr(result, 'error') and result.error:
                    print(f"Error uploading {path}: {result.error}")
                    continue
                    
                success_count += 1
                print(f"Successfully migrated {path}")
                
            except Exception as e:
                print(f"Error processing {path}: {str(e)}")
                continue
        
        print(f"\nMigration complete!")
        print(f"Successfully migrated {success_count} of {len(includes)} includes")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_includes() 