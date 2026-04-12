from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.db.session import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialise la base de données :
    - Crée les tables
    - Crée un utilisateur admin par défaut
    """
    logger.info("Initializing database...")
    
    # Créer les tables
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")
    
    # Créer un utilisateur admin
    db = SessionLocal()
    try:
        _create_admin_user(db)
        _create_demo_data(db)
    finally:
        db.close()
    
    logger.info("Database initialization complete!")


def _create_admin_user(db: Session) -> None:
    """Crée un utilisateur admin par défaut si aucun n'existe"""
    admin_email = "admin@genealogie.com"
    admin_password = "Admin123!"
    
    # Vérifier si un admin existe déjà
    existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if existing_admin:
        logger.info(f"Admin user already exists: {existing_admin.email}")
        return
    
    # Créer l'admin
    admin = User(
        email=admin_email,
        password_hash=get_password_hash(admin_password),
        first_name="Admin",
        last_name="Genealogie",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    
    db.add(admin)
    db.commit()
    
    logger.info(f"✅ Admin user created: {admin_email} / {admin_password}")
    logger.info("⚠️  Please change the default password on first login!")


def _create_demo_data(db: Session) -> None:
    """Crée des données de démonstration (optionnel)"""
    # Vérifier si des données existent déjà
    person_count = db.execute(text("SELECT COUNT(*) FROM persons")).scalar()
    
    if person_count > 0:
        logger.info(f"Demo data already exists ({person_count} persons)")
        return
    
    logger.info("Creating demo data...")
    
    # Ici, tu peux ajouter des données de démonstration
    # Exemple : créer quelques personnes factices
    
    # Cette partie est optionnelle - tu peux la commenter
    pass


def reset_db() -> None:
    """
    Réinitialise complètement la base de données (⚠️ DESTRUCTIF)
    Utile pour les tests ou le développement
    """
    logger.warning("⚠️  Resetting database - ALL DATA WILL BE LOST!")
    
    from app.db.base import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database reset complete")