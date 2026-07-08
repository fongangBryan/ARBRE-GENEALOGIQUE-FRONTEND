"""
Tests API des événements de vie — endpoints /api/v1/events/

Couverture :
  EV01  Créer un événement (EDITOR)          → 201
  EV02  Créer un événement (READER)          → 403
  EV03  Créer sans authentification          → 401
  EV04  Lister les événements d'une personne → 200
  EV05  Obtenir un événement par ID          → 200
  EV06  Obtenir un événement inexistant      → 404
  EV07  Modifier un événement (EDITOR)       → 200
  EV08  Modifier un événement (READER)       → 403
  EV09  Supprimer un événement (EDITOR)      → 204
  EV10  Supprimer un événement (READER)      → 403
  EV11  Filtrer les événements par type      → 200
  EV12  Timeline chronologique               → 200
  EV13  Champs obligatoires manquants        → 422
  EV14  Type d'événement invalide            → 422
"""
import pytest

# ── Données de test ────────────────────────────────────────────────────────────

SAMPLE_EVENT = {
    "event_type": "birth",
    "date_start": "1990-01-15",
    "date_end":   None,
    "place":      "Paris, France",
    "description": "Naissance à l'hôpital Saint-Louis",
}

ALL_EVENT_TYPES = ["birth", "death", "baptism", "burial", "education", "employment", "residence", "custom"]


def make_event_payload(person_id: str, **kwargs) -> dict:
    payload = {"person_id": person_id, **SAMPLE_EVENT}
    payload.update(kwargs)
    return payload


# ── EV01-03 — Création ────────────────────────────────────────────────────────

