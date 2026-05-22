from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.filiation import Filiation


class FiliationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, filiation: Filiation) -> Filiation:
        self.db.add(filiation)
        self.db.commit()
        self.db.refresh(filiation)
        return filiation

    def get_by_id(self, filiation_id: UUID) -> Optional[Filiation]:
        return self.db.query(Filiation).filter(Filiation.id == filiation_id).first()

    def get_parents(self, child_id: UUID) -> List[Filiation]:
        return self.db.query(Filiation).filter(Filiation.child_id == child_id).all()

    def get_children(self, parent_id: UUID) -> List[Filiation]:
        return self.db.query(Filiation).filter(Filiation.parent_id == parent_id).all()

    def get_by_parent_and_child(self, parent_id: UUID, child_id: UUID) -> Optional[Filiation]:
        return self.db.query(Filiation).filter(
            Filiation.parent_id == parent_id,
            Filiation.child_id == child_id
        ).first()

    def get_all_ancestors(self, person_id: UUID) -> List[UUID]:
        """Return all ancestor IDs via BFS (used for cycle detection)."""
        visited: set[UUID] = set()
        queue: List[UUID] = [person_id]
        while queue:
            current = queue.pop(0)
            for fil in self.get_parents(current):
                if fil.parent_id not in visited:
                    visited.add(fil.parent_id)
                    queue.append(fil.parent_id)
        return list(visited)

    def update(self, filiation: Filiation) -> Filiation:
        self.db.commit()
        self.db.refresh(filiation)
        return filiation

    def delete(self, filiation_id: UUID) -> bool:
        filiation = self.get_by_id(filiation_id)
        if filiation:
            self.db.delete(filiation)
            self.db.commit()
            return True
        return False
