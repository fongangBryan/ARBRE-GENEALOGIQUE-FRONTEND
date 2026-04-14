# Application d'Arbre Généalogique

## Présentation générale

Application web complète pour la création et la gestion d'arbres généalogiques avec support des générations, gestion des médias, contrôles de confidentialité et visualisation interactive. L'application permet aux utilisateurs de documenter leurs histoires familiales, gérer les relations et contrôler les accès selon les branches et les individus.

## Stack technique

### Backend

- **FastAPI** - Framework web Python haute performance avec documentation OpenAPI automatique
- **SQLAlchemy 2.0** - Toolkit SQL avec typage moderne et gestion des relations
- **PostgreSQL** - Base de données principale avec capacités de recherche full-text
- **Alembic** - Gestion des migrations de base de données
- **JWT** - Authentification par token avec rotation des refresh tokens
- **Pydantic Settings** - Configuration multi-environnements

### Frontend

- **Angular** - Framework frontend professionnel
- **TypeScript** - Développement JavaScript typé
- **Angular Material** - Bibliothèque de composants UI

## Prérequis

- Python 3.11 ou supérieur
- Node.js 18 ou supérieur avec npm
- PostgreSQL 15 ou supérieur
- Docker et Docker Compose (optionnel, pour déploiement conteneurisé)
- Stockage S3 compatible (MinIO pour développement, AWS S3 pour production)

## Installation

### Installation pour développement local

**Backend**

```bash
# Cloner le dépôt
git clone https://github.com/fongangBryan/ARBRE-GENEALOGIQUE-FRONTEND.git
cd family-tree/backend

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Copier la configuration d'environnement
cp .env.example .env

# Démarrer le serveur de développement
uvicorn app.main:app --reload
```

**Frontend**

## Installer les dépendances

npm install

## Démarrer le serveur de développement

npm start
