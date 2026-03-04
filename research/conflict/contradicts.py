"""CONTRADICTS edge creation for detected conflicts.

Takes detected conflicts and adds CONTRADICTS edges to the SN-KG,
enriched with discrepancy magnitude and severity metadata.
"""

import logging

import networkx as nx

from research.graph.schema import EdgeType
from research.conflict.detector import Conflict

logger = logging.getLogger(__name__)


def add_contradicts_edges(
    G: nx.DiGraph,
    conflicts: list[Conflict],
) -> nx.DiGraph:
    """Add CONTRADICTS edges to the graph for each detected conflict.

    Args:
        G: The SN-KG (modified in place).
        conflicts: List of Conflict objects from the detector.

    Returns:
        The modified graph with CONTRADICTS edges.
    """
    added = 0
    for conflict in conflicts:
        if conflict.claim_a_id not in G.nodes or conflict.claim_b_id not in G.nodes:
            logger.warning(
                "Skipping conflict %s: node(s) not in graph", conflict.conflict_id
            )
            continue

        # Add bidirectional CONTRADICTS edges
        attrs = {
            "edge_type": EdgeType.CONTRADICTS.value,
            "conflict_id": conflict.conflict_id,
            "conflict_type": conflict.conflict_type,
            "discrepancy": conflict.discrepancy,
            "discrepancy_pct": conflict.discrepancy_pct,
            "severity": conflict.severity,
            "description": conflict.description,
        }

        G.add_edge(conflict.claim_a_id, conflict.claim_b_id, **attrs)
        G.add_edge(conflict.claim_b_id, conflict.claim_a_id, **attrs)
        added += 1

    logger.info("Added %d CONTRADICTS edge pairs to graph", added)
    return G


def get_contradicts_edges(G: nx.DiGraph) -> list[dict]:
    """Extract all CONTRADICTS edges from the graph.

    Returns:
        List of dicts with edge attributes for each CONTRADICTS edge.
    """
    edges = []
    seen = set()
    for u, v, attrs in G.edges(data=True):
        if attrs.get("edge_type") == EdgeType.CONTRADICTS.value:
            conflict_id = attrs.get("conflict_id", "")
            if conflict_id not in seen:
                seen.add(conflict_id)
                edges.append({
                    "source": u,
                    "target": v,
                    **attrs,
                })
    return edges


def conflict_summary(G: nx.DiGraph) -> dict:
    """Summarize conflicts in the graph by type and severity."""
    edges = get_contradicts_edges(G)

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for e in edges:
        ct = e.get("conflict_type", "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1
        sev = e.get("severity", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total_conflicts": len(edges),
        "by_type": by_type,
        "by_severity": by_severity,
    }
