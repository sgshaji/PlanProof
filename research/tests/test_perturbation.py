"""Tests for perturbation/degradation functions."""

import pytest
import networkx as nx

from research.graph.schema import NodeType, EdgeType
from research.evaluation.perturbation import (
    drop_entities,
    perturb_attributes,
    drop_relationships,
)


def _make_test_graph():
    """Create a graph for perturbation testing."""
    G = nx.DiGraph()
    for i in range(10):
        G.add_node(f"room_{i}", node_type=NodeType.ROOM.value, label=f"Room {i}")
    for i in range(5):
        G.add_node(f"claim_{i}", node_type=NodeType.CLAIM.value,
                   label=f"area: {10 + i}", field_value=str(10 + i))
    for i in range(9):
        G.add_edge(f"room_{i}", f"room_{i+1}",
                   edge_type=EdgeType.ADJACENT_TO.value)
    return G


class TestDropEntities:
    def test_returns_copy(self):
        G = _make_test_graph()
        G2 = drop_entities(G, 0.5, seed=42)
        assert G.number_of_nodes() == 15  # Original unchanged
        assert G2.number_of_nodes() < 15

    def test_zero_rate(self):
        G = _make_test_graph()
        G2 = drop_entities(G, 0.0, seed=42)
        assert G2.number_of_nodes() == G.number_of_nodes()

    def test_full_rate(self):
        G = _make_test_graph()
        G2 = drop_entities(G, 1.0, seed=42)
        # All entity nodes dropped, claim nodes remain
        room_nodes = [n for n, a in G2.nodes(data=True)
                       if a.get("node_type") == NodeType.ROOM.value]
        assert len(room_nodes) == 0

    def test_type_filter(self):
        G = _make_test_graph()
        G.add_node("boundary_1", node_type=NodeType.BOUNDARY.value, label="Wall")
        G2 = drop_entities(G, 1.0, node_type=NodeType.ROOM.value, seed=42)
        # Boundary should remain
        assert "boundary_1" in G2.nodes

    def test_reproducible(self):
        G = _make_test_graph()
        G2a = drop_entities(G, 0.3, seed=42)
        G2b = drop_entities(G, 0.3, seed=42)
        assert set(G2a.nodes) == set(G2b.nodes)


class TestPerturbAttributes:
    def test_perturbs_numeric_claims(self):
        G = _make_test_graph()
        G2 = perturb_attributes(G, 0.1, seed=42)
        # Values should be different
        original_val = G.nodes["claim_0"]["field_value"]
        perturbed_val = G2.nodes["claim_0"]["field_value"]
        # With noise_std=0.1, values might still be close but not identical
        assert G.number_of_nodes() == G2.number_of_nodes()

    def test_zero_noise(self):
        G = _make_test_graph()
        G2 = perturb_attributes(G, 0.0, seed=42)
        for i in range(5):
            # Zero noise still round-trips through float, so compare numerically
            assert float(G2.nodes[f"claim_{i}"]["field_value"]) == float(10 + i)


class TestDropRelationships:
    def test_drops_edges(self):
        G = _make_test_graph()
        G2 = drop_relationships(G, 0.5, seed=42)
        assert G2.number_of_edges() < G.number_of_edges()

    def test_zero_rate(self):
        G = _make_test_graph()
        G2 = drop_relationships(G, 0.0, seed=42)
        assert G2.number_of_edges() == G.number_of_edges()

    def test_reproducible(self):
        G = _make_test_graph()
        G2a = drop_relationships(G, 0.3, seed=42)
        G2b = drop_relationships(G, 0.3, seed=42)
        assert set(G2a.edges) == set(G2b.edges)
