import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def get_connection():
    db_url = urlparse(os.getenv('dbpoolrconnxn'))
    return psycopg2.connect(
        dbname=db_url.path[1:],
        user=db_url.username,
        password=db_url.password,
        host=db_url.hostname,
        port=db_url.port,
        cursor_factory=RealDictCursor
    )

def get_includes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT path, hash, length(content) as content_length FROM prompt_includes ORDER BY path')
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records

if __name__ == "__main__":
    includes = get_includes()
    if includes:
        print("\nPrompt includes:")
        for inc in includes:
            print(f"- {inc['path']}")
            print(f"  Hash: {inc['hash']}")
            print(f"  Content length: {inc['content_length']} bytes") 