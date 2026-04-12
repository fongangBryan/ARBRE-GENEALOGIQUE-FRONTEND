from fastapi import HTTPException, status
from typing import Optional, Any


class AppException(HTTPException):
    """Exception de base pour l'application"""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        headers: Optional[dict] = None,
        context: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.context = context or {}


class NotFoundException(AppException):
    """Ressource non trouvée (404)"""
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} with id '{resource_id}' not found"
        )


class PermissionDeniedException(AppException):
    """Accès non autorisé (403)"""
    def __init__(self, action: str, resource_type: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {action} this {resource_type}"
        )


class ValidationException(AppException):
    """Données invalides (422)"""
    def __init__(self, field: str, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error on '{field}': {message}"
        )


class ConflictException(AppException):
    """Conflit (409) - email déjà utilisé, relation déjà existante, etc."""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message
        )


class CycleDetectedException(AppException):
    """Cycle détecté dans l'arbre généalogique (400)"""
    def __init__(self, person_name: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create relationship: would create a cycle with '{person_name}'"
        )


class AuthenticationException(AppException):
    """Authentification échouée (401)"""
    def __init__(self, detail: str = "Invalid authentication credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class RateLimitException(AppException):
    """Trop de requêtes (429)"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds",
            headers={"Retry-After": str(retry_after)}
        )