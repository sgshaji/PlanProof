"""SN-KG (Spatial Narrative Knowledge Graph) builders.

Two builders:
  - GraphRAGSNKGBuilder: Reads GraphRAG Parquet output (primary, for research pipeline)
  - DBSNKGBuilder: Reads Stage 3 database outputs (legacy, for production pipeline)
"""

import re
import logging
from pathlib import Path
from typing import Optional

import networkx as nx

from research.config import ResearchConfig
from research.graph.schema import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge,
    ENTITY_NODE_TYPES,
)

logger = logging.getLogger(__name__)

# --- GraphRAG entity type → SN-KG NodeType mapping ---

GRAPHRAG_ENTITY_TYPE_MAP: dict[str, NodeType] = {
    "room": NodeType.ROOM,
    "building": NodeType.BUILDING,
    "boundary": NodeType.BOUNDARY,
    "opening": NodeType.OPENING,
    "measurement": NodeType.MEASUREMENT,
    "constraint": NodeType.CONSTRAINT,
    "sitefeature": NodeType.SITE_FEATURE,
}

# --- GraphRAG relationship type → SN-KG EdgeType mapping ---

GRAPHRAG_EDGE_TYPE_MAP: dict[str, EdgeType] = {
    "contains": EdgeType.CONTAINS,
    "adjacent_to": EdgeType.ADJACENT_TO,
    "opens_into": EdgeType.OPENS_INTO,
    "has_measurement": EdgeType.HAS_MEASUREMENT,
    "bounds": EdgeType.BOUNDS,
    "extracted_from": EdgeType.EXTRACTED_FROM,
    "serves": EdgeType.CONTAINS,  # closest semantic match
    "overlooks": EdgeType.ADJACENT_TO,  # closest semantic match
    "accesses": EdgeType.OPENS_INTO,  # closest semantic match
}

# Regex patterns for extracting measurements from descriptions
MEASUREMENT_PATTERNS = [
    # "15 sqm", "18.5 sq m", "22.5 m²", "10 m2"
    r"(\d+\.?\d*)\s*(sqm|sq\s*m|m²|m2)",
    # "4.5m", "2.1 m", "8.5 metres"
    r"(\d+\.?\d*)\s*(m|metres?|meters?)\b",
    # "4m x 3.7m" — captures first dimension
    r"(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m",
]

# Field name classification from entity names
FIELD_NAME_PATTERNS = {
    "area": r"(?:area|floor\s*area|sqm|square)",
    "height": r"(?:height|ridge|eaves|storey)",
    "distance": r"(?:distance|setback|boundary|separation)",
    "width": r"(?:width)",
    "depth": r"(?:depth|projection)",
    "length": r"(?:length)",
}


