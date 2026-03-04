"""Query the GraphRAG index for planning document insights.

Supports both local search (entity-focused) and global search
(broad themes/summaries) against the indexed planning documents.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE = (
    Path(__file__).resolve().parent.parent / "graphrag_workspace"
)

EXAMPLE_QUERIES = {
    "rooms": "What rooms are described in the planning application and what are their dimensions?",
    "conflicts": "Are there any contradictions or discrepancies between the stated measurements in different documents?",
    "boundaries": "What are the boundary distances and constraints mentioned in the application?",
    "heights": "What building heights are proposed and do they comply with any stated limits?",
    "overview": "Provide a summary of the proposed development including key spatial features.",
}


def run_query(
    workspace: Path,
    query: str,
    method: str = "local",
) -> int:
    """Run a graphrag query command."""
    cmd = [
        "graphrag",
        "query",
        "--root",
        str(workspace),
        "--method",
        method,
        "--query",
        query,
    ]

    logger.info("Query method: %s", method)
    logger.info("Query: %s", query)
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Query GraphRAG index for planning document insights."
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="The query to run against the index",
    )
    parser.add_argument(
        "--method",
        choices=["local", "global"],
        default="local",
        help="Search method: local (entity-focused) or global (broad themes)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help=f"GraphRAG workspace root (default: {DEFAULT_WORKSPACE})",
    )
    parser.add_argument(
        "--example",
        choices=list(EXAMPLE_QUERIES.keys()),
        default=None,
        help="Run a pre-defined example query",
    )
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List available example queries",
    )
    args = parser.parse_args()

    if args.list_examples:
        print("Available example queries:")
        for name, q in EXAMPLE_QUERIES.items():
            print(f"  {name}: {q}")
        return

    # Check output exists
    output_dir = args.root / "output"
    if not output_dir.exists():
        logger.error(
            "No output directory found at %s — run indexing first",
            output_dir,
        )
        sys.exit(1)

    query = args.query
    if args.example:
        query = EXAMPLE_QUERIES[args.example]
    if not query:
        logger.error(
            "Provide --query or --example. Use --list-examples to see options."
        )
        sys.exit(1)

    rc = run_query(args.root, query, method=args.method)
    if rc != 0:
        logger.error("Query failed (exit code %d)", rc)
        sys.exit(rc)


if __name__ == "__main__":
    main()
