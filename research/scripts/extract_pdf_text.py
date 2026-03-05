"""Extract text from planning PDFs for GraphRAG indexing.

Reads PDFs from an input directory, extracts text using pdfplumber,
and writes .txt files into the GraphRAG workspace input directory.
Image-only PDFs (with no extractable text) are flagged for Azure
Document Intelligence processing.
"""

import argparse
import logging
import sys
from pathlib import Path

import pdfplumber

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Minimum characters per page to consider text extraction successful
MIN_CHARS_PER_PAGE = 50


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, bool]:
    """Extract text from a single PDF.

    Returns:
        Tuple of (extracted_text, is_text_extractable).
        If the PDF has too little text per page, is_text_extractable is False.
    """
    pages_text = []
    low_text_pages = 0

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append(text)
            if len(text.strip()) < MIN_CHARS_PER_PAGE:
                low_text_pages += 1

    full_text = "\n\n".join(pages_text)
    total_pages = len(pages_text)

    # If more than half the pages have little text, flag as image-only
    is_text_extractable = low_text_pages <= total_pages / 2

    return full_text, is_text_extractable


def extract_pdfs(input_dir: Path, output_dir: Path) -> None:
    """Extract text from all PDFs in input_dir and save to output_dir."""
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in %s", input_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    image_only = []

    for pdf_path in pdf_files:
        logger.info("Processing: %s", pdf_path.name)
        try:
            text, is_text_extractable = extract_text_from_pdf(pdf_path)
        except Exception:
            logger.exception("Failed to process %s", pdf_path.name)
            continue

        if not is_text_extractable:
            image_only.append(pdf_path.name)
            logger.warning(
                "  -> Low text content — may need Azure Document Intelligence: %s",
                pdf_path.name,
            )

        # Write the text file regardless (partial text is still useful)
        out_path = output_dir / f"{pdf_path.stem}.txt"
        out_path.write_text(text, encoding="utf-8")
        logger.info(
            "  -> Saved %s (%d chars)", out_path.name, len(text)
        )

    logger.info(
        "Done: %d PDFs processed, %d text files written",
        len(pdf_files),
        len(pdf_files) - len(image_only) + len(
            [f for f in image_only if (output_dir / f"{Path(f).stem}.txt").exists()]
        ),
    )

    if image_only:
        logger.warning(
            "Image-heavy PDFs needing Azure Document Intelligence:\n  %s",
            "\n  ".join(image_only),
        )


def main():
    # Load .env from project root
    from research.config import ResearchConfig
    cfg = ResearchConfig()

    parser = argparse.ArgumentParser(
        description="Extract text from planning PDFs for GraphRAG indexing."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing PDF files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory for .txt files "
            "(default: research/graphrag_workspace/input/)"
        ),
    )
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = (
            Path(__file__).resolve().parent.parent
            / "graphrag_workspace"
            / "input"
        )

    if not args.input_dir.is_dir():
        logger.error("Input directory does not exist: %s", args.input_dir)
        sys.exit(1)

    extract_pdfs(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
