"""initial

Revision ID: 001
Revises: 
Create Date: 2024-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )

    # Create auth_sessions table with foreign key reference
    with op.batch_alter_table('users', schema=None) as batch_op:
        op.create_table(
            'auth_sessions',
            sa.Column('id', sa.String(36), nullable=False),  # Use String for UUID in SQLite
            sa.Column('user_id', sa.String(36), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'])
        )

def downgrade() -> None:
    op.drop_table('auth_sessions')
    op.drop_table('users') 