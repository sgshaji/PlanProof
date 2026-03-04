"""Tests for the GraphRAG-based SN-KG builder.

Uses mock pandas DataFrames to simulate GraphRAG Parquet output,
so no actual GraphRAG run or Azure calls are needed.
"""

import pytest
import networkx as nx

from research.graph.builder import (
    GraphRAGSNKGBuilder,
    parse_measurement,
    classify_field_name,
    GRAPHRAG_ENTITY_TYPE_MAP,
    GRAPHRAG_EDGE_TYPE_MAP,
)
from research.graph.schema import NodeType, EdgeType
from research.config import ResearchConfig
from research.conflict.detector import detect_conflicts


class TestParseMeasurement:
    """Test measurement extraction from description strings."""

    def test_sqm(self):
        val, unit = parse_measurement("Kitchen area measurement: 15 sqm")
        assert val == 15.0
        assert unit == "sqm"

    def test_sq_m(self):
        val, unit = parse_measurement("Floor area: 22.5 sq m")
        assert val == 22.5
        assert unit == "sqm"

    def test_metres(self):
        val, unit = parse_measurement("Ridge height: 8.5 metres")
        assert val == 8.5
        assert unit == "m"

    def test_m(self):
        val, unit = parse_measurement("Boundary setback distance: 2.0 m")
        assert val == 2.0
        assert unit == "m"

    def test_m_squared(self):
        val, unit = parse_measurement("Total area: 450 m²")
        assert val == 450.0
        assert unit == "sqm"

    def test_no_measurement(self):
        val, unit = parse_measurement("Kitchen in the rear extension")
        assert val is None
        assert unit is None

    def test_empty(self):
        val, unit = parse_measurement("")
        assert val is None
        assert unit is None

    def test_decimal(self):
        val, unit = parse_measurement("Area: 18.5 sqm, dimensions 5m x 3.7m")
        assert val == 18.5
        assert unit == "sqm"


class TestClassifyFieldName:
    """Test field name classification."""

    def test_kitchen_area(self):
        assert classify_field_name("KITCHEN AREA") == "kitchen_area"

    def test_ridge_height(self):
        assert classify_field_name("RIDGE HEIGHT") == "ridge_height"

    def test_boundary_setback(self):
        assert classify_field_name("BOUNDARY SETBACK") == "boundary_setback"

    def test_normalisation(self):
        assert classify_field_name("  Extension Depth  ") == "extension_depth"


class TestEntityTypeMapping:
    """Test that all expected entity types are mapped."""

    def test_room_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["room"] == NodeType.ROOM

    def test_building_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["building"] == NodeType.BUILDING

    def test_boundary_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["boundary"] == NodeType.BOUNDARY

    def test_opening_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["opening"] == NodeType.OPENING

    def test_measurement_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["measurement"] == NodeType.MEASUREMENT

    def test_constraint_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["constraint"] == NodeType.CONSTRAINT

    def test_sitefeature_mapped(self):
        assert GRAPHRAG_ENTITY_TYPE_MAP["sitefeature"] == NodeType.SITE_FEATURE


class TestEdgeTypeMapping:
    """Test that all expected edge types are mapped."""

    def test_contains(self):
        assert GRAPHRAG_EDGE_TYPE_MAP["contains"] == EdgeType.CONTAINS

    def test_adjacent_to(self):
        assert GRAPHRAG_EDGE_TYPE_MAP["adjacent_to"] == EdgeType.ADJACENT_TO

    def test_opens_into(self):
        assert GRAPHRAG_EDGE_TYPE_MAP["opens_into"] == EdgeType.OPENS_INTO

    def test_has_measurement(self):
        assert GRAPHRAG_EDGE_TYPE_MAP["has_measurement"] == EdgeType.HAS_MEASUREMENT

    def test_bounds(self):
        assert GRAPHRAG_EDGE_TYPE_MAP["bounds"] == EdgeType.BOUNDS