class GraphRAGSNKGBuilder:
    """Builds SN-KG from GraphRAG Parquet output files."""

    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        self.workspace = Path(self.config.graphrag_workspace_path)
        self.output_dir = self.workspace / "output"
        self._node_counter = 0

    def _next_id(self, prefix: str) -> str:
        """Generate a unique node ID."""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def build(self) -> nx.DiGraph:
        """Build the full SN-KG from GraphRAG outputs."""
        import pandas as pd

        G = nx.DiGraph()
        self._node_counter = 0

        # Load Parquet files
        entities_df = self._load_parquet("entities")
        relationships_df = self._load_parquet("relationships")
        text_units_df = self._load_parquet("text_units")

        # Build document provenance mapping
        doc_source_map = self._build_doc_source_map(text_units_df)

        # Phase 1: Add entity nodes (Room, Building, Boundary, Opening, etc.)
        entity_id_map = self._add_entity_nodes(G, entities_df, doc_source_map)

        # Phase 2: Add relationship edges
        self._add_relationship_edges(G, relationships_df, entity_id_map)

        # Phase 3: Extract Claim nodes from Measurement entities
        self._extract_claims(G, entities_df, entity_id_map, doc_source_map)

        # Phase 4: Add community data if available
        self._add_community_data(G, entity_id_map)

        logger.info(
            "Built SN-KG from GraphRAG: %d nodes, %d edges",
            G.number_of_nodes(), G.number_of_edges(),
        )
        return G

    def _load_parquet(self, name: str):
        """Load a Parquet file from the GraphRAG output directory."""
        import pandas as pd

        path = self.output_dir / f"{name}.parquet"
        if not path.exists():
            logger.warning("Parquet file not found: %s", path)
            return pd.DataFrame()
        df = pd.read_parquet(path)
        logger.info("Loaded %s: %d rows", name, len(df))
        return df

    def _build_doc_source_map(self, text_units_df) -> dict[str, str]:
        """Map text_unit IDs to source document filenames.

        Returns {text_unit_id: source_type} where source_type is
        inferred from the filename (e.g. "form", "statement", "drawing").
        """
        source_map: dict[str, str] = {}
        if text_units_df.empty:
            return source_map

        for _, row in text_units_df.iterrows():
            tu_id = str(row.get("id", ""))
            doc_ids = row.get("document_ids", [])
            if not doc_ids:
                continue
            # Document ID is typically the filename
            doc_id = str(doc_ids[0]) if isinstance(doc_ids, list) else str(doc_ids)
            source_type = self._classify_source_type(doc_id)
            source_map[tu_id] = source_type

        return source_map

    def _classify_source_type(self, filename: str) -> str:
        """Classify a document filename into a source type."""
        fn = filename.lower()
        if "form" in fn or "application" in fn:
            return "form"
        if "statement" in fn or "planning" in fn:
            return "statement"
        if "floor" in fn or "plan" in fn or "drawing" in fn or "elevation" in fn:
            return "drawing"
        return "document"

    def _add_entity_nodes(
        self, G: nx.DiGraph, entities_df, doc_source_map: dict
    ) -> dict[str, str]:
        """Add entity nodes to the graph.

        Returns {graphrag_entity_id: snkg_node_id} mapping.
        """
        entity_id_map: dict[str, str] = {}
        if entities_df.empty:
            return entity_id_map

        for _, row in entities_df.iterrows():
            graphrag_id = str(row.get("id", ""))
            name = str(row.get("name", "")).strip()
            entity_type_str = str(row.get("type", "")).strip().lower()
            description = str(row.get("description", ""))

            # Map to SN-KG NodeType
            node_type = GRAPHRAG_ENTITY_TYPE_MAP.get(entity_type_str)
            if node_type is None:
                # Try keyword matching on the entity name
                node_type = self._classify_entity_by_name(name)

            # Skip Measurement entities here — they become Claims in Phase 3
            if node_type == NodeType.MEASUREMENT:
                entity_id_map[graphrag_id] = graphrag_id  # placeholder
                continue

            node_id = self._next_id(node_type.value.lower())
            entity_id_map[graphrag_id] = node_id

            # Determine source document
            source = self._get_entity_source(row, doc_source_map)

            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=name,
                properties={
                    "graphrag_id": graphrag_id,
                    "description": description,
                    "source": source,
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())

        return entity_id_map

    def _add_relationship_edges(
        self, G: nx.DiGraph, relationships_df, entity_id_map: dict
    ):
        """Add edges from GraphRAG relationships."""
        if relationships_df.empty:
            return

        for _, row in relationships_df.iterrows():
            source_name = str(row.get("source", "")).strip()
            target_name = str(row.get("target", "")).strip()
            rel_type_str = str(row.get("type", "")).strip().lower()
            description = str(row.get("description", ""))
            weight = row.get("weight", 1.0)

            # Find node IDs — GraphRAG uses entity names as references
            source_id = self._find_node_by_name(G, source_name)
            target_id = self._find_node_by_name(G, target_name)

            if not source_id or not target_id:
                continue

            edge_type = GRAPHRAG_EDGE_TYPE_MAP.get(rel_type_str, EdgeType.CONTAINS)

            edge = GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                properties={
                    "description": description,
                    "weight": float(weight) if weight else 1.0,
                },
            )
            G.add_edge(source_id, target_id, **edge.to_nx_attrs())

    def _extract_claims(
        self, G: nx.DiGraph, entities_df, entity_id_map: dict,
        doc_source_map: dict,
    ):
        """Extract Claim nodes from Measurement entities.

        Each Measurement entity becomes a Claim node with parsed
        field_name, field_value, and field_unit attributes.
        """
        if entities_df.empty:
            return

        measurement_entities = entities_df[
            entities_df.get("type", entities_df.iloc[:, 0]).astype(str).str.lower()
            == "measurement"
        ] if "type" in entities_df.columns else entities_df.iloc[0:0]

        for _, row in measurement_entities.iterrows():
            graphrag_id = str(row.get("id", ""))
            name = str(row.get("name", "")).strip()
            description = str(row.get("description", ""))
            source = self._get_entity_source(row, doc_source_map)

            # Parse measurement from description
            value, unit = parse_measurement(description)
            field_name = classify_field_name(name)

            claim_id = self._next_id("claim")
            entity_id_map[graphrag_id] = claim_id

            node = GraphNode(
                node_id=claim_id,
                node_type=NodeType.CLAIM,
                label=f"{name}: {value} {unit}" if value else name,
                properties={
                    "graphrag_id": graphrag_id,
                    "field_name": field_name,
                    "field_value": str(value) if value is not None else "",
                    "field_unit": unit or "",
                    "source": source,
                    "description": description,
                },
            )
            G.add_node(claim_id, **node.to_nx_attrs())

    def _add_community_data(self, G: nx.DiGraph, entity_id_map: dict):
        """Add community assignments from GraphRAG's Leiden output."""
        import pandas as pd

        communities_path = self.output_dir / "communities.parquet"
        if not communities_path.exists():
            return

        communities_df = pd.read_parquet(communities_path)
        if communities_df.empty:
            return

        for _, row in communities_df.iterrows():
            community_id = str(row.get("id", row.get("community", "")))
            title = str(row.get("title", f"Community {community_id}"))

            comm_node_id = self._next_id("community")
            node = GraphNode(
                node_id=comm_node_id,
                node_type=NodeType.COMMUNITY,
                label=title,
                properties={"community_id": community_id},
            )
            G.add_node(comm_node_id, **node.to_nx_attrs())

    def _classify_entity_by_name(self, name: str) -> NodeType:
        """Classify entity type from its name using keyword matching."""
        name_lower = name.lower()
        for keyword, node_type in ENTITY_NODE_TYPES.items():
            if keyword in name_lower:
                return node_type
        return NodeType.BUILDING  # Default for unclassified

    def _get_entity_source(self, row, doc_source_map: dict) -> str:
        """Get the source document type for an entity."""
        text_unit_ids = row.get("text_unit_ids", [])
        if not text_unit_ids:
            return "unknown"
        if isinstance(text_unit_ids, str):
            text_unit_ids = [text_unit_ids]
        for tu_id in text_unit_ids:
            source = doc_source_map.get(str(tu_id))
            if source:
                return source
        return "unknown"

    def _find_node_by_name(self, G: nx.DiGraph, name: str) -> Optional[str]:
        """Find a node ID by its label (case-insensitive)."""
        name_lower = name.lower()
        for node_id, attrs in G.nodes(data=True):
            if attrs.get("label", "").lower() == name_lower:
                return node_id
        return None


