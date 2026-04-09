from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List, Tuple
from uuid import UUID

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository pour l'entité User"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Récupérer un utilisateur par son email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_id_or_email(self, identifier: str) -> Optional[User]:
        """Récupérer par ID (UUID) ou email"""
        try:
            # Essayer comme UUID
            user_id = UUID(identifier)
            return self.get_by_id(user_id)
        except ValueError:
            # Sinon chercher par email
            return self.get_by_email(identifier)
    
    def list_all(
        self, 
        search: Optional[str] = None, 
        page: int = 1, 
        limit: int = 20
    ) -> Tuple[List[User], int]:
        """Liste paginée des utilisateurs avec recherche optionnelle"""
        query = self.db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%")
                )
            )
        
        total = query.count()
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()
        
        return users, total
    
    def get_active_users(self) -> List[User]:
        """Récupérer tous les utilisateurs actifs"""
        return self.db.query(User).filter(User.is_active == True).all()
    
    def get_by_role(self, role: str) -> List[User]:
        """Récupérer les utilisateurs par rôle"""
        from app.models.user import UserRole
        return self.db.query(User).filter(User.role == UserRole(role)).all()