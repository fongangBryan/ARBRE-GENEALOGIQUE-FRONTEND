from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tag import Tag, PersonTagHistory
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagUpdate
from app.core.exceptions import NotFoundException, ConflictException


class TagService:
    def __init__(self, db: Session):
        self.repo = TagRepository(db)

    def list_tags(self) -> List[Tag]:
        return self.repo.list_all()

    def get_tag(self, tag_id: UUID) -> Tag:
        tag = self.repo.get_by_id(tag_id)
        if not tag:
            raise NotFoundException("Tag", tag_id)
        return tag

    def create_tag(self, data: TagCreate, user_id: UUID) -> Tag:
        if self.repo.get_by_label(data.label):
            raise ConflictException(f"A tag with label '{data.label}' already exists")
        tag = Tag(
            label=data.label,
            description=data.description,
            color=data.color,
            icon=data.icon,
            created_by=user_id,
        )
        return self.repo.create(tag)

    def update_tag(self, tag_id: UUID, data: TagUpdate) -> Tag:
        tag = self.get_tag(tag_id)
        if data.label is not None:
            existing = self.repo.get_by_label(data.label)
            if existing and existing.id != tag_id:
                raise ConflictException(f"A tag with label '{data.label}' already exists")
            tag.label = data.label
        if data.description is not None:
            tag.description = data.description
        if data.color is not None:
            tag.color = data.color
        if data.icon is not None:
            tag.icon = data.icon
        return self.repo.update(tag)

    def delete_tag(self, tag_id: UUID) -> bool:
        self.get_tag(tag_id)
        return self.repo.delete(tag_id)

    def get_person_tags(self, person_id: UUID) -> List[Tag]:
        return self.repo.get_person_tags(person_id)

    def add_tag_to_person(self, person_id: UUID, tag_id: UUID, user_id: UUID) -> bool:
        tag = self.get_tag(tag_id)
        person = self.repo.get_person(person_id)
        if not person:
            raise NotFoundException("Person", person_id)
        result = self.repo.add_tag_to_person(person, tag)
        if result:
            self.repo.log_history(PersonTagHistory(
                person_id=person_id,
                tag_id=tag_id,
                action="added",
                performed_by=user_id,
            ))
        return result

    def remove_tag_from_person(self, person_id: UUID, tag_id: UUID, user_id: UUID) -> bool:
        tag = self.get_tag(tag_id)
        person = self.repo.get_person(person_id)
        if not person:
            raise NotFoundException("Person", person_id)
        result = self.repo.remove_tag_from_person(person, tag)
        if result:
            self.repo.log_history(PersonTagHistory(
                person_id=person_id,
                tag_id=tag_id,
                action="removed",
                performed_by=user_id,
            ))
        return result
