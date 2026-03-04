"""Master experiment runner.

Orchestrates the full research pipeline:
1. Build SN-KGs for all submissions
2. Run Leiden community detection
3. Detect conflicts
4. Run all evaluation experiments
5. Output results as JSON
"""

import json
import logging
import os
import sys
from typing import Optional

from research.config import ResearchConfig
from research.db_reader import DBReader
from research.graph.builder import SNKGBuilder
from research.graph.nx_utils import graph_summary, add_community_nodes
from research.community.leiden import run_leiden
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges, conflict_summary
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.experiments.exp_community_quality import run_community_quality_experiment
from research.experiments.exp_conflict_detection import run_conflict_detection_experiment
from research.experiments.exp_perturbation import run_perturbation_experiment
from research.experiments.exp_flat_vs_graph import run_flat_vs_graph_experiment

logger = logging.getLogger(__name__)


def run_all(
    submission_ids: Optional[list[int]] = None,
    config: Optional[ResearchConfig] = None,
):
    """Run all experiments end-to-end.

    Args:
        submission_ids: Specific submissions to process. If None, uses all.
        config: Research configuration.
    """
    cfg = config or ResearchConfig()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("PlanProof Research Pipeline — Starting")
    logger.info("=" * 60)

    # Load ground truths
    ground_truths_list = GroundTruthAnnotation.load_all(cfg.ground_truth_dir)
    ground_truths = {gt.submission_id: gt for gt in ground_truths_list}
    logger.info("Loaded %d ground truth annotations", len(ground_truths))

    # If no submissions specified, use those with ground truth
    if submission_ids is None:
        submission_ids = list(ground_truths.keys())

    if not submission_ids:
        logger.error("No submissions to process. Add ground truth annotations first.")
        return

    # Phase 1: Build graphs and run pipeline
    logger.info("Phase 1: Building SN-KGs")
    builder = SNKGBuilder(cfg)
    graphs = {}
    for sid in submission_ids:
        try:
            G = builder.build_for_submission(sid)
            summary = graph_summary(G)
            logger.info("  Submission %d: %s", sid, summary)
            graphs[sid] = G
        except Exception as e:
            logger.error("  Failed for submission %d: %s", sid, e)

    # Phase 2: Community detection
    logger.info("Phase 2: Leiden community detection")
    leiden_results = {}
    for sid, G in graphs.items():
        leiden_result = run_leiden(G, config=cfg)
        add_community_nodes(G, leiden_result.community_map)
        leiden_results[sid] = leiden_result

    # Phase 3: Conflict detection
    logger.info("Phase 3: Conflict detection")
    for sid, G in graphs.items():
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)
        summary = conflict_summary(G)
        logger.info("  Submission %d: %s", sid, summary)

    # Phase 4: Run experiments
    logger.info("Phase 4: Running experiments")
    all_results = {}

    # Experiment 1: Community quality
    logger.info("  Running community quality experiment")
    all_results["community_quality"] = run_community_quality_experiment(
        submission_ids, cfg,
    )

    # Experiment 2: Conflict detection
    logger.info("  Running conflict detection experiment")
    all_results["conflict_detection"] = run_conflict_detection_experiment(
        submission_ids, ground_truths, cfg,
    )

    # Experiment 3: Perturbation
    logger.info("  Running perturbation experiment")
    all_results["perturbation"] = run_perturbation_experiment(
        submission_ids, ground_truths, cfg,
    )

    # Experiment 4: Flat vs graph (needs flat results from DB)
    logger.info("  Running flat vs graph experiment")
    db = DBReader(cfg)
    flat_results = {}
    for sid in submission_ids:
        checks = db.get_validation_checks(sid)
        flat_results[sid] = [
            {
                "rule_id": vc.rule_id_string or str(vc.rule_id),
                "status": vc.status.value if hasattr(vc.status, "value") else str(vc.status),
                "message": vc.explanation or "",
            }
            for vc in checks
        ]

    all_results["flat_vs_graph"] = run_flat_vs_graph_experiment(
        submission_ids, ground_truths, flat_results, cfg,
    )

    # Save results
    output_path = os.path.join(cfg.output_dir, "experiment_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    logger.info("=" * 60)
    logger.info("Results saved to %s", output_path)
    logger.info("=" * 60)

    return all_results


if __name__ == "__main__":
    submission_ids = None
    if len(sys.argv) > 1:
        submission_ids = [int(x) for x in sys.argv[1:]]
    run_all(submission_ids)
