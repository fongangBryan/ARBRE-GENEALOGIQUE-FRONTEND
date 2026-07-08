from typing import Optional
from uuid import UUID as UUIDType
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.services.user_service import UserService
from app.services.acl_service import ACLService
from app.core.exceptions import AuthenticationException, PermissionDeniedException

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationException(detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException(detail="Invalid token")

    try:
        user_uuid = UUIDType(user_id)
    except (ValueError, AttributeError):
        raise AuthenticationException(detail="Invalid token")

    user_service = UserService(db)
    user = user_service.get_by_id(user_uuid)

    if not user or not user.is_active:
        raise AuthenticationException(detail="User not found or inactive")

    return user

def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin_user(current_user = Depends(get_current_user)):
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException(action="access", resource_type="admin area")
    return current_user

def get_current_editor_user(current_user = Depends(get_current_user)):
    from app.models.user import UserRole
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
        raise PermissionDeniedException(action="modify", resource_type="data")
    return current_user