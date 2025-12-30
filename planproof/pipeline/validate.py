"""
Validate module: Apply deterministic validation rules to extracted fields.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
import logging
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    from planproof.db import Database, ValidationCheck, ValidationStatus

LOGGER = logging.getLogger(__name__)

def validate_document(
    document_id: int,
    validation_rules: Optional[Dict[str, Any]] = None,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Apply deterministic validation rules to extracted document fields.

    Args:
        document_id: Document ID
        validation_rules: Optional dictionary of validation rules.
                         If not provided, uses default rules.
        db: Optional Database instance

    Returns:
        List of validation result dictionaries
    """
    if db is None:
        db = Database()

    # Get extraction result
    from planproof.pipeline.extract import get_extraction_result
    from planproof.db import ValidationResult

    extraction_result = get_extraction_result(document_id, db=db)
    if extraction_result is None:
        raise ValueError(f"No extraction result found for document {document_id}")

    # Use default rules if not provided
    if validation_rules is None:
        validation_rules = _get_default_validation_rules()

    # Extract text content for field matching
    all_text = _extract_all_text(extraction_result)

    from planproof.config import get_settings

    # Apply validation rules
    validation_results: List[Dict[str, Any]] = []
    validation_rows = []
    session = db.get_session() if get_settings().enable_db_writes else None

    try:
        for field_name, rule in validation_rules.items():
            result = _validate_field(
                field_name=field_name,
                rule=rule,
                extraction_result=extraction_result,
                all_text=all_text
            )

            if session:
                # Create validation result record
                validation_result = ValidationResult(
                    document_id=document_id,
                    field_name=field_name,
                    status=result["status"],
                    confidence=result.get("confidence"),
                    extracted_value=result.get("extracted_value"),
                    expected_value=result.get("expected_value"),
                    rule_name=result.get("rule_name"),
                    error_message=result.get("error_message"),
                    evidence_page=result.get("evidence_page"),
                    evidence_location=result.get("evidence_location")
                )
                session.add(validation_result)
                validation_rows.append(validation_result)
            validation_results.append(result)

        if session:
            session.commit()

        # Refresh to get IDs
        if session:
            for row, result in zip(validation_rows, validation_results, strict=False):
                session.refresh(row)
                result["id"] = row.id

    finally:
        if session:
            session.close()

    return validation_results


def _extract_all_text(extraction_result: Dict[str, Any]) -> str:
    """Extract all text content from extraction result."""
    text_parts = []

    # Add text blocks
    for block in extraction_result.get("text_blocks", []):
        if block.get("content"):
            text_parts.append(block["content"])

    # Add table content
    for table in extraction_result.get("tables", []):
        for cell in table.get("cells", []):
            if cell.get("content"):
                text_parts.append(cell["content"])

    return "\n".join(text_parts)


def _validate_field(
    field_name: str,
    rule: Dict[str, Any],
    extraction_result: Dict[str, Any],
    all_text: str
) -> Dict[str, Any]:
    """
    Validate a single field against a rule.

    Args:
        field_name: Name of the field
        rule: Validation rule dictionary
        extraction_result: Document extraction result
        all_text: All text content from document

    Returns:
        Validation result dictionary
    """
    from planproof.db import ValidationStatus

    rule_type = rule.get("type", "presence")
    required = rule.get("required", False)
    pattern = rule.get("pattern")
    min_length = rule.get("min_length")
    max_length = rule.get("max_length")

    # Try to extract field value (simple keyword matching for now)
    extracted_value = _extract_field_value(field_name, all_text, extraction_result)

    # Check if field is required and missing
    if required and not extracted_value:
        return {
            "status": ValidationStatus.FAIL,
            "extracted_value": None,
            "rule_name": rule.get("name", field_name),
            "error_message": f"Required field '{field_name}' not found",
            "confidence": 0.0
        }

    # If field is not required and not found, mark as pass
    if not required and not extracted_value:
        return {
            "status": ValidationStatus.PASS,
            "extracted_value": None,
            "rule_name": rule.get("name", field_name),
            "confidence": 1.0
        }

    # Validate pattern if provided
    if pattern and extracted_value:
        import re
        if not re.search(pattern, extracted_value, re.IGNORECASE):
            return {
                "status": ValidationStatus.FAIL,
                "extracted_value": extracted_value,
                "rule_name": rule.get("name", field_name),
                "error_message": f"Field '{field_name}' does not match required pattern",
                "confidence": 0.5
            }

    # Validate length constraints
    if extracted_value:
        if min_length and len(extracted_value) < min_length:
            return {
                "status": ValidationStatus.FAIL,
                "extracted_value": extracted_value,
                "rule_name": rule.get("name", field_name),
                "error_message": f"Field '{field_name}' is too short (min: {min_length})",
                "confidence": 0.5
            }

        if max_length and len(extracted_value) > max_length:
            return {
                "status": ValidationStatus.FAIL,
                "extracted_value": extracted_value,
                "rule_name": rule.get("name", field_name),
                "error_message": f"Field '{field_name}' is too long (max: {max_length})",
                "confidence": 0.5
            }

    # Find evidence location
    evidence_page, evidence_location = _find_evidence_location(
        field_name, extracted_value, extraction_result
    )

    return {
        "status": ValidationStatus.PASS,
        "extracted_value": extracted_value,
        "rule_name": rule.get("name", field_name),
        "confidence": 0.8,  # Default confidence for deterministic validation
        "evidence_page": evidence_page,
        "evidence_location": evidence_location
    }


