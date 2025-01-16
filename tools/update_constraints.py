import asyncio
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def update_temperature_constraint():
    """Update the temperature constraint to allow values up to 2.0."""
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
        
        cur = conn.cursor()
        
        print("Updating temperature constraint...")
        
        # Drop the existing constraint
        cur.execute("""
            ALTER TABLE public.advisors 
            DROP CONSTRAINT IF EXISTS advisors_temperature_check;
        """)
        
        # Add new constraint allowing temperatures up to 2.0
        cur.execute("""
            ALTER TABLE public.advisors 
            ADD CONSTRAINT advisors_temperature_check 
            CHECK (temperature >= 0 AND temperature <= 2);
        """)
        
        conn.commit()
        print("Successfully updated temperature constraint to allow values up to 2.0")
        
        cur.close()
        conn.close()
                
    except Exception as e:
        print(f"Error updating constraint: {str(e)}")

if __name__ == "__main__":
    asyncio.run(update_temperature_constraint()) 