"""
Profile document processing to identify performance bottlenecks.

Usage:
    python scripts/utilities/profile_processing.py <document_id>
    python scripts/utilities/profile_processing.py --pdf "path/to/file.pdf"
"""

import sys
import time
from pathlib import Path
from datetime import datetime

from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence
from planproof.aoai import AzureOpenAIClient
from planproof.pipeline.ingest import ingest_pdf
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.field_mapper import map_fields


def time_operation(name, func, *args, **kwargs):
    """Time an operation and print the result."""
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"⏱️  {name}: {elapsed:.2f}s")
        return result, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ {name}: {elapsed:.2f}s (ERROR: {e})")
        raise


def profile_document_processing(pdf_path: str):
    """Profile the entire processing pipeline for a document."""
    print(f"\n🔍 Profiling document processing: {Path(pdf_path).name}")
    print("=" * 60)
    
    total_start = time.time()
    
    # Initialize clients
    db = Database()
    storage_client = StorageClient()
    docintel = DocumentIntelligence()
    aoai_client = AzureOpenAIClient()
    
    # Stage 1: Ingest
    print("\n📤 Stage 1: Ingestion")
    ingested, ingest_time = time_operation(
        "Upload to blob & create DB records",
        ingest_pdf,
        pdf_path,
        "PROFILE-TEST",
        storage_client=storage_client,
        db=db
    )
    
    # Stage 2: Extract
    print("\n📄 Stage 2: Extraction")
    pdf_bytes = Path(pdf_path).read_bytes()
    
    # Time Document Intelligence API call specifically
    print("  Calling Document Intelligence API...")
    di_start = time.time()
    extraction_result = docintel.analyze_document(pdf_bytes)
    di_time = time.time() - di_start
    print(f"  ⏱️  Document Intelligence API: {di_time:.2f}s")
    
    # Time field mapping
    def map_fields_wrapper():
        return map_fields(extraction_result)
    
    mapped, map_time = time_operation(
        "Field mapping",
        map_fields_wrapper
    )
    
    # Stage 3: Validate
    print("\n✅ Stage 3: Validation")
    rules = load_rule_catalog("artefacts/rule_catalog.json")
    extraction_structured = {
        "fields": mapped["fields"],
        "evidence_index": mapped["evidence_index"],
        "metadata": extraction_result.get("metadata", {}),
        "text_blocks": extraction_result.get("text_blocks", []),
        "tables": extraction_result.get("tables", []),
        "page_anchors": extraction_result.get("page_anchors", {})
    }
    
    validation, validate_time = time_operation(
        "Rule validation",
        validate_extraction,
        extraction_structured,
        rules,
        context={"document_id": ingested["document_id"]},
        db=db,
        write_to_tables=False  # Skip DB writes for profiling
    )
    
    total_time = time.time() - total_start
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"  Ingestion:        {ingest_time:>8.2f}s ({ingest_time/total_time*100:.1f}%)")
    print(f"  Document Intel:   {di_time:>8.2f}s ({di_time/total_time*100:.1f}%) ⚠️  LARGEST BOTTLENECK")
    print(f"  Field Mapping:    {map_time:>8.2f}s ({map_time/total_time*100:.1f}%)")
    print(f"  Validation:       {validate_time:>8.2f}s ({validate_time/total_time*100:.1f}%)")
    print(f"  ───────────────────────────────────────")
    print(f"  TOTAL:            {total_time:>8.2f}s")
    print("\n💡 RECOMMENDATIONS:")
    
    if di_time > 60:
        print("  ⚠️  Document Intelligence API is very slow (>60s)")
        print("     - Check network connectivity to Azure")
        print("     - Check Azure service status/health")
        print("     - Consider document size/complexity")
        print("     - Check for API throttling/rate limits")
    
    if di_time / total_time > 0.8:
        print("  ⚠️  Document Intelligence accounts for >80% of processing time")
        print("     - This is expected but slow network/API can cause delays")
    
    if total_time > 300:
        print("  ⚠️  Total processing time >5 minutes - this is unusually slow")
        print("     - Normal range: 5-30 seconds for typical documents")
    
    print("\n✅ Profiling complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/utilities/profile_processing.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)
    
    try:
        profile_document_processing(pdf_path)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