def _extract_field_value(
    field_name: str,
    all_text: str,
    extraction_result: Dict[str, Any]
) -> Optional[str]:
    """
    Extract field value from document text (simple keyword-based extraction).

    This is a basic implementation. In production, you might use:
    - Named entity recognition (NER)
    - LLM-based extraction
    - Structured form extraction
    """
    # Simple keyword matching (case-insensitive)
    keywords = [
        field_name.replace("_", " "),
        field_name.replace("_", "-"),
        field_name
    ]

    for keyword in keywords:
        # Look for patterns like "Field Name: value" or "Field Name value"
        patterns = [
            f"{keyword}:\\s*([^\\n]+)",
            f"{keyword}\\s+([^\\n]+)",
        ]

        import re
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    return value

    return None


def _find_evidence_location(
    field_name: str,
    field_value: Optional[str],
    extraction_result: Dict[str, Any]
) -> Tuple[Optional[int], Optional[str]]:
    """Find the page number and location where field evidence was found."""
    if not field_value:
        return None, None

    # Search through text blocks
    for block in extraction_result.get("text_blocks", []):
        if field_value.lower() in block.get("content", "").lower():
            page_num = block.get("page_number")
            bbox = block.get("bounding_box")
            location = f"text_block_{block.get('page_number')}" if page_num else None
            return page_num, location

    return None, None


def _get_default_validation_rules() -> Dict[str, Dict[str, Any]]:
    """
    Get default validation rules.

    In production, these should be loaded from validation_requirements.md
    or a configuration file.
    """
    return {
        "site_address": {
            "type": "presence",
            "required": True,
            "min_length": 10,
            "name": "Site Address Validation"
        },
        "proposed_use": {
            "type": "presence",
            "required": True,
            "name": "Proposed Use Validation"
        },
        "application_ref": {
            "type": "presence",
            "required": True,
            "pattern": r"APP/\d{4}/\d+",
            "name": "Application Reference Format"
        }
    }


# New rule catalog-based validation functions
from planproof.rules.catalog import Rule


def load_rule_catalog(path: str | Path = "artefacts/rule_catalog.json") -> List[Rule]:
    """Load rule catalog from JSON file."""
    import json as jsonlib
    
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Rule catalog not found: {path}\n"
            "Please run: python scripts/build_rule_catalog.py"
        )
    
    data = jsonlib.loads(p.read_text(encoding="utf-8"))
    rules = []
    for r in data.get("rules", []):
        # Rehydrate Rule from dict
        from planproof.rules.catalog import EvidenceExpectation
        ev_dict = r.get("evidence", {})
        evidence = EvidenceExpectation(
            source_types=ev_dict.get("source_types", []),
            keywords=ev_dict.get("keywords", []),
            min_confidence=ev_dict.get("min_confidence", 0.6)
        )
        rules.append(
            Rule(
                rule_id=r["rule_id"],
                title=r.get("title", ""),
                description=r.get("description", ""),
                required_fields=r.get("required_fields", []),
                evidence=evidence,
                severity=r.get("severity", "error"),
                applies_to=r.get("applies_to", []),
                tags=r.get("tags", []),
                required_fields_any=r.get("required_fields_any", False)  # Support OR logic
            )
        )
    return rules


