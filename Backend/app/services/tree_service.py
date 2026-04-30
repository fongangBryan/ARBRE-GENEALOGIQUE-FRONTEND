import math
from sqlalchemy.orm import Session
from typing import List, Dict
from uuid import UUID
from collections import deque

from app.services.filiation_service import FiliationService
from app.services.union_service import UnionService
from app.services.person_service import PersonService
from app.schemas.tree import CytoscapeGraph, CytoscapeNode, CytoscapeEdge
from app.utils.helpers import format_name, truncate_text


class TreeService:
    def __init__(self, db: Session):
        self.db = db
        self.filiation_service = FiliationService(db)
        self.union_service = UnionService(db)
        self.person_service = PersonService(db)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _node_data(self, person_id: UUID) -> dict | None:
        person = self.person_service.get_person(person_id)
        if not person:
            return None
        full_name = format_name(person.first_name, person.last_name, person.maiden_name)
        return {
            "id": str(person_id),
            "label": truncate_text(full_name, 30),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "birth_date": person.birth_date,
            "is_living": person.is_living,
        }

    def _spouse_id(self, union, person_id: UUID) -> UUID:
        return union.person_id_2 if union.person_id_1 == person_id else union.person_id_1

    def _all_neighbor_ids(self, person_id: UUID) -> List[UUID]:
        """Parent IDs + child IDs + spouse IDs — used for path-finding."""
        ids: List[UUID] = []
        for f in self.filiation_service.get_parents(person_id):
            ids.append(f.parent_id)
        for f in self.filiation_service.get_children(person_id):
            ids.append(f.child_id)
        for u in self.union_service.get_unions_by_person(person_id):
            ids.append(self._spouse_id(u, person_id))
        return ids

    # ── public methods ────────────────────────────────────────────────────────

    def build_subtree(self, root_id: UUID, depth: int, include_spouses: bool, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        processed: set = set()

        queue: deque = deque([(root_id, 0, None)])

        while queue:
            person_id, current_depth, parent_id = queue.popleft()

            if person_id in processed or current_depth > depth:
                continue
            processed.add(person_id)

            data = self._node_data(person_id)
            if data:
                nodes[person_id] = data

            if parent_id:
                edges.append({
                    "id": f"{parent_id}-{person_id}",
                    "source": str(parent_id),
                    "target": str(person_id),
                    "label": "parent-child",
                })

            for fil in self.filiation_service.get_children(person_id):
                if fil.child_id not in processed:
                    queue.append((fil.child_id, current_depth + 1, person_id))

            if include_spouses or current_depth == 0:
                for fil in self.filiation_service.get_parents(person_id):
                    if fil.parent_id not in processed:
                        queue.append((fil.parent_id, current_depth + 1, person_id))

            if include_spouses:
                for union in self.union_service.get_unions_by_person(person_id):
                    spouse_id = self._spouse_id(union, person_id)
                    if spouse_id not in processed:
                        queue.append((spouse_id, current_depth + 1, person_id))

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e) for e in edges],
        )

    def build_neighbors_graph(self, person_id: UUID, radius: int, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []

        data = self._node_data(person_id)
        if data:
            nodes[person_id] = data

        def add_connections(center_id: UUID, depth: int):
            # parent-child filiations
            for fil in self.filiation_service.get_parents(center_id):
                other_id = fil.parent_id
                if other_id not in nodes:
                    d = self._node_data(other_id)
                    if d:
                        nodes[other_id] = d
                edges.append({"id": f"{other_id}-{center_id}", "source": str(other_id), "target": str(center_id), "label": "parent-child"})
                if depth > 1:
                    add_connections(other_id, depth - 1)

            for fil in self.filiation_service.get_children(center_id):
                other_id = fil.child_id
                if other_id not in nodes:
                    d = self._node_data(other_id)
                    if d:
                        nodes[other_id] = d
                edges.append({"id": f"{center_id}-{other_id}", "source": str(center_id), "target": str(other_id), "label": "parent-child"})
                if depth > 1:
                    add_connections(other_id, depth - 1)

            # unions
            for union in self.union_service.get_unions_by_person(center_id):
                other_id = self._spouse_id(union, center_id)
                if other_id not in nodes:
                    d = self._node_data(other_id)
                    if d:
                        nodes[other_id] = d
                edges.append({"id": f"{center_id}-{other_id}-union", "source": str(center_id), "target": str(other_id), "label": union.union_type.value})

        add_connections(person_id, radius)

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e) for e in edges],
        )

    def build_ancestors_tree(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []

        def add_ancestors(current_id: UUID, gen: int, pos: int):
            if gen > generations:
                return
            data = self._node_data(current_id)
            if data and current_id not in nodes:
                nodes[current_id] = {**data, "generation": gen, "position": pos}

            for i, fil in enumerate(self.filiation_service.get_parents(current_id)[:2]):
                parent_id = fil.parent_id
                if parent_id not in nodes:
                    add_ancestors(parent_id, gen + 1, pos * 2 + i)
                edges.append({"id": f"{parent_id}-{current_id}", "source": str(parent_id), "target": str(current_id)})

        add_ancestors(person_id, 0, 0)

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n, position={"x": n.get("position", 0) * 100, "y": n.get("generation", 0) * 120}) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e) for e in edges],
        )

    def _calculate_ancestors_positions(self, root_id: UUID, generations: int) -> Dict[UUID, tuple]:
        positions: Dict[UUID, tuple] = {}

        def compute(node_id: UUID, gen: int, pos: int):
            positions[node_id] = (gen, pos)
            for i, fil in enumerate(self.filiation_service.get_parents(node_id)[:2]):
                compute(fil.parent_id, gen + 1, pos * 2 + i)

        compute(root_id, 0, 0)
        return positions

    def build_descendants_tree(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []

        def add_descendants(current_id: UUID, gen: int):
            if gen > generations:
                return
            data = self._node_data(current_id)
            if data and current_id not in nodes:
                nodes[current_id] = {**data, "generation": gen}

            for fil in self.filiation_service.get_children(current_id):
                child_id = fil.child_id
                if child_id not in nodes:
                    add_descendants(child_id, gen + 1)
                edges.append({"id": f"{current_id}-{child_id}", "source": str(current_id), "target": str(child_id)})

        add_descendants(person_id, 0)

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e) for e in edges],
        )

    def find_path_between(self, person_id_1: UUID, person_id_2: UUID, user_id: UUID) -> CytoscapeGraph:
        queue: deque = deque([(person_id_1, [person_id_1])])
        visited = {person_id_1}

        while queue:
            current_id, path = queue.popleft()

            if current_id == person_id_2:
                nodes: Dict[UUID, dict] = {}
                edges: List[dict] = []
                for i, nid in enumerate(path):
                    data = self._node_data(nid)
                    if data:
                        nodes[nid] = data
                    if i > 0:
                        edges.append({"id": f"{path[i-1]}-{nid}", "source": str(path[i-1]), "target": str(nid)})
                return CytoscapeGraph(
                    nodes=[CytoscapeNode(data=n) for n in nodes.values()],
                    edges=[CytoscapeEdge(data=e) for e in edges],
                )

            for neighbor_id in self._all_neighbor_ids(current_id):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return CytoscapeGraph(nodes=[], edges=[])

    def build_family_group(self, person_id: UUID, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []

        data = self._node_data(person_id)
        if data:
            nodes[person_id] = {**data, "class": "center"}

        for fil in self.filiation_service.get_parents(person_id):
            pid = fil.parent_id
            if pid not in nodes:
                d = self._node_data(pid)
                if d:
                    nodes[pid] = {**d, "class": "parent"}
            edges.append({"id": f"{pid}-{person_id}", "source": str(pid), "target": str(person_id), "class": "parent-child"})

        for union in self.union_service.get_unions_by_person(person_id):
            spouse_id = self._spouse_id(union, person_id)
            if spouse_id not in nodes:
                d = self._node_data(spouse_id)
                if d:
                    nodes[spouse_id] = {**d, "class": "spouse"}
            edges.append({"id": f"{person_id}-{spouse_id}-union", "source": str(person_id), "target": str(spouse_id), "class": "couple"})

            # Enfants communs (ceux dans les filiations des deux parents)
            spouse_children = {f.child_id for f in self.filiation_service.get_children(spouse_id)}
            for fil in self.filiation_service.get_children(person_id):
                child_id = fil.child_id
                if child_id not in nodes:
                    d = self._node_data(child_id)
                    if d:
                        nodes[child_id] = {**d, "class": "child"}
                edges.append({"id": f"{person_id}-{child_id}", "source": str(person_id), "target": str(child_id), "class": "parent-child"})

        # Enfants sans conjoint commun
        for fil in self.filiation_service.get_children(person_id):
            child_id = fil.child_id
            if child_id not in nodes:
                d = self._node_data(child_id)
                if d:
                    nodes[child_id] = {**d, "class": "child"}
                edges.append({"id": f"{person_id}-{child_id}", "source": str(person_id), "target": str(child_id), "class": "parent-child"})

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n, classes=n.get("class")) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e, classes=e.get("class")) for e in edges],
        )

    def build_pedigree_wheel(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []

        def add_to_wheel(current_id: UUID, sosa: int, gen: int):
            if gen > generations:
                return
            data = self._node_data(current_id)
            if data and current_id not in nodes:
                angle = (sosa * 360 / (2 ** gen)) if gen > 0 else 0
                radius = gen * 150
                nodes[current_id] = {
                    **data,
                    "sosa": sosa,
                    "generation": gen,
                    "x": radius * math.cos(math.radians(angle)),
                    "y": radius * math.sin(math.radians(angle)),
                }

            for i, fil in enumerate(self.filiation_service.get_parents(current_id)[:2]):
                parent_id = fil.parent_id
                if parent_id not in nodes:
                    add_to_wheel(parent_id, sosa * 2 + i, gen + 1)
                edges.append({"id": f"{parent_id}-{current_id}", "source": str(parent_id), "target": str(current_id)})

        add_to_wheel(person_id, 1, 0)

        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=n, position={"x": n.get("x", 0), "y": n.get("y", 0)}) for n in nodes.values()],
            edges=[CytoscapeEdge(data=e) for e in edges],
        )
