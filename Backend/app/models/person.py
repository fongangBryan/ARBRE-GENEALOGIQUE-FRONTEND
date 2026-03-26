"""
Modèle Person — entité centrale de l'arbre généalogique.
Supporte les données incomplètes (dates nullables, champs optionnels).
"""
from typing import List, Optional, TYPE_CHECKING
import uuid

from sqlalchemy import (
    String, Text, Boolean, Date, Enum as SAEnum,
    Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base
from app.db.types import JSONB, PortableTSVECTOR
from app.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.relationship import Relationship
    from app.models.event import Event
    from app.models.media import Media
    from app.models.tag import Tag, PersonTag
    from app.models.access_control import AccessControl


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class PrivacyLevel(str, enum.Enum):
    PUBLIC = "public"
    FAMILY = "family"
    PRIVATE = "private"


class Person(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Représente une personne dans l'arbre généalogique.

    Points clés du cahier des charges :
    - Toutes les dates sont optionnelles (données incomplètes acceptées)
    - privacy_level gère la visibilité (public / famille / privé)
    - is_living permet le masquage automatique des vivants (RGPD)
    - search_vector : colonne tsvector pour la full-text search PostgreSQL
    """
    __tablename__ = "persons"

    # ── Identité ─────────────────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    middle_names: Mapped[Optional[str]] = mapped_column(String(300))
    maiden_name: Mapped[Optional[str]] = mapped_column(String(150))     # nom de jeune fille
    nickname: Mapped[Optional[str]] = mapped_column(String(150))

    sex: Mapped[Optional[Sex]] = mapped_column(
        SAEnum(Sex, name="sex_enum"),
        nullable=True,
    )

    # ── Naissance / Décès  ───────────────────────────────────────────────────
    # On accepte Date OU texte libre ("vers 1850", "ca. 1920")
    birth_date: Mapped[Optional[str]] = mapped_column(String(100))      # texte structuré
    birth_date_exact: Mapped[Optional["Date"]] = mapped_column(Date, nullable=True)
    birth_place: Mapped[Optional[str]] = mapped_column(String(300))

    death_date: Mapped[Optional[str]] = mapped_column(String(100))
    death_date_exact: Mapped[Optional["Date"]] = mapped_column(Date, nullable=True)
    death_place: Mapped[Optional[str]] = mapped_column(String(300))

    is_living: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Informations complémentaires ─────────────────────────────────────────
    nationalities: Mapped[Optional[str]] = mapped_column(
        String(500)
    )  # CSV ou JSONB selon besoin
    professions: Mapped[Optional[str]] = mapped_column(String(500))
    contacts: Mapped[Optional[dict]] = mapped_column(JSONB)              # email, phone…

    biography: Mapped[Optional[str]] = mapped_column(Text)
    notes_private: Mapped[Optional[str]] = mapped_column(Text)          # visibles admin/éditeur
    notes_public: Mapped[Optional[str]] = mapped_column(Text)

    # ── Confidentialité ──────────────────────────────────────────────────────
    privacy_level: Mapped[PrivacyLevel] = mapped_column(
        SAEnum(PrivacyLevel, name="privacy_level_enum"),
        default=PrivacyLevel.FAMILY,
        nullable=False,
    )

    # ── Full-text search (PostgreSQL) ─────────────────────────────────────────
    # Mis à jour via trigger SQL ou Alembic computed column
    search_vector: Mapped[Optional[str]] = mapped_column(PortableTSVECTOR, nullable=True)

    # ── Photo principale ─────────────────────────────────────────────────────
    # Clé étrangère vers Media (optionnelle, définie après pour éviter la circularité)
    profile_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medias.id", use_alter=True, name="fk_person_profile_media"),
        nullable=True,
    )

    # ── Relations SQLAlchemy ─────────────────────────────────────────────────
    events: Mapped[List["Event"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    medias: Mapped[List["Media"]] = relationship(
        "Media",
        primaryjoin="and_(Media.owner_id == Person.id, Media.owner_type == 'PERSON')",
        foreign_keys="Media.owner_id",
        lazy="selectin",
        overlaps="profile_media",
    )
    profile_media: Mapped[Optional["Media"]] = relationship(
        "Media",
        foreign_keys=[profile_media_id],
        lazy="select",
        overlaps="medias",
    )
    person_tags: Mapped[List["PersonTag"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    access_controls: Mapped[List["AccessControl"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )

    # ── Index composites ─────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_person_full_name", "last_name", "first_name"),
        # Index GIN PostgreSQL uniquement (ignoré sur SQLite)
        # Index("ix_person_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_person_privacy", "privacy_level"),
        Index("ix_person_living", "is_living"),
    )

    def __repr__(self) -> str:
        return f"<Person {self.first_name} {self.last_name} [{self.id}]>"

    @property
    def full_name(self) -> str:
        parts = [self.first_name]
        if self.middle_names:
            parts.append(self.middle_names)
        parts.append(self.last_name)
        return " ".join(parts)
