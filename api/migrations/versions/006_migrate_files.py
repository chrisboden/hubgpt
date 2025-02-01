"""migrate_files

Revision ID: 006
Revises: 005
Create Date: 2024-03-19 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pathlib import Path
import shutil
from uuid import uuid4
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Get SQLAlchemy connection
    connection = op.get_bind()
    
    # Get all users
    users = connection.execute(
        sa.text("SELECT id, username FROM users")
    ).fetchall()
    
    # Old files directory
    old_files_dir = Path("files")
    if not old_files_dir.exists():
        return
        
    # New storage directory
    storage_dir = Path("storage")
    
    # Create user directories
    for user in users:
        user_dir = storage_dir / "users" / user.id / "files"
        user_dir.mkdir(parents=True, exist_ok=True)
        
    # Move shared files
    shared_dir = storage_dir / "shared"
    if old_files_dir.exists():
        # Move advisor files
        advisor_files = list(old_files_dir.glob("advisors/*"))
        if advisor_files:
            advisor_dir = shared_dir / "advisors"
            advisor_dir.mkdir(parents=True, exist_ok=True)
            for file in advisor_files:
                target = advisor_dir / file.name
                if file.is_file():
                    shutil.copy2(file, target)
                    
        # Move other shared files
        content_files = [f for f in old_files_dir.glob("*") 
                        if f.is_file() and not str(f).startswith("advisors")]
        if content_files:
            content_dir = shared_dir / "content"
            content_dir.mkdir(parents=True, exist_ok=True)
            for file in content_files:
                target = content_dir / file.name
                if file.is_file():
                    shutil.copy2(file, target)
                    
    # Create file records for shared files
    if shared_dir.exists():
        for file in shared_dir.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(storage_dir)
                file_type = file.suffix.lstrip('.') or 'txt'
                size_bytes = file.stat().st_size
                
                # Insert file record
                connection.execute(
                    sa.text("""
                        INSERT INTO user_files (
                            id, user_id, file_path, file_type, 
                            size_bytes, is_public, metadata,
                            created_at, updated_at
                        ) VALUES (
                            :id, :user_id, :file_path, :file_type,
                            :size_bytes, :is_public, :metadata,
                            :created_at, :updated_at
                        )
                    """),
                    {
                        "id": str(uuid4()),
                        "user_id": users[0].id,  # Assign to first user
                        "file_path": str(rel_path),
                        "file_type": file_type,
                        "size_bytes": size_bytes,
                        "is_public": True,
                        "metadata": "{}",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )

def downgrade() -> None:
    # Get SQLAlchemy connection
    connection = op.get_bind()
    
    # Delete all file records
    connection.execute(sa.text("DELETE FROM file_shares"))
    connection.execute(sa.text("DELETE FROM user_files"))
    
    # Move files back (optional)
    storage_dir = Path("storage")
    old_files_dir = Path("files")
    
    if storage_dir.exists():
        if old_files_dir.exists():
            shutil.rmtree(old_files_dir)
        old_files_dir.mkdir(parents=True)
        
        # Move shared files back
        shared_dir = storage_dir / "shared"
        if shared_dir.exists():
            for file in shared_dir.rglob("*"):
                if file.is_file():
                    target = old_files_dir / file.name
                    shutil.copy2(file, target) 