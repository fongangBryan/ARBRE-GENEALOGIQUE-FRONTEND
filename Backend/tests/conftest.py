import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "Test123!",
        "first_name": "Test",
        "last_name": "User",
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _register_and_get_token(client, email: str, password: str) -> str:
    data = {"email": email, "password": password, "first_name": "Test", "last_name": "User"}
    resp = client.post("/api/v1/auth/register", json=data)
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    return resp.json()["access_token"]


def _set_role(email: str, role: UserRole) -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = role
            db.commit()
    finally:
        db.close()


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ── Role fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def editor_token(client):
    """Token JWT d'un utilisateur EDITOR (rôle par défaut)."""
    email, password = "editor@test.com", "Editor123!"
    _register_and_get_token(client, email, password)
    return _login(client, email, password)


@pytest.fixture
def admin_token(client):
    """Token JWT d'un utilisateur ADMIN."""
    email, password = "admin@test.com", "Admin123!"
    _register_and_get_token(client, email, password)
    _set_role(email, UserRole.ADMIN)
    return _login(client, email, password)


@pytest.fixture
def reader_token(client):
    """Token JWT d'un utilisateur READER."""
    email, password = "reader@test.com", "Reader123!"
    _register_and_get_token(client, email, password)
    _set_role(email, UserRole.READER)
    return _login(client, email, password)


@pytest.fixture
def auth_headers(editor_token):
    return {"Authorization": f"Bearer {editor_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def reader_headers(reader_token):
    return {"Authorization": f"Bearer {reader_token}"}


# ── Data fixtures ──────────────────────────────────────────────────────────────

SAMPLE_PERSON = {
    "first_name": "Jean",
    "last_name": "Dupont",
    "gender": "male",
    "birth_date": "1990-01-15",
    "birth_place": "Paris",
    "is_living": True,
    "privacy_level": "private",
}


@pytest.fixture
def created_person(client, auth_headers):
    """Crée une personne et retourne sa réponse JSON."""
    resp = client.post("/api/v1/persons/", json=SAMPLE_PERSON, headers=auth_headers)
    assert resp.status_code == 201, f"Person creation failed: {resp.text}"
    return resp.json()
