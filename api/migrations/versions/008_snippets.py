"""snippets

Revision ID: 008
Revises: 007
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create snippets table
    op.create_table(
        'snippets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text()),
        sa.Column('title', sa.String()),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('snippet_metadata', sa.JSON(), server_default='{}')
    )

    # Create indexes
    op.create_index('ix_snippets_user_id', 'snippets', ['user_id'])
    op.create_index('ix_snippets_title', 'snippets', ['title'])

def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_snippets_title')
    op.drop_index('ix_snippets_user_id')
    
    # Drop table
    op.drop_table('snippets') 