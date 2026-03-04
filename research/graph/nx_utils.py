"""NetworkX utilities for the SN-KG.

Provides helpers for subgraph extraction, NetworkX-to-igraph conversion
(required for Leiden community detection), and community mapping.
"""

import logging
from typing import Optional

import networkx as nx

from research.graph.schema import NodeType, EdgeType

logger = logging.getLogger(__name__)


def subgraph_by_node_type(G: nx.DiGraph, node_types: set[str]) -> nx.DiGraph:
    """Extract a subgraph containing only nodes of the specified types.

    Args:
        G: The full SN-KG.
        node_types: Set of NodeType.value strings to include.

    Returns:
        Induced subgraph with only the specified node types.
    """
    nodes = [
        n for n, attrs in G.nodes(data=True)
        if attrs.get("node_type") in node_types
    ]
    return G.subgraph(nodes).copy()


def subgraph_by_edge_type(G: nx.DiGraph, edge_types: set[str]) -> nx.DiGraph:
    """Extract a subgraph containing only edges of the specified types."""
    sub = nx.DiGraph()
    for u, v, attrs in G.edges(data=True):
        if attrs.get("edge_type") in edge_types:
            sub.add_node(u, **G.nodes[u])
            sub.add_node(v, **G.nodes[v])
            sub.add_edge(u, v, **attrs)
    return sub


def spatial_subgraph(G: nx.DiGraph) -> nx.DiGraph:
    """Extract only spatial entity nodes and spatial edges.

    This is the subgraph used for Leiden community detection — excludes
    Page, PlanningDocument, and Claim nodes.
    """
    spatial_types = {
        NodeType.ROOM.value,
        NodeType.BUILDING.value,
        NodeType.BOUNDARY.value,
        NodeType.OPENING.value,
    }
    return subgraph_by_node_type(G, spatial_types)


def nx_to_igraph(G: nx.DiGraph, directed: bool = False):
    """Convert a NetworkX graph to an igraph Graph for Leiden.

    Args:
        G: NetworkX DiGraph.
        directed: If False (default), create undirected igraph graph.

    Returns:
        Tuple of (igraph.Graph, node_id_list) where node_id_list[i]
        gives the original NetworkX node ID for igraph vertex i.
    """
    import igraph as ig

    node_list = list(G.nodes())
    node_index = {n: i for i, n in enumerate(node_list)}

    edges = []
    for u, v in G.edges():
        if u in node_index and v in node_index:
            edges.append((node_index[u], node_index[v]))

    ig_graph = ig.Graph(n=len(node_list), edges=edges, directed=directed)

    # Copy node attributes
    for attr_key in ["node_type", "label"]:
        values = [G.nodes[n].get(attr_key, "") for n in node_list]
        ig_graph.vs[attr_key] = values

    return ig_graph, node_list


def map_communities_to_nx(
    G: nx.DiGraph,
    partition,
    node_list: list[str],
) -> dict[str, int]:
    """Map Leiden partition results back to NetworkX node IDs.

    Args:
        G: The original NetworkX DiGraph.
        partition: Leiden partition result.
        node_list: Node ID mapping from nx_to_igraph.

    Returns:
        Dict mapping NetworkX node_id -> community_id.
    """
    membership = partition.membership
    community_map = {}
    for i, community_id in enumerate(membership):
        if i < len(node_list):
            nx_node_id = node_list[i]
            community_map[nx_node_id] = community_id
    return community_map


def add_community_nodes(
    G: nx.DiGraph,
    community_map: dict[str, int],
) -> nx.DiGraph:
    """Add Community nodes and IN_COMMUNITY edges to the graph.

    Args:
        G: The SN-KG (modified in place).
        community_map: Mapping of node_id -> community_id.

    Returns:
        The modified graph.
    """
    community_ids = set(community_map.values())
    for cid in community_ids:
        comm_node_id = f"community_{cid}"
        G.add_node(
            comm_node_id,
            node_type=NodeType.COMMUNITY.value,
            label=f"Community {cid}",
            community_id=cid,
        )

    for node_id, cid in community_map.items():
        comm_node_id = f"community_{cid}"
        G.add_edge(
            node_id, comm_node_id,
            edge_type=EdgeType.IN_COMMUNITY.value,
            community_id=cid,
        )

    return G


def graph_summary(G: nx.DiGraph) -> dict:
    """Generate a summary of node and edge counts by type."""
    node_counts: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        nt = attrs.get("node_type", "Unknown")
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts: dict[str, int] = {}
    for _, _, attrs in G.edges(data=True):
        et = attrs.get("edge_type", "Unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "nodes_by_type": node_counts,
        "edges_by_type": edge_counts,
        "density": nx.density(G),
        "is_weakly_connected": nx.is_weakly_connected(G) if G.number_of_nodes() > 0 else False,
        "num_weakly_connected_components": nx.number_weakly_connected_components(G),
    }
