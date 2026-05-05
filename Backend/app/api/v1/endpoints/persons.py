from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.person import PersonCreate, PersonUpdate, PersonResponse, PersonListResponse
from app.services.person_service import PersonService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.api.v1.guards.acl import require_view_access, require_edit_access
from app.core.exceptions import NotFoundException, PermissionDeniedException

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.get("/", response_model=PersonListResponse)
def list_persons(
    search: Optional[str] = Query(None, min_length=1),
    page: int  = Query(1,  ge=1),
    limit: int = Query(20, ge=1, le=500),
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    person_service = PersonService(db)
    acl_service    = ACLService(db, current_user)
    is_admin       = current_user.role == UserRole.ADMIN

    persons, _ = person_service.list_persons(
        search=search,
        page=page,
        limit=limit,
        user_id=current_user.id,
        is_admin=is_admin,
    )

    # Filtre ACL supplémentaire (privacy_level, partages…)
    visible = [p for p in persons if acl_service.can_view_person(p.id)]

    return PersonListResponse(
        items=visible,
        total=len(visible),
        page=page,
        limit=limit,
        pages=(len(visible) + limit - 1) // limit if visible else 1,
    )


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    person_data: PersonCreate,
    current_user = Depends(get_current_editor_user),
    db: Session  = Depends(get_db),
):
    return PersonService(db).create_person(person_data, current_user.id)


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    dependencies=[Depends(get_current_user), Depends(require_view_access)],
)
def get_person(person_id: UUID, db: Session = Depends(get_db)):
    person = PersonService(db).get_person(person_id)
    if not person:
        raise NotFoundException("Person", person_id)
    return person


@router.put(
    "/{person_id}",
    response_model=PersonResponse,
    dependencies=[Depends(get_current_editor_user), Depends(require_edit_access)],
)
def update_person(
    person_id: UUID,
    person_data: PersonUpdate,
    db: Session = Depends(get_db),
):
    return PersonService(db).update_person(person_id, person_data)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: UUID,
    current_user = Depends(get_current_editor_user),
    db: Session  = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException("delete", "person")

    if not PersonService(db).delete_person(person_id):
        raise NotFoundException("Person", person_id)
