from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse
from app.services.tag_service import TagService
from app.api.deps import get_current_user, get_current_editor_user, get_current_admin_user

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("/", response_model=TagListResponse)
def list_tags(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste tous les tags disponibles"""
    svc = TagService(db)
    tags = svc.list_tags()
    return TagListResponse(items=tags, total=len(tags))


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    data: TagCreate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Crée un nouveau tag (éditeur+)"""
    svc = TagService(db)
    return svc.create_tag(data, current_user.id)


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère un tag par son ID"""
    return TagService(db).get_tag(tag_id)


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    data: TagUpdate,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Met à jour un tag (éditeur+)"""
    return TagService(db).update_tag(tag_id, data)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    current_user=Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Supprime un tag (admin uniquement)"""
    TagService(db).delete_tag(tag_id)


# ── Person ↔ Tag association ──────────────────────────────────────────────────

@router.get("/person/{person_id}", response_model=List[TagResponse])
def get_person_tags(
    person_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retourne les tags d'une personne"""
    return TagService(db).get_person_tags(person_id)


@router.post("/person/{person_id}/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_tag_to_person(
    person_id: UUID,
    tag_id: UUID,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Attache un tag à une personne (éditeur+)"""
    TagService(db).add_tag_to_person(person_id, tag_id, current_user.id)


@router.delete("/person/{person_id}/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_person(
    person_id: UUID,
    tag_id: UUID,
    current_user=Depends(get_current_editor_user),
    db: Session = Depends(get_db),
):
    """Détache un tag d'une personne (éditeur+)"""
    TagService(db).remove_tag_from_person(person_id, tag_id, current_user.id)
