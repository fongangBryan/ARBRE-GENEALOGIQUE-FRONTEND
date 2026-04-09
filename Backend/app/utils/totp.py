import pyotp
import qrcode
from io import BytesIO
import base64

def generate_2fa_secret() -> str:
    """Generate a new TOTP secret"""
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str, issuer: str = "GenealogieApp") -> str:
    """Get TOTP URI for QR code generation"""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def verify_2fa_token(secret: str, token: str) -> bool:
    """Verify a TOTP token"""
    if not secret or not token:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

def generate_qr_code_base64(uri: str) -> str:
    """Generate QR code as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()