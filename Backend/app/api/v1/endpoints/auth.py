from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, TokenRefresh, LoginResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService  # NOUVEAU
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.config import settings
from app.core.exceptions import ConflictException, AuthenticationException  # NOUVEAU
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    user_service = UserService(db)  # NOUVEAU
    
    # Vérifier si l'utilisateur existe déjà
    existing = user_service.get_by_email(user_data.email)
    if existing:
        raise ConflictException("Email already registered")  # MODIFIÉ
    
    user = auth_service.register(user_data)
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=LoginResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    
    try:
        user, requires_2fa = auth_service.authenticate(
            user_data.email, 
            user_data.password,
            user_data.two_factor_code if user_data.two_factor_code else None
        )
    except Exception as e:
        raise AuthenticationException(detail=str(e))  # MODIFIÉ
    
    if requires_2fa:
        return LoginResponse(
            access_token="",
            refresh_token="",
            requires_2fa=True,
            user_id=str(user.id)
        )
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_2fa=False
    )

@router.post("/refresh", response_model=Token)
def refresh_token(refresh_data: TokenRefresh, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_data.refresh_token)
    except Exception:
        raise AuthenticationException(detail="Invalid refresh token")
    
    if payload.get("type") != "refresh":
        raise AuthenticationException(detail="Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException(detail="Invalid token")
    
    user_service = UserService(db)  # NOUVEAU
    user = user_service.get_by_id(user_id)
    
    if not user or not user.is_active:
        raise AuthenticationException(detail="User not found")
    
    new_access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)

@router.post("/setup-2fa")
def setup_two_factor(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.setup_two_factor(current_user)

@router.post("/verify-2fa")
def verify_two_factor(
    token: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.verify_two_factor(current_user, token)

@router.post("/logout")
def logout(current_user = Depends(get_current_user)):
    return {"message": "Logged out successfully"}