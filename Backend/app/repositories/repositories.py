"""
Repositories — couche d'accès aux données (pattern Repository).
Cf. cours Jour 1 : BaseRepository générique + repositories spécialisés.
Cf. cours Jour 2 : SQLAlchemy 2.0, eager loading, requêtes optimisées.
"""
import math
import uuid
from typing import Generic, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.base import Base
from app.models.person import Person, PrivacyLevel
from app.models.relationship import Relationship, RelationshipType
from app.models.event import Event
from app.models.media import Media
from app.models.tag_and_acl import Tag, PersonTag
from app.models.user import User

ModelType = TypeVar("ModelType")


# ═════════════════════════════════════════════════════════════════════════════
# BASE REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class BaseRepository(Generic[ModelType]):
    """
    Repository générique avec opérations CRUD de base.
    Utilise les Generics (TypeVar) pour la réutilisabilité (cf. cours Jour 1).
    """

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: uuid.UUID) -> Optional[ModelType]:
        return self.db.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.db.execute(stmt).scalar_one()

    def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: uuid.UUID, obj_in: dict) -> Optional[ModelType]:
        db_obj = self.get(id)
        if not db_obj:
            return None
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: uuid.UUID) -> bool:
        db_obj = self.get(id)
        if not db_obj:
            return False
        self.db.delete(db_obj)
        self.db.commit()
        return True


