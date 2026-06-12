"""
Tests CRUD des personnes — couverture du plan de tests P01-P13.

Légende des rôles :
  READER  → peut lister/lire, pas créer/modifier/supprimer
  EDITOR  → peut créer/modifier, pas supprimer
  ADMIN   → droits complets (CRUD + suppression)
"""
import pytest

SAMPLE_PERSON = {
    "first_name": "Jean",
    "last_name": "Dupont",
    "gender": "male",
    "birth_date": "1990-01-15",
    "birth_place": "Paris",
    "is_living": True,
    "privacy_level": "private",
}

UPDATED_PERSON = {
    "first_name": "Marie",
    "last_name": "Curie",
    "gender": "female",
    "birth_date": "1867-11-07",
    "birth_place": "Varsovie",
    "is_living": False,
    "privacy_level": "public",
}


# ──────────────────────────────────────────────────────────────────────────────
# P01 — Lister les membres (READER)
# ──────────────────────────────────────────────────────────────────────────────

def test_P01_list_persons_reader(client, reader_headers):
    """READER peut lister les membres et obtenir une réponse paginée."""
    response = client.get("/api/v1/persons/", headers=reader_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "pages" in data
    assert isinstance(data["items"], list)


def test_P01_list_persons_unauthenticated(client):
    """Sans token, la liste est refusée."""
    response = client.get("/api/v1/persons/")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# P02 — Créer une personne (EDITOR)
# ──────────────────────────────────────────────────────────────────────────────

def test_P02_create_person_editor(client, auth_headers):
    """EDITOR peut créer une personne — retourne 201 avec les données."""
    response = client.post("/api/v1/persons/", json=SAMPLE_PERSON, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == SAMPLE_PERSON["first_name"]
    assert data["last_name"] == SAMPLE_PERSON["last_name"]
    assert data["gender"] == SAMPLE_PERSON["gender"]
    assert "id" in data
    assert "created_at" in data


# ──────────────────────────────────────────────────────────────────────────────
# P03 — Créer une personne (READER) → 403
# ──────────────────────────────────────────────────────────────────────────────

def test_P03_create_person_reader_forbidden(client, reader_headers):
    """READER ne peut pas créer — doit recevoir 403."""
    response = client.post("/api/v1/persons/", json=SAMPLE_PERSON, headers=reader_headers)
    assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# P04 — Modifier une personne (EDITOR)
# ──────────────────────────────────────────────────────────────────────────────

def test_P04_update_person_editor(client, auth_headers, created_person):
    """EDITOR peut modifier une personne — retourne 200 avec les nouvelles données."""
    person_id = created_person["id"]
    response = client.put(
        f"/api/v1/persons/{person_id}",
        json={"first_name": "Pierre", "last_name": "Martin"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Pierre"
    assert data["last_name"] == "Martin"
    assert data["id"] == person_id


# ──────────────────────────────────────────────────────────────────────────────
# P05 — Modifier une personne (READER) → 403
# ──────────────────────────────────────────────────────────────────────────────

def test_P05_update_person_reader_forbidden(client, auth_headers, reader_headers, created_person):
    """READER ne peut pas modifier — doit recevoir 403."""
    person_id = created_person["id"]
    response = client.put(
        f"/api/v1/persons/{person_id}",
        json={"first_name": "Interdit"},
        headers=reader_headers,
    )
    assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# P06 — Supprimer une personne (ADMIN)
# ──────────────────────────────────────────────────────────────────────────────

def test_P06_delete_person_admin(client, admin_headers, created_person):
    """ADMIN peut supprimer une personne — retourne 204."""
    person_id = created_person["id"]
    response = client.delete(f"/api/v1/persons/{person_id}", headers=admin_headers)
    assert response.status_code == 204

    # Vérification : la personne n'existe plus
    get_response = client.get(f"/api/v1/persons/{person_id}", headers=admin_headers)
    assert get_response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# P07 — Supprimer une personne (EDITOR) → 403
# ──────────────────────────────────────────────────────────────────────────────

def test_P07_delete_person_editor_forbidden(client, auth_headers, created_person):
    """EDITOR ne peut pas supprimer — doit recevoir 403."""
    person_id = created_person["id"]
    response = client.delete(f"/api/v1/persons/{person_id}", headers=auth_headers)
    assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# P08 — Supprimer une personne (READER) → 403
# ──────────────────────────────────────────────────────────────────────────────

def test_P08_delete_person_reader_forbidden(client, reader_headers, created_person):
    """READER ne peut pas supprimer — doit recevoir 403."""
    person_id = created_person["id"]
    response = client.delete(f"/api/v1/persons/{person_id}", headers=reader_headers)
    assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# P09 — Obtenir une personne par ID (READER)
# ──────────────────────────────────────────────────────────────────────────────

def test_P09_get_person_by_id_reader(client, reader_headers, created_person):
    """READER peut récupérer la fiche complète d'une personne."""
    person_id = created_person["id"]
    response = client.get(f"/api/v1/persons/{person_id}", headers=reader_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == person_id
    assert data["first_name"] == SAMPLE_PERSON["first_name"]
    assert data["last_name"] == SAMPLE_PERSON["last_name"]
    assert "created_at" in data
    assert "updated_at" in data


# ──────────────────────────────────────────────────────────────────────────────
# P10 — Obtenir une personne inexistante → 404
# ──────────────────────────────────────────────────────────────────────────────

def test_P10_get_nonexistent_person(client, reader_headers):
    """Retourne 404 pour un UUID qui n'existe pas en base."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/persons/{fake_id}", headers=reader_headers)
    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# P11 — Recherche par nom
# ──────────────────────────────────────────────────────────────────────────────

def test_P11_search_by_name(client, auth_headers, reader_headers):
    """La recherche filtre les résultats par nom."""
    # Créer deux personnes
    client.post("/api/v1/persons/", json={**SAMPLE_PERSON, "first_name": "Alice", "last_name": "Dupont"}, headers=auth_headers)
    client.post("/api/v1/persons/", json={**SAMPLE_PERSON, "first_name": "Bob", "last_name": "Martin"}, headers=auth_headers)

    # Rechercher "Alice"
    response = client.get("/api/v1/persons/?search=Alice", headers=reader_headers)
    assert response.status_code == 200
    data = response.json()
    names = [p["first_name"] for p in data["items"]]
    assert "Alice" in names
    assert "Bob" not in names


def test_P11_search_no_result(client, auth_headers, reader_headers):
    """Une recherche sans correspondance retourne une liste vide."""
    client.post("/api/v1/persons/", json=SAMPLE_PERSON, headers=auth_headers)
    response = client.get("/api/v1/persons/?search=XYZ_INEXISTANT", headers=reader_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


# ──────────────────────────────────────────────────────────────────────────────
# P12 — Pagination
# ──────────────────────────────────────────────────────────────────────────────

def test_P12_pagination(client, auth_headers, reader_headers):
    """La pagination retourne les bons éléments par page."""
    # Créer 5 personnes
    for i in range(5):
        client.post(
            "/api/v1/persons/",
            json={**SAMPLE_PERSON, "first_name": f"Person{i}", "last_name": "Test"},
            headers=auth_headers,
        )

    # Page 1, taille 2
    resp_p1 = client.get("/api/v1/persons/?page=1&limit=2", headers=reader_headers)
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert len(data_p1["items"]) <= 2
    assert data_p1["page"] == 1

    # Page 2, taille 2
    resp_p2 = client.get("/api/v1/persons/?page=2&limit=2", headers=reader_headers)
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert data_p2["page"] == 2

    # Les deux pages ne doivent pas contenir les mêmes IDs
    ids_p1 = {p["id"] for p in data_p1["items"]}
    ids_p2 = {p["id"] for p in data_p2["items"]}
    assert ids_p1.isdisjoint(ids_p2)


# ──────────────────────────────────────────────────────────────────────────────
# P13 — Champs obligatoires manquants → 422
# ──────────────────────────────────────────────────────────────────────────────

def test_P13_missing_first_name(client, auth_headers):
    """Sans first_name, la création retourne 422."""
    payload = {k: v for k, v in SAMPLE_PERSON.items() if k != "first_name"}
    response = client.post("/api/v1/persons/", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_P13_missing_last_name(client, auth_headers):
    """Sans last_name, la création retourne 422."""
    payload = {k: v for k, v in SAMPLE_PERSON.items() if k != "last_name"}
    response = client.post("/api/v1/persons/", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_P13_empty_first_name(client, auth_headers):
    """Avec first_name vide (min_length=1), la création retourne 422."""
    response = client.post(
        "/api/v1/persons/",
        json={**SAMPLE_PERSON, "first_name": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_P13_invalid_gender(client, auth_headers):
    """Avec une valeur de genre invalide, la création retourne 422."""
    response = client.post(
        "/api/v1/persons/",
        json={**SAMPLE_PERSON, "gender": "invalid_value"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_P13_invalid_privacy_level(client, auth_headers):
    """Avec un privacy_level inconnu, la création retourne 422."""
    response = client.post(
        "/api/v1/persons/",
        json={**SAMPLE_PERSON, "privacy_level": "top_secret"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Tests complémentaires — robustesse
# ──────────────────────────────────────────────────────────────────────────────

def test_create_person_full_fields(client, auth_headers):
    """Création avec tous les champs optionnels renseignés."""
    payload = {
        "first_name": "Marie",
        "last_name": "Curie",
        "maiden_name": "Skłodowska",
        "gender": "female",
        "birth_date": "1867-11-07",
        "birth_place": "Varsovie, Pologne",
        "death_date": "1934-07-04",
        "death_place": "Passy, France",
        "is_living": False,
        "biography": "Physicienne et chimiste pionnière.",
        "occupation": "Scientifique",
        "nationality": "Française",
        "privacy_level": "public",
    }
    response = client.post("/api/v1/persons/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["maiden_name"] == "Skłodowska"
    assert data["is_living"] is False
    assert data["biography"] == payload["biography"]


def test_delete_nonexistent_person_admin(client, admin_headers):
    """Supprimer un UUID inconnu retourne 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = client.delete(f"/api/v1/persons/{fake_id}", headers=admin_headers)
    assert response.status_code == 404


def test_update_nonexistent_person(client, auth_headers):
    """Modifier un UUID inconnu retourne 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = client.put(
        f"/api/v1/persons/{fake_id}",
        json={"first_name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404
