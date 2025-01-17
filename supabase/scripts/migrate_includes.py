import os
import json
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv
import re
from pathlib import Path

# Load environment variables
load_dotenv()

def calculate_hash(content: str) -> str:
    """Calculate SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()

def extract_includes(content: str) -> set:
    """Extract include paths from content."""
    pattern = r'<\$([^$]+)\$>'
    return set(re.findall(pattern, content))

def read_file_content(path: str) -> str:
    """Read file content."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        return None

def migrate_includes():
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
        cur.execute("SELECT * FROM advisors")
        advisors = cur.fetchall()

        # Track all includes
        all_includes = set()
        for advisor in advisors:
            includes = extract_includes(advisor['system_message'])
            all_includes.update(includes)

        print(f"Found {len(all_includes)} unique includes to migrate")

        # Migrate each include
        for include_path in all_includes:
            # Read file content
            content = read_file_content(include_path)
            if content is None:
                print(f"Skipping {include_path} - file not found")
                continue

            # Calculate hash
            content_hash = calculate_hash(content)

            # Insert or update in database
            cur.execute("""
                SELECT id FROM prompt_includes WHERE path = %s
            """, (include_path,))
            existing = cur.fetchone()

            if existing:
                # Update existing record
                cur.execute("""
                    UPDATE prompt_includes 
                    SET content = %s, hash = %s 
                    WHERE path = %s
                """, (content, content_hash, include_path))
                print(f"Updated {include_path}")
            else:
                # Insert new record
                cur.execute("""
                    INSERT INTO prompt_includes (path, content, hash)
                    VALUES (%s, %s, %s)
                """, (include_path, content, content_hash))
                print(f"Migrated {include_path}")

        conn.commit()
        print("\nMigration complete!")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_includes() 