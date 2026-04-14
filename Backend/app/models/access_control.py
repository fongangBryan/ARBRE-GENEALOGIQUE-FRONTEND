from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class PermissionType(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

class PrincipalType(str, enum.Enum):
    USER = "user"
    ROLE = "role"

class AccessControl(Base):
    __tablename__ = "access_controls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), nullable=False)
    principal_type = Column(SQLEnum(PrincipalType), nullable=False)
    principal_id = Column(String(255), nullable=False)  # user_id or role name
    permission = Column(SQLEnum(PermissionType), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)