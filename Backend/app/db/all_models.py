# Ce fichier importe tous les modèles pour que SQLAlchemy
# les enregistre dans Base.metadata avant create_all()
# Importer ce fichier AVANT d'appeler Base.metadata.create_all()

from app.models.user import User
from app.models.person import Person
from app.models.filiation import Filiation
from app.models.union import Union
from app.models.event import Event
from app.models.media import Media
from app.models.access_control import AccessControl
from app.models.tag import Tag, PersonTagHistory
