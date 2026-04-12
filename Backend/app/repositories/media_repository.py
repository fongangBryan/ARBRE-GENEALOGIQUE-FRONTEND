from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.media import Media

class MediaRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, media: Media) -> Media:
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media
    
    def get_by_id(self, media_id: UUID) -> Optional[Media]:
        return self.db.query(Media).filter(Media.id == media_id).first()
    
    def get_by_owner(self, owner_type: str, owner_id: UUID) -> List[Media]:
        return self.db.query(Media).filter(
            Media.owner_type == owner_type,
            Media.owner_id == str(owner_id)
        ).all()
    
    def update(self, media: Media) -> Media:
        self.db.commit()
        self.db.refresh(media)
        return media
    
    def delete(self, media_id: UUID) -> bool:
        media = self.get_by_id(media_id)
        if media:
            self.db.delete(media)
            self.db.commit()
            return True
        return False
    
    def update_privacy(self, media_id: UUID, privacy_level: str) -> Optional[Media]:
        media = self.get_by_id(media_id)
        if media:
            media.privacy_level = privacy_level
            self.db.commit()
            self.db.refresh(media)
            return media
        return None