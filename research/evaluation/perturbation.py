"""Degradation experiments for SN-KG robustness evaluation.

Provides functions to systematically degrade the graph by dropping
entities, perturbing attributes, and removing edges, then measuring
the impact on downstream compliance verdicts.
"""

import copy
import logging
import random
from typing import Optional

import networkx as nx

from research.config import ResearchConfig
from research.graph.schema import NodeType, EdgeType

logger = logging.getLogger(__name__)


def drop_entities(
    G: nx.DiGraph,
    rate: float,
    node_type: Optional[str] = None,
    seed: Optional[int] = None,
) -> nx.DiGraph:
    """Remove a fraction of entity nodes from the graph.

    Args:
        G: The SN-KG (not modified — returns a copy).
        rate: Fraction of entities to drop (0.0 to 1.0).
        node_type: If specified, only drop nodes of this type.
        seed: Random seed for reproducibility.

    Returns:
        A new graph with entities removed.
    """
    rng = random.Random(seed)
    G_copy = copy.deepcopy(G)

    entity_types = {
        NodeType.ROOM.value, NodeType.BUILDING.value,
        NodeType.BOUNDARY.value, NodeType.OPENING.value,
    }

    candidates = [
        nid for nid, attrs in G_copy.nodes(data=True)
        if attrs.get("node_type") in entity_types
        and (node_type is None or attrs.get("node_type") == node_type)
    ]

    n_drop = int(len(candidates) * rate)
    to_drop = rng.sample(candidates, min(n_drop, len(candidates)))
    G_copy.remove_nodes_from(to_drop)

    logger.info(
        "Dropped %d/%d entities (rate=%.2f, type=%s)",
        len(to_drop), len(candidates), rate, node_type or "all",
    )
    return G_copy


def perturb_attributes(
    G: nx.DiGraph,
    noise_std: float,
    attribute: str = "field_value",
    seed: Optional[int] = None,
) -> nx.DiGraph:
    """Add Gaussian noise to numeric attributes of Claim nodes.

    Args:
        G: The SN-KG (not modified — returns a copy).
        noise_std: Standard deviation of noise as fraction of value.
        attribute: The node attribute to perturb.
        seed: Random seed for reproducibility.

    Returns:
        A new graph with perturbed attributes.
    """
    rng = random.Random(seed)
    G_copy = copy.deepcopy(G)
    perturbed = 0

    for nid, attrs in G_copy.nodes(data=True):
        if attrs.get("node_type") != NodeType.CLAIM.value:
            continue
        val = attrs.get(attribute)
        if val is None:
            continue

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            continue

        noise = rng.gauss(0, abs(num_val) * noise_std)
        new_val = num_val + noise
        G_copy.nodes[nid][attribute] = str(round(new_val, 4))
        perturbed += 1

    logger.info("Perturbed %d claim attributes (noise_std=%.3f)", perturbed, noise_std)
    return G_copy


def drop_relationships(
    G: nx.DiGraph,
    rate: float,
    edge_type: Optional[str] = None,
    seed: Optional[int] = None,
) -> nx.DiGraph:
    """Remove a fraction of edges from the graph.

    Args:
        G: The SN-KG (not modified — returns a copy).
        rate: Fraction of edges to drop (0.0 to 1.0).
        edge_type: If specified, only drop edges of this type.
        seed: Random seed for reproducibility.

    Returns:
        A new graph with edges removed.
    """
    rng = random.Random(seed)
    G_copy = copy.deepcopy(G)

    candidates = [
        (u, v) for u, v, attrs in G_copy.edges(data=True)
        if edge_type is None or attrs.get("edge_type") == edge_type
    ]

    n_drop = int(len(candidates) * rate)
    to_drop = rng.sample(candidates, min(n_drop, len(candidates)))
    G_copy.remove_edges_from(to_drop)

    logger.info(
        "Dropped %d/%d edges (rate=%.2f, type=%s)",
        len(to_drop), len(candidates), rate, edge_type or "all",
    )
    return G_copy


def sweep_degradation(
    G: nx.DiGraph,
    rates: Optional[list[float]] = None,
    config: Optional[ResearchConfig] = None,
) -> list[tuple[float, nx.DiGraph]]:
    """Generate a series of degraded graphs at increasing degradation levels.

    Returns list of (rate, degraded_graph) tuples.
    """
    cfg = config or ResearchConfig()
    if rates is None:
        rates = cfg.perturbation_rates

    results = []
    for rate in rates:
        degraded = drop_entities(G, rate, seed=cfg.random_seed)
        degraded = drop_relationships(degraded, rate, seed=cfg.random_seed + 1)
        results.append((rate, degraded))

    return results
