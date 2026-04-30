import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ajouter le dossier Backend au path pour importer les modules app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer la config de l'app pour récupérer DATABASE_URL
from app.config import settings

# Importer Base et TOUS les modèles pour que Alembic les détecte
from app.db.base import Base
from app.models.user import User
from app.models.person import Person
from app.models.filiation import Filiation
from app.models.union import Union
from app.models.event import Event
from app.models.media import Media
from app.models.access_control import AccessControl
from app.models.tag import Tag

# Config Alembic
config = context.config

# Surcharger l'URL avec celle de l'application (lit les variables d'env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurer les logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées cibles pour la détection automatique des changements
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Mode offline : génère le SQL sans connexion à la BDD.
    Utile pour générer des scripts à exécuter manuellement.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Mode online : applique les migrations directement sur la BDD.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # Détecte les changements de type de colonne
            compare_server_default=True,  # Détecte les changements de valeur par défaut
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
