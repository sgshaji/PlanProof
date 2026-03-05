"""Experiment: Perturbation robustness analysis.

RQ: How does extraction noise affect compliance verdict reliability?

Methodology:
1. Build SN-KG for annotated submissions
2. For each degradation rate (0%, 5%, 10%, 20%, 30%, 50%):
   a. Drop entities at that rate
   b. Perturb numeric attributes
   c. Drop relationships
   d. Re-run community detection and conflict detection
   e. Evaluate against ground truth
3. Plot degradation curves
"""

import logging
from typing import Optional, Union

from research.config import ResearchConfig
from research.graph.builder import SNKGBuilder
from research.community.leiden import run_leiden
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.evaluation.metrics import evaluate
from research.evaluation.perturbation import (
    drop_entities,
    perturb_attributes,
    drop_relationships,
)

logger = logging.getLogger(__name__)


def run_perturbation_experiment(
    submission_ids: list[Union[int, str]],
    ground_truths: dict[Union[int, str], GroundTruthAnnotation],
    config: Optional[ResearchConfig] = None,
) -> dict:
    """Run the perturbation robustness experiment.

    Args:
        submission_ids: Submissions to analyze.
        ground_truths: Dict mapping submission_id -> GroundTruthAnnotation.
        config: Research configuration.

    Returns:
        Dict with degradation curves per submission.
    """
    cfg = config or ResearchConfig()
    builder = SNKGBuilder(cfg)
    results = {
        "experiment": "perturbation",
        "submissions": [],
    }

    for sid in submission_ids:
        gt = ground_truths.get(sid)
        if gt is None:
            logger.warning("No ground truth for submission %s, skipping", sid)
            continue

        logger.info("Processing submission %s", sid)
        G_original = builder.build_for_submission(sid)

        degradation_curve = []

        for rate in cfg.perturbation_rates:
            logger.info("  Degradation rate: %.2f", rate)

            # Apply degradations
            G_degraded = drop_entities(G_original, rate, seed=cfg.random_seed)
            G_degraded = perturb_attributes(G_degraded, rate, seed=cfg.random_seed)
            G_degraded = drop_relationships(G_degraded, rate, seed=cfg.random_seed + 1)

            # Re-run pipeline on degraded graph
            leiden_result = run_leiden(G_degraded, config=cfg)
            conflicts = detect_conflicts(G_degraded, cfg)
            G_degraded = add_contradicts_edges(G_degraded, conflicts)

            # Evaluate
            eval_result = evaluate(G_degraded, gt)

            point = {
                "rate": rate,
                "nodes_remaining": G_degraded.number_of_nodes(),
                "edges_remaining": G_degraded.number_of_edges(),
                "num_communities": leiden_result.num_communities,
                "modularity": leiden_result.modularity,
                "conflicts_detected": len(conflicts),
                "entity_precision": eval_result.overall_entity.precision if eval_result.overall_entity else None,
                "entity_recall": eval_result.overall_entity.recall if eval_result.overall_entity else None,
                "entity_f1": eval_result.overall_entity.f1 if eval_result.overall_entity else None,
                "relationship_f1": eval_result.overall_relationship.f1 if eval_result.overall_relationship else None,
            }
            degradation_curve.append(point)

        results["submissions"].append({
            "submission_id": sid,
            "degradation_curve": degradation_curve,
        })

    return results