# ═════════════════════════════════════════════════════════════════════════════
# PERSON REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class PersonRepository(BaseRepository[Person]):
    """
    Repository spécialisé pour les personnes.
    Optimisé pour éviter les N+1 (selectinload sur tags et media).
    """

    def __init__(self, db: Session):
        super().__init__(Person, db)

    # ── Lecture ──────────────────────────────────────────────────────────────

    def get_with_relations(self, person_id: uuid.UUID) -> Optional[Person]:
        """Charge une personne avec tous ses événements, médias et tags (eager)."""
        stmt = (
            select(Person)
            .where(Person.id == person_id)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.events),
                selectinload(Person.medias),
                selectinload(Person.person_tags).selectinload(PersonTag.tag),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        search: Optional[str] = None,
        tag_label: Optional[str] = None,
        sex: Optional[str] = None,
        living_only: Optional[bool] = None,
        privacy_levels: Optional[List[PrivacyLevel]] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Person], int]:
        """
        Recherche paginée avec filtres multiples.
        Retourne (items, total) pour construire la réponse paginée.

        Optimisations :
        - Index GIN sur search_vector pour la full-text search
        - Index composites sur (last_name, first_name) et privacy_level
        - selectinload sur person_tags pour éviter N+1
        """
        stmt = (
            select(Person)
            .where(Person.deleted_at.is_(None))
            .options(
                selectinload(Person.person_tags).selectinload(PersonTag.tag),
                selectinload(Person.profile_media),
            )
        )
        count_stmt = select(func.count(Person.id)).where(Person.deleted_at.is_(None))

        # ── Filtres ──────────────────────────────────────────────────────────
        if search:
            # Full-text search PostgreSQL sur le vecteur pré-calculé,
            # avec fallback ILIKE pour SQLite (tests)
            search_filter = or_(
                Person.first_name.ilike(f"%{search}%"),
                Person.last_name.ilike(f"%{search}%"),
                Person.nickname.ilike(f"%{search}%"),
                Person.maiden_name.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        if tag_label:
            stmt = (
                stmt.join(PersonTag, PersonTag.person_id == Person.id)
                    .join(Tag, Tag.id == PersonTag.tag_id)
                    .where(Tag.label == tag_label)
            )
            count_stmt = (
                count_stmt.join(PersonTag, PersonTag.person_id == Person.id)
                          .join(Tag, Tag.id == PersonTag.tag_id)
                          .where(Tag.label == tag_label)
            )

        if sex:
            stmt = stmt.where(Person.sex == sex)
            count_stmt = count_stmt.where(Person.sex == sex)

        if living_only is True:
            stmt = stmt.where(Person.is_living.is_(True))
            count_stmt = count_stmt.where(Person.is_living.is_(True))
        elif living_only is False:
            stmt = stmt.where(Person.is_living.is_(False))
            count_stmt = count_stmt.where(Person.is_living.is_(False))

        if privacy_levels:
            stmt = stmt.where(Person.privacy_level.in_(privacy_levels))
            count_stmt = count_stmt.where(Person.privacy_level.in_(privacy_levels))

        # ── Tri + pagination ─────────────────────────────────────────────────
        stmt = stmt.order_by(Person.last_name, Person.first_name).offset(skip).limit(limit)

        items = list(self.db.execute(stmt).scalars().all())
        total = self.db.execute(count_stmt).scalar_one()
        return items, total

    def get_by_ids(self, ids: List[uuid.UUID]) -> List[Person]:
        """Récupère plusieurs personnes en une seule requête (bulk fetch pour le graphe)."""
        stmt = (
            select(Person)
            .where(Person.id.in_(ids))
            .where(Person.deleted_at.is_(None))
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Écriture ─────────────────────────────────────────────────────────────

    def soft_delete(self, person_id: uuid.UUID) -> bool:
        """Suppression logique (RGPD — on ne supprime pas définitivement)."""
        person = self.get(person_id)
        if not person:
            return False
        person.soft_delete()
        self.db.commit()
        return True


# ═════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class RelationshipRepository(BaseRepository[Relationship]):

    def __init__(self, db: Session):
        super().__init__(Relationship, db)

    def get_for_person(self, person_id: uuid.UUID) -> List[Relationship]:
        """Toutes les relations d'une personne (elle peut être person_id_1 OU _2)."""
        stmt = (
            select(Relationship)
            .where(
                or_(
                    Relationship.person_id_1 == person_id,
                    Relationship.person_id_2 == person_id,
                )
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_parents(self, person_id: uuid.UUID) -> List[Relationship]:
        """Retourne les liens où la personne est l'enfant (person_id_2)."""
        stmt = (
            select(Relationship)
            .where(Relationship.person_id_2 == person_id)
            .where(Relationship.relationship_type == RelationshipType.PARENT_CHILD)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_children(self, person_id: uuid.UUID) -> List[Relationship]:
        """Retourne les liens où la personne est le parent (person_id_1)."""
        stmt = (
            select(Relationship)
            .where(Relationship.person_id_1 == person_id)
            .where(Relationship.relationship_type == RelationshipType.PARENT_CHILD)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_spouses(self, person_id: uuid.UUID) -> List[Relationship]:
        """Retourne les unions de la personne."""
        stmt = (
            select(Relationship)
            .where(
                or_(
                    Relationship.person_id_1 == person_id,
                    Relationship.person_id_2 == person_id,
                )
            )
            .where(Relationship.relationship_type == RelationshipType.COUPLE)
        )
        return list(self.db.execute(stmt).scalars().all())

    def exists(
        self,
        person_id_1: uuid.UUID,
        person_id_2: uuid.UUID,
        rel_type: RelationshipType,
    ) -> bool:
        """Vérifie si un lien identique existe déjà (dans les deux sens pour COUPLE)."""
        stmt = select(Relationship.id).where(
            or_(
                (Relationship.person_id_1 == person_id_1)
                & (Relationship.person_id_2 == person_id_2)
                & (Relationship.relationship_type == rel_type),
                (Relationship.person_id_1 == person_id_2)
                & (Relationship.person_id_2 == person_id_1)
                & (Relationship.relationship_type == rel_type),
            )
        )
        return self.db.execute(stmt).first() is not None

    def get_ancestor_ids(
        self, person_id: uuid.UUID, max_depth: int = 10
    ) -> set[uuid.UUID]:
        """
        Remonte les ancêtres pour détecter les cycles avant insertion.
        Utilise une BFS itérative pour éviter la récursion Python.
        En production : remplacer par une CTE récursive PostgreSQL.
        """
        visited: set[uuid.UUID] = set()
        queue = [person_id]
        depth = 0

        while queue and depth < max_depth:
            current_ids = queue[:]
            queue = []
            depth += 1
            for cid in current_ids:
                parents = self.get_parents(cid)
                for rel in parents:
                    parent_id = rel.person_id_1
                    if parent_id not in visited:
                        visited.add(parent_id)
                        queue.append(parent_id)

        return visited


# ═════════════════════════════════════════════════════════════════════════════
# EVENT REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class EventRepository(BaseRepository[Event]):

    def __init__(self, db: Session):
        super().__init__(Event, db)

    def get_for_person(self, person_id: uuid.UUID) -> List[Event]:
        """Événements d'une personne, triés chronologiquement."""
        stmt = (
            select(Event)
            .where(Event.person_id == person_id)
            .order_by(Event.date_start.asc().nulls_last())
        )
        return list(self.db.execute(stmt).scalars().all())


# ═════════════════════════════════════════════════════════════════════════════
# USER REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class UserRepository(BaseRepository[User]):

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(User.email == email.lower().strip())
        return self.db.execute(stmt).first() is not None


# ═════════════════════════════════════════════════════════════════════════════
# TAG REPOSITORY
# ═════════════════════════════════════════════════════════════════════════════

class TagRepository(BaseRepository[Tag]):

    def __init__(self, db: Session):
        super().__init__(Tag, db)

    def get_by_label(self, label: str) -> Optional[Tag]:
        stmt = select(Tag).where(Tag.label == label)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_sorted(self) -> List[Tag]:
        stmt = select(Tag).order_by(Tag.label)
        return list(self.db.execute(stmt).scalars().all())
