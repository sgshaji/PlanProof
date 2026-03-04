"""Build SN-KG from GraphRAG output and run conflict detection.

Usage:
    python -m research.scripts.build_snkg [--detect-conflicts] [--run-leiden]
"""

import argparse
import json
import logging
import pickle
from pathlib import Path

import networkx as nx

from research.config import ResearchConfig
from research.graph.builder import GraphRAGSNKGBuilder
from research.graph.nx_utils import graph_summary
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges, conflict_summary

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Build SN-KG from GraphRAG output and detect conflicts."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="GraphRAG workspace path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for graph and reports",
    )
    parser.add_argument(
        "--detect-conflicts",
        action="store_true",
        help="Run conflict detection on the SN-KG",
    )
    parser.add_argument(
        "--run-leiden",
        action="store_true",
        help="Run Leiden community detection",
    )
    args = parser.parse_args()

    cfg = ResearchConfig()
    if args.workspace:
        cfg.graphrag_workspace_path = str(args.workspace)

    output_path = Path(args.output) if args.output else Path(cfg.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Build SN-KG from GraphRAG Parquet
    logger.info("Building SN-KG from GraphRAG output...")
    builder = GraphRAGSNKGBuilder(config=cfg)
    G = builder.build()
    logger.info("SN-KG: %s", graph_summary(G))

    # Step 2: Optional Leiden community detection
    if args.run_leiden:
        from research.community.leiden import run_leiden
        from research.graph.nx_utils import add_community_nodes

        logger.info("Running Leiden community detection...")
        leiden_result = run_leiden(G, config=cfg)
        add_community_nodes(G, leiden_result.community_map)
        logger.info(
            "Found %d communities",
            len(set(leiden_result.community_map.values())),
        )

    # Step 3: Optional conflict detection
    if args.detect_conflicts:
        logger.info("Running conflict detection...")
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)
        summary = conflict_summary(G)

        logger.info("Conflict summary: %s", json.dumps(summary, indent=2))

        # Save conflict report
        report_path = output_path / "conflict_report.json"
        with open(report_path, "w") as f:
            json.dump(
                {
                    "summary": summary,
                    "conflicts": [
                        {
                            "conflict_id": c.conflict_id,
                            "conflict_type": c.conflict_type,
                            "field_name": c.field_name,
                            "value_a": c.value_a,
                            "value_b": c.value_b,
                            "severity": c.severity,
                            "description": c.description,
                        }
                        for c in conflicts
                    ],
                },
                f,
                indent=2,
            )
        logger.info("Conflict report saved to %s", report_path)

    # Step 4: Save graph
    graph_path = output_path / "snkg.graphml"
    nx.write_graphml(G, str(graph_path))
    logger.info("SN-KG saved to %s", graph_path)

    pickle_path = output_path / "snkg.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(G, f)
    logger.info("SN-KG pickle saved to %s", pickle_path)


if __name__ == "__main__":
    main()