class TestCreateEvent:

    def test_EV01_create_event_editor(self, client, auth_headers, created_person):
        """EDITOR peut créer un événement — retourne 201 avec les données."""
        resp = client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"]),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "birth"
        assert data["place"] == "Paris, France"
        assert "id" in data
        assert data["person_id"] == created_person["id"]

    def test_EV02_create_event_reader_forbidden(self, client, reader_headers, created_person):
        """READER ne peut pas créer un événement — 403."""
        resp = client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"]),
            headers=reader_headers,
        )
        assert resp.status_code == 403

    def test_EV03_create_event_unauthenticated(self, client, created_person):
        """Sans token, la création retourne 401."""
        resp = client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"]),
        )
        assert resp.status_code == 401

    def test_create_event_all_types(self, client, auth_headers, created_person):
        """Chaque type d'événement peut être créé."""
        for event_type in ALL_EVENT_TYPES:
            resp = client.post(
                "/api/v1/events/",
                json=make_event_payload(created_person["id"], event_type=event_type),
                headers=auth_headers,
            )
            assert resp.status_code == 201, f"Failed for event_type={event_type}: {resp.text}"

    def test_create_event_minimal(self, client, auth_headers, created_person):
        """Création avec uniquement les champs obligatoires."""
        resp = client.post(
            "/api/v1/events/",
            json={"person_id": created_person["id"], "event_type": "custom"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_create_event_with_date_range(self, client, auth_headers, created_person):
        """Création avec date_start et date_end."""
        resp = client.post(
            "/api/v1/events/",
            json=make_event_payload(
                created_person["id"],
                event_type="education",
                date_start="2005-09-01",
                date_end="2010-06-30",
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["date_start"] == "2005-09-01"
        assert data["date_end"] == "2010-06-30"


# ── EV04 — Lister les événements d'une personne ───────────────────────────────

class TestGetPersonEvents:

    def test_EV04_get_person_events(self, client, auth_headers, created_person):
        """Retourne la liste des événements d'une personne."""
        client.post("/api/v1/events/", json=make_event_payload(created_person["id"], event_type="birth"),  headers=auth_headers)
        client.post("/api/v1/events/", json=make_event_payload(created_person["id"], event_type="custom"), headers=auth_headers)

        resp = client.get(
            f"/api/v1/events/person/{created_person['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_person_events_empty(self, client, auth_headers, created_person):
        """Retourne une liste vide si la personne n'a pas d'événements."""
        resp = client.get(
            f"/api/v1/events/person/{created_person['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_person_events_unauthenticated(self, client, created_person):
        """Sans token, l'accès retourne 401."""
        resp = client.get(f"/api/v1/events/person/{created_person['id']}")
        assert resp.status_code == 401


# ── EV05-06 — Obtenir un événement par ID ─────────────────────────────────────

class TestGetEventById:

    def _create_event(self, client, auth_headers, created_person, **kwargs):
        resp = client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"], **kwargs),
            headers=auth_headers,
        )
        return resp.json()

    def test_EV05_get_event_by_id(self, client, auth_headers, created_person):
        """Retourne un événement complet par son ID."""
        event = self._create_event(client, auth_headers, created_person)
        resp = client.get(f"/api/v1/events/{event['id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == event["id"]
        assert data["event_type"] == "birth"

    def test_EV06_get_nonexistent_event(self, client, auth_headers):
        """Retourne 404 pour un UUID inconnu."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/events/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ── EV07-08 — Modifier un événement ──────────────────────────────────────────

class TestUpdateEvent:

    def _create_event(self, client, auth_headers, created_person):
        return client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"]),
            headers=auth_headers,
        ).json()

    def test_EV07_update_event_editor(self, client, auth_headers, created_person):
        """EDITOR peut modifier un événement — retourne 200."""
        event = self._create_event(client, auth_headers, created_person)
        resp = client.put(
            f"/api/v1/events/{event['id']}",
            json={"place": "Lyon, France", "description": "Mise à jour"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["place"] == "Lyon, France"
        assert data["description"] == "Mise à jour"

    def test_EV08_update_event_reader_forbidden(self, client, auth_headers, reader_headers, created_person):
        """READER ne peut pas modifier un événement — 403."""
        event = self._create_event(client, auth_headers, created_person)
        resp = client.put(
            f"/api/v1/events/{event['id']}",
            json={"place": "Marseille"},
            headers=reader_headers,
        )
        assert resp.status_code == 403

    def test_update_nonexistent_event(self, client, auth_headers):
        """Modifier un UUID inconnu retourne 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.put(
            f"/api/v1/events/{fake_id}",
            json={"place": "Paris"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_preserves_unmodified_fields(self, client, auth_headers, created_person):
        """Un champ non inclus dans le PUT reste inchangé."""
        event = self._create_event(client, auth_headers, created_person)
        client.put(
            f"/api/v1/events/{event['id']}",
            json={"place": "Bordeaux"},
            headers=auth_headers,
        )
        resp = client.get(f"/api/v1/events/{event['id']}", headers=auth_headers)
        assert resp.json()["date_start"] == SAMPLE_EVENT["date_start"]


# ── EV09-10 — Supprimer un événement ─────────────────────────────────────────

class TestDeleteEvent:

    def _create_event(self, client, auth_headers, created_person):
        return client.post(
            "/api/v1/events/",
            json=make_event_payload(created_person["id"]),
            headers=auth_headers,
        ).json()

    def test_EV09_delete_event_editor(self, client, auth_headers, created_person):
        """EDITOR peut supprimer un événement — retourne 204."""
        event = self._create_event(client, auth_headers, created_person)
        resp = client.delete(f"/api/v1/events/{event['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_deleted_event_no_longer_exists(self, client, auth_headers, created_person):
        """Après suppression, l'événement retourne 404."""
        event = self._create_event(client, auth_headers, created_person)
        client.delete(f"/api/v1/events/{event['id']}", headers=auth_headers)
        resp = client.get(f"/api/v1/events/{event['id']}", headers=auth_headers)
        assert resp.status_code == 404

    def test_EV10_delete_event_reader_forbidden(self, client, auth_headers, reader_headers, created_person):
        """READER ne peut pas supprimer un événement — 403."""
        event = self._create_event(client, auth_headers, created_person)
        resp = client.delete(f"/api/v1/events/{event['id']}", headers=reader_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_event(self, client, auth_headers):
        """Supprimer un UUID inconnu retourne 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/api/v1/events/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ── EV11 — Filtrer par type ────────────────────────────────────────────────────

class TestFilterEventsByType:

    def test_EV11_filter_by_event_type(self, client, auth_headers, created_person):
        """Le filtre ?event_type= retourne uniquement les événements du type demandé."""
        pid = created_person["id"]
        client.post("/api/v1/events/", json=make_event_payload(pid, event_type="birth"),  headers=auth_headers)
        client.post("/api/v1/events/", json=make_event_payload(pid, event_type="death"),  headers=auth_headers)
        client.post("/api/v1/events/", json=make_event_payload(pid, event_type="custom"), headers=auth_headers)

        resp = client.get(
            f"/api/v1/events/person/{pid}?event_type=birth",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "birth"

    def test_filter_returns_empty_when_no_match(self, client, auth_headers, created_person):
        """Filtre sans résultat retourne une liste vide."""
        pid = created_person["id"]
        client.post("/api/v1/events/", json=make_event_payload(pid, event_type="birth"), headers=auth_headers)

        resp = client.get(
            f"/api/v1/events/person/{pid}?event_type=death",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_event_type_filter(self, client, auth_headers, created_person):
        """Un event_type inconnu dans le filtre retourne 422."""
        resp = client.get(
            f"/api/v1/events/person/{created_person['id']}?event_type=invalid_type",
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── EV12 — Timeline ────────────────────────────────────────────────────────────

class TestTimeline:

    def _seed_events(self, client, auth_headers, pid):
        events_data = [
            {"event_type": "birth",      "date_start": "1990-01-15"},
            {"event_type": "education",  "date_start": "2005-09-01"},
            {"event_type": "employment", "date_start": "2013-03-01"},
            {"event_type": "death",      "date_start": "2060-12-31"},
        ]
        for data in events_data:
            client.post("/api/v1/events/", json={"person_id": pid, **data}, headers=auth_headers)

    def test_EV12_timeline_returns_events(self, client, auth_headers, created_person):
        """La timeline retourne tous les événements d'une personne."""
        self._seed_events(client, auth_headers, created_person["id"])
        resp = client.get(
            f"/api/v1/events/timeline/{created_person['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    def test_timeline_filter_start_year(self, client, auth_headers, created_person):
        """Le filtre start_year exclut les événements antérieurs."""
        self._seed_events(client, auth_headers, created_person["id"])
        resp = client.get(
            f"/api/v1/events/timeline/{created_person['id']}?start_year=2005",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        years = [int(e["date_start"][:4]) for e in events if e.get("date_start")]
        assert all(y >= 2005 for y in years)

    def test_timeline_filter_end_year(self, client, auth_headers, created_person):
        """Le filtre end_year exclut les événements postérieurs."""
        self._seed_events(client, auth_headers, created_person["id"])
        resp = client.get(
            f"/api/v1/events/timeline/{created_person['id']}?end_year=2013",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        years = [int(e["date_start"][:4]) for e in events if e.get("date_start")]
        assert all(y <= 2013 for y in years)

    def test_timeline_empty(self, client, auth_headers, created_person):
        """Timeline sans événements retourne une liste vide."""
        resp = client.get(
            f"/api/v1/events/timeline/{created_person['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ── EV13-14 — Validation ──────────────────────────────────────────────────────

class TestEventValidation:

    def test_EV13_missing_person_id(self, client, auth_headers):
        """Sans person_id, la création retourne 422."""
        resp = client.post(
            "/api/v1/events/",
            json={"event_type": "birth"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_EV13_missing_event_type(self, client, auth_headers, created_person):
        """Sans event_type, la création retourne 422."""
        resp = client.post(
            "/api/v1/events/",
            json={"person_id": created_person["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_EV14_invalid_event_type(self, client, auth_headers, created_person):
        """Un event_type inconnu retourne 422."""
        resp = client.post(
            "/api/v1/events/",
            json={"person_id": created_person["id"], "event_type": "wedding"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
