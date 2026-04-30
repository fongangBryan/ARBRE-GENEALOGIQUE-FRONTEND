from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    READER = "reader"

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserRoleUpdate(BaseModel):
    role: UserRoleEnum

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: UUID
    role: UserRoleEnum
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

from typing import List as _List  # évite conflit avec List importé en dehors

class UserListResponse(BaseModel):
    items: _List[UserResponse]
    total: int
    page: int
    limit: int
    pages: int