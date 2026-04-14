from sqlalchemy.orm import Session
from typing import Dict, Any, List
from uuid import UUID
import json
import csv
from io import StringIO
from datetime import datetime

from app.models.user import User
from app.models.person import Person
from app.models.relationship import Relationship
from app.models.event import Event
from app.models.media import Media
from app.repositories.user_repository import UserRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.repositories.event_repository import EventRepository
from app.repositories.media_repository import MediaRepository


class ExportService:
    """Service d'export des données (JSON, GEDCOM, CSV)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.person_repo = PersonRepository(db)
        self.relationship_repo = RelationshipRepository(db)
        self.event_repo = EventRepository(db)
        self.media_repo = MediaRepository(db)
    
    def export_to_json(self) -> Dict[str, Any]:
        """
        Exporte toutes les données de l'application au format JSON.
        """
        # Récupérer toutes les données
        users = self.user_repo.get_all()
        persons = self.person_repo.get_all()
        relationships = self.relationship_repo.get_all()
        events = self.event_repo.get_all()
        medias = self.media_repo.get_all()
        
        # Construire l'objet d'export
        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "application": "Genealogie App",
            "data": {
                "users": [
                    {
                        "id": str(u.id),
                        "email": u.email,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "role": u.role.value if u.role else None,
                        "is_active": u.is_active,
                        "is_2fa_enabled": u.is_2fa_enabled,
                        "created_at": u.created_at.isoformat() if u.created_at else None,
                        "last_login": u.last_login.isoformat() if u.last_login else None
                    }
                    for u in users
                ],
                "persons": [
                    {
                        "id": str(p.id),
                        "first_name": p.first_name,
                        "last_name": p.last_name,
                        "maiden_name": p.maiden_name,
                        "gender": p.gender.value if p.gender else None,
                        "birth_date": p.birth_date,
                        "birth_place": p.birth_place,
                        "death_date": p.death_date,
                        "death_place": p.death_place,
                        "is_living": p.is_living,
                        "biography": p.biography,
                        "occupation": p.occupation,
                        "nationality": p.nationality,
                        "privacy_level": p.privacy_level.value if p.privacy_level else None,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    }
                    for p in persons
                ],
                "relationships": [
                    {
                        "id": str(r.id),
                        "type": r.type.value if r.type else None,
                        "person_id_1": str(r.person_id_1),
                        "person_id_2": str(r.person_id_2),
                        "child_type": r.child_type.value if r.child_type else None,
                        "marriage_date": r.marriage_date,
                        "marriage_place": r.marriage_place,
                        "divorce_date": r.divorce_date,
                        "meta": r.meta
                    }
                    for r in relationships
                ],
                "events": [
                    {
                        "id": str(e.id),
                        "person_id": str(e.person_id),
                        "event_type": e.event_type.value if e.event_type else None,
                        "date_start": e.date_start,
                        "date_end": e.date_end,
                        "place": e.place,
                        "description": e.description,
                        "meta": e.meta
                    }
                    for e in events
                ],
                "media": [
                    {
                        "id": str(m.id),
                        "owner_type": m.owner_type,
                        "owner_id": m.owner_id,
                        "media_type": m.media_type.value if m.media_type else None,
                        "privacy_level": m.privacy_level,
                        "original_filename": m.original_filename,
                        "mime_type": m.mime_type,
                        "file_size": m.file_size,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in medias
                ]
            }
        }
        
        return export_data
    
    def export_to_gedcom(self) -> str:
        """
        Exporte les données au format GEDCOM 5.5.1.
        C'est une version simplifiée - à enrichir selon les besoins.
        """
        persons = self.person_repo.get_all()
        relationships = self.relationship_repo.get_all()
        
        gedcom_lines = []
        
        # En-tête GEDCOM
        gedcom_lines.append("0 HEAD")
        gedcom_lines.append("1 SOUR GENEALOGIE_APP")
        gedcom_lines.append("2 VERS 1.0")
        gedcom_lines.append("1 GEDC")
        gedcom_lines.append("2 VERS 5.5.1")
        gedcom_lines.append("1 CHAR UTF-8")
        gedcom_lines.append(f"1 DATE {datetime.utcnow().strftime('%d %b %Y')}")
        
        # Enregistrements des personnes
        person_refs = {}
        for idx, person in enumerate(persons, start=1):
            ref = f"P{idx:05d}"
            person_refs[person.id] = ref
            
            gedcom_lines.append(f"0 @{ref}@ INDI")
            
            # Nom
            name_parts = []
            if person.first_name:
                name_parts.append(person.first_name)
            if person.last_name:
                name_parts.append(f"/{person.last_name}/")
            if name_parts:
                gedcom_lines.append(f"1 NAME {' '.join(name_parts)}")
            
            # Sexe
            if person.gender:
                sex_code = "M" if person.gender.value == "male" else "F" if person.gender.value == "female" else "U"
                gedcom_lines.append(f"1 SEX {sex_code}")
            
            # Naissance
            if person.birth_date or person.birth_place:
                gedcom_lines.append("1 BIRT")
                if person.birth_date:
                    gedcom_lines.append(f"2 DATE {person.birth_date}")
                if person.birth_place:
                    gedcom_lines.append(f"2 PLAC {person.birth_place}")
            
            # Décès
            if person.death_date or person.death_place or not person.is_living:
                gedcom_lines.append("1 DEAT")
                if person.death_date:
                    gedcom_lines.append(f"2 DATE {person.death_date}")
                if person.death_place:
                    gedcom_lines.append(f"2 PLAC {person.death_place}")
                if person.is_living:
                    gedcom_lines.append("2 Y")
            
            # Profession
            if person.occupation:
                gedcom_lines.append(f"1 OCCU {person.occupation}")
        
        # Enregistrements des familles
        family_refs = {}
        family_counter = 1
        
        for rel in relationships:
            if rel.type.value == "couple":
                family_ref = f"F{family_counter:05d}"
                family_refs[rel.id] = family_ref
                family_counter += 1
                
                gedcom_lines.append(f"0 @{family_ref}@ FAM")
                
                # Mari
                if rel.person_id_1 in person_refs:
                    gedcom_lines.append(f"1 HUSB @{person_refs[rel.person_id_1]}@")
                if rel.person_id_2 in person_refs:
                    gedcom_lines.append(f"1 WIFE @{person_refs[rel.person_id_2]}@")
                
                # Date de mariage
                if rel.marriage_date:
                    gedcom_lines.append("1 MARR")
                    gedcom_lines.append(f"2 DATE {rel.marriage_date}")
                    if rel.marriage_place:
                        gedcom_lines.append(f"2 PLAC {rel.marriage_place}")
                
                # Divorce
                if rel.divorce_date:
                    gedcom_lines.append("1 DIV")
                    gedcom_lines.append(f"2 DATE {rel.divorce_date}")
        
        # Lier les enfants aux familles
        for rel in relationships:
            if rel.type.value == "parent_child":
                # Trouver la famille du couple
                for fam_rel in relationships:
                    if fam_rel.type.value == "couple":
                        if (fam_rel.person_id_1 == rel.person_id_1 or fam_rel.person_id_2 == rel.person_id_1):
                            if fam_rel.id in family_refs:
                                family_ref = family_refs[fam_rel.id]
                                if rel.person_id_2 in person_refs:
                                    # Vérifier si l'enfant n'est pas déjà lié
                                    gedcom_lines.append(f"0 @{family_ref}@ FAM")
                                    gedcom_lines.append(f"1 CHIL @{person_refs[rel.person_id_2]}@")
                                break
        
        # Fin du fichier
        gedcom_lines.append("0 TRLR")
        
        return "\n".join(gedcom_lines)
    
    def export_users_to_csv(self) -> str:
        """
        Exporte la liste des utilisateurs au format CSV.
        """
        users = self.user_repo.get_all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            "ID", "Email", "Prénom", "Nom", "Rôle", 
            "Actif", "2FA Activé", "Date création", "Dernière connexion"
        ])
        
        # Données
        for user in users:
            writer.writerow([
                str(user.id),
                user.email,
                user.first_name or "",
                user.last_name or "",
                user.role.value if user.role else "",
                "Oui" if user.is_active else "Non",
                "Oui" if user.is_2fa_enabled else "Non",
                user.created_at.isoformat() if user.created_at else "",
                user.last_login.isoformat() if user.last_login else ""
            ])
        
        return output.getvalue()
    
    def export_persons_to_csv(self) -> str:
        """
        Exporte la liste des personnes au format CSV.
        """
        persons = self.person_repo.get_all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            "ID", "Prénom", "Nom", "Nom jeune fille", "Genre",
            "Date naissance", "Lieu naissance", "Date décès", "Lieu décès",
            "Vivant", "Profession", "Nationalité", "Niveau confidentialité"
        ])
        
        # Données
        for person in persons:
            writer.writerow([
                str(person.id),
                person.first_name,
                person.last_name,
                person.maiden_name or "",
                person.gender.value if person.gender else "",
                person.birth_date or "",
                person.birth_place or "",
                person.death_date or "",
                person.death_place or "",
                "Oui" if person.is_living else "Non",
                person.occupation or "",
                person.nationality or "",
                person.privacy_level.value if person.privacy_level else ""
            ])
        
        return output.getvalue()