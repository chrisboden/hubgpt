import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_includes():
    """Check includes in database."""
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
        
        # Get content and me includes from database
        cur = conn.cursor()
        cur.execute("""
            SELECT path, content
            FROM prompt_includes 
            WHERE path LIKE 'content/%' OR path LIKE 'me/%'
            LIMIT 5
        """)
        includes = cur.fetchall()
        
        print(f"Found {len(includes)} includes")
        for path, content in includes:
            print(f"\nPath: {path}")
            print(f"Content type: {type(content).__name__}")
            print(f"Content value: {content}")
        
    except Exception as e:
        print(f"Error checking includes: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_includes() 