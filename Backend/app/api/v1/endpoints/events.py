from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.schemas.event import (
    EventCreate, 
    EventUpdate, 
    EventResponse, 
    EventListResponse,
    EventTypeEnum
)
from app.services.event_service import EventService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.api.v1.guards.acl import require_view_access, require_edit_access  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException  # NOUVEAU

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Créer un événement (naissance, mariage, décès, etc.)"""
    event_service = EventService(db)
    acl_service = ACLService(db, current_user)
    
    # Vérifier les droits sur la personne associée
    if not acl_service.can_edit_person(event_data.person_id):
        raise PermissionDeniedException("edit", "person")
    
    event = event_service.create_event(event_data)
    return event


@router.get("/person/{person_id}", response_model=List[EventResponse])
def get_person_events(
    person_id: UUID,
    event_type: Optional[EventTypeEnum] = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """Récupérer tous les événements d'une personne (timeline)"""
    event_service = EventService(db)
    
    events = event_service.get_events_by_person(
        person_id, 
        event_type.value if event_type else None
    )
    
    return events


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer un événement par son ID"""
    event_service = EventService(db)
    acl_service = ACLService(db, current_user)
    
    event = event_service.get_event(event_id)
    if not event:
        raise NotFoundException("Event", event_id)
    
    if not acl_service.can_view_person(event.person_id):
        raise PermissionDeniedException("view", "person")
    
    return event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    event_data: EventUpdate,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour un événement"""
    event_service = EventService(db)
    
    existing = event_service.get_event(event_id)
    if not existing:
        raise NotFoundException("Event", event_id)
    
    acl_service = ACLService(db, current_user)
    if not acl_service.can_edit_person(existing.person_id):
        raise PermissionDeniedException("edit", "person")
    
    event = event_service.update_event(event_id, event_data)
    if not event:
        raise NotFoundException("Event", event_id)
    
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Supprimer un événement"""
    event_service = EventService(db)
    
    existing = event_service.get_event(event_id)
    if not existing:
        raise NotFoundException("Event", event_id)
    
    acl_service = ACLService(db, current_user)
    if not acl_service.can_edit_person(existing.person_id):
        raise PermissionDeniedException("delete", "event")
    
    success = event_service.delete_event(event_id)
    if not success:
        raise NotFoundException("Event", event_id)


@router.get("/timeline/{person_id}", response_model=List[EventResponse])
def get_timeline(
    person_id: UUID,
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """Récupérer la timeline chronologique d'une personne avec filtres par année"""
    event_service = EventService(db)
    
    events = event_service.get_timeline(person_id, start_year, end_year)
    
    return events