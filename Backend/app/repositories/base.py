from sqlalchemy.orm import Session
from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID

from app.db.base import Base

# Type générique pour les modèles
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Repository générique avec les opérations CRUD de base.
    Tous les autres repositories héritent de cette classe.
    """
    
    def __init__(self, db: Session, model_class: Type[ModelType]):
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Récupérer une entité par son ID"""
        return self.db.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Récupérer plusieurs entités avec pagination"""
        return self.db.query(self.model_class).offset(skip).limit(limit).all()
    
    def create(self, entity: ModelType) -> ModelType:
        """Créer une nouvelle entité"""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update(self, entity: ModelType) -> ModelType:
        """Mettre à jour une entité existante"""
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def delete(self, id: UUID) -> bool:
        """Supprimer une entité par son ID"""
        entity = self.get_by_id(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False
    
    def exists(self, id: UUID) -> bool:
        """Vérifier si une entité existe"""
        return self.get_by_id(id) is not None
    
    def count(self) -> int:
        """Compter le nombre total d'entités"""
        return self.db.query(self.model_class).count()