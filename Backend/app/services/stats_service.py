from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.models.user import User, UserRole
from app.models.person import Person, PrivacyLevel
from app.models.relationship import Relationship, RelationshipType
from app.models.event import Event
from app.models.media import Media
from app.repositories.user_repository import UserRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.repositories.event_repository import EventRepository
from app.repositories.media_repository import MediaRepository


class StatsService:
    """Service de statistiques pour l'administration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.person_repo = PersonRepository(db)
        self.relationship_repo = RelationshipRepository(db)
        self.event_repo = EventRepository(db)
        self.media_repo = MediaRepository(db)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Statistiques globales de l'application.
        """
        # Compter les entités
        total_users = self.db.query(User).count()
        total_active_users = self.db.query(User).filter(User.is_active == True).count()
        total_persons = self.db.query(Person).count()
        total_relationships = self.db.query(Relationship).count()
        total_events = self.db.query(Event).count()
        total_media = self.db.query(Media).count()
        
        # Compter par niveau de confidentialité
        public_persons = self.db.query(Person).filter(Person.privacy_level == PrivacyLevel.PUBLIC).count()
        family_persons = self.db.query(Person).filter(Person.privacy_level == PrivacyLevel.FAMILY).count()
        private_persons = self.db.query(Person).filter(Person.privacy_level == PrivacyLevel.PRIVATE).count()
        
        # Compter par type de relation
        parent_child_rels = self.db.query(Relationship).filter(Relationship.type == RelationshipType.PARENT_CHILD).count()
        couple_rels = self.db.query(Relationship).filter(Relationship.type == RelationshipType.COUPLE).count()
        
        # Compter par type d'événement
        events_by_type = {}
        event_types = self.db.query(Event.event_type, func.count(Event.id)).group_by(Event.event_type).all()
        for event_type, count in event_types:
            events_by_type[event_type.value if hasattr(event_type, 'value') else event_type] = count
        
        # Compter par rôle utilisateur
        users_by_role = {}
        role_counts = self.db.query(User.role, func.count(User.id)).group_by(User.role).all()
        for role, count in role_counts:
            users_by_role[role.value if hasattr(role, 'value') else role] = count
        
        return {
            "users": {
                "total": total_users,
                "active": total_active_users,
                "by_role": users_by_role
            },
            "persons": {
                "total": total_persons,
                "by_privacy": {
                    "public": public_persons,
                    "family": family_persons,
                    "private": private_persons
                }
            },
            "relationships": {
                "total": total_relationships,
                "parent_child": parent_child_rels,
                "couple": couple_rels
            },
            "events": {
                "total": total_events,
                "by_type": events_by_type
            },
            "media": {
                "total": total_media
            }
        }
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        Statistiques détaillées des utilisateurs.
        """
        # Nouveaux utilisateurs par mois (derniers 12 mois)
        now = datetime.utcnow()
        months_ago = now - timedelta(days=365)
        
        monthly_signups = self.db.query(
            func.date_trunc('month', User.created_at).label('month'),
            func.count(User.id).label('count')
        ).filter(User.created_at >= months_ago).group_by('month').order_by('month').all()
        
        # Utilisateurs par rôle
        users_by_role = self.db.query(User.role, func.count(User.id)).group_by(User.role).all()
        
        # Utilisateurs avec 2FA
        users_with_2fa = self.db.query(User).filter(User.is_2fa_enabled == True).count()
        
        # Derniers utilisateurs actifs
        last_active = self.db.query(User).filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).limit(10).all()
        
        return {
            "total_users": self.db.query(User).count(),
            "users_with_2fa": users_with_2fa,
            "users_by_role": [
                {"role": role.value if hasattr(role, 'value') else role, "count": count}
                for role, count in users_by_role
            ],
            "monthly_signups": [
                {"month": month.strftime('%Y-%m'), "count": count}
                for month, count in monthly_signups
            ],
            "last_active_users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "name": f"{u.first_name or ''} {u.last_name or ''}".strip(),
                    "last_login": u.last_login.isoformat() if u.last_login else None
                }
                for u in last_active
            ]
        }
    
    def get_person_stats(self) -> Dict[str, Any]:
        """
        Statistiques détaillées des personnes.
        """
        # Personnes par génération (approximatif via année de naissance)
        persons_with_birth = self.db.query(Person).filter(Person.birth_date.isnot(None)).all()
        
        generations = {}
        for person in persons_with_birth:
            try:
                # Extraire l'année
                year_str = person.birth_date.split('-')[0]
                year = int(year_str)
                decade = (year // 10) * 10
                decade_key = f"{decade}s"
                generations[decade_key] = generations.get(decade_key, 0) + 1
            except (ValueError, AttributeError):
                pass
        
        # Personnes vivantes vs décédées
        living_persons = self.db.query(Person).filter(Person.is_living == True).count()
        deceased_persons = self.db.query(Person).filter(Person.is_living == False).count()
        
        # Personnes par niveau de confidentialité
        privacy_stats = self.db.query(
            Person.privacy_level, func.count(Person.id)
        ).group_by(Person.privacy_level).all()
        
        # Personnes par sexe
        gender_stats = self.db.query(
            Person.gender, func.count(Person.id)
        ).group_by(Person.gender).all()
        
        # Top lieux de naissance
        top_birth_places = self.db.query(
            Person.birth_place, func.count(Person.id)
        ).filter(Person.birth_place.isnot(None)).group_by(Person.birth_place).order_by(func.count(Person.id).desc()).limit(10).all()
        
        return {
            "total_persons": self.db.query(Person).count(),
            "living": living_persons,
            "deceased": deceased_persons,
            "by_gender": [
                {"gender": gender.value if hasattr(gender, 'value') else str(gender), "count": count}
                for gender, count in gender_stats if gender
            ],
            "by_privacy": [
                {"level": level.value if hasattr(level, 'value') else str(level), "count": count}
                for level, count in privacy_stats if level
            ],
            "by_birth_decade": generations,
            "top_birth_places": [
                {"place": place, "count": count}
                for place, count in top_birth_places if place
            ]
        }
    
    def get_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Statistiques d'activité récente.
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Nouvelles personnes créées
        new_persons = self.db.query(Person).filter(Person.created_at >= since_date).count()
        
        # Nouvelles relations créées
        new_relationships = self.db.query(Relationship).filter(Relationship.created_at >= since_date).count()
        
        # Nouveaux événements créés
        new_events = self.db.query(Event).filter(Event.created_at >= since_date).count()
        
        # Nouveaux médias uploadés
        new_media = self.db.query(Media).filter(Media.created_at >= since_date).count()
        
        # Nouveaux utilisateurs
        new_users = self.db.query(User).filter(User.created_at >= since_date).count()
        
        return {
            "period_days": days,
            "since_date": since_date.isoformat(),
            "new_persons": new_persons,
            "new_relationships": new_relationships,
            "new_events": new_events,
            "new_media": new_media,
            "new_users": new_users
        }
    
    def get_tree_stats(self, root_person_id: str = None) -> Dict[str, Any]:
        """
        Statistiques sur l'arbre généalogique.
        """
        # Profondeur maximale de l'arbre
        # Cette requête peut être complexe, on fait une approximation
        
        # Nombre de générations (via relations parent-enfant)
        # Requête récursive PostgreSQL pour trouver la profondeur maximale
        max_depth = 0
        try:
            # Compter le nombre de générations maximum
            result = self.db.execute(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT person_id_2 as person_id, 1 as depth
                    FROM relationships
                    WHERE type = 'parent_child'
                    
                    UNION ALL
                    
                    SELECT r.person_id_2, a.depth + 1
                    FROM relationships r
                    INNER JOIN ancestors a ON r.person_id_1 = a.person_id
                    WHERE r.type = 'parent_child'
                )
                SELECT MAX(depth) FROM ancestors
                """
            ).scalar()
            max_depth = result or 0
        except Exception:
            pass
        
        return {
            "max_depth_generations": max_depth,
            "total_persons": self.db.query(Person).count(),
            "total_relationships": self.db.query(Relationship).count(),
            "parent_child_relationships": self.db.query(Relationship).filter(Relationship.type == RelationshipType.PARENT_CHILD).count(),
            "couple_relationships": self.db.query(Relationship).filter(Relationship.type == RelationshipType.COUPLE).count(),
            "persons_without_parents": self._count_orphans(),
            "persons_without_children": self._count_without_children()
        }
    
    def _count_orphans(self) -> int:
        """Compte les personnes sans parents connus"""
        persons = self.db.query(Person.id).all()
        orphans = 0
        
        for person in persons:
            parent_count = self.db.query(Relationship).filter(
                Relationship.type == RelationshipType.PARENT_CHILD,
                Relationship.person_id_2 == person.id
            ).count()
            if parent_count == 0:
                orphans += 1
        
        return orphans
    
    def _count_without_children(self) -> int:
        """Compte les personnes sans enfants connus"""
        persons = self.db.query(Person.id).all()
        without_children = 0
        
        for person in persons:
            child_count = self.db.query(Relationship).filter(
                Relationship.type == RelationshipType.PARENT_CHILD,
                Relationship.person_id_1 == person.id
            ).count()
            if child_count == 0:
                without_children += 1
        
        return without_children