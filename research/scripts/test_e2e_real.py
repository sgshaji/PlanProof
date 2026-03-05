"""End-to-end smoke test for the research pipeline.

Tests the full pipeline with 2 real BCC applications:
  - 202506444PA  (7 Scotland Lane — 8 docs, richest data)
  - 202506361PA  (Kingsway Business Park — 1 doc, site plan only)

Usage:
    python -m research.scripts.test_e2e_real

This does NOT call Azure OpenAI (GraphRAG is already indexed).
It exercises: graph build → Leiden → conflict detection → experiments.
"""

import json
import logging
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from research.config import ResearchConfig
from research.local_store import LocalStore
from research.graph.builder import SNKGBuilder
from research.graph.nx_utils import graph_summary, add_community_nodes
from research.community.leiden import run_leiden
from research.community.analysis import analyze_communities
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges, conflict_summary
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.evaluation.metrics import evaluate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────
TEST_APPS = ["202506444PA", "202506361PA"]
# ───────────────────────────────────────────────────────────────────────


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run():
    cfg = ResearchConfig()
    store = LocalStore(cfg)
    builder = SNKGBuilder(cfg)

    # Load ground truths
    ground_truths_list = GroundTruthAnnotation.load_all(cfg.ground_truth_dir)
    ground_truths = {}
    for gt in ground_truths_list:
        ground_truths[gt.submission_id] = gt
        ground_truths[str(gt.submission_id)] = gt
    logger.info("Loaded %d ground truth annotations", len(ground_truths_list))

    graphs = {}
    results = {}

    # ── Phase 1: Build SN-KGs ──────────────────────────────────────────
    separator("PHASE 1: Building SN-KGs")
    for app_id in TEST_APPS:
        logger.info("Building graph for %s ...", app_id)
        try:
            G = builder.build_for_submission(app_id)
            summary = graph_summary(G)
            graphs[app_id] = G
            store.save_graph(G, app_id)

            print(f"\n  {app_id}:")
            print(f"    Nodes: {summary.get('total_nodes', G.number_of_nodes())}")
            print(f"    Edges: {summary.get('total_edges', G.number_of_edges())}")
            if "by_node_type" in summary:
                for nt, count in sorted(summary["by_node_type"].items()):
                    print(f"      {nt}: {count}")
        except Exception as e:
            logger.error("  FAILED for %s: %s", app_id, e, exc_info=True)

    if not graphs:
        print("\n  ERROR: No graphs built. Check GraphRAG output exists.")
        return 1

    # ── Phase 2: Leiden Community Detection ─────────────────────────────
    separator("PHASE 2: Leiden Community Detection")
    leiden_results = {}
    for app_id, G in graphs.items():
        logger.info("Running Leiden for %s ...", app_id)
        lr = run_leiden(G, config=cfg)
        add_community_nodes(G, lr.community_map)
        leiden_results[app_id] = lr
        store.save_graph(G, app_id)

        analysis = analyze_communities(G, lr)

        print(f"\n  {app_id}:")
        print(f"    Communities: {lr.num_communities}")
        print(f"    Modularity:  {lr.modularity:.4f}")
        print(f"    Avg coherence: {analysis.avg_spatial_coherence:.3f}")
        print(f"    Dwelling units: {analysis.dwelling_unit_count}")
        for p in analysis.profiles:
            print(f"      Community {p.community_id}: {p.node_count} nodes, "
                  f"coherence={p.spatial_coherence:.3f}, "
                  f"dwelling={p.is_dwelling_unit}")

    # ── Phase 3: Conflict Detection ────────────────────────────────────
    separator("PHASE 3: Conflict Detection")
    for app_id, G in graphs.items():
        logger.info("Detecting conflicts for %s ...", app_id)
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)
        summary = conflict_summary(G)
        store.save_graph(G, app_id)

        print(f"\n  {app_id}:")
        print(f"    Total conflicts: {summary['total_conflicts']}")
        if summary["by_type"]:
            for ct, count in summary["by_type"].items():
                print(f"      {ct}: {count}")
        if summary["by_severity"]:
            for sev, count in summary["by_severity"].items():
                print(f"      severity={sev}: {count}")

        # Print actual conflict details
        for c in conflicts:
            print(f"    -> {c.conflict_type}: {c.field_name} "
                  f"({c.value_a} vs {c.value_b}) [{c.severity}]")

    # ── Phase 4: Evaluation Against Ground Truth ───────────────────────
    separator("PHASE 4: Evaluation Against Ground Truth")
    for app_id, G in graphs.items():
        gt = ground_truths.get(app_id)
        if gt is None:
            print(f"\n  {app_id}: No ground truth — skipping evaluation")
            continue

        logger.info("Evaluating %s against ground truth ...", app_id)
        eval_result = evaluate(G, gt)
        result_dict = eval_result.to_dict()

        print(f"\n  {app_id}:")
        if eval_result.overall_entity:
            oe = eval_result.overall_entity
            print(f"    Entity P/R/F1: {oe.precision:.3f} / {oe.recall:.3f} / {oe.f1:.3f}")
        if eval_result.overall_relationship:
            orr = eval_result.overall_relationship
            print(f"    Relationship P/R/F1: {orr.precision:.3f} / {orr.recall:.3f} / {orr.f1:.3f}")
        if eval_result.conflict_metrics:
            cm = eval_result.conflict_metrics
            print(f"    Conflict P/R/F1: {cm.precision:.3f} / {cm.recall:.3f} / {cm.f1:.3f}")

        for key, metrics in sorted(result_dict.items()):
            if isinstance(metrics, dict):
                print(f"      {key}: P={metrics.get('precision',0):.3f} "
                      f"R={metrics.get('recall',0):.3f} F1={metrics.get('f1',0):.3f}")

        results[app_id] = result_dict

    # ── Save Results ───────────────────────────────────────────────────
    separator("RESULTS SAVED")
    output_path = os.path.join(cfg.output_dir, "e2e_test_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results: {output_path}")

    # List saved graphs
    saved = store.list_saved_graphs()
    print(f"  Saved graphs: {saved}")

    separator("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(run())
