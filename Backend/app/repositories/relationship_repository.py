from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from uuid import UUID

from app.models.relationship import Relationship, RelationshipType

class RelationshipRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, relationship: Relationship) -> Relationship:
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship
    
    def get_by_id(self, relationship_id: UUID) -> Optional[Relationship]:
        return self.db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    def get_between(self, person_id_1: UUID, person_id_2: UUID) -> Optional[Relationship]:
        return self.db.query(Relationship).filter(
            or_(
                (Relationship.person_id_1 == person_id_1) & (Relationship.person_id_2 == person_id_2),
                (Relationship.person_id_1 == person_id_2) & (Relationship.person_id_2 == person_id_1)
            )
        ).first()
    
    def get_by_person(self, person_id: UUID, relationship_type: Optional[str] = None) -> List[Relationship]:
        query = self.db.query(Relationship).filter(
            or_(
                Relationship.person_id_1 == person_id,
                Relationship.person_id_2 == person_id
            )
        )
        
        if relationship_type:
            query = query.filter(Relationship.type == relationship_type)
        
        return query.all()
    
    def get_parents(self, person_id: UUID) -> List[Relationship]:
        return self.db.query(Relationship).filter(
            Relationship.type == RelationshipType.PARENT_CHILD,
            Relationship.person_id_2 == person_id
        ).all()
    
    def get_children(self, person_id: UUID) -> List[Relationship]:
        return self.db.query(Relationship).filter(
            Relationship.type == RelationshipType.PARENT_CHILD,
            Relationship.person_id_1 == person_id
        ).all()
    
    def get_spouses(self, person_id: UUID) -> List[Relationship]:
        return self.db.query(Relationship).filter(
            Relationship.type == RelationshipType.COUPLE,
            or_(
                Relationship.person_id_1 == person_id,
                Relationship.person_id_2 == person_id
            )
        ).all()
    
    def update(self, relationship: Relationship) -> Relationship:
        self.db.commit()
        self.db.refresh(relationship)
        return relationship
    
    def delete(self, relationship_id: UUID) -> bool:
        relationship = self.get_by_id(relationship_id)
        if relationship:
            self.db.delete(relationship)
            self.db.commit()
            return True
        return False