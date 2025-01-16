import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

def inspect_data():
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
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get Jim Collins advisor
        print("\nFetching Jim Collins advisor data...")
        cur.execute("""
            SELECT * FROM advisors WHERE name = 'Jim_Collins'
        """)
        advisor = cur.fetchone()
        
        if not advisor:
            print("Jim Collins advisor not found!")
            return
            
        print(f"\nAdvisor ID: {advisor['id']}")
        print(f"Model: {advisor['model']}")
        print(f"Temperature: {advisor['temperature']}")
        
        # Extract includes from system message
        pattern = r'<\$([^$]+)\$>'
        includes = re.findall(pattern, advisor['system_message'])
        
        print("\nIncludes found in system message:")
        for include in includes:
            print(f"- '{include}'")
            
        # Check if these includes exist in prompt_includes
        print("\nChecking prompt_includes table...")
        cur.execute("""
            SELECT * FROM prompt_includes
        """)
        all_includes = cur.fetchall()
        print(f"\nTotal includes in database: {len(all_includes)}")
        print("\nAll available paths:")
        for inc in all_includes:
            print(f"- '{inc['path']}'")
        
        print("\nChecking each include:")
        for include in includes:
            cur.execute("""
                SELECT * FROM prompt_includes WHERE path = %s
            """, (include,))
            include_data = cur.fetchone()
            if include_data:
                print(f"\n✓ Found include: '{include}'")
                print(f"  Hash: {include_data['hash']}")
                print(f"  Content length: {len(include_data['content'])} chars")
                print(f"  Content preview: {include_data['content'][:100]}...")
            else:
                print(f"\n✗ Missing include: '{include}'")
                print("  Trying variations:")
                variations = [
                    include,
                    include.strip('/'),
                    f"/{include}",
                    f"/{include.strip('/')}"
                ]
                for var in variations:
                    cur.execute("""
                        SELECT path FROM prompt_includes WHERE path = %s
                    """, (var,))
                    result = cur.fetchone()
                    print(f"  - '{var}': {'Found' if result else 'Not found'}")
        
        cur.close()
        conn.close()
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_data() 