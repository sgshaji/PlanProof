"""SN-KG (Spatial Narrative Knowledge Graph) builder.

Reads Stage 3 database outputs and constructs a typed NetworkX DiGraph
where nodes represent spatial entities and claims, and edges represent
spatial and provenance relationships.
"""

import re
import logging
from typing import Optional

import networkx as nx

from research.config import ResearchConfig
from research.db_reader import DBReader
from research.graph.schema import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge,
    MEASUREMENT_CONTEXT_TO_NODE_TYPE,
    ENTITY_NODE_TYPES,
)

logger = logging.getLogger(__name__)

# Measurement fields that indicate spatial entities
MEASUREMENT_FIELDS = {
    "area", "height", "width", "length", "depth", "distance",
    "min_distance_to_boundary", "projection_depth",
}

# Context keywords for classifying measurements
CONTEXT_KEYWORDS = {
    "area": ["area", "sqm", "sq m", "square metre", "m²", "m2"],
    "height": ["height", "ridge", "eaves", "storey", "floor"],
    "distance": ["distance", "boundary", "setback", "separation"],
}


class SNKGBuilder:
    """Builds a Spatial Narrative Knowledge Graph from Stage 3 outputs."""

    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        self.db = DBReader(self.config)
        self._node_counter = 0

    def _next_id(self, prefix: str) -> str:
        """Generate a unique node ID."""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def build_for_submission(self, submission_id: int) -> nx.DiGraph:
        """Build the SN-KG for a single submission.

        Args:
            submission_id: The submission to build the graph for.

        Returns:
            A NetworkX DiGraph with typed nodes and edges.
        """
        G = nx.DiGraph()
        self._node_counter = 0

        # Fetch all data
        submission = self.db.get_submission(submission_id)
        if submission is None:
            raise ValueError(f"Submission {submission_id} not found")

        fields = self.db.get_extracted_fields(submission_id)
        documents = self.db.get_documents(submission_id)
        geometry_features = self.db.get_geometry_features(submission_id)

        # Phase 1: Document nodes
        doc_node_map = self._add_document_nodes(G, documents)

        # Phase 2: Page nodes
        page_node_map = self._add_page_nodes(G, documents, doc_node_map)

        # Phase 3: Spatial entity nodes from extracted fields
        entity_nodes = self._add_entity_nodes_from_fields(G, fields, page_node_map)

        # Phase 4: Claim nodes from extracted fields
        self._add_claim_nodes(G, fields, page_node_map, entity_nodes)

        # Phase 5: Geometry-derived nodes and metrics
        self._add_geometry_nodes(G, geometry_features, submission_id)

        # Phase 6: Infer spatial relationships (ADJACENT_TO, OPENS_INTO)
        self._infer_spatial_edges(G)

        logger.info(
            "Built SN-KG for submission %d: %d nodes, %d edges",
            submission_id, G.number_of_nodes(), G.number_of_edges(),
        )
        return G

    def _add_document_nodes(
        self, G: nx.DiGraph, documents: list
    ) -> dict[int, str]:
        """Add PlanningDocument nodes. Returns {document_id: node_id}."""
        doc_map = {}
        for doc in documents:
            node_id = self._next_id("doc")
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.PLANNING_DOCUMENT,
                label=doc.filename or f"Document {doc.id}",
                properties={
                    "db_id": doc.id,
                    "document_type": doc.document_type,
                    "filename": doc.filename,
                    "page_count": doc.page_count,
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())
            doc_map[doc.id] = node_id
        return doc_map

    def _add_page_nodes(
        self, G: nx.DiGraph, documents: list, doc_node_map: dict[int, str]
    ) -> dict[tuple[int, int], str]:
        """Add Page nodes and CONTAINS edges. Returns {(doc_id, page_num): node_id}."""
        page_map = {}
        for doc in documents:
            pages = self.db.get_pages(doc.id)
            doc_node_id = doc_node_map.get(doc.id)
            for page in pages:
                node_id = self._next_id("page")
                node = GraphNode(
                    node_id=node_id,
                    node_type=NodeType.PAGE,
                    label=f"Page {page.page_number}",
                    properties={
                        "db_id": page.id,
                        "page_number": page.page_number,
                        "document_id": doc.id,
                    },
                )
                G.add_node(node_id, **node.to_nx_attrs())
                page_map[(doc.id, page.page_number)] = node_id

                # Document CONTAINS Page
                if doc_node_id:
                    edge = GraphEdge(doc_node_id, node_id, EdgeType.CONTAINS)
                    G.add_edge(doc_node_id, node_id, **edge.to_nx_attrs())
        return page_map

    def _add_entity_nodes_from_fields(
        self, G: nx.DiGraph, fields: list, page_node_map: dict
    ) -> dict[str, str]:
        """Add spatial entity nodes (Room, Building, Boundary, Opening) from fields.

        Returns {entity_key: node_id} for linking claims.
        """
        entity_nodes: dict[str, str] = {}

        for ef in fields:
            # Only process measurement-type fields
            if not self._is_measurement_field(ef):
                continue

            entity_key = self._extract_entity_key(ef)
            if entity_key in entity_nodes:
                continue  # Already created

            node_type = self._classify_entity_type(ef)
            node_id = self._next_id(node_type.value.lower())
            label = self._build_entity_label(ef)

            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=label,
                properties={
                    "entity_key": entity_key,
                    "source_field": ef.field_name,
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())
            entity_nodes[entity_key] = node_id

            # Link to source page via EXTRACTED_FROM
            self._link_to_page(G, node_id, ef, page_node_map)

        return entity_nodes

    def _add_claim_nodes(
        self, G: nx.DiGraph, fields: list, page_node_map: dict,
        entity_nodes: dict[str, str],
    ):
        """Add Claim nodes for extracted field values and link to entities."""
        for ef in fields:
            node_id = self._next_id("claim")
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.CLAIM,
                label=f"{ef.field_name}: {ef.field_value}",
                properties={
                    "db_id": ef.id,
                    "field_name": ef.field_name,
                    "field_value": ef.field_value,
                    "field_unit": ef.field_unit,
                    "confidence": ef.confidence,
                    "extractor": ef.extractor,
                    "conflict_flag": ef.conflict_flag,
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())

            # Link claim to its source page
            self._link_to_page(G, node_id, ef, page_node_map)

            # Link claim to its entity (if it's a measurement)
            if self._is_measurement_field(ef):
                entity_key = self._extract_entity_key(ef)
                entity_node_id = entity_nodes.get(entity_key)
                if entity_node_id:
                    edge = GraphEdge(
                        entity_node_id, node_id, EdgeType.CONTAINS,
                        properties={"relationship": "has_measurement"},
                    )
                    G.add_edge(entity_node_id, node_id, **edge.to_nx_attrs())

    def _add_geometry_nodes(
        self, G: nx.DiGraph, geometry_features: list, submission_id: int,
    ):
        """Add nodes from geometry features and spatial metrics."""
        for gf in geometry_features:
            node_type = self._geometry_type_to_node_type(gf.feature_type)
            node_id = self._next_id(node_type.value.lower())
            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=gf.feature_type,
                properties={
                    "db_id": gf.id,
                    "feature_type": gf.feature_type,
                    "source": "geometry",
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())

            # Add spatial metrics as properties
            metrics = self.db.get_spatial_metrics(gf.id)
            for sm in metrics:
                claim_id = self._next_id("claim")
                claim = GraphNode(
                    node_id=claim_id,
                    node_type=NodeType.CLAIM,
                    label=f"{sm.metric_name}: {sm.metric_value} {sm.metric_unit}",
                    properties={
                        "db_id": sm.id,
                        "field_name": sm.metric_name,
                        "field_value": str(sm.metric_value),
                        "field_unit": sm.metric_unit,
                        "source": "geometry",
                    },
                )
                G.add_node(claim_id, **claim.to_nx_attrs())
                edge = GraphEdge(
                    node_id, claim_id, EdgeType.CONTAINS,
                    properties={"relationship": "has_metric"},
                )
                G.add_edge(node_id, claim_id, **edge.to_nx_attrs())

    def _infer_spatial_edges(self, G: nx.DiGraph):
        """Infer ADJACENT_TO and OPENS_INTO edges from co-occurrence on same page."""
        # Group spatial entity nodes by page
        page_entities: dict[str, list[str]] = {}
        for node_id, attrs in G.nodes(data=True):
            if attrs.get("node_type") in (
                NodeType.ROOM.value, NodeType.BUILDING.value,
                NodeType.BOUNDARY.value, NodeType.OPENING.value,
            ):
                # Find pages this entity is linked from
                for pred in G.predecessors(node_id):
                    pred_attrs = G.nodes[pred]
                    if pred_attrs.get("node_type") == NodeType.PAGE.value:
                        page_key = pred
                        page_entities.setdefault(page_key, []).append(node_id)
                for succ in G.successors(node_id):
                    succ_attrs = G.nodes[succ]
                    if succ_attrs.get("node_type") == NodeType.PAGE.value:
                        page_key = succ
                        page_entities.setdefault(page_key, []).append(node_id)

        # Create ADJACENT_TO edges between spatial entities on the same page
        for page_key, entities in page_entities.items():
            for i, e1 in enumerate(entities):
                for e2 in entities[i + 1:]:
                    e1_type = G.nodes[e1].get("node_type")
                    e2_type = G.nodes[e2].get("node_type")

                    # Openings connect to rooms
                    if e1_type == NodeType.OPENING.value and e2_type == NodeType.ROOM.value:
                        edge = GraphEdge(e1, e2, EdgeType.OPENS_INTO)
                        G.add_edge(e1, e2, **edge.to_nx_attrs())
                    elif e2_type == NodeType.OPENING.value and e1_type == NodeType.ROOM.value:
                        edge = GraphEdge(e2, e1, EdgeType.OPENS_INTO)
                        G.add_edge(e2, e1, **edge.to_nx_attrs())
                    # Rooms/buildings on same page are adjacent
                    elif e1_type in (NodeType.ROOM.value, NodeType.BUILDING.value) and \
                         e2_type in (NodeType.ROOM.value, NodeType.BUILDING.value):
                        if not G.has_edge(e1, e2) and not G.has_edge(e2, e1):
                            edge = GraphEdge(e1, e2, EdgeType.ADJACENT_TO)
                            G.add_edge(e1, e2, **edge.to_nx_attrs())

    # --- Helpers ---

    def _is_measurement_field(self, ef) -> bool:
        """Check if an extracted field represents a measurement."""
        if ef.field_unit and ef.field_unit.strip():
            return True
        name_lower = ef.field_name.lower() if ef.field_name else ""
        return any(kw in name_lower for kw in MEASUREMENT_FIELDS)

    def _extract_entity_key(self, ef) -> str:
        """Derive a deduplication key for the spatial entity a field belongs to."""
        name = ef.field_name or ""
        # Strip measurement context to get entity identifier
        for ctx in MEASUREMENT_FIELDS:
            name = name.replace(ctx, "").replace("_", " ").strip()
        name = re.sub(r"\s+", "_", name.strip("_") or "unknown")
        return name.lower()

    def _classify_entity_type(self, ef) -> NodeType:
        """Classify the node type from field name and context."""
        name_lower = (ef.field_name or "").lower()

        # Check entity keywords
        for keyword, node_type in ENTITY_NODE_TYPES.items():
            if keyword in name_lower:
                return node_type

        # Fall back to measurement context
        for context, node_type in MEASUREMENT_CONTEXT_TO_NODE_TYPE.items():
            if context in name_lower:
                return node_type

        return NodeType.ROOM  # Default

    def _build_entity_label(self, ef) -> str:
        """Build a human-readable label for a spatial entity."""
        name = ef.field_name or "Unknown"
        # Clean up underscores and measurement suffixes
        label = name.replace("_", " ").title()
        for suffix in ["Area", "Height", "Width", "Length", "Depth", "Distance"]:
            if label.endswith(suffix):
                label = label[: -len(suffix)].strip()
        return label or name

    def _link_to_page(self, G: nx.DiGraph, node_id: str, ef, page_node_map: dict):
        """Add an EXTRACTED_FROM edge from a node to its source page."""
        if ef.evidence_id is None:
            return
        evidence = self.db.get_evidence_for_field(ef)
        if evidence is None:
            return
        page_key = (evidence.document_id, evidence.page_number)
        page_node_id = page_node_map.get(page_key)
        if page_node_id:
            edge = GraphEdge(
                node_id, page_node_id, EdgeType.EXTRACTED_FROM,
                properties={"evidence_id": evidence.id, "confidence": evidence.confidence},
            )
            G.add_edge(node_id, page_node_id, **edge.to_nx_attrs())

    def _geometry_type_to_node_type(self, feature_type: str) -> NodeType:
        """Map geometry feature types to graph node types."""
        ft = feature_type.lower()
        if "boundary" in ft or "fence" in ft:
            return NodeType.BOUNDARY
        if "extension" in ft or "room" in ft or "balcony" in ft:
            return NodeType.ROOM
        return NodeType.BUILDING
