from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.acl_service import ACLService
from app.models.user import User


async def require_view_access(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """
    Guard qui vérifie que l'utilisateur peut VOIR une personne.
    À utiliser dans les endpoints GET /persons/{id}
    """
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(person_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this person"
        )
    return True


async def require_edit_access(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """
    Guard qui vérifie que l'utilisateur peut MODIFIER une personne.
    À utiliser dans les endpoints PUT /persons/{id}
    """
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_edit_person(person_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this person"
        )
    return True


async def require_media_access(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """
    Guard qui vérifie que l'utilisateur peut voir un média.
    """
    from app.services.media_service import MediaService
    
    media_service = MediaService(db)
    media = media_service.get_media(media_id)
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_media(media):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this media"
        )
    return True