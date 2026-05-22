from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.config import settings
from app.core.exceptions import AuthenticationException  # NOUVEAU

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting simple (à améliorer avec Redis)
_login_attempts = {}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise AuthenticationException("Invalid authentication credentials")

def create_email_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    """Crée un token JWT pour verification email ou reset password."""
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": user_id, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_email_token(token: str, expected_type: str) -> str:
    """Décode un token JWT et retourne le user_id. Lève HTTPException si invalide."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=400, detail="Type de token incorrect")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Token invalide")
    return user_id

def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """Vérifie le rate limiting pour les tentatives de connexion"""
    from datetime import datetime
    
    now = datetime.utcnow()
    if identifier not in _login_attempts:
        _login_attempts[identifier] = []
    
    # Nettoyer les tentatives anciennes
    _login_attempts[identifier] = [
        attempt for attempt in _login_attempts[identifier]
        if (now - attempt).total_seconds() < window_minutes * 60
    ]
    
    if len(_login_attempts[identifier]) >= max_attempts:
        return False
    
    _login_attempts[identifier].append(now)
    return True