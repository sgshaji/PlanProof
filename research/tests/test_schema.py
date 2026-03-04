"""Tests for graph schema definitions."""

import pytest

from research.graph.schema import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge,
    MEASUREMENT_CONTEXT_TO_NODE_TYPE,
    ENTITY_NODE_TYPES,
)


class TestNodeType:
    def test_all_types_defined(self):
        expected = {
            "PlanningDocument", "Room", "Building", "Boundary",
            "Opening", "Page", "Claim", "Community",
            "Measurement", "Constraint", "SiteFeature",
        }
        assert {nt.value for nt in NodeType} == expected

    def test_string_enum(self):
        assert NodeType.ROOM == "Room"
        assert isinstance(NodeType.ROOM, str)


class TestEdgeType:
    def test_all_types_defined(self):
        expected = {
            "CONTAINS", "ADJACENT_TO", "OPENS_INTO",
            "EXTRACTED_FROM", "IN_COMMUNITY", "CONTRADICTS",
            "HAS_MEASUREMENT", "BOUNDS",
        }
        assert {et.value for et in EdgeType} == expected


class TestGraphNode:
    def test_to_nx_attrs(self):
        node = GraphNode(
            node_id="room_1",
            node_type=NodeType.ROOM,
            label="Kitchen",
            properties={"area": 15.0},
        )
        attrs = node.to_nx_attrs()
        assert attrs["node_type"] == "Room"
        assert attrs["label"] == "Kitchen"
        assert attrs["area"] == 15.0

    def test_default_properties(self):
        node = GraphNode(
            node_id="test", node_type=NodeType.CLAIM, label="Test",
        )
        assert node.properties == {}


class TestGraphEdge:
    def test_to_nx_attrs(self):
        edge = GraphEdge(
            source_id="a", target_id="b",
            edge_type=EdgeType.CONTAINS,
            properties={"weight": 1.0},
        )
        attrs = edge.to_nx_attrs()
        assert attrs["edge_type"] == "CONTAINS"
        assert attrs["weight"] == 1.0


class TestMappings:
    def test_measurement_context_mapping(self):
        assert MEASUREMENT_CONTEXT_TO_NODE_TYPE["area"] == NodeType.ROOM
        assert MEASUREMENT_CONTEXT_TO_NODE_TYPE["height"] == NodeType.BUILDING
        assert MEASUREMENT_CONTEXT_TO_NODE_TYPE["distance"] == NodeType.BOUNDARY

    def test_entity_node_types(self):
        assert ENTITY_NODE_TYPES["bedroom"] == NodeType.ROOM
        assert ENTITY_NODE_TYPES["door"] == NodeType.OPENING
        assert ENTITY_NODE_TYPES["fence"] == NodeType.BOUNDARY
        assert ENTITY_NODE_TYPES["house"] == NodeType.BUILDING
