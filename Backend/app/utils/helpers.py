import re
from datetime import datetime
from typing import Optional, Tuple
from unidecode import unidecode


def parse_date_partial(date_str: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Parse une date partielle au format :
    - "2002" -> (2002, None, None)
    - "2002-03" -> (2002, 3, None)
    - "2002-03-08" -> (2002, 3, 8)
    """
    if not date_str:
        return None, None, None
    
    parts = date_str.split("-")
    
    year = int(parts[0]) if parts[0] else None
    month = int(parts[1]) if len(parts) > 1 and parts[1] else None
    day = int(parts[2]) if len(parts) > 2 and parts[2] else None
    
    return year, month, day


def format_date_partial(year: Optional[int], month: Optional[int] = None, day: Optional[int] = None) -> Optional[str]:
    """Formate une date partielle en string"""
    if not year:
        return None
    
    if day and month:
        return f"{year:04d}-{month:02d}-{day:02d}"
    elif month:
        return f"{year:04d}-{month:02d}"
    else:
        return f"{year:04d}"


def calculate_age(birth_date: Optional[str], death_date: Optional[str] = None) -> Optional[int]:
    """Calcule l'âge à partir des dates"""
    birth_year, birth_month, birth_day = parse_date_partial(birth_date)
    
    if not birth_year:
        return None
    
    # Date de référence (aujourd'hui ou date de décès)
    if death_date:
        ref_year, ref_month, ref_day = parse_date_partial(death_date)
        if not ref_year:
            return None
    else:
        now = datetime.now()
        ref_year, ref_month, ref_day = now.year, now.month, now.day
    
    age = ref_year - birth_year
    
    # Ajustement si l'anniversaire n'est pas encore passé dans l'année de référence
    if birth_month and ref_month and birth_day and ref_day:
        if ref_month < birth_month or (ref_month == birth_month and ref_day < birth_day):
            age -= 1
    elif birth_month and ref_month:
        if ref_month < birth_month:
            age -= 1
    
    return max(0, age) if age >= 0 else None


def generate_slug(text: str, max_length: int = 50) -> str:
    """Génère un slug à partir d'un texte"""
    # Convertir en ASCII
    text = unidecode(text.lower())
    # Remplacer les espaces et caractères non alphanumériques par des tirets
    slug = re.sub(r'[^a-z0-9]+', '-', text)
    # Supprimer les tirets en début et fin
    slug = slug.strip('-')
    # Limiter la longueur
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    return slug


def validate_email(email: str) -> bool:
    """Valide un email (simple)"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_html(text: Optional[str]) -> Optional[str]:
    """Nettoie le HTML pour la sécurité (supprime les balises script, etc.)"""
    if not text:
        return text
    
    import html
    # Échapper les caractères HTML
    return html.escape(text)


def truncate_text(text: Optional[str], max_length: int = 200, suffix: str = "...") -> str:
    """Tronque un texte à une longueur maximale"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def format_name(first_name: str, last_name: str, maiden_name: Optional[str] = None) -> str:
    """Formate un nom complet"""
    if maiden_name:
        return f"{last_name.upper()} {first_name} (née {maiden_name})"
    return f"{last_name.upper()} {first_name}"


def is_valid_uuid(uuid_string: str) -> bool:
    """Vérifie si une chaîne est un UUID valide"""
    import uuid
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def extract_year_from_date(date_str: Optional[str]) -> Optional[int]:
    """Extrait l'année d'une date partielle"""
    if not date_str:
        return None
    try:
        return int(date_str.split("-")[0])
    except (ValueError, IndexError):
        return None


def get_generation_from_sosa(sosa_number: int) -> int:
    """
    Calcule la génération à partir du numéro Sosa.
    Sosa 1 = génération 0
    Sosa 2,3 = génération 1
    Sosa 4-7 = génération 2
    """
    import math
    return int(math.floor(math.log2(sosa_number))) if sosa_number > 0 else 0


def build_sosa_uri(person_id: str, sosa_number: int) -> str:
    """Construit un URI Sosa pour une personne"""
    return f"sosa://{person_id}/{sosa_number}"