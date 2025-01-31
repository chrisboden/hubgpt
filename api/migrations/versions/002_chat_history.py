"""chat_history

Revision ID: 002b
Revises: 002a
Create Date: 2024-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002b'
down_revision = '002a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create conversations table to track chat sessions
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('advisor_id', sa.String(36), sa.ForeignKey('advisors.id'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),  # Optional user association
        sa.Column('title', sa.String(), nullable=True),  # Optional conversation title
        sa.Column('status', sa.String(), nullable=False, default='active'),  # active, archived
        sa.Column('message_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=True)
    )

    # Create messages table for individual messages
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),  # user, assistant, system, tool
        sa.Column('content', sa.Text(), nullable=True),  # Nullable because tool calls might have null content
        sa.Column('name', sa.String(), nullable=True),  # For tool messages
        sa.Column('llm_message_id', sa.String(), nullable=True),  # ID from LLM response
        sa.Column('parent_message_id', sa.String(36), nullable=True),  # For threading/reply tracking
        sa.Column('sequence', sa.Integer(), nullable=False),  # Order in conversation
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('finish_reason', sa.String(), nullable=True),  # stop, length, tool_calls, etc
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True)
    )

    # Create tool_calls table for assistant messages that include tool calls
    op.create_table(
        'tool_calls',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('message_id', sa.String(36), sa.ForeignKey('messages.id'), nullable=False),
        sa.Column('tool_call_id', sa.String(), nullable=False),  # ID from LLM tool call
        sa.Column('type', sa.String(), nullable=False),  # function, etc
        sa.Column('function_name', sa.String(), nullable=False),
        sa.Column('function_arguments', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # Create indexes
    op.create_index('ix_conversations_advisor_id', 'conversations', ['advisor_id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_status', 'conversations', ['status'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_sequence', 'messages', ['conversation_id', 'sequence'])
    op.create_index('ix_tool_calls_message_id', 'tool_calls', ['message_id'])

def downgrade() -> None:
    op.drop_index('ix_tool_calls_message_id')
    op.drop_index('ix_messages_sequence')
    op.drop_index('ix_messages_conversation_id')
    op.drop_index('ix_conversations_status')
    op.drop_index('ix_conversations_user_id')
    op.drop_index('ix_conversations_advisor_id')
    op.drop_table('tool_calls')
    op.drop_table('messages')
    op.drop_table('conversations') 