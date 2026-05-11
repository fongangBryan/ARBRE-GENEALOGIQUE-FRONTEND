from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.filiation import FiliationCreate, FiliationUpdate, FiliationResponse
from app.services.filiation_service import FiliationService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.core.exceptions import NotFoundException, PermissionDeniedException, ConflictException, CycleDetectedException

router = APIRouter(prefix="/filiations", tags=["Filiations"])


@router.post("/", response_model=FiliationResponse, status_code=status.HTTP_201_CREATED)
def create_filiation(
    data: FiliationCreate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Créer une filiation parent → enfant"""
    acl = ACLService(db, current_user)
    if not acl.can_edit_person(data.parent_id):
        raise PermissionDeniedException("edit", "parent")
    if not acl.can_edit_person(data.child_id):
        raise PermissionDeniedException("edit", "child")

    return FiliationService(db).create_filiation(data)


@router.get("/person/{person_id}/parents", response_model=List[FiliationResponse])
def get_parents(
    person_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer les filiations parentales d'une personne (elle en tant qu'enfant)"""
    acl = ACLService(db, current_user)
    if not acl.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    return FiliationService(db).get_parents(person_id)


@router.get("/person/{person_id}/children", response_model=List[FiliationResponse])
def get_children(
    person_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer les filiations enfants d'une personne (elle en tant que parent)"""
    acl = ACLService(db, current_user)
    if not acl.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    return FiliationService(db).get_children(person_id)


@router.get("/{filiation_id}", response_model=FiliationResponse)
def get_filiation(
    filiation_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupérer une filiation par son ID"""
    service = FiliationService(db)
    filiation = service.get_filiation(filiation_id)
    if not filiation:
        raise NotFoundException("Filiation", filiation_id)

    acl = ACLService(db, current_user)
    if not acl.can_view_person(filiation.parent_id) or not acl.can_view_person(filiation.child_id):
        raise PermissionDeniedException("view", "person")

    return filiation


@router.put("/{filiation_id}", response_model=FiliationResponse)
def update_filiation(
    filiation_id: UUID,
    data: FiliationUpdate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Mettre à jour le type d'une filiation"""
    service = FiliationService(db)
    existing = service.get_filiation(filiation_id)
    if not existing:
        raise NotFoundException("Filiation", filiation_id)

    acl = ACLService(db, current_user)
    if not acl.can_edit_person(existing.parent_id) or not acl.can_edit_person(existing.child_id):
        raise PermissionDeniedException("edit", "person")

    return service.update_filiation(filiation_id, data)


@router.delete("/{filiation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filiation(
    filiation_id: UUID,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Supprimer une filiation"""
    service = FiliationService(db)
    existing = service.get_filiation(filiation_id)
    if not existing:
        raise NotFoundException("Filiation", filiation_id)

    acl = ACLService(db, current_user)
    if not acl.can_edit_person(existing.parent_id) or not acl.can_edit_person(existing.child_id):
        raise PermissionDeniedException("edit", "person")

    service.delete_filiation(filiation_id)
