"""advisor_schema

Revision ID: 004
Revises: 003
Create Date: 2024-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4
import yaml

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create a connection to use for raw SQL
    connection = op.get_bind()
    
    # Drop existing advisors table if it exists
    op.drop_table('advisors', if_exists=True)
    
    # Create new advisors table with updated schema
    op.create_table(
        'advisors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('stream', sa.Boolean(), nullable=True),
        sa.Column('messages', sa.JSON(), nullable=False),
        sa.Column('gateway', sa.String(), nullable=True),
        sa.Column('tools', sa.JSON(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), nullable=True),
        sa.Column('presence_penalty', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Migrate existing advisors from files
    advisors_dir = Path("advisors")
    if advisors_dir.exists():
        # Process JSON files
        for file_path in advisors_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
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
                        "id": str(uuid4()),
                        "name": file_path.stem,
                        "description": data.get("description"),
                        "model": data.get("model", "openai/gpt-4o-mini"),
                        "temperature": float(data.get("temperature", 1.0)),
                        "max_tokens": int(data.get("max_tokens", 1000)),
                        "stream": bool(data.get("stream", True)),
                        "messages": json.dumps(data.get("messages", [])),
                        "gateway": data.get("gateway", "openrouter"),
                        "tools": json.dumps(data.get("tools", [])),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )
                print(f"Migrated advisor from {file_path}")
                
            except Exception as e:
                print(f"Error migrating advisor {file_path}: {str(e)}")
                continue
        
        # Process Markdown files
        for file_path in advisors_dir.glob("*.md"):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Split content into frontmatter and markdown
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    # Parse YAML frontmatter
                    frontmatter = yaml.safe_load(parts[1])
                    markdown_content = parts[2].strip()
                    
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
                            "id": str(uuid4()),
                            "name": file_path.stem,
                            "description": None,
                            "model": frontmatter.get("model", "openai/gpt-4o-mini"),
                            "temperature": float(frontmatter.get("temperature", 1.0)),
                            "max_tokens": int(frontmatter.get("max_output_tokens", frontmatter.get("max_tokens", 1000))),
                            "stream": bool(frontmatter.get("stream", True)),
                            "messages": json.dumps([{
                                "role": "system",
                                "content": markdown_content
                            }]),
                            "gateway": frontmatter.get("gateway", "openrouter"),
                            "tools": json.dumps(frontmatter.get("tools", [])),
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                    print(f"Migrated advisor from {file_path}")
                    
            except Exception as e:
                print(f"Error migrating advisor {file_path}: {str(e)}")
                continue

def downgrade() -> None:
    # Drop the advisors table
    op.drop_table('advisors') 