from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.schemas.tree import (
    CytoscapeGraph,
    CytoscapeNode,
    CytoscapeEdge,
    SubtreeRequest,
    NeighborsRequest
)
from app.services.tree_service import TreeService
from app.services.acl_service import ACLService
from app.api.deps import get_current_user
from app.api.v1.guards.acl import require_view_access  # NOUVEAU
from app.core.exceptions import NotFoundException, PermissionDeniedException  # NOUVEAU

router = APIRouter(prefix="/tree", tags=["Tree"])


@router.get("/subtree", response_model=CytoscapeGraph)
def get_subtree(
    root_id: UUID = Query(..., description="ID de la personne racine"),
    depth: int = Query(2, ge=1, le=5, description="Profondeur maximum"),
    include_spouses: bool = Query(True, description="Inclure les conjoints"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """
    Récupère un sous-arbre à partir d'une personne racine.
    Format compatible Cytoscape.js.
    """
    tree_service = TreeService(db)
    
    graph = tree_service.build_subtree(
        root_id=root_id,
        depth=depth,
        include_spouses=include_spouses,
        user_id=current_user.id
    )
    
    return graph


@router.get("/neighbors", response_model=CytoscapeGraph)
def get_neighbors(
    person_id: UUID = Query(..., description="ID de la personne centrale"),
    radius: int = Query(1, ge=1, le=3, description="Rayon (nombre de relations)"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """
    Récupère les voisins d'une personne (parents, enfants, conjoints).
    Format compatible Cytoscape.js.
    """
    tree_service = TreeService(db)
    
    graph = tree_service.build_neighbors_graph(
        person_id=person_id,
        radius=radius,
        user_id=current_user.id
    )
    
    return graph


@router.get("/ancestors/{person_id}", response_model=CytoscapeGraph)
def get_ancestors(
    person_id: UUID,
    generations: int = Query(4, ge=1, le=8, description="Nombre de générations"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """Récupère les ascendants d'une personne (format arbre généalogique classique)"""
    tree_service = TreeService(db)
    
    graph = tree_service.build_ancestors_tree(
        person_id=person_id,
        generations=generations,
        user_id=current_user.id
    )
    
    return graph


@router.get("/descendants/{person_id}", response_model=CytoscapeGraph)
def get_descendants(
    person_id: UUID,
    generations: int = Query(3, ge=1, le=6, description="Nombre de générations"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """Récupère les descendants d'une personne"""
    tree_service = TreeService(db)
    
    graph = tree_service.build_descendants_tree(
        person_id=person_id,
        generations=generations,
        user_id=current_user.id
    )
    
    return graph


@router.get("/path/{from_id}/{to_id}", response_model=CytoscapeGraph)
def get_relationship_path(
    from_id: UUID,
    to_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trouve le chemin de parenté entre deux personnes"""
    tree_service = TreeService(db)
    acl_service = ACLService(db, current_user)
    
    if not acl_service.can_view_person(from_id) or not acl_service.can_view_person(to_id):
        raise PermissionDeniedException("view", "person")
    
    graph = tree_service.find_path_between(
        person_id_1=from_id,
        person_id_2=to_id,
        user_id=current_user.id
    )
    
    return graph


@router.get("/family/{person_id}", response_model=CytoscapeGraph)
def get_family_group(
    person_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """
    Récupère le groupe familial complet d'une personne :
    - Ses parents
    - Ses conjoints
    - Ses enfants
    """
    tree_service = TreeService(db)
    
    graph = tree_service.build_family_group(
        person_id=person_id,
        user_id=current_user.id
    )
    
    return graph


@router.get("/pedigree/{person_id}", response_model=CytoscapeGraph)
def get_pedigree_roue(
    person_id: UUID,
    generations: int = Query(5, ge=1, le=8, description="Nombre de générations"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(require_view_access)  # NOUVEAU
):
    """
    Récupère l'arbre en roue (pedigree) avec les positions Sosa.
    Format spécial pour l'affichage circulaire.
    """
    tree_service = TreeService(db)
    
    graph = tree_service.build_pedigree_wheel(
        person_id=person_id,
        generations=generations,
        user_id=current_user.id
    )
    
    return graph