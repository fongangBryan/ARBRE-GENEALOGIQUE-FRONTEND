from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from uuid import UUID

from app.models.user import User, UserRole
from app.schemas.user import UserUpdate
from app.core.security import get_password_hash
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Récupérer un utilisateur par son ID"""
        return self.repo.get_by_id(user_id)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Récupérer un utilisateur par son email"""
        return self.repo.get_by_email(email)
    
    def get_by_id_or_email(self, identifier: str) -> Optional[User]:
        """Récupérer par ID ou email"""
        return self.repo.get_by_id_or_email(identifier)
    
    def create_user(self, email: str, password: str, first_name: str = None, last_name: str = None) -> User:
        """Créer un nouvel utilisateur"""
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.EDITOR,
            is_active=True,
            is_verified=False
        )
        return self.repo.create(user)
    
    def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Mettre à jour un utilisateur"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)
        
        return self.repo.update(user)
    
    def update_role(self, user_id: UUID, role: UserRole) -> Optional[User]:
        """Changer le rôle d'un utilisateur"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return None
        
        user.role = role
        return self.repo.update(user)
    
    def change_password(self, user_id: UUID, new_password: str) -> bool:
        """Changer le mot de passe d'un utilisateur"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return False
        
        user.password_hash = get_password_hash(new_password)
        self.repo.update(user)
        return True
    
    def delete_user(self, user_id: UUID, soft_delete: bool = True) -> bool:
        """
        Supprimer un utilisateur.
        soft_delete: désactive le compte au lieu de supprimer définitivement
        """
        if soft_delete:
            user = self.repo.get_by_id(user_id)
            if user:
                user.is_active = False
                self.repo.update(user)
                return True
        return self.repo.delete(user_id)
    
    def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activer un utilisateur"""
        user = self.repo.get_by_id(user_id)
        if user:
            user.is_active = True
            return self.repo.update(user)
        return None
    
    def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Désactiver un utilisateur"""
        user = self.repo.get_by_id(user_id)
        if user:
            user.is_active = False
            return self.repo.update(user)
        return None
    
    def list_users(self, search: Optional[str] = None, page: int = 1, limit: int = 20) -> Tuple[List[User], int]:
        """Liste paginée des utilisateurs"""
        return self.repo.list_all(search, page, limit)
    
    def get_user_activity(self, user_id: UUID) -> List[dict]:
        """Récupérer l'activité d'un utilisateur (créations, modifications)"""
        # À implémenter avec un modèle d'audit
        # Retourne une liste d'actions récentes
        return []