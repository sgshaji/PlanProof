"""Run GraphRAG indexing on extracted planning documents.

Validates the workspace configuration and runs the GraphRAG
indexing pipeline to extract entities, relationships, and
communities from planning document text.
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

REQUIRED_ENV_VARS = [
    "GRAPHRAG_API_KEY",
    "GRAPHRAG_API_BASE",
    "GRAPHRAG_CHAT_DEPLOYMENT",
    "GRAPHRAG_EMBEDDING_DEPLOYMENT",
]


def validate_workspace(workspace: Path) -> list[str]:
    """Check workspace is ready for indexing. Returns list of errors."""
    errors = []

    settings_path = workspace / "settings.yaml"
    if not settings_path.exists():
        errors.append(f"Missing settings.yaml at {settings_path}")

    input_dir = workspace / "input"
    if not input_dir.exists():
        errors.append(f"Missing input directory at {input_dir}")
    else:
        txt_files = list(input_dir.glob("*.txt"))
        if not txt_files:
            errors.append(
                f"No .txt files in {input_dir} — "
                "run extract_pdf_text.py first"
            )
        else:
            logger.info("Found %d input text files", len(txt_files))

    import os

    missing_env = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing_env:
        errors.append(
            f"Missing environment variables: {', '.join(missing_env)}"
        )

    return errors


def run_index(workspace: Path, verbose: bool = False) -> int:
    """Run graphrag index command."""
    cmd = ["graphrag", "index", "--root", str(workspace)]
    if verbose:
        cmd.append("--verbose")

    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)
    return result.returncode


def main():
    # Load .env from project root
    from research.config import ResearchConfig
    ResearchConfig()

    parser = argparse.ArgumentParser(
        description="Run GraphRAG indexing on planning documents."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help=f"GraphRAG workspace root (default: {DEFAULT_WORKSPACE})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose GraphRAG output",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip pre-flight validation checks",
    )
    args = parser.parse_args()

    if not args.skip_validation:
        errors = validate_workspace(args.root)
        if errors:
            logger.error("Workspace validation failed:")
            for err in errors:
                logger.error("  - %s", err)
            sys.exit(1)
        logger.info("Workspace validation passed")

    rc = run_index(args.root, verbose=args.verbose)
    if rc != 0:
        logger.error("GraphRAG indexing failed (exit code %d)", rc)
        sys.exit(rc)

    logger.info("GraphRAG indexing completed successfully")
    logger.info(
        "Output written to: %s", args.root / "output"
    )


if __name__ == "__main__":
    main()
