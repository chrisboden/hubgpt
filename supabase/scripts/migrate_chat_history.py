import asyncio
import json
import os
import hashlib
import psycopg2
import re
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def migrate_chat_history(advisor_name: str):
    """Migrate chat history for a specific advisor."""
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
        
        # Load chat history file
        chat_path = Path(f"advisors/chats/{advisor_name}.json")
        if not chat_path.exists():
            print(f"Error: {chat_path} not found")
            return
            
        with open(chat_path, 'r') as f:
            chat_data = json.load(f)
            
        print(f"\nFound {len(chat_data)} messages in {advisor_name}'s chat history")
        
        # Get advisor ID from database
        cur.execute("""
            SELECT id FROM advisors WHERE name = %s
        """, (advisor_name,))
        advisor = cur.fetchone()
        if not advisor:
            print(f"Error: Advisor {advisor_name} not found in database")
            return
            
        advisor_id = advisor['id']
        
        # Create chat entry
        cur.execute("""
            INSERT INTO chats (advisor_id, created_at)
            VALUES (%s, NOW())
            RETURNING id
        """, (advisor_id,))
        chat_id = cur.fetchone()['id']
        
        print(f"Created chat with ID: {chat_id}")
        
        # Process each message
        successful = []
        failed = []
        
        for i, message in enumerate(chat_data):
            try:
                # Extract message components
                role = message.get('role')
                content = message.get('content')
                tool_calls = message.get('tool_calls', [])
                tool_name = message.get('name') if role == 'tool' else None
                tool_call_id = message.get('tool_call_id') if role == 'tool' else None
                
                # Insert message
                cur.execute("""
                    INSERT INTO chat_messages (
                        chat_id, 
                        sequence, 
                        role, 
                        content,
                        tool_name,
                        tool_call_id,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    chat_id,
                    i + 1,  # 1-based sequence
                    role,
                    content,
                    tool_name,
                    tool_call_id
                ))
                message_id = cur.fetchone()['id']
                
                # Handle tool calls if present
                if tool_calls:
                    for tool_call in tool_calls:
                        cur.execute("""
                            INSERT INTO message_tool_calls (
                                message_id,
                                tool_call_id,
                                tool_name,
                                arguments,
                                created_at
                            )
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (
                            message_id,
                            tool_call['id'],
                            tool_call['function']['name'],
                            json.dumps(tool_call['function']['arguments'])
                        ))
                
                successful.append(i)
                print(f"✓ Migrated message {i+1}")
                
            except Exception as e:
                print(f"Error processing message {i+1}: {str(e)}")
                failed.append(i)
        
        # Commit all changes
        conn.commit()
        
        # Print summary
        print("\nMigration Summary:")
        print(f"Successfully migrated: {len(successful)} messages")
        print(f"Failed to migrate: {len(failed)} messages")
        
        if failed:
            print("\nFailed messages:")
            for idx in failed:
                print(f"✗ Message {idx+1}")
        
        cur.close()
        conn.close()
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        advisor_name = sys.argv[1]
    else:
        advisor_name = "Jim_Collins"
        
    asyncio.run(migrate_chat_history(advisor_name)) 