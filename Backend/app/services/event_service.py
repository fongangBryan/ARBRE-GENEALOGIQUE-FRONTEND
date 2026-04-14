from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
from app.repositories.event_repository import EventRepository

class EventService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EventRepository(db)
    
    def create_event(self, event_data: EventCreate) -> Event:
        event = Event(
            person_id=event_data.person_id,
            event_type=event_data.event_type,
            date_start=event_data.date_start,
            date_end=event_data.date_end,
            place=event_data.place,
            description=event_data.description,
            meta=event_data.meta or {}
        )
        return self.repo.create(event)
    
    def get_event(self, event_id: UUID) -> Optional[Event]:
        return self.repo.get_by_id(event_id)
    
    def get_events_by_person(self, person_id: UUID, event_type: Optional[str] = None) -> List[Event]:
        return self.repo.get_by_person(person_id, event_type)
    
    def update_event(self, event_id: UUID, event_data: EventUpdate) -> Optional[Event]:
        event = self.repo.get_by_id(event_id)
        if not event:
            return None
        
        update_data = event_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)
        
        return self.repo.update(event)
    
    def delete_event(self, event_id: UUID) -> bool:
        return self.repo.delete(event_id)
    
    def get_timeline(self, person_id: UUID, start_year: Optional[int] = None, end_year: Optional[int] = None) -> List[Event]:
        return self.repo.get_timeline(person_id, start_year, end_year)