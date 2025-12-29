"""
PlanProof - Main entry point for the planning validation system.
"""

import sys
from pathlib import Path
from typing import Optional

from planproof.config import get_settings
from planproof.db import Database
from planproof.pipeline import ingest_pdf, extract_document, validate_document, resolve_with_llm


def main():
    """Main entry point."""
    print("PlanProof - Planning Validation System MVP")
    print("=" * 50)

    # Example usage (replace with actual CLI or API)
    if len(sys.argv) < 2:
        print("Usage: python main.py <command> [args...]")
        print("\nCommands:")
        print("  ingest <pdf_path> <application_ref> [applicant_name]")
        print("  extract <document_id>")
        print("  validate <document_id>")
        print("  resolve <document_id> [field_name]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "ingest":
            if len(sys.argv) < 4:
                print("Usage: python main.py ingest <pdf_path> <application_ref> [applicant_name]")
                sys.exit(1)

            pdf_path = sys.argv[2]
            application_ref = sys.argv[3]
            applicant_name = sys.argv[4] if len(sys.argv) > 4 else None

            result = ingest_pdf(pdf_path, application_ref, applicant_name=applicant_name)
            print(f"✓ Ingested: {result['filename']}")
            print(f"  Application ID: {result['application_id']}")
            print(f"  Document ID: {result['document_id']}")
            print(f"  Blob URI: {result['blob_uri']}")

        elif command == "extract":
            if len(sys.argv) < 3:
                print("Usage: python main.py extract <document_id>")
                sys.exit(1)

            document_id = int(sys.argv[2])
            result = extract_document(document_id)
            print(f"✓ Extracted document {document_id}")
            print(f"  Artefact ID: {result['artefact_id']}")
            print(f"  Artefact URI: {result['artefact_blob_uri']}")
            print(f"  Page count: {result['extraction_result']['metadata']['page_count']}")

        elif command == "validate":
            if len(sys.argv) < 3:
                print("Usage: python main.py validate <document_id>")
                sys.exit(1)

            document_id = int(sys.argv[2])
            results = validate_document(document_id)
            print(f"✓ Validated document {document_id}")
            for r in results:
                status_icon = "✓" if r["status"] == "pass" else "✗"
                print(f"  {status_icon} {r['field_name']}: {r['status']} (confidence: {r.get('confidence', 'N/A')})")

        elif command == "resolve":
            if len(sys.argv) < 3:
                print("Usage: python main.py resolve <document_id> [field_name]")
                sys.exit(1)

            document_id = int(sys.argv[2])
            field_name = sys.argv[3] if len(sys.argv) > 3 else None
            results = resolve_with_llm(document_id, field_name=field_name)
            print(f"✓ Resolved with LLM for document {document_id}")
            for r in results:
                print(f"  {r['field_name']}: {r['status']} (confidence: {r.get('confidence', 'N/A')})")
                if r.get("reasoning"):
                    print(f"    Reasoning: {r['reasoning'][:100]}...")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

