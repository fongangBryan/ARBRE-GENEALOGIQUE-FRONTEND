from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import os
import shutil
from PIL import Image
from fastapi import UploadFile
import uuid as uuid_lib

from app.models.media import Media
from app.schemas.media import MediaCreate
from app.repositories.media_repository import MediaRepository
from app.core.constants import THUMBNAIL_SIZES, ALLOWED_IMAGE_TYPES  # NOUVEAU
from app.utils.helpers import generate_slug  # NOUVEAU

class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MediaRepository(db)
        self.upload_dir = "uploads"
        
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.join(self.upload_dir, "thumbnails"), exist_ok=True)
    
    async def upload_media(
        self,
        file: UploadFile,
        owner_type: str,
        owner_id: UUID,
        media_type: str,
        privacy_level: str,
        user_id: UUID
    ) -> Media:
        # Générer un nom de fichier unique avec slug
        name_part = generate_slug(file.filename.split('.')[0][:30])  # NOUVEAU
        extension = os.path.splitext(file.filename)[1]
        storage_key = f"{owner_type}/{owner_id}/{name_part}-{uuid_lib.uuid4().hex[:8]}{extension}"
        file_path = os.path.join(self.upload_dir, storage_key)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Générer la miniature pour les images - Utiliser THUMBNAIL_SIZES
        thumbnail_key = None
        if file.content_type in ALLOWED_IMAGE_TYPES:
            thumbnail_key = await self._generate_thumbnail(storage_key, file_path, THUMBNAIL_SIZES["medium"])  # MODIFIÉ
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        media_data = MediaCreate(
            owner_type=owner_type,
            owner_id=owner_id,
            media_type=media_type,
            privacy_level=privacy_level,
            original_filename=file.filename,
            storage_key=storage_key,
            thumbnail_key=thumbnail_key,
            mime_type=file.content_type,
            file_size=file_size
        )
        
        media = Media(**media_data.model_dump())
        return self.repo.create(media)
    
    async def _generate_thumbnail(self, storage_key: str, file_path: str, size: tuple = (200, 200)) -> str:
        """Génère une miniature pour une image"""
        try:
            img = Image.open(file_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            thumbnail_key = f"thumbnails/{storage_key}"
            thumbnail_path = os.path.join(self.upload_dir, thumbnail_key)
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
            
            # Convertir en RGB si nécessaire (pour PNG avec transparence)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            img.save(thumbnail_path, "JPEG", quality=85)
            return thumbnail_key
        except Exception as e:
            print(f"Failed to generate thumbnail: {e}")
            return None
    
    # ... Le reste de la classe reste identique ...