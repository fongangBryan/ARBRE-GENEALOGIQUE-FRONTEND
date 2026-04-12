from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base

class RelationshipType(str, enum.Enum):
    PARENT_CHILD = "parent_child"
    COUPLE = "couple"

class ParentChildType(str, enum.Enum):
    BIOLOGICAL = "biological"
    ADOPTIVE = "adoptive"
    GUARDIAN = "guardian"
    STEP = "step"

class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(SQLEnum(RelationshipType), nullable=False)
    
    person_id_1 = Column(UUID(as_uuid=True), nullable=False)
    person_id_2 = Column(UUID(as_uuid=True), nullable=False)
    
    # Pour PARENT_CHILD: person_id_1 = parent, person_id_2 = child
    # Pour COUPLE: ordre indifférent
    
    child_type = Column(SQLEnum(ParentChildType), nullable=True)  # Pour PARENT_CHILD
    
    # Pour COUPLE
    marriage_date = Column(String(50), nullable=True)
    marriage_place = Column(String(255), nullable=True)
    divorce_date = Column(String(50), nullable=True)
    
    # Métadonnées additionnelles (JSON)
    meta = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)