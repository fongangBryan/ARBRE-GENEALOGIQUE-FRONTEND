from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, Tuple, List
from uuid import UUID

from app.models.person import Person

class PersonRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, person: Person) -> Person:
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)
        return person
    
    def get_by_id(self, person_id: UUID) -> Optional[Person]:
        return self.db.query(Person).filter(Person.id == person_id).first()
    
    def update(self, person: Person) -> Person:
        self.db.commit()
        self.db.refresh(person)
        return person
    
    def delete(self, person_id: UUID) -> bool:
        person = self.get_by_id(person_id)
        if person:
            self.db.delete(person)
            self.db.commit()
            return True
        return False
    
    def list_persons(self, search: Optional[str], page: int, limit: int) -> Tuple[List[Person], int]:
        query = self.db.query(Person)
        
        if search:
            query = query.filter(
                or_(
                    Person.first_name.ilike(f"%{search}%"),
                    Person.last_name.ilike(f"%{search}%")
                )
            )
        
        total = query.count()
        offset = (page - 1) * limit
        persons = query.offset(offset).limit(limit).all()
        
        return persons, total