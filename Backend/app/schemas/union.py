from pydantic import BaseModel, UUID4, model_validator
from typing import Optional
from datetime import datetime

from app.models.union import UnionType, UnionStatut


class UnionCreate(BaseModel):
    person_id_1: UUID4
    person_id_2: UUID4
    union_type: UnionType = UnionType.MARIAGE
    date_union: Optional[str] = None       # AAAA / AAAA-MM / AAAA-MM-JJ
    lieu_union: Optional[str] = None
    date_dissolution: Optional[str] = None
    statut: UnionStatut = UnionStatut.ACTIF

    @model_validator(mode="after")
    def different_persons(self) -> "UnionCreate":
        if self.person_id_1 == self.person_id_2:
            raise ValueError("Les deux personnes d'une union doivent être différentes")
        return self


class UnionUpdate(BaseModel):
    union_type: Optional[UnionType] = None
    date_union: Optional[str] = None
    lieu_union: Optional[str] = None
    date_dissolution: Optional[str] = None
    statut: Optional[UnionStatut] = None


class UnionResponse(BaseModel):
    id: UUID4
    person_id_1: UUID4
    person_id_2: UUID4
    union_type: UnionType
    date_union: Optional[str]
    lieu_union: Optional[str]
    date_dissolution: Optional[str]
    statut: UnionStatut
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
