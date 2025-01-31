"""migrate_chats

Revision ID: 003
Revises: 002b
Create Date: 2024-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import json
import os
from pathlib import Path
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002b'
branch_labels = None
depends_on = None

def get_chat_files():
    """Get all chat files from chats and archive directories"""
    base_dir = Path("api")
    chats_dir = base_dir / "advisors" / "chats"
    archive_dir = base_dir / "advisors" / "archive"
    
    chat_files = []
    if chats_dir.exists():
        chat_files.extend(list(chats_dir.glob("*.json")))
    if archive_dir.exists():
        chat_files.extend(list(archive_dir.glob("*.json")))
    return chat_files

def upgrade() -> None:
    # Create a connection to use for raw SQL
    connection = op.get_bind()
    
    # First create default advisor if it doesn't exist
    advisor_path = Path("advisors/default.json")
    if advisor_path.exists():
        with open(advisor_path, 'r') as f:
            advisor_data = json.load(f)
            
        # Check if advisor exists
        result = connection.execute(
            sa.text("SELECT id FROM advisors WHERE name = :name"),
            {"name": advisor_data["name"]}
        ).fetchone()
        
        if not result:
            # Create advisor
            advisor_id = str(uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO advisors (
                        id, name, description, model, temperature, max_tokens,
                        stream, messages, gateway, tools, created_at, updated_at
                    ) VALUES (
                        :id, :name, :description, :model, :temperature, :max_tokens,
                        :stream, :messages, :gateway, :tools, :created_at, :updated_at
                    )
                """),
                {
                    "id": advisor_id,
                    "name": advisor_data["name"],
                    "description": advisor_data["description"],
                    "model": advisor_data["model"],
                    "temperature": advisor_data["temperature"],
                    "max_tokens": advisor_data["max_tokens"],
                    "stream": advisor_data["stream"],
                    "messages": json.dumps(advisor_data["messages"]),
                    "gateway": advisor_data["gateway"],
                    "tools": json.dumps(advisor_data.get("tools", [])),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )
            print(f"Created default advisor with ID: {advisor_id}")
    else:
        print(f"Warning: Default advisor file not found at {advisor_path}")
    
    # Get all chat files
    chat_files = get_chat_files()
    
    for chat_file in chat_files:
        try:
            with open(chat_file, 'r') as f:
                messages = json.load(f)
                
            # Extract advisor name from filename
            advisor_name = chat_file.stem
            if '_' in advisor_name:  # Handle archived chats
                advisor_name = '_'.join(advisor_name.split('_')[:-1])
            
            # Get advisor_id from database
            result = connection.execute(
                sa.text("SELECT id FROM advisors WHERE name = :name"),
                {"name": advisor_name}
            ).fetchone()
            
            if not result:
                print(f"Warning: Advisor {advisor_name} not found in database")
                continue
                
            advisor_id = result[0]
            
            # Create conversation
            conversation_id = str(uuid4())
            file_stat = os.stat(chat_file)
            created_at = datetime.fromtimestamp(file_stat.st_ctime)
            updated_at = datetime.fromtimestamp(file_stat.st_mtime)
            
            connection.execute(
                sa.text("""
                    INSERT INTO conversations (id, advisor_id, status, message_count, created_at, updated_at)
                    VALUES (:id, :advisor_id, :status, :count, :created_at, :updated_at)
                """),
                {
                    "id": conversation_id,
                    "advisor_id": advisor_id,
                    "status": "archived" if "archive" in str(chat_file) else "active",
                    "count": len(messages),
                    "created_at": created_at,
                    "updated_at": updated_at
                }
            )
            
            # Insert messages
            for sequence, msg in enumerate(messages, 1):
                message_id = str(uuid4())
                
                # Insert message
                connection.execute(
                    sa.text("""
                        INSERT INTO messages (id, conversation_id, role, content, name, sequence, created_at)
                        VALUES (:id, :conv_id, :role, :content, :name, :seq, :created_at)
                    """),
                    {
                        "id": message_id,
                        "conv_id": conversation_id,
                        "role": msg["role"],
                        "content": msg.get("content"),
                        "name": msg.get("name"),
                        "seq": sequence,
                        "created_at": created_at
                    }
                )
                
                # Handle tool calls if present
                if msg.get("tool_calls"):
                    for tool_call in msg["tool_calls"]:
                        connection.execute(
                            sa.text("""
                                INSERT INTO tool_calls (id, message_id, tool_call_id, type, function_name, function_arguments, created_at)
                                VALUES (:id, :msg_id, :tool_id, :type, :func_name, :func_args, :created_at)
                            """),
                            {
                                "id": str(uuid4()),
                                "msg_id": message_id,
                                "tool_id": tool_call["id"],
                                "type": tool_call["type"],
                                "func_name": tool_call["function"]["name"],
                                "func_args": json.dumps(tool_call["function"]["arguments"]),
                                "created_at": created_at
                            }
                        )
            
            print(f"Successfully migrated chat: {chat_file}")
            
        except Exception as e:
            print(f"Error migrating chat {chat_file}: {str(e)}")
            continue

def downgrade() -> None:
    # No downgrade path provided as this is a data migration
    pass 