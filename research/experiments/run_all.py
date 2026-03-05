"""Master experiment runner.

Orchestrates the full research pipeline:
1. Build SN-KGs for all submissions
2. Run Leiden community detection
3. Detect conflicts
4. Run all evaluation experiments
5. Output results as JSON (locally, no database required)
"""

import json
import logging
import os
import sys
from typing import Optional, Union

from research.config import ResearchConfig
from research.local_store import LocalStore
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
    submission_ids: Optional[list[Union[int, str]]] = None,
    config: Optional[ResearchConfig] = None,
):
    """Run all experiments end-to-end.

    Args:
        submission_ids: Specific submissions to process. If None, uses all
            available ground truth annotations or BCC application IDs.
        config: Research configuration.
    """
    cfg = config or ResearchConfig()
    store = LocalStore(cfg)

    # Cost tracking
    from research.cost_tracker import CostTracker
    tracker = CostTracker(budget_usd=cfg.budget_usd)

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
    ground_truths = {}
    for gt in ground_truths_list:
        # Support both int and string submission IDs
        ground_truths[gt.submission_id] = gt
        if isinstance(gt.submission_id, int):
            ground_truths[str(gt.submission_id)] = gt
    logger.info("Loaded %d ground truth annotations", len(ground_truths_list))

    # If no submissions specified, use ground truths or BCC app IDs
    if submission_ids is None:
        submission_ids = [gt.submission_id for gt in ground_truths_list]
        if not submission_ids:
            # Fall back to BCC application folder names
            submission_ids = cfg.get_bcc_app_ids()
            logger.info("Using BCC application IDs: %s", submission_ids)

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
            logger.info("  Submission %s: %s", sid, summary)
            graphs[sid] = G
            # Save graph locally
            store.save_graph(G, str(sid))
        except Exception as e:
            logger.error("  Failed for submission %s: %s", sid, e)

    if not graphs:
        logger.error("No graphs were built. Check GraphRAG output or data paths.")
        return

    # Phase 2: Community detection
    logger.info("Phase 2: Leiden community detection")
    leiden_results = {}
    for sid, G in graphs.items():
        leiden_result = run_leiden(G, config=cfg)
        add_community_nodes(G, leiden_result.community_map)
        leiden_results[sid] = leiden_result
        # Save updated graph and leiden results
        store.save_graph(G, str(sid))
        store.save_leiden_results(str(sid), {
            "num_communities": leiden_result.num_communities,
            "modularity": leiden_result.modularity,
            "resolution": leiden_result.resolution,
            "community_map": leiden_result.community_map,
        })

    # Phase 3: Conflict detection
    logger.info("Phase 3: Conflict detection")
    for sid, G in graphs.items():
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)
        summary = conflict_summary(G)
        logger.info("  Submission %s: %s", sid, summary)
        # Save updated graph and conflict results
        store.save_graph(G, str(sid))
        store.save_conflict_results(str(sid), {
            "summary": summary,
            "conflicts": [
                {
                    "conflict_id": c.conflict_id,
                    "conflict_type": c.conflict_type,
                    "field_name": c.field_name,
                    "value_a": c.value_a,
                    "value_b": c.value_b,
                    "discrepancy": c.discrepancy,
                    "discrepancy_pct": c.discrepancy_pct,
                    "severity": c.severity,
                    "description": c.description,
                }
                for c in conflicts
            ],
        })

    # Phase 4: Run experiments
    logger.info("Phase 4: Running experiments")
    all_results = {}

    # Experiment 1: Community quality
    logger.info("  Running community quality experiment")
    all_results["community_quality"] = run_community_quality_experiment(
        submission_ids, cfg,
    )

    # Experiment 2: Conflict detection (needs ground truth)
    sids_with_gt = [sid for sid in submission_ids if sid in ground_truths]
    if sids_with_gt:
        logger.info("  Running conflict detection experiment")
        all_results["conflict_detection"] = run_conflict_detection_experiment(
            sids_with_gt, ground_truths, cfg,
        )
    else:
        logger.warning("  Skipping conflict detection experiment (no ground truth)")
        all_results["conflict_detection"] = {"skipped": True, "reason": "no ground truth"}

    # Experiment 3: Perturbation (needs ground truth)
    if sids_with_gt:
        logger.info("  Running perturbation experiment")
        all_results["perturbation"] = run_perturbation_experiment(
            sids_with_gt, ground_truths, cfg,
        )
    else:
        logger.warning("  Skipping perturbation experiment (no ground truth)")
        all_results["perturbation"] = {"skipped": True, "reason": "no ground truth"}

    # Experiment 4: Flat vs graph
    if cfg.use_database:
        logger.info("  Running flat vs graph experiment (DB mode)")
        from research.db_reader import DBReader
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
    else:
        logger.info("  Skipping flat vs graph experiment (no database)")
        all_results["flat_vs_graph"] = {
            "skipped": True,
            "reason": "database not configured (set use_database=True)",
        }

    # Save results
    output_path = os.path.join(cfg.output_dir, "experiment_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Also save via store
    store.save_results(all_results, "experiment_results")

    # Cost summary
    tracker.print_summary()
    cost_data = tracker.summary()
    store.save_results(cost_data, "cost_summary")

    logger.info("=" * 60)
    logger.info("Results saved to %s", output_path)
    logger.info("=" * 60)

    return all_results


if __name__ == "__main__":
    submission_ids = None
    if len(sys.argv) > 1:
        submission_ids = sys.argv[1:]
        # Try to convert to int if possible
        try:
            submission_ids = [int(x) for x in submission_ids]
        except ValueError:
            pass  # Keep as strings (BCC app IDs)
    run_all(submission_ids)

