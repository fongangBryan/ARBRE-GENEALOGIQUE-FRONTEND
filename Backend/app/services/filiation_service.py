from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.filiation import Filiation
from app.schemas.filiation import FiliationCreate, FiliationUpdate
from app.repositories.filiation_repository import FiliationRepository
from app.repositories.person_repository import PersonRepository
from app.core.exceptions import NotFoundException, ConflictException, CycleDetectedException


class FiliationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FiliationRepository(db)
        self.person_repo = PersonRepository(db)

    def create_filiation(self, data: FiliationCreate) -> Filiation:
        parent = self.person_repo.get_by_id(data.parent_id)
        child = self.person_repo.get_by_id(data.child_id)

        if not parent:
            raise NotFoundException("Person", data.parent_id)
        if not child:
            raise NotFoundException("Person", data.child_id)

        if data.parent_id == data.child_id:
            raise ConflictException("Une personne ne peut pas être son propre parent")

        existing = self.repo.get_by_parent_and_child(data.parent_id, data.child_id)
        if existing:
            raise ConflictException("Cette filiation existe déjà")

        if self._would_create_cycle(data.parent_id, data.child_id):
            raise CycleDetectedException("Cette filiation créerait un cycle dans l'arbre généalogique")

        filiation = Filiation(
            parent_id=data.parent_id,
            child_id=data.child_id,
            filiation_type=data.filiation_type,
        )
        return self.repo.create(filiation)

    def _would_create_cycle(self, parent_id: UUID, child_id: UUID) -> bool:
        ancestors = set(self.repo.get_all_ancestors(parent_id))
        return child_id in ancestors

    def get_filiation(self, filiation_id: UUID) -> Optional[Filiation]:
        return self.repo.get_by_id(filiation_id)

    def get_parents(self, child_id: UUID) -> List[Filiation]:
        return self.repo.get_parents(child_id)

    def get_children(self, parent_id: UUID) -> List[Filiation]:
        return self.repo.get_children(parent_id)

    def update_filiation(self, filiation_id: UUID, data: FiliationUpdate) -> Filiation:
        filiation = self.repo.get_by_id(filiation_id)
        if not filiation:
            raise NotFoundException("Filiation", filiation_id)

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(filiation, key, value)

        return self.repo.update(filiation)

    def delete_filiation(self, filiation_id: UUID) -> bool:
        if not self.repo.get_by_id(filiation_id):
            raise NotFoundException("Filiation", filiation_id)
        return self.repo.delete(filiation_id)
