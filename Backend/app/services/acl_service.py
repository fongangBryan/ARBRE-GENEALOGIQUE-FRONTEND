from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.user import User, UserRole
from app.models.person import Person, PrivacyLevel
from app.models.media import Media
from app.models.access_control import AccessControl, PermissionType, PrincipalType
from app.repositories.acl_repository import ACLRepository
from app.repositories.person_repository import PersonRepository


class ACLService:
    """
    Service de contrôle d'accès (Access Control List)
    Gère les permissions fines pour les personnes et les médias
    """
    
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user
        self.acl_repo = ACLRepository(db)
        self.person_repo = PersonRepository(db)
    
    def can_view_person(self, person_id: UUID) -> bool:
        """
        Vérifie si l'utilisateur courant peut voir une personne.
        
        Règles :
        1. Admin peut tout voir
        2. Public : tout le monde peut voir
        3. Family : seulement les membres de la famille (ACL ou créateur)
        4. Private : seulement le créateur et les personnes avec ACL explicite
        """
        # Admin a tous les droits
        if self.current_user.role == UserRole.ADMIN:
            return True
        
        person = self.person_repo.get_by_id(person_id)
        if not person:
            return False
        
        # Niveau public : tout le monde peut voir
        if person.privacy_level == PrivacyLevel.PUBLIC:
            return True
        
        # Niveau famille : vérifier les ACL
        if person.privacy_level == PrivacyLevel.FAMILY:
            # Le créateur peut voir
            if person.created_by == self.current_user.id:
                return True
            
            # Vérifier les ACLs
            acls = self.acl_repo.get_acls_for_person(person_id, self.current_user.id)
            if acls:
                return True
            
            # Les éditeurs peuvent voir les personnes famille par défaut
            if self.current_user.role == UserRole.EDITOR:
                return True
            
            return False
        
        # Niveau privé : accès très restreint
        if person.privacy_level == PrivacyLevel.PRIVATE:
            # Seul le créateur et les ACLs explicites
            if person.created_by == self.current_user.id:
                return True
            
            acls = self.acl_repo.get_acls_for_person(person_id, self.current_user.id)
            return len(acls) > 0
        
        return False
    
    def can_edit_person(self, person_id: UUID) -> bool:
        """
        Vérifie si l'utilisateur peut modifier une personne.
        
        Règles :
        1. Admin peut tout modifier
        2. Editor peut modifier si créateur ou ACL write
        3. Reader ne peut pas modifier
        """
        # Admin a tous les droits
        if self.current_user.role == UserRole.ADMIN:
            return True
        
        # Reader ne peut pas modifier
        if self.current_user.role == UserRole.READER:
            return False
        
        person = self.person_repo.get_by_id(person_id)
        if not person:
            return False
        
        # Le créateur peut modifier
        if person.created_by == self.current_user.id:
            return True
        
        # Vérifier les ACLs write
        acls = self.acl_repo.get_acls_for_person(person_id, self.current_user.id, PermissionType.WRITE)
        if acls:
            return True
        
        return False
    
    def can_delete_person(self, person_id: UUID) -> bool:
        """Seul l'admin peut supprimer une personne"""
        return self.current_user.role == UserRole.ADMIN
    
    def can_view_media(self, media: Media) -> bool:
        """Vérifie si l'utilisateur peut voir un média"""
        # Admin peut tout voir
        if self.current_user.role == UserRole.ADMIN:
            return True
        
        # Média public
        if media.privacy_level == "public":
            return True
        
        # Pour les médias attachés à une personne, utiliser la même logique que la personne
        if media.owner_type == "person":
            return self.can_view_person(UUID(media.owner_id))
        
        # Pour les médias attachés à un événement, remonter à la personne
        if media.owner_type == "event":
            from app.services.event_service import EventService
            event_service = EventService(self.db)
            event = event_service.get_event(UUID(media.owner_id))
            if event:
                return self.can_view_person(event.person_id)
        
        return False
    
    def grant_access(
        self, 
        person_id: UUID, 
        principal_type: PrincipalType, 
        principal_id: str,
        permission: PermissionType
    ) -> AccessControl:
        """
        Accorde un accès spécifique à une personne.
        principal_type: "user" or "role"
        principal_id: user_id or role_name
        """
        # Vérifier que l'utilisateur courant a le droit de donner des accès
        if not self.can_edit_person(person_id):
            raise PermissionError("You don't have permission to grant access to this person")
        
        # Créer l'ACL
        acl = AccessControl(
            person_id=person_id,
            principal_type=principal_type,
            principal_id=principal_id,
            permission=permission
        )
        
        return self.acl_repo.create(acl)
    
    def revoke_access(self, acl_id: UUID) -> bool:
        """Révoque un accès"""
        acl = self.acl_repo.get_by_id(acl_id)
        if not acl:
            return False
        
        # Vérifier les droits
        if not self.can_edit_person(acl.person_id):
            raise PermissionError("You don't have permission to revoke access")
        
        return self.acl_repo.delete(acl_id)
    
    def list_acls_for_person(self, person_id: UUID) -> List[AccessControl]:
        """Liste toutes les ACLs pour une personne"""
        if not self.can_view_person(person_id):
            return []
        return self.acl_repo.get_acls_for_person(person_id)