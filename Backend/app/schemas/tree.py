from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

class CytoscapeNode(BaseModel):
    data: Dict[str, Any]
    position: Optional[Dict[str, float]] = None
    classes: Optional[str] = None

class CytoscapeEdge(BaseModel):
    data: Dict[str, Any]
    classes: Optional[str] = None

class CytoscapeGraph(BaseModel):
    nodes: List[CytoscapeNode]
    edges: List[CytoscapeEdge]

class SubtreeRequest(BaseModel):
    root_id: UUID
    depth: int = 2
    include_spouses: bool = True

class NeighborsRequest(BaseModel):
    person_id: UUID
    radius: int = 1