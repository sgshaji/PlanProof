"""Community analysis for SN-KG Leiden partitions.

Provides tools to analyze community composition, spatial coherence,
dwelling unit heuristics, and community-level compliance aggregation.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from research.graph.schema import NodeType, EdgeType
from research.community.leiden import LeidenResult

logger = logging.getLogger(__name__)


@dataclass
class CommunityProfile:
    """Profile of a single community."""

    community_id: int
    node_ids: list[str]
    node_count: int
    composition: dict[str, int]  # node_type -> count
    spatial_coherence: float  # intra-community edge ratio
    is_dwelling_unit: bool  # heuristic: contains rooms on same floor
    compliance_summary: Optional[dict] = None


@dataclass
class CommunityAnalysisResult:
    """Result of full community analysis."""

    profiles: list[CommunityProfile]
    num_communities: int
    avg_community_size: float
    avg_spatial_coherence: float
    dwelling_unit_count: int


def analyze_communities(
    G: nx.DiGraph,
    leiden_result: LeidenResult,
) -> CommunityAnalysisResult:
    """Analyze community structure of the partitioned SN-KG.

    Args:
        G: The SN-KG with all node types.
        leiden_result: Result from Leiden community detection.

    Returns:
        CommunityAnalysisResult with per-community profiles.
    """
    community_map = leiden_result.community_map

    # Group nodes by community
    communities: dict[int, list[str]] = {}
    for node_id, cid in community_map.items():
        communities.setdefault(cid, []).append(node_id)

    profiles = []
    for cid, node_ids in sorted(communities.items()):
        composition = _compute_composition(G, node_ids)
        coherence = _compute_spatial_coherence(G, node_ids)
        is_dwelling = _is_dwelling_unit(G, node_ids, composition)

        profile = CommunityProfile(
            community_id=cid,
            node_ids=node_ids,
            node_count=len(node_ids),
            composition=composition,
            spatial_coherence=coherence,
            is_dwelling_unit=is_dwelling,
        )
        profiles.append(profile)

    avg_size = sum(p.node_count for p in profiles) / max(len(profiles), 1)
    avg_coherence = sum(p.spatial_coherence for p in profiles) / max(len(profiles), 1)
    dwelling_count = sum(1 for p in profiles if p.is_dwelling_unit)

    result = CommunityAnalysisResult(
        profiles=profiles,
        num_communities=len(profiles),
        avg_community_size=avg_size,
        avg_spatial_coherence=avg_coherence,
        dwelling_unit_count=dwelling_count,
    )

    logger.info(
        "Community analysis: %d communities, avg size=%.1f, "
        "avg coherence=%.3f, %d dwelling units",
        result.num_communities, avg_size, avg_coherence, dwelling_count,
    )
    return result


def aggregate_compliance_by_community(
    G: nx.DiGraph,
    leiden_result: LeidenResult,
    validation_checks: list,
) -> dict[int, dict]:
    """Aggregate validation results at the community level.

    Maps each validation check to the community containing its related
    spatial entities, then aggregates pass/fail/warning counts.

    Args:
        G: The SN-KG.
        leiden_result: Leiden partition result.
        validation_checks: List of ValidationCheck ORM objects.

    Returns:
        Dict mapping community_id -> {pass: n, fail: n, warning: n, total: n}.
    """
    community_map = leiden_result.community_map
    results: dict[int, dict] = {}

    # Build a lookup from claim field_name to community
    claim_to_community: dict[str, int] = {}
    for node_id, attrs in G.nodes(data=True):
        if attrs.get("node_type") == NodeType.CLAIM.value:
            field_name = attrs.get("field_name", "")
            cid = community_map.get(node_id)
            if cid is not None:
                claim_to_community[field_name] = cid
            else:
                # Check if the claim's parent entity is in a community
                for pred in G.predecessors(node_id):
                    if pred in community_map:
                        claim_to_community[field_name] = community_map[pred]
                        break

    # Aggregate checks by community
    for vc in validation_checks:
        # Try to find which community this check relates to
        cid = None
        if hasattr(vc, "rule") and vc.rule and hasattr(vc.rule, "required_fields"):
            req_fields = vc.rule.required_fields or []
            for rf in req_fields:
                if rf in claim_to_community:
                    cid = claim_to_community[rf]
                    break

        if cid is None:
            cid = -1  # Unassigned

        if cid not in results:
            results[cid] = {"pass": 0, "fail": 0, "warning": 0, "needs_review": 0, "total": 0}

        status = vc.status.value if hasattr(vc.status, "value") else str(vc.status)
        if status in results[cid]:
            results[cid][status] += 1
        results[cid]["total"] += 1

    return results


def _compute_composition(G: nx.DiGraph, node_ids: list[str]) -> dict[str, int]:
    """Count nodes by type within a community."""
    counts: dict[str, int] = {}
    for nid in node_ids:
        if nid in G.nodes:
            nt = G.nodes[nid].get("node_type", "Unknown")
            counts[nt] = counts.get(nt, 0) + 1
    return counts


def _compute_spatial_coherence(G: nx.DiGraph, node_ids: list[str]) -> float:
    """Compute spatial coherence as ratio of intra-community edges to total edges.

    Higher coherence means the community is internally well-connected.
    """
    node_set = set(node_ids)
    if len(node_set) < 2:
        return 1.0

    intra_edges = 0
    total_edges = 0

    for nid in node_ids:
        if nid not in G.nodes:
            continue
        for _, target in G.out_edges(nid):
            total_edges += 1
            if target in node_set:
                intra_edges += 1
        for source, _ in G.in_edges(nid):
            if source not in node_set:
                total_edges += 1

    if total_edges == 0:
        return 0.0
    return intra_edges / total_edges


def _is_dwelling_unit(
    G: nx.DiGraph, node_ids: list[str], composition: dict[str, int]
) -> bool:
    """Heuristic: a community is a dwelling unit if it contains
    multiple rooms, suggesting a functional spatial grouping."""
    room_count = composition.get(NodeType.ROOM.value, 0)
    has_rooms = room_count >= 2

    # Check for adjacency edges between rooms
    room_nodes = [
        nid for nid in node_ids
        if G.nodes.get(nid, {}).get("node_type") == NodeType.ROOM.value
    ]
    has_adjacency = False
    for i, r1 in enumerate(room_nodes):
        for r2 in room_nodes[i + 1:]:
            if G.has_edge(r1, r2) or G.has_edge(r2, r1):
                has_adjacency = True
                break
        if has_adjacency:
            break

    return has_rooms and has_adjacency
