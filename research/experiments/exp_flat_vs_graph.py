"""Experiment: Flat vs graph-structured compliance comparison.

RQ: Does community-structured graph compliance outperform flat compliance?

Methodology:
1. For each annotated submission:
   a. Get Stage 3 flat validation results
   b. Build SN-KG, run Leiden, detect conflicts
   c. Compare both against ground truth expected verdicts
   d. Report per-rule accuracy, F1, and improvement
"""

import logging
from typing import Optional

from research.config import ResearchConfig
from research.db_reader import DBReader
from research.graph.builder import SNKGBuilder
from research.community.leiden import run_leiden
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.evaluation.comparison import compare_flat_vs_graph

logger = logging.getLogger(__name__)


def run_flat_vs_graph_experiment(
    submission_ids: list[int],
    ground_truths: dict[int, GroundTruthAnnotation],
    flat_results_by_submission: dict[int, list[dict]],
    config: Optional[ResearchConfig] = None,
) -> dict:
    """Run the flat vs graph comparison experiment.

    Args:
        submission_ids: Submissions to analyze.
        ground_truths: Dict mapping submission_id -> GroundTruthAnnotation.
        flat_results_by_submission: Dict mapping submission_id -> flat validation results.
        config: Research configuration.

    Returns:
        Dict with comparison results.
    """
    cfg = config or ResearchConfig()
    builder = SNKGBuilder(cfg)
    results = {
        "experiment": "flat_vs_graph",
        "submissions": [],
        "aggregate": {},
    }

    total_flat_f1 = 0.0
    total_graph_f1 = 0.0
    total_improvements = 0.0
    count = 0

    for sid in submission_ids:
        gt = ground_truths.get(sid)
        flat_results = flat_results_by_submission.get(sid, [])

        if gt is None:
            logger.warning("No ground truth for submission %d, skipping", sid)
            continue

        logger.info("Processing submission %d", sid)

        # Build graph pipeline
        G = builder.build_for_submission(sid)
        leiden_result = run_leiden(G, config=cfg)
        conflicts = detect_conflicts(G, cfg)
        G = add_contradicts_edges(G, conflicts)

        # Compare
        comparison = compare_flat_vs_graph(flat_results, G, leiden_result, gt, cfg)

        submission_result = {
            "submission_id": sid,
            "flat_f1": comparison.flat_metrics.f1,
            "graph_f1": comparison.graph_metrics.f1,
            "improvement": comparison.improvement(),
            "agreements": comparison.agreements,
            "disagreements": comparison.disagreements,
            "graph_only_correct": comparison.graph_only_correct,
            "flat_only_correct": comparison.flat_only_correct,
            "flat_verdict_count": len(comparison.flat_verdicts),
            "graph_verdict_count": len(comparison.graph_verdicts),
        }
        results["submissions"].append(submission_result)

        total_flat_f1 += comparison.flat_metrics.f1
        total_graph_f1 += comparison.graph_metrics.f1
        total_improvements += comparison.improvement()
        count += 1

    if count > 0:
        results["aggregate"] = {
            "avg_flat_f1": total_flat_f1 / count,
            "avg_graph_f1": total_graph_f1 / count,
            "avg_improvement": total_improvements / count,
            "n_submissions": count,
        }

    return results
