"""Typed graph schema for the Spatial Narrative Knowledge Graph (SN-KG).

Defines node types, edge types, and dataclasses for graph elements
used throughout the research pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NodeType(str, Enum):
    """Types of nodes in the SN-KG."""

    PLANNING_DOCUMENT = "PlanningDocument"
    ROOM = "Room"
    BUILDING = "Building"
    BOUNDARY = "Boundary"
    OPENING = "Opening"
    PAGE = "Page"
    CLAIM = "Claim"
    COMMUNITY = "Community"
    MEASUREMENT = "Measurement"
    CONSTRAINT = "Constraint"
    SITE_FEATURE = "SiteFeature"


class EdgeType(str, Enum):
    """Types of edges in the SN-KG."""

    CONTAINS = "CONTAINS"
    ADJACENT_TO = "ADJACENT_TO"
    OPENS_INTO = "OPENS_INTO"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    IN_COMMUNITY = "IN_COMMUNITY"
    CONTRADICTS = "CONTRADICTS"
    HAS_MEASUREMENT = "HAS_MEASUREMENT"
    BOUNDS = "BOUNDS"


@dataclass
class GraphNode:
    """A node in the SN-KG."""

    node_id: str
    node_type: NodeType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_nx_attrs(self) -> dict[str, Any]:
        """Return attributes dict for NetworkX."""
        return {
            "node_type": self.node_type.value,
            "label": self.label,
            **self.properties,
        }


@dataclass
class GraphEdge:
    """An edge in the SN-KG."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = field(default_factory=dict)

    def to_nx_attrs(self) -> dict[str, Any]:
        """Return attributes dict for NetworkX."""
        return {
            "edge_type": self.edge_type.value,
            **self.properties,
        }


# Measurement context to node type mapping
MEASUREMENT_CONTEXT_TO_NODE_TYPE: dict[str, NodeType] = {
    "area": NodeType.ROOM,
    "height": NodeType.BUILDING,
    "width": NodeType.ROOM,
    "length": NodeType.ROOM,
    "depth": NodeType.ROOM,
    "distance": NodeType.BOUNDARY,
}

# Spatial entity keywords mapped to node types
ENTITY_NODE_TYPES: dict[str, NodeType] = {
    "room": NodeType.ROOM,
    "bedroom": NodeType.ROOM,
    "bathroom": NodeType.ROOM,
    "kitchen": NodeType.ROOM,
    "living_room": NodeType.ROOM,
    "lounge": NodeType.ROOM,
    "hallway": NodeType.ROOM,
    "corridor": NodeType.ROOM,
    "garage": NodeType.ROOM,
    "utility": NodeType.ROOM,
    "extension": NodeType.ROOM,
    "loft": NodeType.ROOM,
    "dormer": NodeType.ROOM,
    "conservatory": NodeType.ROOM,
    "building": NodeType.BUILDING,
    "house": NodeType.BUILDING,
    "dwelling": NodeType.BUILDING,
    "property": NodeType.BUILDING,
    "boundary": NodeType.BOUNDARY,
    "fence": NodeType.BOUNDARY,
    "wall": NodeType.BOUNDARY,
    "door": NodeType.OPENING,
    "window": NodeType.OPENING,
    "gate": NodeType.OPENING,
}
