"""PlanProof Research CLI — end-to-end pipeline in one command.

Usage:
    python -m research.cli analyze 202506444PA
    python -m research.cli analyze --all
    python -m research.cli list
    python -m research.cli report 202506444PA
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def _setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ── Formatting helpers ─────────────────────────────────────────────────

def _header(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _severity_color(severity: str) -> str:
    """ANSI colour prefix for severity level."""
    colours = {"high": "\033[91m", "medium": "\033[93m", "low": "\033[92m"}
    return colours.get(severity, "")

RESET = "\033[0m"


# ── Commands ───────────────────────────────────────────────────────────

def cmd_list(cfg: ResearchConfig):
    """List available applications and their status."""
    store = LocalStore(cfg)
    app_ids = cfg.get_bcc_app_ids()

    # Also check for ground truth files
    gt_files = set()
    gt_dir = Path(cfg.ground_truth_dir)
    if gt_dir.exists():
        for f in gt_dir.glob("gt_submission_*.json"):
            gt_files.add(f.stem.replace("gt_submission_", ""))

    # Check workspace input files for app coverage
    input_dir = Path(cfg.graphrag_workspace_path) / "input"
    apps_in_workspace = set()
    if input_dir.exists():
        for txt in input_dir.glob("*.txt"):
            # Extract app ID from filenames like "202506444PA_doc1_page1.txt"
            parts = txt.stem.split("_")
            if parts:
                apps_in_workspace.add(parts[0])

    _header("Available Applications")
    print(f"  {'APP ID':<20} {'INDEXED':<10} {'GRAPH':<10} {'GROUND TRUTH':<15}")
    print(f"  {'─'*20} {'─'*10} {'─'*10} {'─'*15}")

    all_ids = sorted(set(app_ids) | apps_in_workspace)
    if not all_ids:
        print("  No applications found.")
        return

    for app_id in all_ids:
        indexed = "yes" if app_id in apps_in_workspace else "no"
        has_graph = "yes" if store.graph_exists(app_id) else "no"
        has_gt = "yes" if app_id in gt_files else "no"
        print(f"  {app_id:<20} {indexed:<10} {has_graph:<10} {has_gt:<15}")

    print(f"\n  Total: {len(all_ids)} application(s)")


def cmd_analyze(app_ids: list[str], cfg: ResearchConfig, force: bool = False):
    """Run full analysis pipeline for given application(s)."""
    store = LocalStore(cfg)
    builder = SNKGBuilder(cfg)

    # Load ground truths
    ground_truths = {}
    try:
        gt_list = GroundTruthAnnotation.load_all(cfg.ground_truth_dir)
        for gt in gt_list:
            ground_truths[str(gt.submission_id)] = gt
    except Exception:
        pass

    all_results = {}

    for app_id in app_ids:
        _header(f"Analyzing {app_id}")

        # ── Step 1: Build SN-KG ──
        print("  [1/4] Building knowledge graph...", end=" ", flush=True)
        try:
            G = builder.build_for_submission(app_id)
        except Exception as e:
            print(f"FAILED: {e}")
            continue
        summary = graph_summary(G)
        n_nodes = summary.get("total_nodes", G.number_of_nodes())
        n_edges = summary.get("total_edges", G.number_of_edges())
        print(f"{n_nodes} nodes, {n_edges} edges")

        # ── Step 2: Leiden community detection ──
        print("  [2/4] Community detection...", end=" ", flush=True)
        lr = run_leiden(G, config=cfg)
        add_community_nodes(G, lr.community_map)
        analysis = analyze_communities(G, lr)
        print(f"{lr.num_communities} communities, "
              f"modularity={lr.modularity:.3f}, "
              f"{analysis.dwelling_unit_count} dwelling units")

        # ── Step 3: Conflict detection ──
        print("  [3/4] Detecting conflicts...", end=" ", flush=True)
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)
        c_summary = conflict_summary(G)
        print(f"{c_summary['total_conflicts']} conflicts found")

        # Save graph
        store.save_graph(G, app_id)

        # Save conflict report
        conflict_data = {
            "app_id": app_id,
            "summary": c_summary,
            "conflicts": [
                {
                    "conflict_id": c.conflict_id,
                    "conflict_type": c.conflict_type,
                    "field_name": c.field_name,
                    "value_a": c.value_a,
                    "value_b": c.value_b,
                    "unit": c.unit,
                    "discrepancy_pct": c.discrepancy_pct,
                    "severity": c.severity,
                    "description": c.description,
                }
                for c in conflicts
            ],
        }
        store.save_conflict_results(app_id, conflict_data)

        # ── Step 4: Evaluation (if ground truth exists) ──
        gt = ground_truths.get(app_id)
        if gt:
            print("  [4/4] Evaluating against ground truth...", end=" ", flush=True)
            eval_result = evaluate(G, gt)
            oe = eval_result.overall_entity
            print(f"Entity F1={oe.f1:.3f}, ", end="")
            if eval_result.conflict_metrics:
                cm = eval_result.conflict_metrics
                print(f"Conflict P={cm.precision:.3f} R={cm.recall:.3f} F1={cm.f1:.3f}")
            else:
                print("no conflict ground truth")
            all_results[app_id] = eval_result.to_dict()
        else:
            print("  [4/4] No ground truth — skipping evaluation")

        # ── Print conflict report ──
        _print_conflict_report(conflicts, app_id)

    # Save combined results
    if all_results:
        output_path = Path(cfg.output_dir) / "analysis_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, default=str)

    _header("Done")


def cmd_report(app_id: str, cfg: ResearchConfig):
    """Show saved conflict report for an application."""
    store = LocalStore(cfg)
    data = store.load_results(f"conflicts_{app_id}")
    if data is None:
        print(f"No saved report for {app_id}. Run: python -m research.cli analyze {app_id}")
        return

    conflicts_data = data.get("conflicts", [])

    from research.conflict.detector import Conflict
    conflicts = [
        Conflict(
            conflict_id=c["conflict_id"],
            conflict_type=c["conflict_type"],
            claim_a_id="",
            claim_b_id="",
            field_name=c["field_name"],
            value_a=c["value_a"],
            value_b=c["value_b"],
            unit=c.get("unit"),
            discrepancy=None,
            discrepancy_pct=c.get("discrepancy_pct"),
            severity=c["severity"],
            description=c["description"],
        )
        for c in conflicts_data
    ]
    _print_conflict_report(conflicts, app_id)


def _print_conflict_report(conflicts: list, app_id: str):
    """Pretty-print the conflict table."""
    if not conflicts:
        print(f"\n  No conflicts detected for {app_id}.")
        return

    # Sort: high first, then medium, then low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_conflicts = sorted(conflicts, key=lambda c: severity_order.get(c.severity, 3))

    _header(f"Conflict Report: {app_id} ({len(sorted_conflicts)} conflicts)")
    print(f"  {'#':<4} {'SEVERITY':<10} {'TYPE':<10} {'FIELD':<30} {'VALUE A':<12} {'VALUE B':<12} {'DIFF %':<8}")
    print(f"  {'─'*4} {'─'*10} {'─'*10} {'─'*30} {'─'*12} {'─'*12} {'─'*8}")

    for i, c in enumerate(sorted_conflicts, 1):
        sev_prefix = _severity_color(c.severity)
        pct = f"{c.discrepancy_pct:.0%}" if c.discrepancy_pct is not None else "—"
        field_display = c.field_name[:30]
        va = str(c.value_a)[:12]
        vb = str(c.value_b)[:12]
        print(f"  {i:<4} {sev_prefix}{c.severity.upper():<10}{RESET} "
              f"{c.conflict_type:<10} {field_display:<30} {va:<12} {vb:<12} {pct:<8}")

    # Summary by severity
    by_sev = {}
    for c in sorted_conflicts:
        by_sev[c.severity] = by_sev.get(c.severity, 0) + 1
    parts = [f"{count} {sev}" for sev, count in sorted(by_sev.items(), key=lambda x: severity_order.get(x[0], 3))]
    print(f"\n  Summary: {', '.join(parts)}")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="planproof",
        description="PlanProof — planning application conflict detection",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze
    p_analyze = subparsers.add_parser(
        "analyze",
        help="Run full analysis pipeline (build → communities → conflicts → evaluate)",
    )
    p_analyze.add_argument(
        "app_ids",
        nargs="*",
        help="Application ID(s) to analyze (e.g. 202506444PA)",
    )
    p_analyze.add_argument(
        "--all",
        action="store_true",
        dest="analyze_all",
        help="Analyze all available applications",
    )
    p_analyze.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if cached graph exists",
    )
    p_analyze.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # list
    subparsers.add_parser("list", help="List available applications")

    # report
    p_report = subparsers.add_parser(
        "report",
        help="Show saved conflict report for an application",
    )
    p_report.add_argument("app_id", help="Application ID")

    args = parser.parse_args()
    cfg = ResearchConfig()

    if args.command == "list":
        cmd_list(cfg)
    elif args.command == "analyze":
        _setup_logging(getattr(args, "verbose", False))
        if args.analyze_all:
            # Discover all apps that have indexed data
            input_dir = Path(cfg.graphrag_workspace_path) / "input"
            app_set = set()
            if input_dir.exists():
                for txt in input_dir.glob("*.txt"):
                    parts = txt.stem.split("_")
                    if parts:
                        app_set.add(parts[0])
            app_ids = sorted(app_set)
        elif args.app_ids:
            app_ids = args.app_ids
        else:
            parser.error("Specify app ID(s) or --all")
            return
        if not app_ids:
            print("No applications found with indexed data.")
            return
        cmd_analyze(app_ids, cfg, force=args.force)
    elif args.command == "report":
        cmd_report(args.app_id, cfg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
