"""
Tests API de l'arbre généalogique — endpoints /api/v1/tree/

Couverture (plan T01-T04 + cas complémentaires) :
  T01  Obtenir un sous-arbre complet         → 200, structure CytoscapeGraph
  T02  Obtenir l'arbre d'une personne        → 200, nœud présent
  T03  Arbre avec personne inexistante        → 404 ou 403
  T04  Arbre vide (aucun lien)               → 200, nodes/edges []
  T05  Ancêtres d'une personne               → 200
  T06  Descendants d'une personne            → 200
  T07  Groupe familial                       → 200
  T08  Chemin entre deux personnes           → 200
  T09  Voisins d'une personne                → 200
  T10  Pedigree (roue)                       → 200
  T11  Authentification requise              → 401
  T12  Profondeur / générations hors-bornes  → 422
"""
import pytest

FAKE_UUID = "00000000-0000-0000-0000-000000000000"

# ── Fixture locale : famille minimale (parent → enfant) ───────────────────────

@pytest.fixture
def family(client, auth_headers):
    """Crée un parent, un enfant et une filiation entre eux."""
    parent = client.post("/api/v1/persons/", json={
        "first_name": "Henri", "last_name": "Durand",
        "gender": "male", "is_living": False, "privacy_level": "private",
    }, headers=auth_headers).json()

    child = client.post("/api/v1/persons/", json={
        "first_name": "Sophie", "last_name": "Durand",
        "gender": "female", "is_living": True, "privacy_level": "private",
    }, headers=auth_headers).json()

    client.post("/api/v1/filiations/", json={
        "parent_id": parent["id"],
        "child_id":  child["id"],
        "filiation_type": "biological",
    }, headers=auth_headers)

    return {"parent": parent, "child": child}


# ── Helpers ────────────────────────────────────────────────────────────────────

def assert_cytoscape_graph(data: dict):
    """Vérifie la structure minimale d'un CytoscapeGraph."""
    assert "nodes" in data, f"Clé 'nodes' absente : {data}"
    assert "edges" in data, f"Clé 'edges' absente : {data}"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


# ── T01 — Sous-arbre ──────────────────────────────────────────────────────────

