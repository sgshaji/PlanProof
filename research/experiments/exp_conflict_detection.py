"""Experiment: Conflict detection recall and inter-rater agreement.

RQ: How accurately does the graph-based conflict detector identify
cross-document inconsistencies compared to human annotations?

Methodology:
1. Build SN-KG for annotated submissions
2. Run conflict detection
3. Compare against ground truth conflicts
4. Compute recall, precision, F1, and Cohen's kappa
"""

import logging
from typing import Optional, Union

from research.config import ResearchConfig
from research.graph.builder import SNKGBuilder
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges, conflict_summary
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.evaluation.metrics import evaluate
from research.evaluation.inter_rater import compute_cohen_kappa

logger = logging.getLogger(__name__)


def run_conflict_detection_experiment(
    submission_ids: list[Union[int, str]],
    ground_truths: dict[Union[int, str], GroundTruthAnnotation],
    config: Optional[ResearchConfig] = None,
) -> dict:
    """Run the conflict detection experiment.

    Args:
        submission_ids: Submissions to analyze.
        ground_truths: Dict mapping submission_id -> GroundTruthAnnotation.
        config: Research configuration.

    Returns:
        Dict with experiment results.
    """
    cfg = config or ResearchConfig()
    builder = SNKGBuilder(cfg)
    results = {
        "experiment": "conflict_detection",
        "submissions": [],
        "aggregate": {},
    }

    total_tp, total_fp, total_fn = 0, 0, 0
    all_kappas = []

    for sid in submission_ids:
        gt = ground_truths.get(sid)
        if gt is None:
            logger.warning("No ground truth for submission %s, skipping", sid)
            continue

        logger.info("Processing submission %s", sid)
        G = builder.build_for_submission(sid)

        # Detect conflicts
        conflicts = detect_conflicts(G, cfg)
        G = add_contradicts_edges(G, conflicts)
        summary = conflict_summary(G)

        # Evaluate against ground truth
        eval_result = evaluate(G, gt)

        # Cohen's kappa
        kappa_result = compute_cohen_kappa(G, gt)
        all_kappas.append(kappa_result.kappa)

        conflict_metrics = eval_result.conflict_metrics
        if conflict_metrics:
            total_tp += conflict_metrics.true_positives
            total_fp += conflict_metrics.false_positives
            total_fn += conflict_metrics.false_negatives

        submission_result = {
            "submission_id": sid,
            "detected_conflicts": len(conflicts),
            "ground_truth_conflicts": len(gt.conflicts),
            "conflict_summary": summary,
            "precision": conflict_metrics.precision if conflict_metrics else None,
            "recall": conflict_metrics.recall if conflict_metrics else None,
            "f1": conflict_metrics.f1 if conflict_metrics else None,
            "cohen_kappa": kappa_result.kappa,
            "kappa_interpretation": kappa_result.interpretation,
        }
        results["submissions"].append(submission_result)

    # Aggregate metrics
    denom_p = total_tp + total_fp
    denom_r = total_tp + total_fn
    results["aggregate"] = {
        "precision": total_tp / denom_p if denom_p > 0 else 0.0,
        "recall": total_tp / denom_r if denom_r > 0 else 0.0,
        "avg_kappa": sum(all_kappas) / len(all_kappas) if all_kappas else 0.0,
    }

    return results
