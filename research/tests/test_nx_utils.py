"""Tests for NetworkX utilities."""

import pytest
import networkx as nx

from research.graph.schema import NodeType, EdgeType
from research.graph.nx_utils import (
    subgraph_by_node_type,
    subgraph_by_edge_type,
    spatial_subgraph,
    graph_summary,
    add_community_nodes,
)


def _make_test_graph():
    """Create a small test graph."""
    G = nx.DiGraph()
    G.add_node("room_1", node_type=NodeType.ROOM.value, label="Kitchen")
    G.add_node("room_2", node_type=NodeType.ROOM.value, label="Bedroom")
    G.add_node("door_1", node_type=NodeType.OPENING.value, label="Door")
    G.add_node("page_1", node_type=NodeType.PAGE.value, label="Page 1")
    G.add_node("claim_1", node_type=NodeType.CLAIM.value, label="area: 15sqm")

    G.add_edge("room_1", "room_2", edge_type=EdgeType.ADJACENT_TO.value)
    G.add_edge("door_1", "room_1", edge_type=EdgeType.OPENS_INTO.value)
    G.add_edge("room_1", "page_1", edge_type=EdgeType.EXTRACTED_FROM.value)
    G.add_edge("room_1", "claim_1", edge_type=EdgeType.CONTAINS.value)
    return G


class TestSubgraphByNodeType:
    def test_filter_spatial_only(self):
        G = _make_test_graph()
        sub = subgraph_by_node_type(
            G, {NodeType.ROOM.value, NodeType.OPENING.value}
        )
        assert sub.number_of_nodes() == 3
        assert "page_1" not in sub.nodes
        assert "claim_1" not in sub.nodes

    def test_empty_filter(self):
        G = _make_test_graph()
        sub = subgraph_by_node_type(G, set())
        assert sub.number_of_nodes() == 0


class TestSpatialSubgraph:
    def test_excludes_non_spatial(self):
        G = _make_test_graph()
        sub = spatial_subgraph(G)
        assert "page_1" not in sub.nodes
        assert "claim_1" not in sub.nodes
        assert "room_1" in sub.nodes
        assert "door_1" in sub.nodes


class TestSubgraphByEdgeType:
    def test_filter_edges(self):
        G = _make_test_graph()
        sub = subgraph_by_edge_type(G, {EdgeType.ADJACENT_TO.value})
        assert sub.number_of_edges() == 1
        assert sub.has_edge("room_1", "room_2")


class TestGraphSummary:
    def test_summary_structure(self):
        G = _make_test_graph()
        summary = graph_summary(G)
        assert summary["total_nodes"] == 5
        assert summary["total_edges"] == 4
        assert "Room" in summary["nodes_by_type"]
        assert summary["nodes_by_type"]["Room"] == 2
        assert "density" in summary


class TestAddCommunityNodes:
    def test_adds_communities(self):
        G = _make_test_graph()
        community_map = {"room_1": 0, "room_2": 0, "door_1": 1}
        add_community_nodes(G, community_map)

        assert "community_0" in G.nodes
        assert "community_1" in G.nodes
        assert G.nodes["community_0"]["node_type"] == NodeType.COMMUNITY.value
        assert G.has_edge("room_1", "community_0")
        assert G.has_edge("door_1", "community_1")
