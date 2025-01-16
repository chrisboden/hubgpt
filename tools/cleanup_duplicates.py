import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_duplicates():
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

        # Find duplicates for specific cases
        cur.execute("""
            WITH cases AS (
                SELECT unnest(ARRAY[
                    'jim_collins',
                    'elon_musk'
                ]) as base_name
            )
            SELECT 
                c.base_name,
                array_agg(a.name) as names,
                COUNT(*),
                array_agg(a.id ORDER BY a.id) as ids
            FROM cases c
            JOIN advisors a ON (
                LOWER(a.name) LIKE '%' || c.base_name || '%' OR
                REPLACE(LOWER(a.name), ' ', '_') LIKE '%' || c.base_name || '%'
            )
            GROUP BY c.base_name
            HAVING COUNT(*) > 1
        """)
        duplicates = cur.fetchall()

        print(f"Found {len(duplicates)} advisors with duplicates")

        for dupe in duplicates:
            base_name = dupe['base_name']
            names = dupe['names']
            ids = dupe['ids']
            keep_id = ids[0]  # Keep the first (oldest) ID
            remove_ids = ids[1:]  # Remove subsequent duplicates
            
            print(f"\nProcessing {base_name}")
            print(f"Original names: {names}")
            print(f"Keeping ID: {keep_id}")
            print(f"Removing IDs: {remove_ids}")

            # Update foreign key references in chats table
            cur.execute("""
                UPDATE chats 
                SET advisor_id = %s 
                WHERE advisor_id = ANY(%s)
            """, (keep_id, remove_ids))
            print(f"Updated chat references")

            # Delete duplicate advisors
            cur.execute("""
                DELETE FROM advisors 
                WHERE id = ANY(%s)
            """, (remove_ids,))
            print(f"Deleted duplicate entries")

        conn.commit()
        print("\nCleanup complete!")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    cleanup_duplicates() 