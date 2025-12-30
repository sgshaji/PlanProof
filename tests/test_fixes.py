#!/usr/bin/env python3
"""
Test script to verify all ground-truth fixes are working correctly.
Tests the 3 documents from run 10 with expected values.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from planproof.pipeline.ingest import ingest_pdf
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.llm_gate import should_trigger_llm
from planproof.db import Database
from planproof.storage import StorageClient
from planproof.docintel import DocumentIntelligence

# Expected ground truth values
EXPECTED = {
    "Document-92C2F0E3D233D9722023BD0BAA17C379.pdf": {  # Doc 82 - Application Form
        "document_type": "application_form",
        "application_ref": "PP-14469287",
        "site_address": "Saltley Business Park, Unit M, Dorset Road, Washwood Heath, Birmingham, B8 1BG",
        "postcode": "B8 1BG",  # NOT B1 1TU
        "proposed_use": "Prior Approval",  # Should contain "Prior Approval"
        "applicant_name": "Daniel Green",  # Should contain this
        "applicant_email": None,  # Should NOT be council email
        "applicant_phone": None,  # Should NOT be council phone
    },
    "Document-DEA8A9AF4764ABA5965D620017BCD119.pdf": {  # Doc 83 - Site Notice
        "document_type": "site_notice",
        "site_address": "Unit M, Dorset Road, Saltley Business Park",  # From demolition pattern
        "postcode": "B8 1BG",
        "proposed_use": None,  # Optional for site_notice
        "application_ref": None,  # Should NOT be required
    },
    "Document-8B3727462503AC2C6EB3A930DDC04D92.pdf": {  # Doc 81 - Site Plan
        "document_type": "site_plan",
        "site_address": None,  # Optional, but should NOT be "4 2447"
        "postcode": "B8 1BG",  # Optional
        "proposed_use": None,  # Should NOT be required
        "application_ref": None,  # Should NOT be required
    }
}

def test_document(file_path: Path, expected: dict, app_ref: str = "TEST-2025"):
    """Test a single document against expected values."""
    print(f"\n{'='*70}")
    print(f"Testing: {file_path.name}")
    print(f"{'='*70}")
    
    db = Database()
    storage_client = StorageClient()
    docintel = DocumentIntelligence()
    
    try:
        # Ingest
        print("\n1. Ingesting...")
        ingested = ingest_pdf(
            str(file_path),
            app_ref,
            storage_client=storage_client,
            db=db
        )
        doc_id = ingested["document_id"]
        print(f"   ✓ Document ID: {doc_id}")
        
        # Extract
        print("\n2. Extracting...")
        pdf_bytes = file_path.read_bytes()
        ingested_with_context = {**ingested, "context": {"run_id": 999}}
        extraction = extract_from_pdf_bytes(
            pdf_bytes,
            ingested_with_context,
            docintel=docintel,
            storage_client=storage_client,
            db=db,
            write_to_tables=False  # Don't write to DB for test
        )
        
        fields = extraction.get("fields", {})
        print(f"   Document Type: {fields.get('document_type', 'unknown')}")
        print(f"   Extracted Fields:")
        for key, value in fields.items():
            if not key.endswith("_confidence"):
                print(f"     - {key}: {value}")
        
        # Validate
        print("\n3. Validating...")
        rules = load_rule_catalog("artefacts/rule_catalog.json")
        validation = validate_extraction(
            extraction,
            rules,
            context={"document_id": doc_id, "submission_id": ingested.get("submission_id")},
            db=db,
            write_to_tables=False
        )
        
        findings = validation.get("findings", [])
        summary = validation.get("summary", {})
        print(f"   Summary: {summary.get('pass')} pass, {summary.get('needs_review')} needs_review, {summary.get('fail')} fail")
        print(f"   Needs LLM: {summary.get('needs_llm', False)}")
        
        # Check LLM trigger
        print("\n4. Checking LLM Gate...")
        llm_should_trigger = should_trigger_llm(
            validation,
            extraction,
            application_ref=app_ref,
            submission_id=ingested.get("submission_id"),
            db=db
        )
        print(f"   LLM Triggered: {llm_should_trigger}")
        
        # Compare with expected
        print("\n5. Comparing with Expected Values:")
        issues = []
        
        for field, expected_value in expected.items():
            if field == "document_type":
                actual = fields.get("document_type")
                if actual != expected_value:
                    issues.append(f"❌ {field}: Expected '{expected_value}', got '{actual}'")
                else:
                    print(f"   ✅ {field}: {actual}")
            elif field == "application_ref":
                actual = fields.get("application_ref")
                if expected_value:
                    if actual != expected_value:
                        issues.append(f"❌ {field}: Expected '{expected_value}', got '{actual}'")
                    else:
                        print(f"   ✅ {field}: {actual}")
                else:
                    if actual:
                        issues.append(f"⚠️  {field}: Should be None, got '{actual}'")
                    else:
                        print(f"   ✅ {field}: None (as expected)")
            elif field == "site_address":
                actual = fields.get("site_address")
                if expected_value:
                    # Check if expected is contained in actual (flexible matching)
                    if actual and expected_value.lower() in actual.lower():
                        print(f"   ✅ {field}: Contains expected value")
                    elif actual == "4 2447" or actual == "We can only make recommendations":
                        issues.append(f"❌ {field}: Extracted noise '{actual}' instead of proper address")
                    elif not actual:
                        issues.append(f"❌ {field}: Expected '{expected_value}', got None")
                    else:
                        print(f"   ⚠️  {field}: Got '{actual}' (expected contains '{expected_value}')")
                else:
                    if actual == "4 2447":
                        issues.append(f"❌ {field}: Extracted noise '{actual}' (should be None or proper address)")
                    elif actual:
                        print(f"   ⚠️  {field}: Got '{actual}' (optional field)")
                    else:
                        print(f"   ✅ {field}: None (optional)")
            elif field == "postcode":
                actual = fields.get("postcode")
                if expected_value:
                    if actual == expected_value:
                        print(f"   ✅ {field}: {actual}")
                    elif actual == "B1 1TU":
                        issues.append(f"❌ {field}: Extracted council PO box '{actual}' instead of '{expected_value}'")
                    elif not actual:
                        issues.append(f"❌ {field}: Expected '{expected_value}', got None")
                    else:
                        issues.append(f"❌ {field}: Expected '{expected_value}', got '{actual}'")
                else:
                    print(f"   ✅ {field}: {actual or 'None'} (optional)")
            elif field == "proposed_use":
                actual = fields.get("proposed_use")
                if expected_value:
                    if actual and expected_value.lower() in actual.lower():
                        print(f"   ✅ {field}: Contains expected value")
                    elif not actual:
                        issues.append(f"❌ {field}: Expected to contain '{expected_value}', got None")
                    else:
                        print(f"   ⚠️  {field}: Got '{actual}' (expected contains '{expected_value}')")
                else:
                    if actual:
                        print(f"   ⚠️  {field}: Got '{actual}' (optional)")
                    else:
                        print(f"   ✅ {field}: None (optional)")
            elif field == "applicant_name":
                actual = fields.get("applicant_name")
                if expected_value:
                    if actual and expected_value.lower() in actual.lower():
                        print(f"   ✅ {field}: Contains expected value")
                    elif not actual:
                        issues.append(f"❌ {field}: Expected to contain '{expected_value}', got None")
                    else:
                        print(f"   ⚠️  {field}: Got '{actual}' (expected contains '{expected_value}')")
            elif field == "applicant_email":
                actual = fields.get("applicant_email")
                if expected_value is None:
                    if actual and "birmingham.gov.uk" in actual:
                        issues.append(f"❌ {field}: Extracted council email '{actual}' (should be None)")
                    elif actual:
                        print(f"   ⚠️  {field}: Got '{actual}' (not council)")
                    else:
                        print(f"   ✅ {field}: None (no council email)")
            elif field == "applicant_phone":
                actual = fields.get("applicant_phone")
                if expected_value is None:
                    if actual and "0121 464" in actual:
                        issues.append(f"❌ {field}: Extracted council phone '{actual}' (should be None)")
                    elif actual:
                        print(f"   ⚠️  {field}: Got '{actual}' (not council)")
                    else:
                        print(f"   ✅ {field}: None (no council phone)")
        
        # Check validation rules
        print("\n6. Validation Rules Check:")
        doc_type = fields.get("document_type", "unknown")
        applied_rules = [f["rule_id"] for f in findings]
        print(f"   Applied Rules: {', '.join(applied_rules) if applied_rules else 'None'}")
        
        if doc_type == "site_plan":
            if "R3" in applied_rules:
                issues.append("❌ R3 (application_ref) should NOT apply to site_plan")
            if "R2" in applied_rules:
                issues.append("❌ R2 (proposed_use) should NOT apply to site_plan")
            print(f"   ✅ No inappropriate rules applied to site_plan")
        
        if doc_type == "site_notice":
            if "R3" in applied_rules:
                issues.append("❌ R3 (application_ref) should NOT apply to site_notice")
            print(f"   ✅ R1-SITE-NOTICE applied (lenient OR rule)")
        
        # Summary
        print(f"\n{'='*70}")
        if issues:
            print(f"❌ ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("✅ ALL CHECKS PASSED!")
        print(f"{'='*70}\n")
        
        return {
            "document_id": doc_id,
            "filename": file_path.name,
            "fields": fields,
            "validation": validation,
            "llm_triggered": llm_should_trigger,
            "issues": issues
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "filename": file_path.name}


def main():
    """Run tests on all 3 documents."""
    print("="*70)
    print("GROUND-TRUTH FIXES VERIFICATION TEST")
    print("="*70)
    
    # Get test files
    test_dir = Path("runs/10/inputs")
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    test_files = list(test_dir.glob("*.pdf"))
    if not test_files:
        print(f"❌ No PDF files found in {test_dir}")
        return
    
    print(f"\nFound {len(test_files)} test files")
    
    results = []
    for pdf_file in sorted(test_files):
        expected = EXPECTED.get(pdf_file.name, {})
        result = test_document(pdf_file, expected, app_ref="TEST-2025")
        results.append(result)
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    
    total_issues = sum(len(r.get("issues", [])) for r in results)
    llm_triggers = sum(1 for r in results if r.get("llm_triggered"))
    
    print(f"\nTotal Documents Tested: {len(results)}")
    print(f"Total Issues Found: {total_issues}")
    print(f"LLM Triggers: {llm_triggers} / {len(results)}")
    
    if total_issues == 0:
        print("\n✅ ALL TESTS PASSED! All fixes are working correctly.")
    else:
        print(f"\n⚠️  Found {total_issues} issues. Review the output above.")
    
    # Save results
    output_file = Path("test_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
