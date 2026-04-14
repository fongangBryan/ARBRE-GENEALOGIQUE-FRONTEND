from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class PrivacyLevelEnum(str, Enum):
    public = "public"
    family = "family"
    private = "private"

class PersonBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    maiden_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
    is_living: bool = True
    biography: Optional[str] = None
    occupation: Optional[str] = None
    nationality: Optional[str] = None
    privacy_level: PrivacyLevelEnum = PrivacyLevelEnum.private

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
    is_living: Optional[bool] = None
    biography: Optional[str] = None
    occupation: Optional[str] = None
    nationality: Optional[str] = None
    privacy_level: Optional[PrivacyLevelEnum] = None

class PersonResponse(PersonBase):
    id: UUID
    main_photo_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PersonListResponse(BaseModel):
    items: List[PersonResponse]
    total: int
    page: int
    limit: int
    pages: int