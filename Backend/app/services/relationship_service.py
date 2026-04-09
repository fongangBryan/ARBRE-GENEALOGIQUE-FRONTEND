from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from uuid import UUID

from app.models.relationship import Relationship, RelationshipType
from app.schemas.relationship import RelationshipCreate, RelationshipUpdate
from app.repositories.relationship_repository import RelationshipRepository
from app.repositories.person_repository import PersonRepository

class RelationshipService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RelationshipRepository(db)
        self.person_repo = PersonRepository(db)
    
    def create_relationship(self, relationship_data: RelationshipCreate) -> Relationship:
        # Vérifier que les deux personnes existent
        person1 = self.person_repo.get_by_id(relationship_data.person_id_1)
        person2 = self.person_repo.get_by_id(relationship_data.person_id_2)
        
        if not person1 or not person2:
            raise ValueError("One or both persons not found")
        
        # Vérifier si la relation existe déjà
        existing = self.repo.get_between(
            relationship_data.person_id_1, 
            relationship_data.person_id_2
        )
        if existing:
            raise ValueError("Relationship already exists between these persons")
        
        # Pour PARENT_CHILD, vérifier les cycles
        if relationship_data.type == RelationshipType.PARENT_CHILD:
            if self._would_create_cycle(relationship_data.person_id_1, relationship_data.person_id_2):
                raise ValueError("This relationship would create a cycle in the tree")
        
        relationship = Relationship(
            type=relationship_data.type,
            person_id_1=relationship_data.person_id_1,
            person_id_2=relationship_data.person_id_2,
            child_type=relationship_data.child_type,
            marriage_date=relationship_data.marriage_date,
            marriage_place=relationship_data.marriage_place,
            divorce_date=relationship_data.divorce_date,
            meta=relationship_data.meta or {}
        )
        
        return self.repo.create(relationship)
    
    def _would_create_cycle(self, parent_id: UUID, child_id: UUID) -> bool:
        """Vérifie si ajouter parent->enfant créerait un cycle"""
        # Vérifier si child est un ancêtre de parent
        ancestors = self._get_all_ancestors(parent_id)
        return child_id in ancestors
    
    def _get_all_ancestors(self, person_id: UUID) -> set:
        """Récupère tous les ancêtres d'une personne"""
        ancestors = set()
        to_process = [person_id]
        
        while to_process:
            current = to_process.pop()
            parents = self.repo.get_parents(current)
            for parent_rel in parents:
                parent_id = parent_rel.person_id_1
                if parent_id not in ancestors:
                    ancestors.add(parent_id)
                    to_process.append(parent_id)
        
        return ancestors
    
    def get_relationship(self, relationship_id: UUID) -> Optional[Relationship]:
        return self.repo.get_by_id(relationship_id)
    
    def get_relationships_by_person(self, person_id: UUID, relationship_type: Optional[str] = None) -> List[Relationship]:
        return self.repo.get_by_person(person_id, relationship_type)
    
    def get_relationship_between(self, person_id_1: UUID, person_id_2: UUID) -> Optional[Relationship]:
        return self.repo.get_between(person_id_1, person_id_2)
    
    def update_relationship(self, relationship_id: UUID, relationship_data: RelationshipUpdate) -> Optional[Relationship]:
        relationship = self.repo.get_by_id(relationship_id)
        if not relationship:
            return None
        
        update_data = relationship_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(relationship, key, value)
        
        return self.repo.update(relationship)
    
    def delete_relationship(self, relationship_id: UUID) -> bool:
        return self.repo.delete(relationship_id)
    
    def get_parents(self, person_id: UUID) -> List[Relationship]:
        return self.repo.get_parents(person_id)
    
    def get_children(self, person_id: UUID) -> List[Relationship]:
        return self.repo.get_children(person_id)
    
    def get_spouses(self, person_id: UUID) -> List[Relationship]:
        return self.repo.get_spouses(person_id)