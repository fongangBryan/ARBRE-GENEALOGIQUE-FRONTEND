"""
Constantes globales de l'application
Centralise toutes les valeurs configurables
"""

# ============ MÉDIAS ============
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
MAX_UPLOAD_SIZE_MB = 20

ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png", 
    "image/webp",
    "image/gif"
]

ALLOWED_DOCUMENT_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_DOCUMENT_TYPES

# Tailles des miniatures
THUMBNAIL_SIZES = {
    "small": (100, 100),
    "medium": (200, 200),
    "large": (400, 400)
}

# ============ ARBRE GÉNÉALOGIQUE ============
MAX_TREE_DEPTH = 8  # Profondeur maximale de l'arbre
MAX_NEIGHBOR_RADIUS = 3  # Rayon maximum pour les voisins
DEFAULT_TREE_DEPTH = 2
DEFAULT_ANCESTORS_GENERATIONS = 5
DEFAULT_DESCENDANTS_GENERATIONS = 3

# ============ CONFIDENTIALITÉ ============
PRIVACY_LEVELS = ["public", "family", "private"]
DEFAULT_PRIVACY_LEVEL = "private"

# Pour les personnes vivantes, masquer automatiquement
HIDE_LIVING_PERSON_DETAILS = True
LIVING_PERSON_VISIBLE_FIELDS = ["first_name", "last_name", "birth_year_only"]

# ============ AUTHENTIFICATION ============
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# 2FA
TOTP_VALIDITY_WINDOW = 30  # secondes
TOTP_ISSUER_NAME = "GenealogieApp"

# ============ PAGINATION ============
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============ RECHERCHE ============
MIN_SEARCH_QUERY_LENGTH = 2
MAX_SEARCH_RESULTS = 100

# ============ EXPORT ============
MAX_EXPORT_RECORDS = 10000
SUPPORTED_EXPORT_FORMATS = ["json", "gedcom", "csv"]

# ============ RÔLES ============
USER_ROLES = {
    "admin": "Administrateur (accès total)",
    "editor": "Éditeur (peut créer et modifier)",
    "reader": "Lecteur (consultation uniquement)"
}

# ============ TYPES D'ÉVÉNEMENTS ============
EVENT_TYPES = [
    "birth", "death", "marriage", "divorce",
    "baptism", "burial", "education", "employment",
    "residence", "military_service", "custom"
]

# ============ TYPES DE RELATIONS ============
RELATIONSHIP_TYPES = {
    "parent_child": "Parent ↔ Enfant",
    "couple": "Couple / Mariage"
}

PARENT_CHILD_TYPES = {
    "biological": "Biologique",
    "adoptive": "Adoptif",
    "guardian": "Tuteur légal",
    "step": "Beau-parent / Belle-mère"
}

# ============ LIMITES ============
MAX_BIOGRAPHY_LENGTH = 5000
MAX_NOTE_LENGTH = 2000
MAX_PLACE_NAME_LENGTH = 255
MAX_PERSON_NAME_LENGTH = 100