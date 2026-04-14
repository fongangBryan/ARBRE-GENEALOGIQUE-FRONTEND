from sqlalchemy.orm import Session
from typing import List, Set, Dict, Optional
from uuid import UUID
from collections import deque

from app.services.relationship_service import RelationshipService
from app.services.person_service import PersonService
from app.schemas.tree import CytoscapeGraph, CytoscapeNode, CytoscapeEdge
from app.utils.helpers import format_name, truncate_text  # NOUVEAU

class TreeService:
    def __init__(self, db: Session):
        self.db = db
        self.relationship_service = RelationshipService(db)
        self.person_service = PersonService(db)
    
    def build_subtree(
        self, 
        root_id: UUID, 
        depth: int, 
        include_spouses: bool,
        user_id: UUID
    ) -> CytoscapeGraph:
        """Construit un sous-arbre à partir d'une racine"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        processed = set()
        
        # BFS pour explorer l'arbre
        queue = deque([(root_id, 0, None)])
        
        while queue:
            person_id, current_depth, parent_id = queue.popleft()
            
            if person_id in processed or current_depth > depth:
                continue
            
            processed.add(person_id)
            
            # Ajouter le nœud - Utiliser helpers
            person = self.person_service.get_person(person_id)
            if person:
                full_name = format_name(person.first_name, person.last_name, person.maiden_name)  # MODIFIÉ
                nodes[person_id] = {
                    "id": str(person_id),
                    "label": truncate_text(full_name, 30),  # MODIFIÉ
                    "birth_date": person.birth_date,
                    "is_living": person.is_living,
                    "first_name": person.first_name,
                    "last_name": person.last_name
                }
            
            # Ajouter l'arête parent-enfant
            if parent_id:
                edges.append({
                    "id": f"{parent_id}-{person_id}",
                    "source": str(parent_id),
                    "target": str(person_id)
                })
            
            # Récupérer les enfants
            children = self.relationship_service.get_children(person_id)
            for child_rel in children:
                child_id = child_rel.person_id_2
                if child_id not in processed:
                    queue.append((child_id, current_depth + 1, person_id))
            
            # Récupérer les parents
            if include_spouses or current_depth == 0:
                parents = self.relationship_service.get_parents(person_id)
                for parent_rel in parents:
                    parent_id_rel = parent_rel.person_id_1
                    if parent_id_rel not in processed:
                        queue.append((parent_id_rel, current_depth + 1, person_id))
            
            # Récupérer les conjoints
            if include_spouses:
                spouses = self.relationship_service.get_spouses(person_id)
                for spouse_rel in spouses:
                    spouse_id = spouse_rel.person_id_2 if spouse_rel.person_id_1 == person_id else spouse_rel.person_id_1
                    if spouse_id not in processed:
                        queue.append((spouse_id, current_depth + 1, person_id))
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge) for edge in edges]
        )
    
    # ... Le reste de la classe reste identique ...

    def build_neighbors_graph(self, person_id: UUID, radius: int, user_id: UUID) -> CytoscapeGraph:
        """Construit un graphe des voisins"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        
        # Ajouter la personne centrale
        person = self.person_service.get_person(person_id)
        if person:
            nodes[person_id] = {
                "id": str(person_id),
                "label": f"{person.first_name} {person.last_name}"
            }
        
        # Récupérer toutes les relations
        relationships = self.relationship_service.get_relationships_by_person(person_id)
        
        for rel in relationships:
            other_id = rel.person_id_2 if rel.person_id_1 == person_id else rel.person_id_1
            
            # Ajouter le voisin
            if other_id not in nodes:
                other = self.person_service.get_person(other_id)
                if other:
                    nodes[other_id] = {
                        "id": str(other_id),
                        "label": f"{other.first_name} {other.last_name}"
                    }
            
            # Ajouter l'arête
            edges.append({
                "id": f"{person_id}-{other_id}",
                "source": str(person_id),
                "target": str(other_id),
                "label": rel.type.value
            })
            
            # Si radius > 1, ajouter les voisins des voisins
            if radius > 1:
                deeper_rels = self.relationship_service.get_relationships_by_person(other_id)
                for deeper_rel in deeper_rels:
                    deeper_other = deeper_rel.person_id_2 if deeper_rel.person_id_1 == other_id else deeper_rel.person_id_1
                    if deeper_other != person_id:
                        if deeper_other not in nodes:
                            deeper_person = self.person_service.get_person(deeper_other)
                            if deeper_person:
                                nodes[deeper_other] = {
                                    "id": str(deeper_other),
                                    "label": f"{deeper_person.first_name} {deeper_person.last_name}"
                                }
                        edges.append({
                            "id": f"{other_id}-{deeper_other}",
                            "source": str(other_id),
                            "target": str(deeper_other),
                            "label": deeper_rel.type.value
                        })
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge) for edge in edges]
        )
    
    def build_ancestors_tree(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        """Construit l'arbre des ascendants (format classique)"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        
        # Positionnement pour affichage arbre généalogique
        positions = self._calculate_ancestors_positions(person_id, generations)
        
        def add_ancestors(current_id: UUID, current_gen: int, position: int):
            if current_gen > generations:
                return
            
            # Ajouter la personne
            person = self.person_service.get_person(current_id)
            if person and current_id not in nodes:
                nodes[current_id] = {
                    "id": str(current_id),
                    "label": f"{person.first_name} {person.last_name}",
                    "generation": current_gen,
                    "position": position
                }
            
            # Récupérer les parents
            parents = self.relationship_service.get_parents(current_id)
            for i, parent_rel in enumerate(parents[:2]):  # Max 2 parents
                parent_id = parent_rel.person_id_1
                child_position = position * 2 + i
                
                if parent_id not in nodes:
                    add_ancestors(parent_id, current_gen + 1, child_position)
                
                edges.append({
                    "id": f"{parent_id}-{current_id}",
                    "source": str(parent_id),
                    "target": str(current_id)
                })
        
        add_ancestors(person_id, 0, 0)
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node, position={"x": node.get("position", 0) * 100, "y": node.get("generation", 0) * 120}) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge) for edge in edges]
        )
    
    def _calculate_ancestors_positions(self, root_id: UUID, generations: int) -> Dict[UUID, tuple]:
        """Calcule les positions pour l'affichage en arbre"""
        positions = {}
        
        def compute(node_id: UUID, gen: int, pos: int):
            positions[node_id] = (gen, pos)
            parents = self.relationship_service.get_parents(node_id)
            for i, parent_rel in enumerate(parents[:2]):
                compute(parent_rel.person_id_1, gen + 1, pos * 2 + i)
        
        compute(root_id, 0, 0)
        return positions
    
    def build_descendants_tree(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        """Construit l'arbre des descendants"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        
        def add_descendants(current_id: UUID, current_gen: int):
            if current_gen > generations:
                return
            
            person = self.person_service.get_person(current_id)
            if person and current_id not in nodes:
                nodes[current_id] = {
                    "id": str(current_id),
                    "label": f"{person.first_name} {person.last_name}",
                    "generation": current_gen
                }
            
            children = self.relationship_service.get_children(current_id)
            for child_rel in children:
                child_id = child_rel.person_id_2
                if child_id not in nodes:
                    add_descendants(child_id, current_gen + 1)
                
                edges.append({
                    "id": f"{current_id}-{child_id}",
                    "source": str(current_id),
                    "target": str(child_id)
                })
        
        add_descendants(person_id, 0)
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge) for edge in edges]
        )
    
    def find_path_between(self, person_id_1: UUID, person_id_2: UUID, user_id: UUID) -> CytoscapeGraph:
        """Trouve le chemin de parenté entre deux personnes (BFS)"""
        # BFS pour trouver le chemin
        queue = deque([(person_id_1, [person_id_1])])
        visited = {person_id_1}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == person_id_2:
                # Construire le graphe du chemin
                nodes = {}
                edges = []
                
                for i, node_id in enumerate(path):
                    person = self.person_service.get_person(node_id)
                    if person:
                        nodes[node_id] = {
                            "id": str(node_id),
                            "label": f"{person.first_name} {person.last_name}"
                        }
                    if i > 0:
                        edges.append({
                            "id": f"{path[i-1]}-{node_id}",
                            "source": str(path[i-1]),
                            "target": str(node_id)
                        })
                
                return CytoscapeGraph(
                    nodes=[CytoscapeNode(data=node) for node in nodes.values()],
                    edges=[CytoscapeEdge(data=edge) for edge in edges]
                )
            
            # Explorer les voisins
            neighbors = self.relationship_service.get_relationships_by_person(current_id)
            for rel in neighbors:
                neighbor_id = rel.person_id_2 if rel.person_id_1 == current_id else rel.person_id_1
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        # Aucun chemin trouvé
        return CytoscapeGraph(nodes=[], edges=[])
    
    def build_family_group(self, person_id: UUID, user_id: UUID) -> CytoscapeGraph:
        """Construit le groupe familial complet"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        
        # Ajouter la personne
        person = self.person_service.get_person(person_id)
        if person:
            nodes[person_id] = {
                "id": str(person_id),
                "label": f"{person.first_name} {person.last_name}",
                "class": "center"
            }
        
        # Ajouter les parents
        parents = self.relationship_service.get_parents(person_id)
        for parent_rel in parents:
            parent_id = parent_rel.person_id_1
            parent = self.person_service.get_person(parent_id)
            if parent and parent_id not in nodes:
                nodes[parent_id] = {
                    "id": str(parent_id),
                    "label": f"{parent.first_name} {parent.last_name}",
                    "class": "parent"
                }
            edges.append({
                "id": f"{parent_id}-{person_id}",
                "source": str(parent_id),
                "target": str(person_id),
                "class": "parent-child"
            })
        
        # Ajouter les conjoints
        spouses = self.relationship_service.get_spouses(person_id)
        for spouse_rel in spouses:
            spouse_id = spouse_rel.person_id_2 if spouse_rel.person_id_1 == person_id else spouse_rel.person_id_1
            spouse = self.person_service.get_person(spouse_id)
            if spouse and spouse_id not in nodes:
                nodes[spouse_id] = {
                    "id": str(spouse_id),
                    "label": f"{spouse.first_name} {spouse.last_name}",
                    "class": "spouse"
                }
            edges.append({
                "id": f"{person_id}-{spouse_id}",
                "source": str(person_id),
                "target": str(spouse_id),
                "class": "couple"
            })
        
        # Ajouter les enfants
        children = self.relationship_service.get_children(person_id)
        for child_rel in children:
            child_id = child_rel.person_id_2
            child = self.person_service.get_person(child_id)
            if child and child_id not in nodes:
                nodes[child_id] = {
                    "id": str(child_id),
                    "label": f"{child.first_name} {child.last_name}",
                    "class": "child"
                }
            edges.append({
                "id": f"{person_id}-{child_id}",
                "source": str(person_id),
                "target": str(child_id),
                "class": "parent-child"
            })
        
        # Ajouter aussi les enfants des conjoints
        for spouse_rel in spouses:
            spouse_id = spouse_rel.person_id_2 if spouse_rel.person_id_1 == person_id else spouse_rel.person_id_1
            spouse_children = self.relationship_service.get_children(spouse_id)
            for child_rel in spouse_children:
                child_id = child_rel.person_id_2
                if child_id != person_id and child_id not in nodes:
                    child = self.person_service.get_person(child_id)
                    if child:
                        nodes[child_id] = {
                            "id": str(child_id),
                            "label": f"{child.first_name} {child.last_name}",
                            "class": "half-sibling"
                        }
                    edges.append({
                        "id": f"{spouse_id}-{child_id}",
                        "source": str(spouse_id),
                        "target": str(child_id),
                        "class": "parent-child"
                    })
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node, classes=node.get("class")) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge, classes=edge.get("class")) for edge in edges]
        )
    
    def build_pedigree_wheel(self, person_id: UUID, generations: int, user_id: UUID) -> CytoscapeGraph:
        """Construit l'arbre en roue (pedigree) avec positions circulaires"""
        nodes: Dict[UUID, dict] = {}
        edges: List[dict] = []
        
        def add_to_wheel(current_id: UUID, sosa_number: int, current_gen: int):
            if current_gen > generations:
                return
            
            person = self.person_service.get_person(current_id)
            if person and current_id not in nodes:
                # Calculer l'angle pour la position circulaire
                angle = (sosa_number * 360 / (2 ** current_gen)) if current_gen > 0 else 0
                radius = current_gen * 150
                import math
                x = radius * math.cos(math.radians(angle))
                y = radius * math.sin(math.radians(angle))
                
                nodes[current_id] = {
                    "id": str(current_id),
                    "label": f"{person.first_name} {person.last_name}",
                    "sosa": sosa_number,
                    "generation": current_gen,
                    "x": x,
                    "y": y
                }
            
            # Ajouter les parents
            parents = self.relationship_service.get_parents(current_id)
            for i, parent_rel in enumerate(parents[:2]):
                parent_id = parent_rel.person_id_1
                new_sosa = sosa_number * 2 + i
                if parent_id not in nodes:
                    add_to_wheel(parent_id, new_sosa, current_gen + 1)
                
                edges.append({
                    "id": f"{parent_id}-{current_id}",
                    "source": str(parent_id),
                    "target": str(current_id)
                })
        
        add_to_wheel(person_id, 1, 0)
        
        return CytoscapeGraph(
            nodes=[CytoscapeNode(data=node, position={"x": node.get("x", 0), "y": node.get("y", 0)}) for node in nodes.values()],
            edges=[CytoscapeEdge(data=edge) for edge in edges]
        )