from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.access_control import AccessControl, PermissionType, PrincipalType
from app.repositories.base import BaseRepository


class ACLRepository(BaseRepository):
    """Repository pour les Access Control Lists"""
    
    def __init__(self, db: Session):
        super().__init__(db, AccessControl)
    
    def get_acls_for_person(self, person_id: UUID, user_id: Optional[UUID] = None, permission: Optional[PermissionType] = None) -> List[AccessControl]:
        """
        Récupère toutes les ACLs pour une personne.
        Si user_id est fourni, filtre pour cet utilisateur.
        Si permission est fournie, filtre par type de permission.
        """
        query = self.db.query(AccessControl).filter(AccessControl.person_id == person_id)
        
        if user_id:
            # Rechercher les ACLs pour l'utilisateur spécifique OU pour son rôle
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            
            query = query.filter(
                (AccessControl.principal_type == PrincipalType.USER) & (AccessControl.principal_id == str(user_id)) |
                (AccessControl.principal_type == PrincipalType.ROLE) & (AccessControl.principal_id == user.role.value if user else None)
            )
        
        if permission:
            query = query.filter(AccessControl.permission == permission)
        
        return query.all()
    
    def get_acls_for_user(self, user_id: UUID) -> List[AccessControl]:
        """Récupère toutes les ACLs accordées à un utilisateur spécifique"""
        return self.db.query(AccessControl).filter(
            AccessControl.principal_type == PrincipalType.USER,
            AccessControl.principal_id == str(user_id)
        ).all()
    
    def get_acls_by_principal(self, principal_type: PrincipalType, principal_id: str) -> List[AccessControl]:
        """Récupère les ACLs par type de principal (user ou role)"""
        return self.db.query(AccessControl).filter(
            AccessControl.principal_type == principal_type,
            AccessControl.principal_id == principal_id
        ).all()
    
    def get_user_permission_for_person(self, person_id: UUID, user_id: UUID) -> Optional[PermissionType]:
        """
        Récupère la permission maximale qu'un utilisateur a sur une personne.
        Retourne None si aucun accès.
        """
        from app.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Chercher les ACLs pour cet utilisateur ou son rôle
        acls = self.db.query(AccessControl).filter(
            AccessControl.person_id == person_id,
            (
                (AccessControl.principal_type == PrincipalType.USER) & (AccessControl.principal_id == str(user_id)) |
                (AccessControl.principal_type == PrincipalType.ROLE) & (AccessControl.principal_id == user.role.value)
            )
        ).all()
        
        # Retourner la permission la plus élevée
        permission_order = {
            PermissionType.DELETE: 3,
            PermissionType.WRITE: 2,
            PermissionType.READ: 1
        }
        
        best_permission = None
        best_score = 0
        
        for acl in acls:
            score = permission_order.get(acl.permission, 0)
            if score > best_score:
                best_score = score
                best_permission = acl.permission
        
        return best_permission
    
    def has_permission(self, person_id: UUID, user_id: UUID, required_permission: PermissionType) -> bool:
        """Vérifie si un utilisateur a une permission spécifique sur une personne"""
        user_permission = self.get_user_permission_for_person(person_id, user_id)
        
        if not user_permission:
            return False
        
        permission_order = {
            PermissionType.DELETE: 3,
            PermissionType.WRITE: 2,
            PermissionType.READ: 1
        }
        
        return permission_order.get(user_permission, 0) >= permission_order.get(required_permission, 0)