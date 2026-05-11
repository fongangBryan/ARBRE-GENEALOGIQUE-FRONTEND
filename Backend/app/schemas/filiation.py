from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime

from app.models.filiation import FiliationType


class FiliationCreate(BaseModel):
    parent_id: UUID4
    child_id: UUID4
    filiation_type: FiliationType = FiliationType.BIOLOGICAL


class FiliationUpdate(BaseModel):
    filiation_type: Optional[FiliationType] = None


class FiliationResponse(BaseModel):
    id: UUID4
    parent_id: UUID4
    child_id: UUID4
    filiation_type: FiliationType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
