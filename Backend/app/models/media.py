from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SQLEnum
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class MediaType(str, enum.Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    PDF = "pdf"

class Media(Base):
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_type = Column(String(50), nullable=False)  # person, event, user
    owner_id = Column(String(255), nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False)
    privacy_level = Column(String(50), default="private")
    
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    thumbnail_key = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)