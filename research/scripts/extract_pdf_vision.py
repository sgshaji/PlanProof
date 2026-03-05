"""Extract spatial descriptions from floor plan PDFs using GPT-4o Vision.

Converts each PDF page to an image, sends it to Azure OpenAI GPT-4o
with a planning-domain prompt, and saves the text description for
GraphRAG indexing.
"""

import argparse
import base64
import json
import logging
import sys
from pathlib import Path

import fitz  # PyMuPDF
from openai import AzureOpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

VISION_PROMPT = """\
You are analysing an architectural drawing from a UK planning application.
Describe ALL spatial information visible in this image in detail:

1. **Rooms**: Name, dimensions (length x width), area if labelled, floor level
2. **Building**: Overall footprint, height annotations, number of storeys
3. **Boundaries**: Fences, walls, hedges — heights, materials, distances from building
4. **Openings**: Doors, windows, rooflights — dimensions, types, which rooms they connect
5. **Measurements**: Every dimension annotation visible (distances, setbacks, heights)
6. **Site features**: Driveways, gardens, parking, trees, drainage
7. **Spatial relationships**: What is adjacent to what, what contains what, what opens into what
8. **Title block**: Drawing title, scale, revision, architect details if visible
9. **Annotations**: Any text labels, notes, or planning references on the drawing

Be exhaustive. Include every measurement, label, and spatial relationship you can see.
If text is unclear or partially visible, note what you can read and flag uncertainty.
Write in plain English paragraphs, not bullet points — this text will be processed
by a knowledge graph system that needs natural language."""


def pdf_page_to_png_bytes(pdf_path: Path, page_num: int, dpi: int = 200) -> bytes:
    """Render a single PDF page to PNG bytes."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def describe_image(
    client: AzureOpenAI,
    image_bytes: bytes,
    deployment: str,
    api_version: str,
    cost_tracker=None,
) -> str:
    """Send an image to GPT-4o Vision and get a spatial description."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=4096,
    )
    # Track cost
    if cost_tracker:
        cost_tracker.record_from_response(response, deployment, "vision_extraction")
        cost_tracker.check_budget()
    return response.choices[0].message.content


def extract_application(
    client: AzureOpenAI,
    app_dir: Path,
    output_dir: Path,
    raw_output_dir: Path,
    deployment: str,
    api_version: str,
    cost_tracker=None,
) -> int:
    """Extract all PDFs in an application directory. Returns count of pages processed."""
    app_id = app_dir.name
    pdf_files = sorted(app_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDFs found in %s", app_dir)
        return 0

    pages_processed = 0
    for doc_idx, pdf_path in enumerate(pdf_files, 1):
        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        doc.close()

        logger.info(
            "  [%s] Document %d/%d: %s (%d pages)",
            app_id, doc_idx, len(pdf_files), pdf_path.name[:30], num_pages,
        )

        for page_num in range(num_pages):
            out_name = f"{app_id}_doc{doc_idx}_page{page_num + 1}"
            txt_path = output_dir / f"{out_name}.txt"
            json_path = raw_output_dir / f"{out_name}.json"

            # Skip if already extracted
            if txt_path.exists():
                logger.info("    Page %d: already extracted, skipping", page_num + 1)
                pages_processed += 1
                continue

            logger.info("    Page %d: extracting via GPT-4o Vision...", page_num + 1)
            try:
                png_bytes = pdf_page_to_png_bytes(pdf_path, page_num)
                description = describe_image(
                    client, png_bytes, deployment, api_version,
                    cost_tracker=cost_tracker,
                )

                # Save text for GraphRAG
                txt_path.write_text(description, encoding="utf-8")

                # Save raw response for provenance
                json_path.write_text(
                    json.dumps(
                        {
                            "application_id": app_id,
                            "document": pdf_path.name,
                            "page": page_num + 1,
                            "description": description,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                pages_processed += 1
                logger.info(
                    "    Page %d: saved (%d chars)", page_num + 1, len(description)
                )
            except Exception:
                logger.exception(
                    "    Page %d: FAILED", page_num + 1
                )

    if cost_tracker:
        logger.info("  [%s] Cost so far: $%.4f", app_id, cost_tracker.total_cost)

    return pages_processed


def main():
    import os

    # Load .env from project root
    from research.config import ResearchConfig
    cfg = ResearchConfig()

    parser = argparse.ArgumentParser(
        description="Extract spatial descriptions from floor plan PDFs using GPT-4o Vision."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(cfg.bcc_data_path),
        help="Directory containing application subdirectories with PDFs (default: BCC sample data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for .txt files (default: graphrag_workspace/input/)",
    )
    parser.add_argument(
        "--raw-output-dir",
        type=Path,
        default=None,
        help="Output directory for raw JSON responses (default: output/vision_raw/)",
    )
    parser.add_argument(
        "--applications",
        nargs="*",
        default=None,
        help="Specific application IDs to process (default: all)",
    )
    args = parser.parse_args()

    # Defaults
    research_dir = Path(__file__).resolve().parent.parent
    if args.output_dir is None:
        args.output_dir = research_dir / "graphrag_workspace" / "input"
    if args.raw_output_dir is None:
        args.raw_output_dir = research_dir / "output" / "vision_raw"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.raw_output_dir.mkdir(parents=True, exist_ok=True)

    # Validate input
    if not args.input_dir.is_dir():
        logger.error("Input directory does not exist: %s", args.input_dir)
        sys.exit(1)

    # Azure OpenAI client
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "")

    if not all([endpoint, api_key, deployment]):
        logger.error(
            "Missing Azure OpenAI env vars: AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHAT_DEPLOYMENT"
        )
        sys.exit(1)

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    # Cost tracking
    from research.cost_tracker import CostTracker
    tracker = CostTracker(budget_usd=cfg.budget_usd)
    logger.info("Budget limit: $%.2f (set RESEARCH_BUDGET_USD to change)", tracker.budget_usd)

    # Find application directories
    app_dirs = sorted(
        d for d in args.input_dir.iterdir()
        if d.is_dir() and (args.applications is None or d.name in args.applications)
    )

    if not app_dirs:
        logger.warning("No application directories found in %s", args.input_dir)
        sys.exit(1)

    total_pages = 0
    for app_dir in app_dirs:
        logger.info("Processing application: %s", app_dir.name)
        pages = extract_application(
            client, app_dir, args.output_dir, args.raw_output_dir,
            deployment, api_version,
            cost_tracker=tracker,
        )
        total_pages += pages

    tracker.print_summary()
    logger.info("Done: %d pages extracted from %d applications", total_pages, len(app_dirs))


if __name__ == "__main__":
    main()
