"""End-to-end PlanProof GraphRAG research pipeline.

Runs the full pipeline:
  1. Extract text from floor plan PDFs via GPT-4o Vision
  2. Run GraphRAG indexing on extracted text
  3. Build SN-KG from GraphRAG output
  4. Run conflict detection
  5. Print results

Usage:
    python -m research.scripts.run_pipeline
    python -m research.scripts.run_pipeline --skip-extract --skip-index
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).resolve().parent.parent


def step_extract(input_dir: Path, output_dir: Path):
    """Step 1: Extract text from PDFs using GPT-4o Vision."""
    logger.info("=" * 60)
    logger.info("STEP 1: Extracting text from PDFs via GPT-4o Vision")
    logger.info("=" * 60)

    cmd = [
        sys.executable,
        "-m", "research.scripts.extract_pdf_vision",
        "--input-dir", str(input_dir),
        "--output-dir", str(output_dir),
    ]
    result = subprocess.run(cmd, cwd=str(RESEARCH_DIR.parent))
    if result.returncode != 0:
        logger.error("PDF extraction failed")
        sys.exit(1)

    txt_files = list(output_dir.glob("*.txt"))
    logger.info("Extraction complete: %d text files", len(txt_files))


def step_index(workspace: Path, verbose: bool = False):
    """Step 2: Run GraphRAG indexing."""
    logger.info("=" * 60)
    logger.info("STEP 2: Running GraphRAG indexing")
    logger.info("=" * 60)

    cmd = [
        sys.executable,
        "-m", "research.scripts.run_graphrag_index",
        "--root", str(workspace),
    ]
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, cwd=str(RESEARCH_DIR.parent))
    if result.returncode != 0:
        logger.error("GraphRAG indexing failed")
        sys.exit(1)

    logger.info("Indexing complete")


def step_build_snkg(workspace: Path, output_dir: Path):
    """Step 3+4: Build SN-KG and detect conflicts."""
    logger.info("=" * 60)
    logger.info("STEP 3: Building SN-KG + conflict detection")
    logger.info("=" * 60)

    cmd = [
        sys.executable,
        "-m", "research.scripts.build_snkg",
        "--workspace", str(workspace),
        "--output", str(output_dir),
        "--detect-conflicts",
        "--run-leiden",
    ]
    result = subprocess.run(cmd, cwd=str(RESEARCH_DIR.parent))
    if result.returncode != 0:
        logger.error("SN-KG build failed")
        sys.exit(1)

    logger.info("SN-KG build complete")


def main():
    from research.config import ResearchConfig

    cfg = ResearchConfig()

    parser = argparse.ArgumentParser(
        description="Run the full PlanProof GraphRAG research pipeline."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(cfg.bcc_data_path),
        help="Directory containing application subdirectories with PDFs",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip PDF extraction (use existing text files)",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip GraphRAG indexing (use existing Parquet output)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    workspace = Path(cfg.graphrag_workspace_path)
    input_dir = workspace / "input"
    output_dir = Path(cfg.output_dir)

    # Step 1: Extract
    if not args.skip_extract:
        step_extract(args.input_dir, input_dir)
    else:
        txt_count = len(list(input_dir.glob("*.txt")))
        logger.info("Skipping extraction (%d existing text files)", txt_count)

    # Step 2: Index
    if not args.skip_index:
        step_index(workspace, verbose=args.verbose)
    else:
        logger.info("Skipping GraphRAG indexing (using existing output)")

    # Step 3+4: Build SN-KG + conflicts
    step_build_snkg(workspace, output_dir)

    # Summary
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)

    report_path = output_dir / "conflict_report.json"
    if report_path.exists():
        import json
        with open(report_path) as f:
            report = json.load(f)
        conflicts = report.get("conflicts", [])
        logger.info("Conflicts found: %d", len(conflicts))
        for c in conflicts:
            logger.info(
                "  [%s] %s: %s vs %s (%s)",
                c["severity"].upper(),
                c["field_name"],
                c["value_a"],
                c["value_b"],
                c["description"],
            )

    graph_path = output_dir / "snkg.graphml"
    if graph_path.exists():
        logger.info("Graph saved to: %s", graph_path)


if __name__ == "__main__":
    main()
