from sqlalchemy import Column, String, DateTime, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base import Base

# Table d'association entre Person et Tag (Many-to-Many)
person_tag = Table(
    "person_tags",
    Base.metadata,
    Column("person_id", UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE")),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE")),
    Column("created_at", DateTime, default=datetime.utcnow)
)


class Tag(Base):
    """
    Tag / libellé libre pour catégoriser les personnes.
    Exemples : "Ancêtre direct", "Branche maternelle", "DNA match", "Vétéran"
    """
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    color = Column(String(7), default="#02E08E")  # Couleur hexadécimale pour l'affichage
    icon = Column(String(50), nullable=True)  # Nom de l'icône (ex: "star", "heart")
    
    # Tag créé par quel utilisateur
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations — backref crée automatiquement Person.tags sans modifier person.py
    persons = relationship("Person", secondary=person_tag, backref="tags")


class PersonTagHistory(Base):
    """
    Historique des tags attribués aux personnes (optionnel, pour audit)
    """
    __tablename__ = "person_tag_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), nullable=False)
    tag_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(20), nullable=False)  # "added" or "removed"
    performed_by = Column(UUID(as_uuid=True), nullable=True)
    performed_at = Column(DateTime, default=datetime.utcnow)