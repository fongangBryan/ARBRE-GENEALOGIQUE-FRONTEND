from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.schemas.relationship import (
    RelationshipCreate, 
    RelationshipUpdate, 
    RelationshipResponse, 
    RelationshipListResponse,
    RelationshipTypeEnum,
    ParentChildTypeEnum
)
from app.services.relationship_service import RelationshipService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.api.v1.guards.acl import require_edit_access  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException, ConflictException, CycleDetectedException  # NOUVEAU

router = APIRouter(prefix="/relationships", tags=["Relationships"])


@router.post("/", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(
    relationship_data: RelationshipCreate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Créer une relation entre deux personnes (parent/enfant ou couple)"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    # Vérifier les droits d'édition sur les deux personnes
    if not acl_service.can_edit_person(relationship_data.person_id_1):
        raise PermissionDeniedException("edit", "person 1")
    if not acl_service.can_edit_person(relationship_data.person_id_2):
        raise PermissionDeniedException("edit", "person 2")
    
    try:
        relationship = relationship_service.create_relationship(relationship_data)
        return relationship
    except ValueError as e:
        if "cycle" in str(e).lower():
            raise CycleDetectedException(str(e))
        raise ConflictException(str(e))


@router.get("/person/{person_id}", response_model=List[RelationshipResponse])
def get_person_relationships(
    person_id: UUID,
    relationship_type: Optional[RelationshipTypeEnum] = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les relations d'une personne"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    
    relationships = relationship_service.get_relationships_by_person(
        person_id, 
        relationship_type.value if relationship_type else None
    )
    
    return relationships


@router.get("/between/{person_id_1}/{person_id_2}", response_model=Optional[RelationshipResponse])
def get_relationship_between(
    person_id_1: UUID,
    person_id_2: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer la relation entre deux personnes spécifiques"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id_1) or not acl_service.can_view_person(person_id_2):
        raise PermissionDeniedException("view", "person")
    
    relationship = relationship_service.get_relationship_between(person_id_1, person_id_2)
    return relationship


@router.get("/{relationship_id}", response_model=RelationshipResponse)
def get_relationship(
    relationship_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer une relation par son ID"""
    relationship_service = RelationshipService(db)
    
    relationship = relationship_service.get_relationship(relationship_id)
    if not relationship:
        raise NotFoundException("Relationship", relationship_id)
    
    acl_service = ACLService(db, current_user)
    if not acl_service.can_view_person(relationship.person_id_1) or \
       not acl_service.can_view_person(relationship.person_id_2):
        raise PermissionDeniedException("view", "person")
    
    return relationship


@router.put("/{relationship_id}", response_model=RelationshipResponse)
def update_relationship(
    relationship_id: UUID,
    relationship_data: RelationshipUpdate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour une relation"""
    relationship_service = RelationshipService(db)
    
    existing = relationship_service.get_relationship(relationship_id)
    if not existing:
        raise NotFoundException("Relationship", relationship_id)
    
    acl_service = ACLService(db, current_user)
    if not acl_service.can_edit_person(existing.person_id_1) or \
       not acl_service.can_edit_person(existing.person_id_2):
        raise PermissionDeniedException("edit", "person")
    
    relationship = relationship_service.update_relationship(relationship_id, relationship_data)
    if not relationship:
        raise NotFoundException("Relationship", relationship_id)
    
    return relationship


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    relationship_id: UUID,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Supprimer une relation"""
    relationship_service = RelationshipService(db)
    
    existing = relationship_service.get_relationship(relationship_id)
    if not existing:
        raise NotFoundException("Relationship", relationship_id)
    
    acl_service = ACLService(db, current_user)
    if not acl_service.can_edit_person(existing.person_id_1) or \
       not acl_service.can_edit_person(existing.person_id_2):
        raise PermissionDeniedException("edit", "person")
    
    success = relationship_service.delete_relationship(relationship_id)
    if not success:
        raise NotFoundException("Relationship", relationship_id)


@router.get("/{person_id}/parents", response_model=List[RelationshipResponse])
def get_parents(
    person_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les parents d'une personne"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    
    parents = relationship_service.get_parents(person_id)
    return parents


@router.get("/{person_id}/children", response_model=List[RelationshipResponse])
def get_children(
    person_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les enfants d'une personne"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    
    children = relationship_service.get_children(person_id)
    return children


@router.get("/{person_id}/spouses", response_model=List[RelationshipResponse])
def get_spouses(
    person_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les conjoints d'une personne"""
    relationship_service = RelationshipService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id):
        raise PermissionDeniedException("view", "person")
    
    spouses = relationship_service.get_spouses(person_id)
    return spouses