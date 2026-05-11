from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.union import UnionCreate, UnionUpdate, UnionResponse
from app.services.union_service import UnionService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.core.exceptions import NotFoundException, PermissionDeniedException

router = APIRouter(prefix="/unions", tags=["Unions"])


@router.post("/", response_model=UnionResponse, status_code=status.HTTP_201_CREATED)
def create_union(
    data: UnionCreate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Créer une union entre deux personnes"""
    acl = ACLService(db, current_user)
    if not acl.can_edit_person(data.person_id_1):
        raise PermissionDeniedException("edit", "person 1")
    if not acl.can_edit_person(data.person_id_2):
        raise PermissionDeniedException("edit", "person 2")

    return UnionService(db).create_union(data)


@router.get("/person/{person_id}", response_model=List[UnionResponse])
def get_unions_by_person(
    person_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer toutes les unions d'une personne"""
    acl = ACLService(db, current_user)
    if not acl.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    return UnionService(db).get_unions_by_person(person_id)


@router.get("/between/{person_id_1}/{person_id_2}", response_model=List[UnionResponse])
def get_unions_between(
    person_id_1: UUID,
    person_id_2: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer les unions entre deux personnes"""
    acl = ACLService(db, current_user)
    if not acl.can_view_person(person_id_1) or not acl.can_view_person(person_id_2):
        raise PermissionDeniedException("view", "person")
    return UnionService(db).get_unions_between(person_id_1, person_id_2)


@router.get("/{union_id}", response_model=UnionResponse)
def get_union(
    union_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer une union par son ID"""
    service = UnionService(db)
    union = service.get_union(union_id)
    if not union:
        raise NotFoundException("Union", union_id)

    acl = ACLService(db, current_user)
    if not acl.can_view_person(union.person_id_1) or not acl.can_view_person(union.person_id_2):
        raise PermissionDeniedException("view", "person")

    return union


@router.put("/{union_id}", response_model=UnionResponse)
def update_union(
    union_id: UUID,
    data: UnionUpdate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Mettre à jour une union"""
    service = UnionService(db)
    existing = service.get_union(union_id)
    if not existing:
        raise NotFoundException("Union", union_id)

    acl = ACLService(db, current_user)
    if not acl.can_edit_person(existing.person_id_1) or not acl.can_edit_person(existing.person_id_2):
        raise PermissionDeniedException("edit", "person")

    return service.update_union(union_id, data)


@router.delete("/{union_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_union(
    union_id: UUID,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Supprimer une union"""
    service = UnionService(db)
    existing = service.get_union(union_id)
    if not existing:
        raise NotFoundException("Union", union_id)

    acl = ACLService(db, current_user)
    if not acl.can_edit_person(existing.person_id_1) or not acl.can_edit_person(existing.person_id_2):
        raise PermissionDeniedException("edit", "person")

    service.delete_union(union_id)
