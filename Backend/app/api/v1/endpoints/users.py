from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.schemas.common import MessageResponse
from app.services.user_service import UserService
from app.api.deps import get_current_user
from app.api.v1.guards.roles import require_self_or_admin
from app.core.security import verify_password, get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer son propre profil"""
    user_service = UserService(db)
    return user_service.get_by_id(current_user.id)


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    user_data: UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour son propre profil"""
    user_service = UserService(db)
    
    # Vérifier si l'email est déjà utilisé par un autre utilisateur
    if user_data.email and user_data.email != current_user.email:
        existing = user_service.get_by_email(user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already used by another account")
    
    user = user_service.update_user(current_user.id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/me/password", response_model=MessageResponse)
def change_my_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Changer son mot de passe"""
    user_service = UserService(db)
    
    # Vérifier l'ancien mot de passe
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Vérifier la longueur du nouveau mot de passe
    if len(password_data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Mettre à jour le mot de passe
    updated = user_service.change_password(current_user.id, password_data.new_password)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    
    return MessageResponse(message="Password changed successfully")


@router.get("/me/activity")
def get_my_activity(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer l'historique des activités de l'utilisateur"""
    user_service = UserService(db)
    activity = user_service.get_user_activity(current_user.id)
    return {"activities": activity}


@router.delete("/me", response_model=MessageResponse)
def delete_my_account(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer son propre compte (RGPD)"""
    user_service = UserService(db)
    
    # Soft delete ou hard delete selon la politique
    success = user_service.delete_user(current_user.id, soft_delete=True)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return MessageResponse(message="Your account has been deleted")


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_self_or_admin)  # Vérifie que c'est soi-même ou admin
):
    """Récupérer un utilisateur par son ID (soi-même ou admin)"""
    user_service = UserService(db)
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user