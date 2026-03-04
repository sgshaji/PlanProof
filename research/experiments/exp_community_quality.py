"""Experiment: Do Leiden clusters map to functional spatial units?

RQ: Do communities detected by Leiden correspond to meaningful
dwelling/spatial units (rooms, floors, buildings)?

Methodology:
1. Build SN-KG for each submission
2. Run Leiden at multiple resolutions
3. Analyze community composition and spatial coherence
4. Report: % communities that are dwelling units, modularity, coherence
"""

import json
import logging
from typing import Optional

from research.config import ResearchConfig
from research.graph.builder import SNKGBuilder
from research.community.leiden import run_leiden, resolution_sweep
from research.community.analysis import analyze_communities
from research.graph.nx_utils import graph_summary

logger = logging.getLogger(__name__)


def run_community_quality_experiment(
    submission_ids: list[int],
    config: Optional[ResearchConfig] = None,
) -> dict:
    """Run the community quality experiment.

    Args:
        submission_ids: List of submission IDs to analyze.
        config: Research configuration.

    Returns:
        Dict with experiment results.
    """
    cfg = config or ResearchConfig()
    builder = SNKGBuilder(cfg)
    results = {
        "experiment": "community_quality",
        "submissions": [],
        "resolution_sweep": [],
    }

    for sid in submission_ids:
        logger.info("Processing submission %d", sid)
        G = builder.build_for_submission(sid)
        summary = graph_summary(G)

        # Run at default resolution
        leiden_result = run_leiden(G, config=cfg)
        analysis = analyze_communities(G, leiden_result)

        submission_result = {
            "submission_id": sid,
            "graph_summary": summary,
            "num_communities": analysis.num_communities,
            "avg_community_size": analysis.avg_community_size,
            "avg_spatial_coherence": analysis.avg_spatial_coherence,
            "dwelling_unit_count": analysis.dwelling_unit_count,
            "dwelling_unit_pct": (
                analysis.dwelling_unit_count / max(analysis.num_communities, 1)
            ),
            "modularity": leiden_result.modularity,
            "communities": [
                {
                    "id": p.community_id,
                    "size": p.node_count,
                    "composition": p.composition,
                    "coherence": p.spatial_coherence,
                    "is_dwelling": p.is_dwelling_unit,
                }
                for p in analysis.profiles
            ],
        }
        results["submissions"].append(submission_result)

        # Resolution sweep for first submission
        if sid == submission_ids[0]:
            sweep = resolution_sweep(G, config=cfg)
            for lr in sweep:
                analysis = analyze_communities(G, lr)
                results["resolution_sweep"].append({
                    "resolution": lr.resolution,
                    "num_communities": lr.num_communities,
                    "modularity": lr.modularity,
                    "avg_coherence": analysis.avg_spatial_coherence,
                    "dwelling_pct": (
                        analysis.dwelling_unit_count / max(analysis.num_communities, 1)
                    ),
                })

    return results
