from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    READER = "reader"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.READER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # 2FA
    is_2fa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String(100), nullable=True)
    temp_2fa_secret = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)