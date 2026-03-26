"""
Modèle Relationship — cœur du modèle généalogique.
Gère les liens parent/enfant et les unions (couples).
"""
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base
from app.db.types import JSONB
from app.models.mixins import UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.person import Person


class RelationshipType(str, enum.Enum):
    PARENT_CHILD = "parent_child"
    COUPLE = "couple"


class ParentChildType(str, enum.Enum):
    """Type de lien filial — stocké dans meta JSONB."""
    BIOLOGICAL = "biological"
    ADOPTIVE = "adoptive"
    GUARDIAN = "guardian"
    STEP = "step"          # beau-parent / belle-mère


class UnionType(str, enum.Enum):
    """Type d'union — stocké dans meta JSONB."""
    MARRIAGE = "marriage"
    CIVIL_UNION = "civil_union"     # PACS, partenariat civil
    COHABITATION = "cohabitation"   # union libre
    ENGAGEMENT = "engagement"
    OTHER = "other"


class Relationship(Base, UUIDMixin, TimestampMixin):
    """
    Lien généalogique entre deux personnes.

    Convention PARENT_CHILD :
        person_id_1 = parent
        person_id_2 = enfant

    Convention COUPLE :
        person_id_1 / person_id_2 = les deux conjoints (ordre non significatif)

    Le champ `meta` (JSONB) stocke les infos contextuelles selon le type :
        PARENT_CHILD  → { "parentage_type": "biological" }
        COUPLE        → { "union_type": "marriage", "start_date": "1985",
                          "end_date": null, "is_ended": false }

    Règle d'intégrité : person_id_1 ≠ person_id_2 (pas d'auto-relation).
    """
    __tablename__ = "relationships"

    # ── Personnes concernées ─────────────────────────────────────────────────
    person_id_1: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id_2: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Type de relation ─────────────────────────────────────────────────────
    relationship_type: Mapped[RelationshipType] = mapped_column(
        SAEnum(RelationshipType, name="relationship_type_enum"),
        nullable=False,
        index=True,
    )

    # ── Métadonnées contextuelles (JSONB flexible) ───────────────────────────
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Note de relation (ex : "adoption notariée le 12/03/1972")
    notes: Mapped[Optional[str]] = mapped_column(String(1000))

    # ── Relations SQLAlchemy ─────────────────────────────────────────────────
    person_1: Mapped["Person"] = relationship(
        "Person", foreign_keys=[person_id_1], lazy="select"
    )
    person_2: Mapped["Person"] = relationship(
        "Person", foreign_keys=[person_id_2], lazy="select"
    )

    # ── Contraintes & Index ──────────────────────────────────────────────────
    __table_args__ = (
        # Empêcher A → A
        CheckConstraint(
            "person_id_1 != person_id_2",
            name="ck_relationship_no_self_loop",
        ),
        Index("ix_rel_person1_type", "person_id_1", "relationship_type"),
        Index("ix_rel_person2_type", "person_id_2", "relationship_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<Relationship {self.relationship_type} "
            f"{self.person_id_1} ↔ {self.person_id_2}>"
        )
