from fastapi import Depends, HTTPException, status
from typing import List

from app.api.deps import get_current_user
from app.models.user import User, UserRole


def require_role(allowed_roles: List[UserRole]):
    """
    Factory pour créer un guard qui vérifie que l'utilisateur a un des rôles autorisés.
    
    Utilisation:
        @router.get("/admin", dependencies=[Depends(require_role([UserRole.ADMIN]))])
    """
    async def role_guard(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_guard


# Guards préconfigurés
require_admin = require_role([UserRole.ADMIN])
require_editor = require_role([UserRole.ADMIN, UserRole.EDITOR])
require_reader = require_role([UserRole.ADMIN, UserRole.EDITOR, UserRole.READER])


async def require_self_or_admin(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Vérifie que l'utilisateur accède à son propre profil OU est admin.
    """
    if current_user.role == UserRole.ADMIN:
        return current_user
    
    if str(current_user.id) == user_id:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you can only access your own profile"
    )