# --- Utility functions (used by builder and tests) ---

def parse_measurement(description: str) -> tuple[Optional[float], Optional[str]]:
    """Parse a numeric measurement and unit from a description string.

    Returns (value, unit) or (None, None) if no measurement found.
    """
    if not description:
        return None, None

    for pattern in MEASUREMENT_PATTERNS:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                unit = match.group(2).strip().lower()
                # Normalise units
                if unit in ("sq m", "m²", "m2"):
                    unit = "sqm"
                if unit in ("metres", "meters", "metre", "meter"):
                    unit = "m"
                return value, unit
            except (ValueError, IndexError):
                continue

    return None, None


def classify_field_name(entity_name: str) -> str:
    """Classify a measurement entity name into a normalised field name.

    E.g., "KITCHEN AREA" → "kitchen_area", "RIDGE HEIGHT" → "ridge_height"
    """
    name = entity_name.lower().strip()
    # Normalise to snake_case
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name


# --- Legacy DB-based builder (preserved for production pipeline) ---

class DBSNKGBuilder:
    """Builds a Spatial Narrative Knowledge Graph from Stage 3 database outputs.

    This is the legacy builder that reads from PostgreSQL. Preserved for
    future use with the production pipeline.
    """

    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        # Lazy import to avoid DB dependency when using GraphRAG builder
        from research.db_reader import DBReader
        self.db = DBReader(self.config)
        self._node_counter = 0

    def _next_id(self, prefix: str) -> str:
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def build_for_submission(self, submission_id: int) -> nx.DiGraph:
        """Build the SN-KG for a single submission from the database."""
        from research.graph.schema import MEASUREMENT_CONTEXT_TO_NODE_TYPE

        G = nx.DiGraph()
        self._node_counter = 0

        submission = self.db.get_submission(submission_id)
        if submission is None:
            raise ValueError(f"Submission {submission_id} not found")

        fields = self.db.get_extracted_fields(submission_id)
        documents = self.db.get_documents(submission_id)
        geometry_features = self.db.get_geometry_features(submission_id)

        doc_node_map = self._add_document_nodes(G, documents)
        page_node_map = self._add_page_nodes(G, documents, doc_node_map)
        entity_nodes = self._add_entity_nodes_from_fields(G, fields, page_node_map)
        self._add_claim_nodes(G, fields, page_node_map, entity_nodes)
        self._add_geometry_nodes(G, geometry_features, submission_id)
        self._infer_spatial_edges(G)

        logger.info(
            "Built SN-KG for submission %d: %d nodes, %d edges",
            submission_id, G.number_of_nodes(), G.number_of_edges(),
        )
        return G

    def _add_document_nodes(self, G, documents):
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

    def _add_page_nodes(self, G, documents, doc_node_map):
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
                if doc_node_id:
                    edge = GraphEdge(doc_node_id, node_id, EdgeType.CONTAINS)
                    G.add_edge(doc_node_id, node_id, **edge.to_nx_attrs())
        return page_map

    def _add_entity_nodes_from_fields(self, G, fields, page_node_map):
        MEASUREMENT_FIELDS = {
            "area", "height", "width", "length", "depth", "distance",
            "min_distance_to_boundary", "projection_depth",
        }
        entity_nodes = {}
        for ef in fields:
            if not self._is_measurement_field(ef, MEASUREMENT_FIELDS):
                continue
            entity_key = self._extract_entity_key(ef, MEASUREMENT_FIELDS)
            if entity_key in entity_nodes:
                continue
            node_type = self._classify_entity_type(ef)
            node_id = self._next_id(node_type.value.lower())
            label = self._build_entity_label(ef)
            node = GraphNode(
                node_id=node_id, node_type=node_type, label=label,
                properties={"entity_key": entity_key, "source_field": ef.field_name},
            )
            G.add_node(node_id, **node.to_nx_attrs())
            entity_nodes[entity_key] = node_id
            self._link_to_page(G, node_id, ef, page_node_map)
        return entity_nodes

    def _add_claim_nodes(self, G, fields, page_node_map, entity_nodes):
        MEASUREMENT_FIELDS = {
            "area", "height", "width", "length", "depth", "distance",
            "min_distance_to_boundary", "projection_depth",
        }
        for ef in fields:
            node_id = self._next_id("claim")
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.CLAIM,
                label=f"{ef.field_name}: {ef.field_value}",
                properties={
                    "db_id": ef.id, "field_name": ef.field_name,
                    "field_value": ef.field_value, "field_unit": ef.field_unit,
                    "confidence": ef.confidence, "extractor": ef.extractor,
                    "conflict_flag": ef.conflict_flag,
                },
            )
            G.add_node(node_id, **node.to_nx_attrs())
            self._link_to_page(G, node_id, ef, page_node_map)
            if self._is_measurement_field(ef, MEASUREMENT_FIELDS):
                entity_key = self._extract_entity_key(ef, MEASUREMENT_FIELDS)
                entity_node_id = entity_nodes.get(entity_key)
                if entity_node_id:
                    edge = GraphEdge(
                        entity_node_id, node_id, EdgeType.CONTAINS,
                        properties={"relationship": "has_measurement"},
                    )
                    G.add_edge(entity_node_id, node_id, **edge.to_nx_attrs())

    def _add_geometry_nodes(self, G, geometry_features, submission_id):
        for gf in geometry_features:
            node_type = self._geometry_type_to_node_type(gf.feature_type)
            node_id = self._next_id(node_type.value.lower())
            node = GraphNode(
                node_id=node_id, node_type=node_type, label=gf.feature_type,
                properties={"db_id": gf.id, "feature_type": gf.feature_type, "source": "geometry"},
            )
            G.add_node(node_id, **node.to_nx_attrs())
            metrics = self.db.get_spatial_metrics(gf.id)
            for sm in metrics:
                claim_id = self._next_id("claim")
                claim = GraphNode(
                    node_id=claim_id, node_type=NodeType.CLAIM,
                    label=f"{sm.metric_name}: {sm.metric_value} {sm.metric_unit}",
                    properties={
                        "db_id": sm.id, "field_name": sm.metric_name,
                        "field_value": str(sm.metric_value),
                        "field_unit": sm.metric_unit, "source": "geometry",
                    },
                )
                G.add_node(claim_id, **claim.to_nx_attrs())
                edge = GraphEdge(
                    node_id, claim_id, EdgeType.CONTAINS,
                    properties={"relationship": "has_metric"},
                )
                G.add_edge(node_id, claim_id, **edge.to_nx_attrs())

    def _infer_spatial_edges(self, G):
        page_entities = {}
        for node_id, attrs in G.nodes(data=True):
            if attrs.get("node_type") in (
                NodeType.ROOM.value, NodeType.BUILDING.value,
                NodeType.BOUNDARY.value, NodeType.OPENING.value,
            ):
                for pred in G.predecessors(node_id):
                    if G.nodes[pred].get("node_type") == NodeType.PAGE.value:
                        page_entities.setdefault(pred, []).append(node_id)
                for succ in G.successors(node_id):
                    if G.nodes[succ].get("node_type") == NodeType.PAGE.value:
                        page_entities.setdefault(succ, []).append(node_id)
        for page_key, entities in page_entities.items():
            for i, e1 in enumerate(entities):
                for e2 in entities[i + 1:]:
                    e1_type = G.nodes[e1].get("node_type")
                    e2_type = G.nodes[e2].get("node_type")
                    if e1_type == NodeType.OPENING.value and e2_type == NodeType.ROOM.value:
                        edge = GraphEdge(e1, e2, EdgeType.OPENS_INTO)
                        G.add_edge(e1, e2, **edge.to_nx_attrs())
                    elif e2_type == NodeType.OPENING.value and e1_type == NodeType.ROOM.value:
                        edge = GraphEdge(e2, e1, EdgeType.OPENS_INTO)
                        G.add_edge(e2, e1, **edge.to_nx_attrs())
                    elif e1_type in (NodeType.ROOM.value, NodeType.BUILDING.value) and \
                         e2_type in (NodeType.ROOM.value, NodeType.BUILDING.value):
                        if not G.has_edge(e1, e2) and not G.has_edge(e2, e1):
                            edge = GraphEdge(e1, e2, EdgeType.ADJACENT_TO)
                            G.add_edge(e1, e2, **edge.to_nx_attrs())

    def _is_measurement_field(self, ef, measurement_fields):
        if ef.field_unit and ef.field_unit.strip():
            return True
        name_lower = ef.field_name.lower() if ef.field_name else ""
        return any(kw in name_lower for kw in measurement_fields)

    def _extract_entity_key(self, ef, measurement_fields):
        name = ef.field_name or ""
        for ctx in measurement_fields:
            name = name.replace(ctx, "").replace("_", " ").strip()
        name = re.sub(r"\s+", "_", name.strip("_") or "unknown")
        return name.lower()

    def _classify_entity_type(self, ef):
        name_lower = (ef.field_name or "").lower()
        for keyword, node_type in ENTITY_NODE_TYPES.items():
            if keyword in name_lower:
                return node_type
        from research.graph.schema import MEASUREMENT_CONTEXT_TO_NODE_TYPE
        for context, node_type in MEASUREMENT_CONTEXT_TO_NODE_TYPE.items():
            if context in name_lower:
                return node_type
        return NodeType.ROOM

    def _build_entity_label(self, ef):
        name = ef.field_name or "Unknown"
        label = name.replace("_", " ").title()
        for suffix in ["Area", "Height", "Width", "Length", "Depth", "Distance"]:
            if label.endswith(suffix):
                label = label[: -len(suffix)].strip()
        return label or name

    def _link_to_page(self, G, node_id, ef, page_node_map):
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

    def _geometry_type_to_node_type(self, feature_type):
        ft = feature_type.lower()
        if "boundary" in ft or "fence" in ft:
            return NodeType.BOUNDARY
        if "extension" in ft or "room" in ft or "balcony" in ft:
            return NodeType.ROOM
        return NodeType.BUILDING