def validate_extraction(
    extraction: Dict[str, Any],
    rules: List[Rule],
    *,
    context: Optional[Dict[str, Any]] = None,
    db: Optional[Database] = None,
    write_to_tables: bool = True
) -> Dict[str, Any]:
    """
    Deterministic validation:
    - expects extraction["fields"] dict (even if sparse) + extraction["evidence_index"]
    - checks required_fields presence/non-empty
    - emits findings and whether LLM gate is needed
    
    **Hybrid Storage Strategy:**
    - Returns dict format (for JSON artefact storage in blob)
    - Optionally writes to relational tables (ValidationCheck)
    - Both storage methods are maintained going forward
    
    Args:
        extraction: Extraction result dictionary
        rules: List of validation rules
        context: Optional context dict (document_id, submission_id, etc.)
        db: Optional Database instance for writing to relational tables
        write_to_tables: If True, write ValidationCheck records to database
                        Note: JSON artefact is always created separately in main pipeline
    """
    context = context or {}
    if write_to_tables and db:
        from planproof.db import ValidationStatus, ValidationCheck
    fields: Dict[str, Any] = extraction.get("fields", {}) or {}
    evidence_index: Dict[str, Any] = extraction.get("evidence_index", {}) or {}
    
    # Get document type for doc-type-aware validation
    document_type = fields.get("document_type", "unknown")

    findings: List[Dict[str, Any]] = []
    needs_llm = False
    
    # Get IDs from context for writing to tables
    document_id = context.get("document_id")
    submission_id = context.get("submission_id")

    session = None
    if write_to_tables and db:
        session = db.get_session()

    try:
        for rule in rules:
            # Skip rule if it doesn't apply to this document type
            if rule.applies_to and len(rule.applies_to) > 0:
                if document_type not in rule.applies_to:
                    # Rule doesn't apply to this document type - skip it
                    continue

            missing = []
            found_any = False

            # Check required fields
            for f in rule.required_fields:
                v = fields.get(f)
                if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and len(v) == 0):
                    missing.append(f)
                else:
                    found_any = True  # At least one field is present

            # For OR logic (required_fields_any=True): pass if ANY field is present
            # For AND logic (required_fields_any=False): fail if ANY field is missing
            if rule.required_fields_any:
                # OR logic: if any field is found, rule passes
                if found_any:
                    missing = []  # Clear missing - rule passes
                # else: missing contains all fields (rule fails)
            # else: AND logic - missing contains fields that are missing (rule fails if any missing)

            if missing:
                status = "needs_review"
                if rule.severity == "error":
                    needs_llm = True
                # Find evidence snippets for missing fields (page numbers + snippets)
                evidence_snippets = []
                evidence_ids = []
                for ev_key, ev_data in evidence_index.items():
                    # Handle both field-specific evidence (list) and general text blocks (dict)
                    if isinstance(ev_data, list):
                        # Field-specific evidence: list of dicts
                        for ev_item in ev_data[:3]:  # Top 3 snippets
                            page_num = ev_item.get("page")
                            snippet = ev_item.get("snippet", "")
                            if page_num and snippet:
                                evidence_snippets.append({
                                    "evidence_key": ev_key,
                                    "page": page_num,
                                    "snippet": snippet
                                })
                    elif isinstance(ev_data, dict):
                        # General text block or table
                        page_num = ev_data.get("page_number")
                        snippet = ev_data.get("snippet", ev_data.get("content", ""))[:100]
                        if page_num and snippet:
                            evidence_snippets.append({
                                "evidence_key": ev_key,
                                "page": page_num,
                                "snippet": snippet
                            })

                finding = {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "status": status,
                    "message": f"Missing required fields: {', '.join(missing)}",
                    "required_fields": rule.required_fields,
                    "missing_fields": missing,
                    "evidence": {
                        "expected_sources": rule.evidence.source_types,
                        "keywords": rule.evidence.keywords,
                        "available_evidence_keys": list(evidence_index.keys()),
                        "evidence_snippets": evidence_snippets[:5]  # Top 5 snippets with page numbers
                    },
                }
                findings.append(finding)

                # Write to ValidationCheck table if enabled
                if session:
                    try:
                        from planproof.db import Evidence
                        # Get evidence IDs for this rule
                        for ev_key in evidence_index.keys():
                            evidence = session.query(Evidence).filter(
                                Evidence.document_id == document_id,
                                Evidence.evidence_key == ev_key
                            ).first()
                            if evidence:
                                evidence_ids.append(evidence.id)

                        # Map status to ValidationStatus enum
                        if status == "pass":
                            check_status = ValidationStatus.PASS
                        elif status == "needs_review":
                            check_status = ValidationStatus.NEEDS_REVIEW
                        else:
                            check_status = ValidationStatus.FAIL

                        validation_check = ValidationCheck(
                            submission_id=submission_id,
                            document_id=document_id,
                            rule_id_string=rule.rule_id,
                            status=check_status,
                            explanation=finding["message"],
                            evidence_ids=evidence_ids if evidence_ids else None
                        )
                        session.add(validation_check)
                    except Exception as exc:
                        LOGGER.warning(
                            "validation_check_write_failed",
                            extra={"document_id": document_id, "rule_id": rule.rule_id, "error": str(exc)},
                        )
            else:
                finding = {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "status": "pass",
                    "message": "All required fields present.",
                    "required_fields": rule.required_fields,
                    "missing_fields": [],
                    "evidence": {"available_evidence_keys": list(evidence_index.keys())},
                }
                findings.append(finding)

                # Write to ValidationCheck table if enabled
                if session:
                    try:
                        validation_check = ValidationCheck(
                            submission_id=submission_id,
                            document_id=document_id,
                            rule_id_string=rule.rule_id,
                            status=ValidationStatus.PASS,
                            explanation="All required fields present."
                        )
                        session.add(validation_check)
                    except Exception as exc:
                        LOGGER.warning(
                            "validation_check_write_failed",
                            extra={"document_id": document_id, "rule_id": rule.rule_id, "error": str(exc)},
                        )

        if session:
            session.commit()
    finally:
        if session:
            session.close()

    summary = {
        "rule_count": len(rules),
        "pass": sum(1 for f in findings if f["status"] == "pass"),
        "needs_review": sum(1 for f in findings if f["status"] == "needs_review"),
        "fail": sum(1 for f in findings if f["status"] == "fail"),
        "needs_llm": needs_llm,
    }

    return {"summary": summary, "findings": findings, "context": context}
