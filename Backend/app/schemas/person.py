"""
Schémas Pydantic — Person.
Accepte les données incomplètes (dates nullables, champs optionnels).
"""
from datetime import date, datetime
from typing import Optional, List, Any
import uuid

from pydantic import BaseModel, Field, model_validator

from app.models.person import Sex, PrivacyLevel


# ─────────────────────────────────────────────────────────────────────────────
# Sous-schémas réutilisables
# ─────────────────────────────────────────────────────────────────────────────

class TagMinimal(BaseModel):
    id: uuid.UUID
    label: str
    color: Optional[str] = None

    model_config = {"from_attributes": True}


class MediaMinimal(BaseModel):
    id: uuid.UUID
    storage_key: str
    thumbnail_key: Optional[str] = None
    caption: Optional[str] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class PersonBase(BaseModel):
    # Identité
    first_name: str = Field(..., min_length=1, max_length=150)
    last_name: str = Field(..., min_length=1, max_length=150)
    middle_names: Optional[str] = Field(None, max_length=300)
    maiden_name: Optional[str] = Field(None, max_length=150)
    nickname: Optional[str] = Field(None, max_length=150)
    sex: Optional[Sex] = None

    # Naissance (données incomplètes acceptées : texte OU date précise)
    birth_date: Optional[str] = Field(
        None, max_length=100,
        description="Date de naissance en texte libre (ex: 'vers 1850', 'ca. 1920')"
    )
    birth_date_exact: Optional[date] = Field(
        None, description="Date précise de naissance (si connue)"
    )
    birth_place: Optional[str] = Field(None, max_length=300)

    # Décès
    death_date: Optional[str] = Field(None, max_length=100)
    death_date_exact: Optional[date] = None
    death_place: Optional[str] = Field(None, max_length=300)

    is_living: bool = True

    # Informations complémentaires
    nationalities: Optional[str] = Field(None, max_length=500)
    professions: Optional[str] = Field(None, max_length=500)
    contacts: Optional[dict] = None

    biography: Optional[str] = None
    notes_public: Optional[str] = None

    # Confidentialité
    privacy_level: PrivacyLevel = PrivacyLevel.FAMILY

    @model_validator(mode="after")
    def validate_death_implies_not_living(self) -> "PersonBase":
        """Si une date de décès est renseignée, is_living doit être False."""
        if (self.death_date or self.death_date_exact) and self.is_living:
            self.is_living = False
        return self

    @model_validator(mode="after")
    def validate_birth_before_death(self) -> "PersonBase":
        """Avertissement (non bloquant) si naissance après décès."""
        if self.birth_date_exact and self.death_date_exact:
            if self.birth_date_exact > self.death_date_exact:
                # On ne lève pas d'erreur car les données peuvent être incertaines
                # Le frontend affichera un warning
                pass
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────────────────────

class PersonCreate(PersonBase):
    notes_private: Optional[str] = None   # Créateur voit ses propres notes
    tag_ids: Optional[List[uuid.UUID]] = Field(
        default=None, description="IDs des tags à associer à la création"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Update (PATCH — tous les champs optionnels)
# ─────────────────────────────────────────────────────────────────────────────

class PersonUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=150)
    last_name: Optional[str] = Field(None, min_length=1, max_length=150)
    middle_names: Optional[str] = Field(None, max_length=300)
    maiden_name: Optional[str] = Field(None, max_length=150)
    nickname: Optional[str] = Field(None, max_length=150)
    sex: Optional[Sex] = None

    birth_date: Optional[str] = Field(None, max_length=100)
    birth_date_exact: Optional[date] = None
    birth_place: Optional[str] = Field(None, max_length=300)

    death_date: Optional[str] = Field(None, max_length=100)
    death_date_exact: Optional[date] = None
    death_place: Optional[str] = Field(None, max_length=300)

    is_living: Optional[bool] = None
    nationalities: Optional[str] = None
    professions: Optional[str] = None
    contacts: Optional[dict] = None
    biography: Optional[str] = None
    notes_public: Optional[str] = None
    notes_private: Optional[str] = None
    privacy_level: Optional[PrivacyLevel] = None

    tag_ids: Optional[List[uuid.UUID]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Responses
# ─────────────────────────────────────────────────────────────────────────────

class PersonSummary(BaseModel):
    """Vue résumée — utilisée dans les listes et les nœuds du graphe."""
    id: uuid.UUID
    first_name: str
    last_name: str
    nickname: Optional[str] = None
    birth_date: Optional[str] = None
    birth_date_exact: Optional[date] = None
    death_date: Optional[str] = None
    death_date_exact: Optional[date] = None
    is_living: bool
    sex: Optional[Sex] = None
    privacy_level: PrivacyLevel
    profile_media: Optional[MediaMinimal] = None
    tags: List[TagMinimal] = []

    model_config = {"from_attributes": True}


class PersonResponse(PersonBase):
    """Vue complète — page de profil."""
    id: uuid.UUID
    notes_private: Optional[str] = None   # Masqué si non autorisé (géré dans la route)
    created_at: datetime
    updated_at: datetime
    profile_media: Optional[MediaMinimal] = None
    tags: List[TagMinimal] = []

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    """Réponse paginée pour GET /persons."""
    items: List[PersonSummary]
    total: int
    page: int
    size: int
    pages: int


# ─────────────────────────────────────────────────────────────────────────────
# Graphe (nœuds / arêtes pour Cytoscape.js)
# ─────────────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """Nœud compatible Cytoscape.js."""
    id: str                             # UUID stringifié
    first_name: str
    last_name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    is_living: bool
    sex: Optional[str] = None
    thumbnail_url: Optional[str] = None
    privacy_level: str


class GraphEdge(BaseModel):
    """Arête compatible Cytoscape.js."""
    id: str
    source: str
    target: str
    relationship_type: str
    meta: Optional[dict] = None


class GraphResponse(BaseModel):
    """Réponse des endpoints /graph — format Cytoscape."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
