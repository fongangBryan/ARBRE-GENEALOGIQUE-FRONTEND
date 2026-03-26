"""
Tests fonctionnels — Auth, Persons, Relationships.
Couvrent les règles métier critiques du cahier des charges.
"""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DEBUG", "true")

from app.db.base import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.person import Person, PrivacyLevel, Sex
from app.models.relationship import Relationship, RelationshipType
from app.models.tag_and_acl import Tag
from app.core.security import get_password_hash, create_access_token

# ── Fixtures ─────────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="module")
def db_session(engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_user(db_session):
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("Admin1234!"),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def editor_user(db_session):
    user = User(
        email="editor@test.com",
        password_hash=get_password_hash("Editor1234!"),
        first_name="Editor",
        last_name="Test",
        role=UserRole.EDITOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def reader_user(db_session):
    user = User(
        email="reader@test.com",
        password_hash=get_password_hash("Reader1234!"),
        first_name="Reader",
        last_name="Test",
        role=UserRole.READER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}

