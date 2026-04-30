from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base import Base


class UnionType(str, enum.Enum):
    MARIAGE     = "mariage"
    UNION_LIBRE = "union_libre"
    PACS        = "pacs"
    FIANCAILLES = "fiancailles"


class UnionStatut(str, enum.Enum):
    ACTIF   = "actif"
    DISSOUS = "dissous"


class Union(Base):
    __tablename__ = "unions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id_1     = Column(UUID(as_uuid=True), nullable=False, index=True)
    person_id_2     = Column(UUID(as_uuid=True), nullable=False, index=True)
    union_type      = Column(SQLEnum(UnionType), default=UnionType.MARIAGE, nullable=False)
    date_union      = Column(String(50), nullable=True)   # Format partiel : AAAA / AAAA-MM / AAAA-MM-JJ
    lieu_union      = Column(String(255), nullable=True)
    date_dissolution = Column(String(50), nullable=True)  # Divorce, veuvage, rupture
    statut          = Column(SQLEnum(UnionStatut), default=UnionStatut.ACTIF, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
