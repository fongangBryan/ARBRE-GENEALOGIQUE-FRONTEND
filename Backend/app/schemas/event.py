from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class EventTypeEnum(str, Enum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    BAPTISM = "baptism"
    BURIAL = "burial"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    RESIDENCE = "residence"
    CUSTOM = "custom"

class EventBase(BaseModel):
    person_id: UUID
    event_type: EventTypeEnum
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    place: Optional[str] = None
    description: Optional[str] = None
    meta: Optional[dict] = {}

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    event_type: Optional[EventTypeEnum] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    place: Optional[str] = None
    description: Optional[str] = None
    meta: Optional[dict] = None

class EventResponse(EventBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int