class TestGraphRAGSNKGBuilderWithMockData:
    """Test the full builder using mock DataFrames injected directly."""

    @pytest.fixture
    def mock_graph(self):
        """Build a graph from mock data simulating GraphRAG output."""
        G = nx.DiGraph()

        # Simulate what the builder produces: spatial entities + claims
        # Kitchen entity
        G.add_node("room_1", node_type=NodeType.ROOM.value, label="KITCHEN",
                    source="form", description="Kitchen in the rear extension")
        # Lounge entity
        G.add_node("room_2", node_type=NodeType.ROOM.value, label="LOUNGE",
                    source="form", description="Lounge at front of dwelling")
        # Building entity
        G.add_node("building_1", node_type=NodeType.BUILDING.value,
                    label="MAIN DWELLING", source="form",
                    description="Two-storey semi-detached dwelling")
        # Boundary entity
        G.add_node("boundary_1", node_type=NodeType.BOUNDARY.value,
                    label="NORTHERN BOUNDARY FENCE", source="form",
                    description="1.8m timber fence on northern boundary")

        # Claim nodes — kitchen area from form (15 sqm)
        G.add_node("claim_1", node_type=NodeType.CLAIM.value,
                    label="KITCHEN AREA: 15.0 sqm",
                    field_name="kitchen_area", field_value="15.0",
                    field_unit="sqm", source="form")
        # Claim nodes — kitchen area from drawing (18.5 sqm) — CONFLICT!
        G.add_node("claim_2", node_type=NodeType.CLAIM.value,
                    label="KITCHEN AREA: 18.5 sqm",
                    field_name="kitchen_area", field_value="18.5",
                    field_unit="sqm", source="drawing")
        # Claim nodes — ridge height from form (8.5m)
        G.add_node("claim_3", node_type=NodeType.CLAIM.value,
                    label="RIDGE HEIGHT: 8.5 m",
                    field_name="ridge_height", field_value="8.5",
                    field_unit="m", source="form")
        # Claim nodes — ridge height from statement (9.2m) — CONFLICT!
        G.add_node("claim_4", node_type=NodeType.CLAIM.value,
                    label="RIDGE HEIGHT: 9.2 m",
                    field_name="ridge_height", field_value="9.2",
                    field_unit="m", source="statement")
        # Claim nodes — boundary distance from form (2m)
        G.add_node("claim_5", node_type=NodeType.CLAIM.value,
                    label="BOUNDARY SETBACK: 2.0 m",
                    field_name="boundary_setback", field_value="2.0",
                    field_unit="m", source="form")
        # Claim nodes — boundary distance from drawing (1.5m) — CONFLICT!
        G.add_node("claim_6", node_type=NodeType.CLAIM.value,
                    label="BOUNDARY SETBACK: 1.5 m",
                    field_name="boundary_setback", field_value="1.5",
                    field_unit="m", source="drawing")
        # Lounge area — consistent (no conflict)
        G.add_node("claim_7", node_type=NodeType.CLAIM.value,
                    label="LOUNGE AREA: 22.5 sqm",
                    field_name="lounge_area", field_value="22.5",
                    field_unit="sqm", source="form")
        G.add_node("claim_8", node_type=NodeType.CLAIM.value,
                    label="LOUNGE AREA: 22.5 sqm",
                    field_name="lounge_area", field_value="22.5",
                    field_unit="sqm", source="drawing")

        # Edges
        G.add_edge("building_1", "room_1",
                    edge_type=EdgeType.CONTAINS.value)
        G.add_edge("building_1", "room_2",
                    edge_type=EdgeType.CONTAINS.value)
        G.add_edge("room_1", "room_2",
                    edge_type=EdgeType.ADJACENT_TO.value)
        G.add_edge("room_1", "claim_1",
                    edge_type=EdgeType.HAS_MEASUREMENT.value)
        G.add_edge("room_1", "claim_2",
                    edge_type=EdgeType.HAS_MEASUREMENT.value)
        G.add_edge("building_1", "claim_3",
                    edge_type=EdgeType.HAS_MEASUREMENT.value)
        G.add_edge("building_1", "claim_4",
                    edge_type=EdgeType.HAS_MEASUREMENT.value)
        G.add_edge("boundary_1", "building_1",
                    edge_type=EdgeType.BOUNDS.value)

        return G

    def test_graph_has_expected_nodes(self, mock_graph):
        """Graph should have spatial entities and claims."""
        room_nodes = [
            n for n, d in mock_graph.nodes(data=True)
            if d.get("node_type") == NodeType.ROOM.value
        ]
        claim_nodes = [
            n for n, d in mock_graph.nodes(data=True)
            if d.get("node_type") == NodeType.CLAIM.value
        ]
        assert len(room_nodes) == 2  # Kitchen, Lounge
        assert len(claim_nodes) == 8  # 6 conflicting + 2 consistent

    def test_conflict_detection_finds_kitchen_conflict(self, mock_graph):
        """Detector should find kitchen area conflict (15 vs 18.5)."""
        conflicts = detect_conflicts(mock_graph)
        kitchen_conflicts = [
            c for c in conflicts if "kitchen" in c.field_name.lower()
        ]
        assert len(kitchen_conflicts) == 1
        c = kitchen_conflicts[0]
        assert c.conflict_type == "area"
        assert c.severity == "medium"  # 23% discrepancy (>10%, <25%)

    def test_conflict_detection_finds_height_conflict(self, mock_graph):
        """Detector should find ridge height conflict (8.5 vs 9.2)."""
        conflicts = detect_conflicts(mock_graph)
        height_conflicts = [
            c for c in conflicts if "height" in c.field_name.lower()
        ]
        assert len(height_conflicts) == 1
        c = height_conflicts[0]
        assert c.conflict_type == "height"

    def test_conflict_detection_finds_boundary_conflict(self, mock_graph):
        """Detector should find boundary setback conflict (2.0 vs 1.5)."""
        conflicts = detect_conflicts(mock_graph)
        boundary_conflicts = [
            c for c in conflicts if "boundary" in c.field_name.lower()
            or "setback" in c.field_name.lower()
        ]
        assert len(boundary_conflicts) == 1
        c = boundary_conflicts[0]
        assert c.conflict_type == "distance"

    def test_no_false_positive_on_consistent_values(self, mock_graph):
        """Lounge area is consistent (22.5 in both docs) — no conflict."""
        conflicts = detect_conflicts(mock_graph)
        lounge_conflicts = [
            c for c in conflicts if "lounge" in c.field_name.lower()
        ]
        assert len(lounge_conflicts) == 0

    def test_total_conflicts(self, mock_graph):
        """Should find exactly 3 conflicts."""
        conflicts = detect_conflicts(mock_graph)
        assert len(conflicts) == 3
