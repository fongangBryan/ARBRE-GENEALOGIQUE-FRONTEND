"""
Tests unitaires de PersonService.

Ces tests vérifient la logique métier du service (nettoyage des données,
sanitisation HTML, isolation par propriétaire, NotFoundException…) en
travaillant directement sur la couche service + repository, sans passer
par l'API HTTP.
"""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.person import Person
from app.schemas.person import PersonCreate, PersonUpdate
from app.services.person_service import PersonService
from app.core.exceptions import NotFoundException

# ── Base SQLite isolée pour les tests de service ──────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_service.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
ServiceSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Crée les tables avant chaque test, les supprime après."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = ServiceSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def service(db):
    return PersonService(db)


# ── Données de test ────────────────────────────────────────────────────────────

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()

def make_payload(**kwargs) -> PersonCreate:
    defaults = {
        "first_name":   "Jean",
        "last_name":    "Dupont",
        "gender":       "male",
        "birth_date":   "1990-01-15",
        "birth_place":  "Paris",
        "is_living":    True,
        "privacy_level": "private",
    }
    defaults.update(kwargs)
    return PersonCreate(**defaults)


# ── create_person ──────────────────────────────────────────────────────────────

class TestCreatePerson:

    def test_creates_person_with_correct_fields(self, service):
        person = service.create_person(make_payload(), created_by=USER_A)
        assert person.id is not None
        assert person.first_name == "Jean"
        assert person.last_name == "Dupont"
        assert person.created_by == USER_A

    def test_strips_whitespace_from_first_name(self, service):
        person = service.create_person(make_payload(first_name="  Alice  "), created_by=USER_A)
        assert person.first_name == "Alice"

    def test_strips_whitespace_from_last_name(self, service):
        person = service.create_person(make_payload(last_name="  Martin  "), created_by=USER_A)
        assert person.last_name == "Martin"

    def test_strips_whitespace_from_maiden_name(self, service):
        person = service.create_person(make_payload(maiden_name="  Curie  "), created_by=USER_A)
        assert person.maiden_name == "Curie"

    def test_maiden_name_none_when_not_provided(self, service):
        person = service.create_person(make_payload(), created_by=USER_A)
        assert person.maiden_name is None

    def test_sanitizes_biography_html(self, service):
        """Les balises HTML dans la biographie doivent être échappées (XSS protection)."""
        dangerous = '<script>alert("xss")</script>Marie Curie'
        person = service.create_person(make_payload(biography=dangerous), created_by=USER_A)
        assert "<script>" not in person.biography
        assert "Marie Curie" in person.biography

    def test_biography_none_when_not_provided(self, service):
        person = service.create_person(make_payload(), created_by=USER_A)
        assert person.biography is None

    def test_persists_to_database(self, service, db):
        person = service.create_person(make_payload(), created_by=USER_A)
        fetched = db.query(Person).filter(Person.id == person.id).first()
        assert fetched is not None
        assert fetched.first_name == "Jean"

    def test_sets_privacy_level(self, service):
        person = service.create_person(make_payload(privacy_level="public"), created_by=USER_A)
        assert person.privacy_level.value == "public"

    def test_creates_multiple_persons(self, service):
        p1 = service.create_person(make_payload(first_name="Alice"), created_by=USER_A)
        p2 = service.create_person(make_payload(first_name="Bob"),   created_by=USER_A)
        assert p1.id != p2.id


# ── get_person ────────────────────────────────────────────────────────────────

