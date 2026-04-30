from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.union import Union
from app.schemas.union import UnionCreate, UnionUpdate
from app.repositories.union_repository import UnionRepository
from app.repositories.person_repository import PersonRepository
from app.core.exceptions import NotFoundException, ConflictException


class UnionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnionRepository(db)
        self.person_repo = PersonRepository(db)

    def create_union(self, data: UnionCreate) -> Union:
        person1 = self.person_repo.get_by_id(data.person_id_1)
        person2 = self.person_repo.get_by_id(data.person_id_2)

        if not person1:
            raise NotFoundException("Person", data.person_id_1)
        if not person2:
            raise NotFoundException("Person", data.person_id_2)

        union = Union(
            person_id_1=data.person_id_1,
            person_id_2=data.person_id_2,
            union_type=data.union_type,
            date_union=data.date_union,
            lieu_union=data.lieu_union,
            date_dissolution=data.date_dissolution,
            statut=data.statut,
        )
        return self.repo.create(union)

    def get_union(self, union_id: UUID) -> Optional[Union]:
        return self.repo.get_by_id(union_id)

    def get_unions_by_person(self, person_id: UUID) -> List[Union]:
        return self.repo.get_by_person(person_id)

    def get_unions_between(self, person_id_1: UUID, person_id_2: UUID) -> List[Union]:
        return self.repo.get_between(person_id_1, person_id_2)

    def update_union(self, union_id: UUID, data: UnionUpdate) -> Union:
        union = self.repo.get_by_id(union_id)
        if not union:
            raise NotFoundException("Union", union_id)

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(union, key, value)

        return self.repo.update(union)

    def delete_union(self, union_id: UUID) -> bool:
        if not self.repo.get_by_id(union_id):
            raise NotFoundException("Union", union_id)
        return self.repo.delete(union_id)
