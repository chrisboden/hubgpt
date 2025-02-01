"""create_admin_user

Revision ID: 007
Revises: 006
Create Date: 2024-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from uuid import uuid4
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def upgrade() -> None:
    # Create a connection to use for raw SQL
    connection = op.get_bind()
    
    # Create admin user
    connection.execute(
        sa.text("""
            INSERT INTO users (
                id, username, email, hashed_password, created_at, settings
            ) VALUES (
                :id, :username, :email, :hashed_password, :created_at, :settings
            )
        """),
        {
            "id": str(uuid4()),
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("password"),
            "created_at": datetime.utcnow(),
            "settings": "{}"
        }
    )

def downgrade() -> None:
    # Remove admin user
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM users WHERE username = 'admin'")
    ) 