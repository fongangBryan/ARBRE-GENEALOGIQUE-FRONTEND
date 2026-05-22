from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from uuid import UUID

from app.models.union import Union


class UnionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, union: Union) -> Union:
        self.db.add(union)
        self.db.commit()
        self.db.refresh(union)
        return union

    def get_by_id(self, union_id: UUID) -> Optional[Union]:
        return self.db.query(Union).filter(Union.id == union_id).first()

    def get_by_person(self, person_id: UUID) -> List[Union]:
        return self.db.query(Union).filter(
            or_(Union.person_id_1 == person_id, Union.person_id_2 == person_id)
        ).all()

    def get_between(self, person_id_1: UUID, person_id_2: UUID) -> List[Union]:
        return self.db.query(Union).filter(
            or_(
                (Union.person_id_1 == person_id_1) & (Union.person_id_2 == person_id_2),
                (Union.person_id_1 == person_id_2) & (Union.person_id_2 == person_id_1),
            )
        ).all()

    def update(self, union: Union) -> Union:
        self.db.commit()
        self.db.refresh(union)
        return union

    def delete(self, union_id: UUID) -> bool:
        union = self.get_by_id(union_id)
        if union:
            self.db.delete(union)
            self.db.commit()
            return True
        return False
