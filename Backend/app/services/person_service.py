from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.person import Person, PrivacyLevel
from app.schemas.person import PersonCreate, PersonUpdate
from app.repositories.person_repository import PersonRepository
from app.core.exceptions import NotFoundException
from app.utils.helpers import sanitize_html


class PersonService:
    def __init__(self, db: Session):
        self.db  = db
        self.repo = PersonRepository(db)

    def create_person(self, person_data: PersonCreate, created_by: UUID) -> Person:
        person = Person(
            first_name=person_data.first_name.strip(),
            last_name=person_data.last_name.strip(),
            maiden_name=person_data.maiden_name.strip() if person_data.maiden_name else None,
            gender=person_data.gender,
            birth_date=person_data.birth_date,
            birth_place=person_data.birth_place,
            death_date=person_data.death_date,
            death_place=person_data.death_place,
            is_living=person_data.is_living,
            biography=sanitize_html(person_data.biography),
            occupation=person_data.occupation,
            nationality=person_data.nationality,
            privacy_level=person_data.privacy_level,
            created_by=created_by,
        )
        return self.repo.create(person)

    def get_person(self, person_id: UUID) -> Optional[Person]:
        return self.repo.get_by_id(person_id)

    def update_person(self, person_id: UUID, person_data: PersonUpdate) -> Person:
        person = self.repo.get_by_id(person_id)
        if not person:
            raise NotFoundException("Person", person_id)

        update_data = person_data.model_dump(exclude_unset=True)

        if "biography" in update_data and update_data["biography"]:
            update_data["biography"] = sanitize_html(update_data["biography"])

        for key, value in update_data.items():
            if value is not None:
                setattr(person, key, value)

        return self.repo.update(person)

    def delete_person(self, person_id: UUID) -> bool:
        return self.repo.delete(person_id)

    def list_persons(
        self,
        search: Optional[str],
        page: int,
        limit: int,
        user_id: UUID,
        is_admin: bool = False,
    ) -> Tuple[List[Person], int]:
        # L'admin voit tous les membres ; les autres voient seulement les leurs
        owner_id = None if is_admin else user_id
        return self.repo.list_persons(search=search, page=page, limit=limit, owner_id=owner_id)
