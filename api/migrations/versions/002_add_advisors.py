"""add_advisors

Revision ID: 002a
Revises: 001
Create Date: 2024-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002a'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create advisors table
    op.create_table(
        'advisors',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('model', sa.String()),
        sa.Column('temperature', sa.Float()),
        sa.Column('max_tokens', sa.Integer()),
        sa.Column('stream', sa.Boolean()),
        sa.Column('messages', sa.JSON()),
        sa.Column('gateway', sa.String()),
        sa.Column('tools', sa.JSON()),
        sa.Column('top_p', sa.Float()),
        sa.Column('frequency_penalty', sa.Float()),
        sa.Column('presence_penalty', sa.Float()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime())
    )

def downgrade() -> None:
    op.drop_table('advisors') 