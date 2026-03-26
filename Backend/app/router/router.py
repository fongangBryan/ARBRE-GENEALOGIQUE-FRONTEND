"""
Routers API v1 — Auth, Persons, Relationships, Graph, Events, Tags.
Chaque router est minimaliste : orchestration uniquement, logique dans les services.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    PaginationParams,
    PersonFilterParams,
    check_person_access,
    get_current_active_user,
    get_current_admin,
    get_current_editor,
    get_db,
    get_optional_user,
)
from app.core.exceptions import NotFoundException
from app.models.person import PrivacyLevel
from app.models.user import User, UserRole
from app.repositories.repositories import (
    EventRepository,
    PersonRepository,
    TagRepository,
)
from app.schemas.person import (
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
)
from app.schemas.relationships_events_media import (
    AccessControlCreate,
    EventCreate,
    EventResponse,
    EventUpdate,
    RelationshipCreate,
    RelationshipResponse,
    TagCreate,
    TagResponse,
)
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.services import (
    AuthService,
    GraphService,
    PersonService,
    RelationshipService,
)


# ═════════════════════════════════════════════════════════════════════════════
# AUTH ROUTER
# ═════════════════════════════════════════════════════════════════════════════

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    svc = AuthService(db)
    return svc.register(user_in)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Se connecter et obtenir les tokens JWT",
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    svc = AuthService(db)
    return svc.login(credentials.email, credentials.password)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler l'access token via le refresh token",
)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    svc = AuthService(db)
    return svc.refresh(body.refresh_token)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Se déconnecter")
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Côté serveur : en JWT stateless, le logout se fait côté client (supprimer les tokens).
    En V2 : implémenter une blacklist Redis pour invalider les tokens avant expiration.
    """
    return None


# ═════════════════════════════════════════════════════════════════════════════
# PERSONS ROUTER
# ═════════════════════════════════════════════════════════════════════════════

persons_router = APIRouter(prefix="/persons", tags=["Persons"])


