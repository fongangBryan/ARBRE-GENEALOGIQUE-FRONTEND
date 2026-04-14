from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class MediaTypeEnum(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    PDF = "pdf"

class MediaBase(BaseModel):
    owner_type: str  # person, event, user
    owner_id: UUID
    media_type: MediaTypeEnum
    privacy_level: str = "private"

class MediaCreate(MediaBase):
    original_filename: str
    storage_key: str
    thumbnail_key: Optional[str] = None
    mime_type: str
    file_size: int

class MediaResponse(MediaBase):
    id: UUID
    original_filename: str
    storage_key: str
    thumbnail_key: Optional[str] = None
    mime_type: str
    file_size: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MediaUploadResponse(BaseModel):
    id: UUID
    filename: str
    storage_key: str
    thumbnail_key: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None

class MediaListResponse(BaseModel):
    items: List[MediaResponse]
    total: int