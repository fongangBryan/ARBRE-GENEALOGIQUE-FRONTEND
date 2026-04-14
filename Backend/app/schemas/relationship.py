from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class RelationshipTypeEnum(str, Enum):
    PARENT_CHILD = "parent_child"
    COUPLE = "couple"

class ParentChildTypeEnum(str, Enum):
    BIOLOGICAL = "biological"
    ADOPTIVE = "adoptive"
    GUARDIAN = "guardian"
    STEP = "step"

class RelationshipBase(BaseModel):
    type: RelationshipTypeEnum
    person_id_1: UUID
    person_id_2: UUID
    child_type: Optional[ParentChildTypeEnum] = None
    marriage_date: Optional[str] = None
    marriage_place: Optional[str] = None
    divorce_date: Optional[str] = None
    meta: Optional[dict] = {}

class RelationshipCreate(RelationshipBase):
    pass

class RelationshipUpdate(BaseModel):
    type: Optional[RelationshipTypeEnum] = None
    child_type: Optional[ParentChildTypeEnum] = None
    marriage_date: Optional[str] = None
    marriage_place: Optional[str] = None
    divorce_date: Optional[str] = None
    meta: Optional[dict] = None

class RelationshipResponse(RelationshipBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RelationshipListResponse(BaseModel):
    items: List[RelationshipResponse]
    total: int