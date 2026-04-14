from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import os

from app.db.session import get_db
from app.schemas.media import (
    MediaResponse, 
    MediaUploadResponse, 
    MediaListResponse,
    MediaTypeEnum
)
from app.services.media_service import MediaService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user, get_current_editor_user
from app.api.v1.guards.acl import require_media_access, require_edit_access  # NOUVEAU
from app.core.constants import MAX_UPLOAD_SIZE, ALLOWED_MEDIA_TYPES  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException  # NOUVEAU

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    owner_type: str = Form(..., description="person, event, or user"),
    owner_id: UUID = Form(...),
    media_type: MediaTypeEnum = Form(default=MediaTypeEnum.IMAGE),
    privacy_level: str = Form(default="private"),
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """
    Upload d'un fichier (image, document, PDF)
    """
    media_service = MediaService(db)
    acl_service = ACLService(db, current_user)
    
    # Vérifier les droits selon le type de propriétaire
    if owner_type == "person":
        if not acl_service.can_edit_person(owner_id):
            raise PermissionDeniedException("edit", "person")
    
    # Vérifier la taille du fichier (utiliser constantes)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_UPLOAD_SIZE:
        raise ValidationException("file", f"File too large. Max size: {MAX_UPLOAD_SIZE // (1024*1024)}MB")
    
    # Vérifier le type MIME
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        raise ValidationException("file", f"File type {file.content_type} not allowed")
    
    try:
        media = await media_service.upload_media(
            file=file,
            owner_type=owner_type,
            owner_id=owner_id,
            media_type=media_type,
            privacy_level=privacy_level,
            user_id=current_user.id
        )
        
        return MediaUploadResponse(
            id=media.id,
            filename=file.filename,
            storage_key=media.storage_key,
            thumbnail_key=media.thumbnail_key,
            url=f"/api/v1/media/{media.id}",
            thumbnail_url=f"/api/v1/media/{media.id}/thumbnail"
        )
    
    except ValueError as e:
        raise ValidationException("file", str(e))


@router.get("/{media_id}", response_model=None)
def get_media(
    media_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_media_access)  # NOUVEAU
):
    """Récupère un fichier média (avec vérification des droits)"""
    media_service = MediaService(db)
    
    media = media_service.get_media(media_id)
    if not media:
        raise NotFoundException("Media", media_id)
    
    file_path = media_service.get_media_file_path(media.storage_key)
    if not os.path.exists(file_path):
        raise NotFoundException("File", media.storage_key)
    
    return FileResponse(
        file_path,
        media_type=media.mime_type,
        filename=media.original_filename
    )


@router.get("/{media_id}/thumbnail", response_model=None)
def get_media_thumbnail(
    media_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_media_access)  # NOUVEAU
):
    """Récupère la miniature d'un média"""
    media_service = MediaService(db)
    
    media = media_service.get_media(media_id)
    if not media:
        raise NotFoundException("Media", media_id)
    
    if not media.thumbnail_key:
        raise NotFoundException("Thumbnail", "not available")
    
    file_path = media_service.get_media_file_path(media.thumbnail_key)
    if not os.path.exists(file_path):
        raise NotFoundException("Thumbnail", "not found")
    
    return FileResponse(file_path)


@router.get("/owner/{owner_type}/{owner_id}", response_model=List[MediaResponse])
def get_owner_media(
    owner_type: str,
    owner_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les médias associés à un propriétaire (personne, événement)"""
    media_service = MediaService(db)
    acl_service = ACLService(db, current_user)
    
    # Vérifier les droits selon le type
    if owner_type == "person":
        if not acl_service.can_view_person(owner_id):
            raise PermissionDeniedException("view", "person")
    
    medias = media_service.get_media_by_owner(owner_type, owner_id)
    
    # Filtrer par ACL
    visible_medias = [m for m in medias if acl_service.can_view_media(m)]
    
    return visible_medias


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: UUID,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Supprime un média"""
    media_service = MediaService(db)
    
    media = media_service.get_media(media_id)
    if not media:
        raise NotFoundException("Media", media_id)
    
    # Vérifier les droits
    acl_service = ACLService(db, current_user)
    if media.owner_type == "person":
        if not acl_service.can_edit_person(UUID(media.owner_id)):
            raise PermissionDeniedException("delete", "media")
    
    success = media_service.delete_media(media_id)
    if not success:
        raise NotFoundException("Media", media_id)


@router.put("/{media_id}/privacy")
def update_media_privacy(
    media_id: UUID,
    privacy_level: str,
    current_user = Depends(get_current_editor_user),
    db: Session = Depends(get_db)
):
    """Met à jour le niveau de confidentialité d'un média"""
    media_service = MediaService(db)
    
    media = media_service.get_media(media_id)
    if not media:
        raise NotFoundException("Media", media_id)
    
    acl_service = ACLService(db, current_user)
    if media.owner_type == "person":
        if not acl_service.can_edit_person(UUID(media.owner_id)):
            raise PermissionDeniedException("edit", "media")
    
    updated = media_service.update_privacy(media_id, privacy_level)
    if not updated:
        raise NotFoundException("Media", media_id)
    
    return {"message": "Privacy level updated"}