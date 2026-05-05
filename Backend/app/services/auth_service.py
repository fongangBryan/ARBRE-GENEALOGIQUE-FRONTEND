from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth import UserRegister
from app.core.security import verify_password, get_password_hash, create_email_token, decode_email_token
from app.utils.totp import generate_2fa_secret, get_totp_uri, generate_qr_code_base64, verify_2fa_token
from app.utils.email import send_verification_email, send_reset_password_email
from app.services.user_service import UserService
from app.core.exceptions import ConflictException, AuthenticationException
from app.config import settings

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)  # MODIFIÉ
    
    def _log(self, user_id, action: str, resource_type: str = None, resource_id: str = None, detail: str = None):
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            detail=detail,
        )
        self.db.add(entry)

    def register(self, user_data: UserRegister) -> User:
        existing = self.user_service.get_by_email(user_data.email)
        if existing:
            raise ConflictException("Email already registered")

        user = self.user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        # Send verification email
        token = create_email_token(
            str(user.id), "email_verification",
            timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
        )
        send_verification_email(user.email, token)
        self._log(user.id, "register", "user", user.id)
        self.db.commit()
        return user

    def verify_email(self, token: str) -> User:
        user_id = decode_email_token(token, "email_verification")
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Email déjà vérifié")
        user.is_verified = True
        self._log(user.id, "email_verified", "user", user.id)
        self.db.commit()
        return user

    def resend_verification(self, user: User) -> None:
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Email déjà vérifié")
        token = create_email_token(
            str(user.id), "email_verification",
            timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
        )
        send_verification_email(user.email, token)

    def forgot_password(self, email: str) -> None:
        user = self.user_service.get_by_email(email)
        if not user:
            return  # Do not reveal whether email exists
        token = create_email_token(
            str(user.id), "password_reset",
            timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
        )
        send_reset_password_email(user.email, token)

    def reset_password(self, token: str, new_password: str) -> None:
        user_id = decode_email_token(token, "password_reset")
        user = self.user_service.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        user.password_hash = get_password_hash(new_password)
        self._log(user.id, "password_reset", "user", user.id)
        self.db.commit()
    
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
        
        user.last_login = datetime.now(timezone.utc)
        self._log(user.id, "login", "user", user.id)
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
            raise HTTPException(status_code=400, detail="2FA not initialized. Call /setup-2fa first.")

        if not verify_2fa_token(user.temp_2fa_secret, token):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")

        user.is_2fa_enabled = True
        user.totp_secret = user.temp_2fa_secret
        user.temp_2fa_secret = None
        self.db.commit()
        return {"message": "2FA enabled successfully"}

    def disable_two_factor(self, user: User, token: str):
        if not user.is_2fa_enabled:
            raise HTTPException(status_code=400, detail="2FA is not enabled on this account")

        if not verify_2fa_token(user.totp_secret, token):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")

        user.is_2fa_enabled = False
        user.totp_secret = None
        user.temp_2fa_secret = None
        self.db.commit()
        return {"message": "2FA disabled successfully"}