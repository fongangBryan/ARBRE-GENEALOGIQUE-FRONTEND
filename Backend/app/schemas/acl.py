from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class PermissionEnum(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

class PrincipalTypeEnum(str, Enum):
    USER = "user"
    ROLE = "role"

class AccessControlBase(BaseModel):
    person_id: UUID
    principal_type: PrincipalTypeEnum
    principal_id: str  # user_id or role name
    permission: PermissionEnum

class AccessControlCreate(AccessControlBase):
    pass

class AccessControlResponse(AccessControlBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True