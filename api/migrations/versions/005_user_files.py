"""user_files

Revision ID: 005
Revises: 004
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import os
from pathlib import Path

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create user_files table
    op.create_table(
        'user_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('content_type', sa.String()),
        sa.Column('size_bytes', sa.BigInteger()),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('file_metadata', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'file_path', name='uq_user_file_path')
    )

    # Create file_shares table
    op.create_table(
        'file_shares',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('file_id', sa.String(36), sa.ForeignKey('user_files.id'), nullable=False),
        sa.Column('shared_with_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('file_id', 'shared_with_id', name='uq_file_share')
    )

    # Create indexes
    op.create_index('ix_user_files_user_id', 'user_files', ['user_id'])
    op.create_index('ix_user_files_file_path', 'user_files', ['file_path'])
    op.create_index('ix_user_files_is_public', 'user_files', ['is_public'])
    op.create_index('ix_file_shares_file_id', 'file_shares', ['file_id'])
    op.create_index('ix_file_shares_shared_with_id', 'file_shares', ['shared_with_id'])

    # Create storage directory structure
    storage_dir = Path("storage")
    (storage_dir / "users").mkdir(parents=True, exist_ok=True)
    (storage_dir / "shared" / "advisors").mkdir(parents=True, exist_ok=True)
    (storage_dir / "shared" / "content").mkdir(parents=True, exist_ok=True)

def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_file_shares_shared_with_id')
    op.drop_index('ix_file_shares_file_id')
    op.drop_index('ix_user_files_is_public')
    op.drop_index('ix_user_files_file_path')
    op.drop_index('ix_user_files_user_id')

    # Drop tables
    op.drop_table('file_shares')
    op.drop_table('user_files') 