from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class PrivacyLevel(str, enum.Enum):
    PUBLIC = "public"
    FAMILY = "family"
    PRIVATE = "private"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Person(Base):
    __tablename__ = "persons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    maiden_name = Column(String(100), nullable=True)  # Nom de jeune fille
    gender = Column(SQLEnum(Gender), nullable=True)
    
    birth_date = Column(String(50), nullable=True)  # Accepte dates partielles (YYYY, YYYY-MM)
    birth_place = Column(String(255), nullable=True)
    death_date = Column(String(50), nullable=True)
    death_place = Column(String(255), nullable=True)
    
    is_living = Column(Boolean, default=True)
    biography = Column(Text, nullable=True)
    occupation = Column(String(255), nullable=True)
    nationality = Column(String(100), nullable=True)
    
    privacy_level = Column(SQLEnum(PrivacyLevel), default=PrivacyLevel.PRIVATE)
    
    # Photo principale
    main_photo_key = Column(String(500), nullable=True)
    
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)