class TestSubtree:

    def test_T01_subtree_returns_cytoscape_graph(self, client, auth_headers, created_person):
        """GET /subtree retourne un CytoscapeGraph valide."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/subtree?root_id={pid}&person_id={pid}&depth=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T01_subtree_contains_root_node(self, client, auth_headers, created_person):
        """Le nœud racine est présent dans le graphe."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/subtree?root_id={pid}&person_id={pid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        node_ids = [n["data"]["id"] for n in nodes]
        assert pid in node_ids

    def test_T01_subtree_with_family(self, client, auth_headers, family):
        """Le sous-arbre inclut les nœuds liés par une filiation."""
        pid = family["parent"]["id"]
        resp = client.get(
            f"/api/v1/tree/subtree?root_id={pid}&person_id={pid}&depth=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        node_ids = [n["data"]["id"] for n in data["nodes"]]
        assert family["parent"]["id"] in node_ids
        assert family["child"]["id"] in node_ids

    def test_T01_subtree_with_edges(self, client, auth_headers, family):
        """Les arêtes (filiations) sont présentes dans le graphe."""
        pid = family["parent"]["id"]
        resp = client.get(
            f"/api/v1/tree/subtree?root_id={pid}&person_id={pid}&depth=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["edges"]) >= 1

    def test_T04_subtree_empty_no_relations(self, client, auth_headers, created_person):
        """T04 : personne sans lien → nodes contient la personne, edges vide."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/subtree?root_id={pid}&person_id={pid}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert_cytoscape_graph(data)
        assert data["edges"] == []


# ── T05 — Ancêtres ────────────────────────────────────────────────────────────

class TestAncestors:

    def test_T05_ancestors_returns_graph(self, client, auth_headers, created_person):
        """GET /ancestors/{person_id} retourne un CytoscapeGraph."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/ancestors/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T05_ancestors_includes_person(self, client, auth_headers, created_person):
        """La personne elle-même est incluse dans les ancêtres."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/ancestors/{pid}", headers=auth_headers)
        nodes = resp.json()["nodes"]
        node_ids = [n["data"]["id"] for n in nodes]
        assert pid in node_ids

    def test_T05_ancestors_with_parent(self, client, auth_headers, family):
        """Le parent figure dans les ancêtres de l'enfant."""
        child_id  = family["child"]["id"]
        parent_id = family["parent"]["id"]
        resp = client.get(f"/api/v1/tree/ancestors/{child_id}", headers=auth_headers)
        assert resp.status_code == 200
        node_ids = [n["data"]["id"] for n in resp.json()["nodes"]]
        assert parent_id in node_ids

    def test_T03_ancestors_nonexistent_person(self, client, auth_headers):
        """T03 : personne inexistante → 403 ou 404."""
        resp = client.get(f"/api/v1/tree/ancestors/{FAKE_UUID}", headers=auth_headers)
        assert resp.status_code in (403, 404)

    def test_T12_ancestors_generations_too_high(self, client, auth_headers, created_person):
        """T12 : générations > 8 → 422."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/ancestors/{pid}?generations=99",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_T11_ancestors_unauthenticated(self, client, created_person):
        """T11 : sans token → 401."""
        resp = client.get(f"/api/v1/tree/ancestors/{created_person['id']}")
        assert resp.status_code == 401


# ── T06 — Descendants ─────────────────────────────────────────────────────────

class TestDescendants:

    def test_T06_descendants_returns_graph(self, client, auth_headers, created_person):
        """GET /descendants/{person_id} retourne un CytoscapeGraph."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/descendants/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T06_descendants_with_child(self, client, auth_headers, family):
        """L'enfant figure dans les descendants du parent."""
        parent_id = family["parent"]["id"]
        child_id  = family["child"]["id"]
        resp = client.get(f"/api/v1/tree/descendants/{parent_id}", headers=auth_headers)
        assert resp.status_code == 200
        node_ids = [n["data"]["id"] for n in resp.json()["nodes"]]
        assert child_id in node_ids

    def test_T04_descendants_no_children(self, client, auth_headers, created_person):
        """T04 : personne sans descendant → edges vide."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/descendants/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["edges"] == []

    def test_T03_descendants_nonexistent_person(self, client, auth_headers):
        """T03 : personne inexistante → 403 ou 404."""
        resp = client.get(f"/api/v1/tree/descendants/{FAKE_UUID}", headers=auth_headers)
        assert resp.status_code in (403, 404)

    def test_T12_descendants_generations_out_of_range(self, client, auth_headers, created_person):
        """T12 : générations < 1 → 422."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/descendants/{pid}?generations=0",
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── T07 — Groupe familial ─────────────────────────────────────────────────────

class TestFamilyGroup:

    def test_T07_family_group_returns_graph(self, client, auth_headers, created_person):
        """GET /family/{person_id} retourne un CytoscapeGraph."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/family/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T07_family_group_includes_parent_and_child(self, client, auth_headers, family):
        """Le groupe familial de l'enfant inclut le parent."""
        child_id  = family["child"]["id"]
        parent_id = family["parent"]["id"]
        resp = client.get(f"/api/v1/tree/family/{child_id}", headers=auth_headers)
        assert resp.status_code == 200
        node_ids = [n["data"]["id"] for n in resp.json()["nodes"]]
        assert parent_id in node_ids

    def test_T11_family_unauthenticated(self, client, created_person):
        """T11 : sans token → 401."""
        resp = client.get(f"/api/v1/tree/family/{created_person['id']}")
        assert resp.status_code == 401


# ── T08 — Chemin entre deux personnes ─────────────────────────────────────────

class TestRelationshipPath:

    def test_T08_path_between_related_persons(self, client, auth_headers, family):
        """Le chemin entre parent et enfant est trouvé."""
        parent_id = family["parent"]["id"]
        child_id  = family["child"]["id"]
        resp = client.get(
            f"/api/v1/tree/path/{parent_id}/{child_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T08_path_same_person(self, client, auth_headers, created_person):
        """Le chemin d'une personne vers elle-même retourne un graphe valide."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/path/{pid}/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T11_path_unauthenticated(self, client, family):
        """T11 : sans token → 401."""
        pid1 = family["parent"]["id"]
        pid2 = family["child"]["id"]
        resp = client.get(f"/api/v1/tree/path/{pid1}/{pid2}")
        assert resp.status_code == 401


# ── T09 — Voisins ─────────────────────────────────────────────────────────────

class TestNeighbors:

    def test_T09_neighbors_returns_graph(self, client, auth_headers, created_person):
        """GET /neighbors retourne un CytoscapeGraph."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/neighbors?person_id={pid}&radius=1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T09_neighbors_with_family(self, client, auth_headers, family):
        """Les voisins incluent les proches par filiation."""
        child_id  = family["child"]["id"]
        parent_id = family["parent"]["id"]
        resp = client.get(
            f"/api/v1/tree/neighbors?person_id={child_id}&radius=1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        node_ids = [n["data"]["id"] for n in resp.json()["nodes"]]
        assert parent_id in node_ids

    def test_T12_neighbors_radius_out_of_range(self, client, auth_headers, created_person):
        """T12 : radius > 3 → 422."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/neighbors?person_id={pid}&radius=99",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_T11_neighbors_unauthenticated(self, client, created_person):
        """T11 : sans token → 401."""
        resp = client.get(f"/api/v1/tree/neighbors?person_id={created_person['id']}")
        assert resp.status_code == 401


# ── T10 — Pedigree (roue) ─────────────────────────────────────────────────────

class TestPedigree:

    def test_T10_pedigree_returns_graph(self, client, auth_headers, created_person):
        """GET /pedigree/{person_id} retourne un CytoscapeGraph."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/pedigree/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert_cytoscape_graph(resp.json())

    def test_T10_pedigree_nodes_have_sosa_data(self, client, auth_headers, created_person):
        """Les nœuds du pedigree contiennent les données de la personne."""
        pid = created_person["id"]
        resp = client.get(f"/api/v1/tree/pedigree/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) >= 1
        # Le nœud racine doit être présent
        root_ids = [n["data"]["id"] for n in nodes]
        assert pid in root_ids

    def test_T12_pedigree_generations_out_of_range(self, client, auth_headers, created_person):
        """T12 : générations > 8 → 422."""
        pid = created_person["id"]
        resp = client.get(
            f"/api/v1/tree/pedigree/{pid}?generations=10",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_T11_pedigree_unauthenticated(self, client, created_person):
        """T11 : sans token → 401."""
        resp = client.get(f"/api/v1/tree/pedigree/{created_person['id']}")
        assert resp.status_code == 401