@persons_router.get(
    "",
    response_model=PersonListResponse,
    summary="Lister les personnes avec filtres et pagination",
)
def list_persons(
    pagination: PaginationParams = Depends(),
    filters: PersonFilterParams = Depends(),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Recherche full-text + filtres (tag, sexe, vivants, confidentialité).
    Les niveaux de confidentialité visibles dépendent du rôle de l'utilisateur.
    """
    # Déterminer les privacy_levels accessibles selon le rôle
    if not current_user:
        allowed_privacy = [PrivacyLevel.PUBLIC]
    elif current_user.role in (UserRole.EDITOR, UserRole.ADMIN):
        allowed_privacy = list(PrivacyLevel)  # Tout voir
    else:
        allowed_privacy = [PrivacyLevel.PUBLIC, PrivacyLevel.FAMILY]

    svc = PersonService(db)
    return svc.get_list(
        search=filters.search,
        tag=filters.tag,
        sex=filters.sex,
        living_only=filters.living_only,
        privacy_levels=allowed_privacy,
        page=pagination.page,
        size=pagination.size,
    )


@persons_router.post(
    "",
    response_model=PersonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle personne",
)
def create_person(
    person_in: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    svc = PersonService(db)
    return svc.create(person_in, current_user)


@persons_router.get(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Détail d'une fiche personne",
)
def get_person(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    repo = PersonRepository(db)
    person = repo.get_with_relations(person_id)
    if not person or person.is_deleted:
        raise NotFoundException("Person", person_id)

    check_person_access(person, current_user)

    # Masquer les notes privées si non éditeur/admin
    response = PersonResponse.model_validate(person)
    if not current_user or current_user.role not in (UserRole.EDITOR, UserRole.ADMIN):
        response.notes_private = None
    return response


@persons_router.patch(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Mettre à jour une fiche personne (PATCH partiel)",
)
def update_person(
    person_id: uuid.UUID,
    person_in: PersonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    svc = PersonService(db)
    return svc.update(person_id, person_in, current_user)


@persons_router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une personne (soft-delete)",
)
def delete_person(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    svc = PersonService(db)
    svc.delete(person_id, current_user)
    return None


# ── Events d'une personne ──────────────────────────────────────────────────

@persons_router.get(
    "/{person_id}/events",
    response_model=List[EventResponse],
    summary="Timeline des événements d'une personne",
)
def get_person_events(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    repo = PersonRepository(db)
    person = repo.get(person_id)
    if not person or person.is_deleted:
        raise NotFoundException("Person", person_id)
    check_person_access(person, current_user)

    event_repo = EventRepository(db)
    return event_repo.get_for_person(person_id)


@persons_router.post(
    "/{person_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un événement à une personne",
)
def create_event(
    person_id: uuid.UUID,
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    from app.models.event import Event

    repo = PersonRepository(db)
    person = repo.get(person_id)
    if not person or person.is_deleted:
        raise NotFoundException("Person", person_id)

    event = Event(person_id=person_id, **event_in.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ── Relations d'une personne ───────────────────────────────────────────────

@persons_router.get(
    "/{person_id}/relationships",
    summary="Relations d'une personne (parents, enfants, conjoints, fratrie)",
)
def get_person_relationships(
    person_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    repo = PersonRepository(db)
    person = repo.get(person_id)
    if not person or person.is_deleted:
        raise NotFoundException("Person", person_id)
    check_person_access(person, current_user)

    svc = RelationshipService(db)
    return svc.get_for_person(person_id)


# ═════════════════════════════════════════════════════════════════════════════
# RELATIONSHIPS ROUTER
# ═════════════════════════════════════════════════════════════════════════════

relationships_router = APIRouter(prefix="/relationships", tags=["Relationships"])


@relationships_router.post(
    "",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un lien généalogique (parent/enfant ou couple)",
)
def create_relationship(
    rel_in: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    """
    Valide et crée le lien.
    Détecte les cycles (A parent de A) et les doublons.
    """
    svc = RelationshipService(db)
    rel = svc.create(rel_in, current_user)
    return RelationshipResponse(
        id=rel.id,
        person_id_1=rel.person_id_1,
        person_id_2=rel.person_id_2,
        relationship_type=rel.relationship_type,
        meta=rel.meta,
        notes=rel.notes,
        created_at=rel.created_at,
    )


@relationships_router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un lien généalogique",
)
def delete_relationship(
    relationship_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    svc = RelationshipService(db)
    svc.delete(relationship_id, current_user)
    return None


# ═════════════════════════════════════════════════════════════════════════════
# GRAPH ROUTER
# ═════════════════════════════════════════════════════════════════════════════

graph_router = APIRouter(prefix="/graph", tags=["Graph"])


@graph_router.get(
    "/neighbors",
    summary="Voisins immédiats d'une personne (format Cytoscape.js)",
)
def get_neighbors(
    personId: uuid.UUID = Query(..., description="ID de la personne centrale"),
    radius: int = Query(1, ge=1, le=3, description="Rayon de voisinage"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retourne nodes[] + edges[] pour le chargement progressif du graphe.
    Compatible avec Cytoscape.js directement.
    """
    svc = GraphService(db)
    return svc.get_neighbors(personId, radius, current_user)


@graph_router.get(
    "/subtree",
    summary="Sous-arbre depuis une racine jusqu'à une profondeur N",
)
def get_subtree(
    rootId: uuid.UUID = Query(..., description="ID de la personne racine"),
    depth: int = Query(3, ge=1, le=6, description="Profondeur maximale"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    svc = GraphService(db)
    return svc.get_subtree(rootId, depth, current_user)


# ═════════════════════════════════════════════════════════════════════════════
# TAGS ROUTER
# ═════════════════════════════════════════════════════════════════════════════

tags_router = APIRouter(prefix="/tags", tags=["Tags"])


@tags_router.get("", response_model=List[TagResponse], summary="Liste de tous les tags")
def list_tags(db: Session = Depends(get_db)):
    repo = TagRepository(db)
    return repo.get_all_sorted()


@tags_router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tag",
)
def create_tag(
    tag_in: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    from app.models.tag_and_acl import Tag
    from app.core.exceptions import ConflictException

    repo = TagRepository(db)
    if repo.get_by_label(tag_in.label):
        raise ConflictException(f"Un tag '{tag_in.label}' existe déjà", resource="Tag")

    tag = Tag(**tag_in.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@tags_router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un tag (admin)",
)
def delete_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    repo = TagRepository(db)
    if not repo.delete(tag_id):
        raise NotFoundException("Tag", tag_id)
    return None


# ═════════════════════════════════════════════════════════════════════════════
# EVENTS ROUTER (standalone — pour PUT/DELETE hors du contexte personne)
# ═════════════════════════════════════════════════════════════════════════════

events_router = APIRouter(prefix="/events", tags=["Events"])


@events_router.put(
    "/{event_id}",
    response_model=EventResponse,
    summary="Mettre à jour un événement",
)
def update_event(
    event_id: uuid.UUID,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    from app.models.event import Event
    from sqlalchemy import select

    event = db.get(Event, event_id)
    if not event:
        raise NotFoundException("Event", event_id)

    for field, value in event_in.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


@events_router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un événement",
)
def delete_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor),
):
    from app.models.event import Event

    event = db.get(Event, event_id)
    if not event:
        raise NotFoundException("Event", event_id)
    db.delete(event)
    db.commit()
    return None


# ═════════════════════════════════════════════════════════════════════════════
# API ROUTER V1 — agrégation de tous les routers
# ═════════════════════════════════════════════════════════════════════════════

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(persons_router)
api_router.include_router(relationships_router)
api_router.include_router(graph_router)
api_router.include_router(tags_router)
api_router.include_router(events_router)
