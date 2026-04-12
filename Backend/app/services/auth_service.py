from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Tuple, Optional

from app.models.user import User
from app.schemas.auth import UserRegister
from app.core.security import verify_password, get_password_hash
from app.utils.totp import generate_2fa_secret, get_totp_uri, generate_qr_code_base64, verify_2fa_token
from app.services.user_service import UserService  # NOUVEAU
from app.core.exceptions import ConflictException, AuthenticationException  # NOUVEAU

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)  # MODIFIÉ
    
    def register(self, user_data: UserRegister) -> User:
        # Check if user exists - Utiliser UserService
        existing = self.user_service.get_by_email(user_data.email)
        if existing:
            raise ConflictException("Email already registered")
        
        # Create user - Utiliser UserService
        user = self.user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        return user
    
    def authenticate(self, email: str, password: str, two_factor_code: Optional[str] = None) -> Tuple[User, bool]:
        user = self.user_service.get_by_email(email)  # MODIFIÉ
        
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password")
        
        if not user.is_active:
            raise AuthenticationException("Account is disabled")
        
        # Check 2FA
        if user.is_2fa_enabled:
            if not two_factor_code:
                return user, True  # Requires 2FA
            
            if not verify_2fa_token(user.totp_secret, two_factor_code):
                raise AuthenticationException("Invalid 2FA code")
        
        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user, False
    
    def setup_two_factor(self, user: User):
        secret = generate_2fa_secret()
        uri = get_totp_uri(secret, user.email)
        qr_code = generate_qr_code_base64(uri)
        
        user.temp_2fa_secret = secret
        self.db.commit()
        
        return {"secret": secret, "qr_code": qr_code}
    
    def verify_two_factor(self, user: User, token: str):
        if not user.temp_2fa_secret:
            raise HTTPException(status_code=400, detail="2FA not initialized")
        
        if verify_2fa_token(user.temp_2fa_secret, token):
            user.is_2fa_enabled = True
            user.totp_secret = user.temp_2fa_secret
            user.temp_2fa_secret = None
            self.db.commit()
            return {"message": "2FA enabled successfully"}
        
        raise HTTPException(status_code=400, detail="Invalid token")