class TestGetPerson:

    def test_returns_person_by_id(self, service):
        created = service.create_person(make_payload(), created_by=USER_A)
        fetched  = service.get_person(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_returns_none_for_unknown_id(self, service):
        result = service.get_person(uuid.uuid4())
        assert result is None

    def test_returns_correct_person_among_many(self, service):
        p1 = service.create_person(make_payload(first_name="Alice"), created_by=USER_A)
        p2 = service.create_person(make_payload(first_name="Bob"),   created_by=USER_A)
        assert service.get_person(p1.id).first_name == "Alice"
        assert service.get_person(p2.id).first_name == "Bob"


# ── update_person ─────────────────────────────────────────────────────────────

class TestUpdatePerson:

    def test_updates_first_name(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        updated = service.update_person(p.id, PersonUpdate(first_name="Pierre"))
        assert updated.first_name == "Pierre"

    def test_updates_last_name(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        updated = service.update_person(p.id, PersonUpdate(last_name="Martin"))
        assert updated.last_name == "Martin"

    def test_updates_multiple_fields(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        updated = service.update_person(
            p.id,
            PersonUpdate(first_name="Marie", last_name="Curie", is_living=False),
        )
        assert updated.first_name == "Marie"
        assert updated.last_name == "Curie"
        assert updated.is_living is False

    def test_preserves_unmodified_fields(self, service):
        """Un champ non inclus dans le payload doit rester inchangé."""
        p = service.create_person(make_payload(birth_date="1990-01-15"), created_by=USER_A)
        updated = service.update_person(p.id, PersonUpdate(first_name="Alice"))
        assert updated.birth_date == "1990-01-15"

    def test_sanitizes_biography_on_update(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        updated = service.update_person(
            p.id, PersonUpdate(biography='<script>alert("xss")</script>Mise à jour')
        )
        assert "<script>" not in updated.biography
        assert "Mise à jour" in updated.biography

    def test_raises_not_found_for_unknown_id(self, service):
        with pytest.raises(NotFoundException):
            service.update_person(uuid.uuid4(), PersonUpdate(first_name="Ghost"))

    def test_update_persists_to_database(self, service, db):
        p = service.create_person(make_payload(), created_by=USER_A)
        service.update_person(p.id, PersonUpdate(first_name="Updated"))
        fetched = db.query(Person).filter(Person.id == p.id).first()
        assert fetched.first_name == "Updated"


# ── delete_person ─────────────────────────────────────────────────────────────

class TestDeletePerson:

    def test_deletes_existing_person(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        result = service.delete_person(p.id)
        assert result is True

    def test_deleted_person_no_longer_exists(self, service):
        p = service.create_person(make_payload(), created_by=USER_A)
        service.delete_person(p.id)
        assert service.get_person(p.id) is None

    def test_returns_false_for_unknown_id(self, service):
        result = service.delete_person(uuid.uuid4())
        assert result is False

    def test_does_not_affect_other_persons(self, service):
        p1 = service.create_person(make_payload(first_name="Alice"), created_by=USER_A)
        p2 = service.create_person(make_payload(first_name="Bob"),   created_by=USER_A)
        service.delete_person(p1.id)
        assert service.get_person(p2.id) is not None


# ── list_persons ──────────────────────────────────────────────────────────────

class TestListPersons:

    def test_returns_all_persons_for_admin(self, service):
        service.create_person(make_payload(first_name="Alice"), created_by=USER_A)
        service.create_person(make_payload(first_name="Bob"),   created_by=USER_B)

        persons, total = service.list_persons(
            search=None, page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert total == 2

    def test_returns_only_own_persons_for_non_admin(self, service):
        service.create_person(make_payload(first_name="Alice"), created_by=USER_A)
        service.create_person(make_payload(first_name="Bob"),   created_by=USER_B)

        persons, total = service.list_persons(
            search=None, page=1, limit=20, user_id=USER_A, is_admin=False
        )
        assert total == 1
        assert persons[0].first_name == "Alice"

    def test_non_admin_cannot_see_other_users_persons(self, service):
        service.create_person(make_payload(first_name="Bob"), created_by=USER_B)

        persons, total = service.list_persons(
            search=None, page=1, limit=20, user_id=USER_A, is_admin=False
        )
        assert total == 0
        assert persons == []

    def test_search_filters_by_first_name(self, service):
        service.create_person(make_payload(first_name="Alice", last_name="Dupont"), created_by=USER_A)
        service.create_person(make_payload(first_name="Bob",   last_name="Martin"), created_by=USER_A)

        persons, total = service.list_persons(
            search="Alice", page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert total == 1
        assert persons[0].first_name == "Alice"

    def test_search_filters_by_last_name(self, service):
        service.create_person(make_payload(first_name="Alice", last_name="Dupont"), created_by=USER_A)
        service.create_person(make_payload(first_name="Bob",   last_name="Martin"), created_by=USER_A)

        persons, total = service.list_persons(
            search="Martin", page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert total == 1
        assert persons[0].last_name == "Martin"

    def test_search_is_case_insensitive(self, service):
        service.create_person(make_payload(first_name="Alice"), created_by=USER_A)

        persons, total = service.list_persons(
            search="alice", page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert total == 1

    def test_search_returns_empty_for_no_match(self, service):
        service.create_person(make_payload(first_name="Alice"), created_by=USER_A)

        persons, total = service.list_persons(
            search="XYZ_INTROUVABLE", page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert total == 0
        assert persons == []

    def test_pagination_page_1(self, service):
        for i in range(5):
            service.create_person(make_payload(first_name=f"Person{i}"), created_by=USER_A)

        persons, total = service.list_persons(
            search=None, page=1, limit=2, user_id=USER_A, is_admin=True
        )
        assert total == 5
        assert len(persons) == 2

    def test_pagination_page_2(self, service):
        for i in range(5):
            service.create_person(make_payload(first_name=f"Person{i}"), created_by=USER_A)

        p1, _ = service.list_persons(search=None, page=1, limit=2, user_id=USER_A, is_admin=True)
        p2, _ = service.list_persons(search=None, page=2, limit=2, user_id=USER_A, is_admin=True)

        ids_p1 = {p.id for p in p1}
        ids_p2 = {p.id for p in p2}
        assert ids_p1.isdisjoint(ids_p2)

    def test_returns_empty_when_no_persons(self, service):
        persons, total = service.list_persons(
            search=None, page=1, limit=20, user_id=USER_A, is_admin=True
        )
        assert persons == []
        assert total == 0


# ── Helpers (utils/helpers.py) ────────────────────────────────────────────────

class TestHelpersUsedByService:
    """Tests des fonctions utilitaires appelées par PersonService."""

    def test_sanitize_html_escapes_script_tag(self):
        from app.utils.helpers import sanitize_html
        result = sanitize_html('<script>alert("xss")</script>Texte')
        assert "<script>" not in result
        assert "Texte" in result

    def test_sanitize_html_returns_none_for_none(self):
        from app.utils.helpers import sanitize_html
        assert sanitize_html(None) is None

    def test_sanitize_html_returns_empty_for_empty(self):
        from app.utils.helpers import sanitize_html
        assert sanitize_html("") == ""

    def test_sanitize_html_preserves_plain_text(self):
        from app.utils.helpers import sanitize_html
        assert sanitize_html("Texte normal") == "Texte normal"

    def test_parse_date_partial_year_only(self):
        from app.utils.helpers import parse_date_partial
        y, m, d = parse_date_partial("1990")
        assert y == 1990
        assert m is None
        assert d is None

    def test_parse_date_partial_year_month(self):
        from app.utils.helpers import parse_date_partial
        y, m, d = parse_date_partial("1990-06")
        assert y == 1990
        assert m == 6
        assert d is None

    def test_parse_date_partial_full_date(self):
        from app.utils.helpers import parse_date_partial
        y, m, d = parse_date_partial("1990-06-15")
        assert y == 1990
        assert m == 6
        assert d == 15

    def test_parse_date_partial_none(self):
        from app.utils.helpers import parse_date_partial
        assert parse_date_partial(None) == (None, None, None)

    def test_calculate_age_living(self):
        from app.utils.helpers import calculate_age
        age = calculate_age("1990-01-01")
        assert age is not None
        assert age >= 34

    def test_calculate_age_deceased(self):
        from app.utils.helpers import calculate_age
        age = calculate_age("1867-11-07", death_date="1934-07-04")
        assert age == 66

    def test_calculate_age_none_birth(self):
        from app.utils.helpers import calculate_age
        assert calculate_age(None) is None

    def test_format_name_with_maiden(self):
        from app.utils.helpers import format_name
        result = format_name("Marie", "Curie", maiden_name="Sklodowska")
        assert "CURIE" in result
        assert "Marie" in result
        assert "Sklodowska" in result

    def test_format_name_without_maiden(self):
        from app.utils.helpers import format_name
        result = format_name("Jean", "Dupont")
        assert "DUPONT" in result
        assert "Jean" in result

    def test_is_valid_uuid_valid(self):
        from app.utils.helpers import is_valid_uuid
        assert is_valid_uuid(str(uuid.uuid4())) is True

    def test_is_valid_uuid_invalid(self):
        from app.utils.helpers import is_valid_uuid
        assert is_valid_uuid("not-a-uuid") is False

    def test_extract_year_from_date(self):
        from app.utils.helpers import extract_year_from_date
        assert extract_year_from_date("1990-06-15") == 1990
        assert extract_year_from_date("1990") == 1990
        assert extract_year_from_date(None) is None
