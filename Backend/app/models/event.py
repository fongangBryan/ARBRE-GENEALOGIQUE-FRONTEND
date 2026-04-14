from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SQLEnum
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class EventType(str, enum.Enum):
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

class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    date_start = Column(String(50), nullable=True)
    date_end = Column(String(50), nullable=True)
    place = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)