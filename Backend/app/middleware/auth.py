from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware léger — la vérification du token est gérée par les dépendances
    FastAPI (get_current_user). Ce middleware peut enrichir les logs ou ajouter
    des headers globaux si besoin.
    """

    EXEMPT_PATHS = {
        "/",
        "/health",
        "/api/docs",
        "/api/redoc",
        "/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response
