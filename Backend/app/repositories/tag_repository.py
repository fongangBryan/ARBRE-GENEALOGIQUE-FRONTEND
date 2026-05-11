from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tag import Tag, PersonTagHistory
from app.models.person import Person


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def get_by_id(self, tag_id: UUID) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def get_by_label(self, label: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.label == label).first()

    def list_all(self) -> List[Tag]:
        return self.db.query(Tag).order_by(Tag.label).all()

    def update(self, tag: Tag) -> Tag:
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete(self, tag_id: UUID) -> bool:
        tag = self.get_by_id(tag_id)
        if not tag:
            return False
        self.db.delete(tag)
        self.db.commit()
        return True

    def get_person_tags(self, person_id: UUID) -> List[Tag]:
        person = self.db.query(Person).filter(Person.id == person_id).first()
        if not person:
            return []
        return list(person.tags)

    def add_tag_to_person(self, person: Person, tag: Tag) -> bool:
        if tag not in person.tags:
            person.tags.append(tag)
            self.db.commit()
        return True

    def remove_tag_from_person(self, person: Person, tag: Tag) -> bool:
        if tag in person.tags:
            person.tags.remove(tag)
            self.db.commit()
            return True
        return False

    def get_person(self, person_id: UUID) -> Optional[Person]:
        return self.db.query(Person).filter(Person.id == person_id).first()

    def log_history(self, history: PersonTagHistory) -> None:
        self.db.add(history)
        self.db.commit()
