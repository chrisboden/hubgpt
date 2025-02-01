from sqlalchemy import Column, String, Boolean, BigInteger, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base
from uuid import uuid4

class UserFile(Base):
    """SQLAlchemy model for user files"""
    __tablename__ = "user_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    content_type = Column(String)
    size_bytes = Column(BigInteger)
    is_public = Column(Boolean, server_default="false")
    file_metadata = Column(JSON, server_default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="files")
    shares = relationship("FileShare", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserFile(id={self.id}, user_id={self.user_id}, path={self.file_path})>"

class FileShare(Base):
    """SQLAlchemy model for file shares"""
    __tablename__ = "file_shares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_id = Column(String(36), ForeignKey("user_files.id"), nullable=False)
    shared_with_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    permissions = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    file = relationship("UserFile", back_populates="shares")
    shared_with = relationship("User")

    def __repr__(self):
        return f"<FileShare(id={self.id}, file_id={self.file_id}, shared_with={self.shared_with_id})>" 