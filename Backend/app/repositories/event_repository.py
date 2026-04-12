from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.event import Event

class EventRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, event: Event) -> Event:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def get_by_id(self, event_id: UUID) -> Optional[Event]:
        return self.db.query(Event).filter(Event.id == event_id).first()
    
    def get_by_person(self, person_id: UUID, event_type: Optional[str] = None) -> List[Event]:
        query = self.db.query(Event).filter(Event.person_id == person_id)
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        return query.order_by(Event.date_start).all()
    
    def update(self, event: Event) -> Event:
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def delete(self, event_id: UUID) -> bool:
        event = self.get_by_id(event_id)
        if event:
            self.db.delete(event)
            self.db.commit()
            return True
        return False
    
    def get_timeline(self, person_id: UUID, start_year: Optional[int] = None, end_year: Optional[int] = None) -> List[Event]:
        query = self.db.query(Event).filter(Event.person_id == person_id)
        
        # Filtrage par année (approximatif, basé sur date_start)
        # À améliorer avec une extraction d'année plus robuste
        if start_year:
            query = query.filter(Event.date_start >= str(start_year))
        if end_year:
            query = query.filter(Event.date_start <= str(end_year))
        
        return query.order_by(Event.date_start).all()