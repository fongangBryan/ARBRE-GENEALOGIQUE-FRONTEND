from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.schemas.person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from app.services.person_service import PersonService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.api.v1.guards.acl import require_view_access, require_edit_access  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException  # NOUVEAU

router = APIRouter(prefix="/persons", tags=["Persons"])

@router.get("/", response_model=PersonListResponse)
def list_persons(
    search: Optional[str] = Query(None, min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    person_service = PersonService(db)
    acl_service = ACLService(db, current_user)
    
    persons, total = person_service.list_persons(
        search=search,
        page=page,
        limit=limit,
        user_id=current_user.id
    )
    
    # Filtrer par ACL
    visible_persons = [p for p in persons if acl_service.can_view_person(p.id)]
    
    return PersonListResponse(
        items=visible_persons,
        total=len(visible_persons),
        page=page,
        limit=limit,
        pages=(len(visible_persons) + limit - 1) // limit if visible_persons else 1
    )

@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    person_data: PersonCreate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    person_service = PersonService(db)
    return person_service.create_person(person_data, current_user.id)

@router.get("/{person_id}", response_model=PersonResponse)
def get_person(
    person_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU - Guard ACL
):
    person_service = PersonService(db)
    
    person = person_service.get_person(person_id)
    if not person:
        raise NotFoundException("Person", person_id)  # MODIFIÉ
    
    return person

@router.put("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: UUID,
    person_data: PersonUpdate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db),
    _ = Depends(require_edit_access)  # NOUVEAU - Guard ACL
):
    person_service = PersonService(db)
    
    person = person_service.update_person(person_id, person_data)
    if not person:
        raise NotFoundException("Person", person_id)  # MODIFIÉ
    
    return person

@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: UUID,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    person_service = PersonService(db)
    
    # Only admin can delete
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException("delete", "person")  # MODIFIÉ
    
    success = person_service.delete_person(person_id)
    if not success:
        raise NotFoundException("Person", person_id)  # MODIFIÉ