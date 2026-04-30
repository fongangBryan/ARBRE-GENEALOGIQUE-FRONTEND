from datetime import datetime, timezone
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrivacyLevel(str, enum.Enum):
    PUBLIC  = "public"
    FAMILY  = "family"
    PRIVATE = "private"


class Gender(str, enum.Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"


def _now():
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Propriétaire de la fiche — clé étrangère vers users.id
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner = relationship("User", foreign_keys=[created_by], backref="persons")

    first_name  = Column(String(100), nullable=False)
    last_name   = Column(String(100), nullable=False)
    maiden_name = Column(String(100), nullable=True)
    gender      = Column(SQLEnum(Gender), nullable=True)

    birth_date  = Column(String(50),  nullable=True)   # accepte YYYY ou YYYY-MM
    birth_place = Column(String(255), nullable=True)
    death_date  = Column(String(50),  nullable=True)
    death_place = Column(String(255), nullable=True)

    is_living    = Column(Boolean, default=True)
    biography    = Column(Text,        nullable=True)
    occupation   = Column(String(255), nullable=True)
    nationality  = Column(String(100), nullable=True)

    privacy_level  = Column(SQLEnum(PrivacyLevel), default=PrivacyLevel.PRIVATE)
    main_photo_key = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
