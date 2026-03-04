"""Tests for conflict detection and CONTRADICTS edge creation."""

import pytest
import networkx as nx

from research.config import ResearchConfig
from research.graph.schema import NodeType, EdgeType
from research.conflict.detector import (
    detect_conflicts,
    Conflict,
    _parse_numeric,
    _classify_conflict_type,
    _fields_are_comparable,
)
from research.conflict.contradicts import (
    add_contradicts_edges,
    get_contradicts_edges,
    conflict_summary,
)


def _make_conflict_graph():
    """Create a graph with known conflicts for testing."""
    G = nx.DiGraph()

    # Form claim: area = 50 sqm
    G.add_node("claim_form_area", **{
        "node_type": NodeType.CLAIM.value,
        "label": "area: 50 sqm",
        "field_name": "floor_area",
        "field_value": "50",
        "field_unit": "sqm",
        "source": "form",
    })

    # Drawing claim: area = 40 sqm (conflict!)
    G.add_node("claim_drawing_area", **{
        "node_type": NodeType.CLAIM.value,
        "label": "area: 40 sqm",
        "field_name": "floor_area",
        "field_value": "40",
        "field_unit": "sqm",
        "source": "geometry",
    })

    # Consistent height claims
    G.add_node("claim_height_1", **{
        "node_type": NodeType.CLAIM.value,
        "label": "height: 5.0m",
        "field_name": "ridge_height",
        "field_value": "5.0",
        "field_unit": "m",
    })
    G.add_node("claim_height_2", **{
        "node_type": NodeType.CLAIM.value,
        "label": "height: 5.05m",
        "field_name": "ridge_height",
        "field_value": "5.05",
        "field_unit": "m",
    })

    return G


class TestParseNumeric:
    def test_integer(self):
        assert _parse_numeric("42") == 42.0

    def test_float(self):
        assert _parse_numeric("3.14") == 3.14

    def test_with_unit(self):
        assert _parse_numeric("50sqm") == 50.0

    def test_non_numeric(self):
        assert _parse_numeric("hello") is None

    def test_empty(self):
        assert _parse_numeric("") is None


class TestClassifyConflictType:
    def test_area(self):
        assert _classify_conflict_type("floor_area") == "area"

    def test_height(self):
        assert _classify_conflict_type("ridge_height") == "height"

    def test_distance(self):
        assert _classify_conflict_type("distance_to_boundary") == "distance"

    def test_address(self):
        assert _classify_conflict_type("site_address") == "address"

    def test_default(self):
        assert _classify_conflict_type("applicant_name") == "value"


class TestFieldsAreComparable:
    def test_same_name(self):
        assert _fields_are_comparable("floor_area", "floor_area") is True

    def test_area_variants(self):
        assert _fields_are_comparable("floor_area", "site_area") is True

    def test_unrelated(self):
        assert _fields_are_comparable("floor_area", "applicant_name") is False


class TestDetectConflicts:
    def test_detects_area_conflict(self):
        G = _make_conflict_graph()
        cfg = ResearchConfig(area_tolerance_pct=0.10)
        conflicts = detect_conflicts(G, cfg)
        # Should detect 50 vs 40 = 20% discrepancy (> 10% tolerance)
        area_conflicts = [c for c in conflicts if c.conflict_type == "area"]
        assert len(area_conflicts) >= 1

    def test_within_tolerance_no_conflict(self):
        G = _make_conflict_graph()
        # Height: 5.0 vs 5.05 = 1% difference, within default tolerance
        cfg = ResearchConfig(height_tolerance_m=0.15)
        conflicts = detect_conflicts(G, cfg)
        height_conflicts = [c for c in conflicts if c.conflict_type == "height"]
        assert len(height_conflicts) == 0


class TestContradicts:
    def test_add_contradicts_edges(self):
        G = _make_conflict_graph()
        conflicts = [
            Conflict(
                conflict_id="test_1",
                conflict_type="area",
                claim_a_id="claim_form_area",
                claim_b_id="claim_drawing_area",
                field_name="floor_area",
                value_a="50", value_b="40",
                unit="sqm",
                discrepancy=10.0,
                discrepancy_pct=0.20,
                severity="medium",
                description="Area conflict",
            )
        ]
        add_contradicts_edges(G, conflicts)
        assert G.has_edge("claim_form_area", "claim_drawing_area")
        assert G.has_edge("claim_drawing_area", "claim_form_area")

    def test_get_contradicts_edges(self):
        G = _make_conflict_graph()
        G.add_edge("claim_form_area", "claim_drawing_area",
                    edge_type=EdgeType.CONTRADICTS.value,
                    conflict_id="c1", conflict_type="area", severity="high")
        edges = get_contradicts_edges(G)
        assert len(edges) == 1
        assert edges[0]["conflict_type"] == "area"

    def test_conflict_summary(self):
        G = _make_conflict_graph()
        G.add_edge("claim_form_area", "claim_drawing_area",
                    edge_type=EdgeType.CONTRADICTS.value,
                    conflict_id="c1", conflict_type="area", severity="high")
        summary = conflict_summary(G)
        assert summary["total_conflicts"] == 1
        assert summary["by_type"]["area"] == 1
        assert summary["by_severity"]["high"] == 1
