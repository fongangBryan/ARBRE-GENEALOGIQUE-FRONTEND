from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base


class FiliationType(str, enum.Enum):
    BIOLOGICAL = "biological"
    ADOPTIVE   = "adoptive"
    STEP       = "step"
    GUARDIAN   = "guardian"


class Filiation(Base):
    __tablename__ = "filiations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id      = Column(UUID(as_uuid=True), nullable=False, index=True)
    child_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    filiation_type = Column(SQLEnum(FiliationType), default=FiliationType.BIOLOGICAL, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
