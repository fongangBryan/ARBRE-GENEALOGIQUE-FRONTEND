"""
Services — couche logique métier (cf. cours Jour 1 — Service Layer).
Les routes ne font qu'orchestrer ; toute la logique est ici.
"""
import math
import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    CyclicRelationshipException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.person import Person, PrivacyLevel
from app.models.relationship import Relationship, RelationshipType
from app.models.tag_and_acl import PersonTag, Tag, ActivityLog
from app.models.user import User, UserRole
from app.repositories.repositories import (
    PersonRepository,
    RelationshipRepository,
    TagRepository,
    UserRepository,
)
from app.schemas.person import PersonCreate, PersonUpdate, PersonListResponse
from app.schemas.relationships_events_media import RelationshipCreate
from app.schemas.user import UserCreate, TokenResponse


# ═════════════════════════════════════════════════════════════════════════════
# AUTH SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class AuthService:
    """Gestion de l'inscription, connexion et refresh des tokens JWT."""

    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.db = db

    def register(self, user_in: UserCreate) -> User:
        """
        Inscrit un nouvel utilisateur.
        - Normalise l'email en minuscules
        - Vérifie l'unicité de l'email
        - Hash le mot de passe avec bcrypt
        """
        email = user_in.email.lower().strip()
        if self.repo.email_exists(email):
            raise ConflictException("Cet email est déjà utilisé", resource="User")

        user = User(
            email=email,
            password_hash=get_password_hash(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            role=UserRole.READER,  # Par défaut : lecteur
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Authentifie un utilisateur et retourne un couple access/refresh token.
        Délai constant pour éviter le timing attack (passlib gère ça en interne).
        """
        user = self.repo.get_by_email(email)
        # On vérifie toujours le hash même si l'utilisateur n'existe pas
        # pour éviter les timing attacks
        # Real bcrypt hash of a random string — ensures constant-time comparison even for unknown emails
        dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/o0gOT7bq6"
        actual_hash = user.password_hash if user else dummy_hash

        if not verify_password(password, actual_hash) or not user:
            raise UnauthorizedException("Email ou mot de passe incorrect")

        if not user.is_active:
            raise UnauthorizedException("Compte désactivé")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
            expires_in=1800,  # 30 min en secondes
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Génère un nouveau access token à partir d'un refresh token valide."""
        from jose import JWTError
        from app.core.security import decode_token

        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Token de rafraîchissement invalide")
            user_id = payload.get("sub")
        except JWTError:
            raise UnauthorizedException("Token de rafraîchissement expiré ou invalide")

        user = self.repo.get(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("Utilisateur introuvable ou désactivé")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
            expires_in=1800,
        )


# ═════════════════════════════════════════════════════════════════════════════
# PERSON SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class PersonService:
    """
    Logique métier sur les personnes.
    Règles :
      - Normalisation des noms (strip des espaces)
      - Association automatique des tags à la création
      - Soft-delete pour la conformité RGPD
      - Journal d'activité sur chaque modification
    """

    def __init__(self, db: Session):
        self.repo = PersonRepository(db)
        self.tag_repo = TagRepository(db)
        self.db = db

    def create(self, person_in: PersonCreate, created_by: User) -> Person:
        """Crée une personne et associe les tags."""
        data = person_in.model_dump(exclude={"tag_ids"})
        # Normalisation
        data["first_name"] = data["first_name"].strip()
        data["last_name"] = data["last_name"].strip()

        person = Person(**data)
        self.db.add(person)
        self.db.flush()  # Pour obtenir l'ID avant les tags

        # ── Tags ─────────────────────────────────────────────────────────────
        if person_in.tag_ids:
            for tag_id in person_in.tag_ids:
                tag = self.tag_repo.get(tag_id)
                if not tag:
                    raise NotFoundException("Tag", tag_id)
                self.db.add(PersonTag(person_id=person.id, tag_id=tag.id))

        # ── Journal d'activité ────────────────────────────────────────────────
        self._log(created_by.id, "person.create", "person", person.id,
                  payload_after={"name": person.full_name})

        self.db.commit()
        self.db.refresh(person)
        return person

    def update(
        self, person_id: uuid.UUID, person_in: PersonUpdate, updated_by: User
    ) -> Person:
        """Mise à jour partielle (PATCH)."""
        person = self.repo.get(person_id)
        if not person or person.is_deleted:
            raise NotFoundException("Person", person_id)

        update_data = person_in.model_dump(exclude_unset=True, exclude={"tag_ids"})
        if "first_name" in update_data:
            update_data["first_name"] = update_data["first_name"].strip()
        if "last_name" in update_data:
            update_data["last_name"] = update_data["last_name"].strip()

        for field, value in update_data.items():
            setattr(person, field, value)

        # ── Mise à jour des tags ──────────────────────────────────────────────
        if person_in.tag_ids is not None:
            # Supprimer les anciennes associations
            from sqlalchemy import delete
            self.db.execute(
                delete(PersonTag).where(PersonTag.person_id == person.id)
            )
            for tag_id in person_in.tag_ids:
                tag = self.tag_repo.get(tag_id)
                if not tag:
                    raise NotFoundException("Tag", tag_id)
                self.db.add(PersonTag(person_id=person.id, tag_id=tag.id))

        self._log(updated_by.id, "person.update", "person", person_id)
        self.db.commit()
        self.db.refresh(person)
        return person

    def delete(self, person_id: uuid.UUID, deleted_by: User) -> None:
        """
        Suppression logique (soft-delete).
        Les données restent en base pour la conformité RGPD et l'historique.
        """
        person = self.repo.get(person_id)
        if not person or person.is_deleted:
            raise NotFoundException("Person", person_id)

        person.soft_delete()
        self._log(deleted_by.id, "person.delete", "person", person_id)
        self.db.commit()

    def get_list(
        self,
        *,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        sex: Optional[str] = None,
        living_only: Optional[bool] = None,
        privacy_levels: Optional[List[PrivacyLevel]] = None,
        page: int = 1,
        size: int = 20,
    ) -> PersonListResponse:
        """Recherche paginée avec filtres."""
        items, total = self.repo.search(
            search=search,
            tag_label=tag,
            sex=sex,
            living_only=living_only,
            privacy_levels=privacy_levels,
            skip=(page - 1) * size,
            limit=size,
        )
        return PersonListResponse(
            items=items,          # type: ignore  (PersonSummary compatible)
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )

    def _log(
        self,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        payload_before: Optional[dict] = None,
        payload_after: Optional[dict] = None,
    ) -> None:
        """Enregistre une entrée dans le journal d'activité."""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_before=payload_before,
            payload_after=payload_after,
        )
        self.db.add(log)


# ═════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class RelationshipService:
    """
    Logique métier sur les relations généalogiques.
    Règles critiques :
      - Détection de cycles (A parent de A)
      - Pas de doublon de lien
      - Construction du JSONB meta selon le type
    """

    def __init__(self, db: Session):
        self.repo = RelationshipRepository(db)
        self.person_repo = PersonRepository(db)
        self.db = db

    def create(
        self, rel_in: RelationshipCreate, created_by: User
    ) -> Relationship:
        """
        Crée un lien généalogique avec toutes les validations métier.
        """
        # ── Vérifier que les deux personnes existent ──────────────────────────
        p1 = self.person_repo.get(rel_in.person_id_1)
        if not p1 or p1.is_deleted:
            raise NotFoundException("Person", rel_in.person_id_1)
        p2 = self.person_repo.get(rel_in.person_id_2)
        if not p2 or p2.is_deleted:
            raise NotFoundException("Person", rel_in.person_id_2)

        # ── Doublon ───────────────────────────────────────────────────────────
        if self.repo.exists(rel_in.person_id_1, rel_in.person_id_2, rel_in.relationship_type):
            raise ConflictException(
                "Ce lien existe déjà entre ces deux personnes", resource="Relationship"
            )

        # ── Détection de cycle (uniquement pour PARENT_CHILD) ─────────────────
        if rel_in.relationship_type == RelationshipType.PARENT_CHILD:
            # person_id_1 = parent, person_id_2 = enfant
            # On vérifie que l'enfant proposé n'est pas déjà un ancêtre du parent
            ancestors_of_parent = self.repo.get_ancestor_ids(rel_in.person_id_1)
            if rel_in.person_id_2 in ancestors_of_parent:
                raise CyclicRelationshipException(str(rel_in.person_id_2))

        # ── Construction du JSONB meta ────────────────────────────────────────
        meta = self._build_meta(rel_in)

        relationship = Relationship(
            person_id_1=rel_in.person_id_1,
            person_id_2=rel_in.person_id_2,
            relationship_type=rel_in.relationship_type,
            meta=meta,
            notes=rel_in.notes,
        )
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def delete(self, relationship_id: uuid.UUID, deleted_by: User) -> None:
        rel = self.repo.get(relationship_id)
        if not rel:
            raise NotFoundException("Relationship", relationship_id)
        self.db.delete(rel)
        self.db.commit()

    def get_for_person(self, person_id: uuid.UUID) -> dict:
        """
        Retourne les relations organisées par type (parents, enfants, conjoints, fratrie).
        La fratrie est calculée dynamiquement (mêmes parents).
        """
        relationships = self.repo.get_for_person(person_id)

        parents = []
        children = []
        spouses = []

        for rel in relationships:
            if rel.relationship_type == RelationshipType.PARENT_CHILD:
                if rel.person_id_2 == person_id:
                    parents.append(rel)    # person est l'enfant
                else:
                    children.append(rel)   # person est le parent
            elif rel.relationship_type == RelationshipType.COUPLE:
                spouses.append(rel)

        # ── Fratrie : enfants des mêmes parents ───────────────────────────────
        siblings = []
        sibling_ids: set[uuid.UUID] = set()
        for parent_rel in parents:
            parent_id = parent_rel.person_id_1
            children_of_parent = self.repo.get_children(parent_id)
            for c in children_of_parent:
                if c.person_id_2 != person_id and c.person_id_2 not in sibling_ids:
                    siblings.append(c)
                    sibling_ids.add(c.person_id_2)

        return {
            "parents": parents,
            "children": children,
            "spouses": spouses,
            "siblings": siblings,
        }

    @staticmethod
    def _build_meta(rel_in: RelationshipCreate) -> dict:
        """Construit le dictionnaire meta JSONB selon le type de relation."""
        if rel_in.relationship_type == RelationshipType.PARENT_CHILD:
            return {
                "parentage_type": rel_in.parentage_type.value
                if rel_in.parentage_type
                else "biological"
            }
        elif rel_in.relationship_type == RelationshipType.COUPLE:
            return {
                "union_type": rel_in.union_type.value if rel_in.union_type else "other",
                "start_date": rel_in.union_start_date,
                "end_date": rel_in.union_end_date,
                "is_ended": rel_in.union_is_ended or False,
            }
        return {}


# ═════════════════════════════════════════════════════════════════════════════
# GRAPH SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class GraphService:
    """
    Construction des réponses graphe pour Cytoscape.js (cf. CDC section 7 & 8).
    Stratégie : chargement progressif — jamais l'arbre complet d'un coup.
    """

    def __init__(self, db: Session):
        self.person_repo = PersonRepository(db)
        self.rel_repo = RelationshipRepository(db)

    def get_neighbors(
        self,
        person_id: uuid.UUID,
        radius: int = 1,
        current_user=None,
    ) -> dict:
        """
        Charge les voisins immédiats d'une personne (parents, enfants, conjoints).
        Format de sortie compatible Cytoscape.js : { nodes: [], edges: [] }
        """
        from app.api.deps import check_person_access

        center = self.person_repo.get(person_id)
        if not center or center.is_deleted:
            raise NotFoundException("Person", person_id)

        check_person_access(center, current_user)

        # Collecter les IDs à charger
        relationships = self.rel_repo.get_for_person(person_id)
        neighbor_ids: set[uuid.UUID] = set()
        for rel in relationships:
            neighbor_ids.add(
                rel.person_id_1 if rel.person_id_2 == person_id else rel.person_id_2
            )

        persons = self.person_repo.get_by_ids(list(neighbor_ids))
        all_persons = [center] + persons

        nodes = [self._to_node(p) for p in all_persons]
        edges = [self._to_edge(r) for r in relationships]

        return {"nodes": nodes, "edges": edges}

    def get_subtree(
        self,
        root_id: uuid.UUID,
        depth: int = 3,
        current_user=None,
    ) -> dict:
        """
        Sous-arbre depuis une racine jusqu'à une profondeur donnée.
        Limitée à 200 nœuds pour les performances du navigateur.
        """
        from app.api.deps import check_person_access

        MAX_NODES = 200
        root = self.person_repo.get(root_id)
        if not root or root.is_deleted:
            raise NotFoundException("Person", root_id)
        check_person_access(root, current_user)

        visited_ids: set[uuid.UUID] = {root_id}
        all_relationships: List[Relationship] = []
        current_level = [root_id]

        for _ in range(depth):
            if len(visited_ids) >= MAX_NODES:
                break
            next_level: List[uuid.UUID] = []
            for pid in current_level:
                rels = self.rel_repo.get_for_person(pid)
                for rel in rels:
                    if rel not in all_relationships:
                        all_relationships.append(rel)
                    neighbor = (
                        rel.person_id_1 if rel.person_id_2 == pid else rel.person_id_2
                    )
                    if neighbor not in visited_ids:
                        visited_ids.add(neighbor)
                        next_level.append(neighbor)
            current_level = next_level

        persons = self.person_repo.get_by_ids(list(visited_ids))
        nodes = [self._to_node(p) for p in persons]
        edges = [self._to_edge(r) for r in all_relationships]

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _to_node(person: Person) -> dict:
        birth_year = None
        if person.birth_date_exact:
            birth_year = person.birth_date_exact.year
        elif person.birth_date and len(person.birth_date) >= 4:
            try:
                birth_year = int(person.birth_date[:4])
            except ValueError:
                pass

        death_year = None
        if person.death_date_exact:
            death_year = person.death_date_exact.year

        thumbnail_url = None
        if person.profile_media and person.profile_media.thumbnail_key:
            thumbnail_url = f"/api/v1/media/{person.profile_media.id}/thumbnail"

        return {
            "id": str(person.id),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "birth_year": birth_year,
            "death_year": death_year,
            "is_living": person.is_living,
            "sex": person.sex.value if person.sex else None,
            "thumbnail_url": thumbnail_url,
            "privacy_level": person.privacy_level.value,
        }

    @staticmethod
    def _to_edge(rel: Relationship) -> dict:
        return {
            "id": str(rel.id),
            "source": str(rel.person_id_1),
            "target": str(rel.person_id_2),
            "relationship_type": rel.relationship_type.value,
            "meta": rel.meta or {},
        }
