"""Leiden community detection wrapper.

Converts the spatial subgraph of the SN-KG to igraph format,
runs Leiden partitioning, and maps results back to NetworkX node IDs.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import networkx as nx
import igraph as ig
import leidenalg

from research.config import ResearchConfig
from research.graph.nx_utils import spatial_subgraph, nx_to_igraph, map_communities_to_nx

logger = logging.getLogger(__name__)


@dataclass
class LeidenResult:
    """Result of a Leiden community detection run."""

    community_map: dict[str, int]  # node_id -> community_id
    num_communities: int
    modularity: float
    resolution: float
    partition: object  # leidenalg partition object


def run_leiden(
    G: nx.DiGraph,
    resolution: Optional[float] = None,
    config: Optional[ResearchConfig] = None,
    use_spatial_subgraph: bool = True,
) -> LeidenResult:
    """Run Leiden community detection on the SN-KG.

    Args:
        G: The full SN-KG DiGraph.
        resolution: Leiden resolution parameter. Higher = more communities.
        config: Research configuration.
        use_spatial_subgraph: If True, only cluster spatial entity nodes.

    Returns:
        LeidenResult with community assignments and quality metrics.
    """
    cfg = config or ResearchConfig()
    res = resolution if resolution is not None else cfg.leiden_resolution

    # Extract spatial subgraph if requested
    target_graph = spatial_subgraph(G) if use_spatial_subgraph else G

    if target_graph.number_of_nodes() == 0:
        logger.warning("Empty graph — no communities to detect")
        return LeidenResult(
            community_map={}, num_communities=0,
            modularity=0.0, resolution=res, partition=None,
        )

    # Convert to undirected igraph
    ig_graph, node_list = nx_to_igraph(target_graph, directed=False)

    # Run Leiden
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=res,
        n_iterations=cfg.leiden_n_iterations,
        seed=cfg.leiden_seed,
    )

    community_map = map_communities_to_nx(G, partition, node_list)
    modularity = partition.modularity

    result = LeidenResult(
        community_map=community_map,
        num_communities=len(set(community_map.values())),
        modularity=modularity,
        resolution=res,
        partition=partition,
    )

    logger.info(
        "Leiden: %d communities, modularity=%.4f (resolution=%.2f)",
        result.num_communities, modularity, res,
    )
    return result


def resolution_sweep(
    G: nx.DiGraph,
    resolutions: Optional[list[float]] = None,
    config: Optional[ResearchConfig] = None,
) -> list[LeidenResult]:
    """Run Leiden at multiple resolution values for parameter sensitivity analysis.

    Args:
        G: The SN-KG.
        resolutions: List of resolution values to try.
        config: Research configuration.

    Returns:
        List of LeidenResult, one per resolution value.
    """
    if resolutions is None:
        resolutions = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]

    results = []
    for res in resolutions:
        result = run_leiden(G, resolution=res, config=config)
        results.append(result)
        logger.info(
            "  resolution=%.2f → %d communities, modularity=%.4f",
            res, result.num_communities, result.modularity,
        )

    return results
