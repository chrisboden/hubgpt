import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_advisors():
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
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get all advisors
        cur.execute("""
            SELECT id, name
            FROM advisors
            WHERE LOWER(name) LIKE '%jim%' OR LOWER(name) LIKE '%elon%'
            ORDER BY name
        """)
        advisors = cur.fetchall()

        print("\nFound advisors:")
        for advisor in advisors:
            print(f"ID: {advisor['id']}, Name: {advisor['name']}")

    except Exception as e:
        print(f"Error checking advisors: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_advisors() 