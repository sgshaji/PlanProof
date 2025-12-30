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
    text_index = _build_text_index(extraction_result)

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
                text_index=text_index
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
    text_index: Dict[str, Any]
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
    extracted_value = _extract_field_value(
        field_name,
        text_index,
        extraction_result
    )

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


def _normalize_label(label: str) -> str:
    return " ".join(
        label.strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace(":", "")
        .split()
    )


def _build_text_index(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    label_value_index: Dict[str, str] = {}
    blocks: List[Dict[str, str]] = []

    for block in extraction_result.get("text_blocks", []):
        content = block.get("content")
        if not content:
            continue
        blocks.append(
            {
                "content": content,
                "content_lower": content.lower()
            }
        )

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if ":" in line:
                label, value = line.split(":", 1)
                label = label.strip()
                value = value.strip()
                if label and value:
                    label_value_index[_normalize_label(label)] = value
                    continue

            if line.endswith(":") and idx + 1 < len(lines):
                label = line[:-1].strip()
                value = lines[idx + 1].strip()
                if label and value:
                    label_value_index[_normalize_label(label)] = value

    return {
        "blocks": blocks,
        "label_value_index": label_value_index,
        "full_text": _extract_all_text(extraction_result)
    }


def _extract_field_value(
    field_name: str,
    text_index: Dict[str, Any],
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

    label_value_index = text_index.get("label_value_index", {})

    for keyword in keywords:
        normalized = _normalize_label(keyword)
        if normalized in label_value_index:
            return label_value_index[normalized]

        for label, value in label_value_index.items():
            if normalized in label:
                return value

    for keyword in keywords:
        keyword_lower = keyword.lower()
        for block in text_index.get("blocks", []):
            content_lower = block.get("content_lower", "")
            if keyword_lower not in content_lower:
                continue
            lines = block.get("content", "").splitlines()
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                if keyword_lower not in line_lower:
                    continue
                if ":" in line:
                    label, value = line.split(":", 1)
                    if keyword_lower in label.lower():
                        value = value.strip()
                        if value:
                            return value
                stripped = line_lower.strip().rstrip(":")
                if stripped == keyword_lower and idx + 1 < len(lines):
                    value = lines[idx + 1].strip()
                    if value:
                        return value

    all_text = text_index.get("full_text", "")

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
                required_fields_any=r.get("required_fields_any", False),  # Support OR logic
                rule_category=r.get("rule_category", "FIELD_REQUIRED")
            )
        )
    return rules


def _dispatch_by_category(
    rule: Rule,
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Dispatch rule to category-specific validator.
    
    Args:
        rule: Rule to validate
        context: Context dict with extraction, fields, evidence_index, document_id, submission_id, etc.
    
    Returns:
        Finding dict or None if rule doesn't apply
    """
    category = rule.rule_category.upper()
    
    if category == "DOCUMENT_REQUIRED":
        return _validate_document_required(rule, context)
    elif category == "CONSISTENCY":
        return _validate_consistency(rule, context)
    elif category == "MODIFICATION":
        return _validate_modification(rule, context)
    elif category == "SPATIAL":
        return _validate_spatial(rule, context)
    elif category == "FIELD_REQUIRED":
        # Default field validation (existing logic)
        return None  # Will be handled by existing logic
    else:
        LOGGER.warning(f"Unknown rule category: {category} for rule {rule.rule_id}")
        return None


def _validate_document_required(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate DOCUMENT_REQUIRED rules.
    Check if required documents are present for the submission.
    """
    submission_id = context.get("submission_id")
    db = context.get("db")
    
    if not submission_id or not db:
        return {
            "status": "needs_review",
            "severity": rule.severity,
            "message": "Cannot validate document requirements: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }
    
    # Get required documents from rule
    # For DOCUMENT_REQUIRED rules, we expect required_documents field or use required_fields as doc types
    required_docs = rule.required_fields if rule.required_fields else []
    
    if not required_docs:
        return None  # No documents specified
    
    # Query documents for this submission
    from planproof.db import Document
    session = db.get_session()
    
    try:
        documents = session.query(Document).filter(Document.submission_id == submission_id).all()
        present_doc_types = {doc.document_type for doc in documents if doc.document_type}
        
        # Check for missing documents
        missing_docs = [doc_type for doc_type in required_docs if doc_type not in present_doc_types]
        
        if missing_docs:
            # Generate evidence: list of present documents
            evidence_snippets = []
            for doc in documents[:5]:  # Show up to 5 present documents
                evidence_snippets.append({
                    "page": 1,
                    "snippet": f"Present: {doc.document_type} - {doc.filename}",
                    "document_type": doc.document_type
                })
            
            return {
                "status": "fail",
                "severity": rule.severity,
                "message": f"Missing required documents: {', '.join(missing_docs)}",
                "missing_fields": missing_docs,
                "evidence": {
                    "evidence_snippets": evidence_snippets,
                    "present_documents": list(present_doc_types),
                    "missing_documents": missing_docs
                }
            }
        else:
            # All required documents present
            evidence_snippets = []
            for doc_type in required_docs:
                matching_docs = [doc for doc in documents if doc.document_type == doc_type]
                if matching_docs:
                    evidence_snippets.append({
                        "page": 1,
                        "snippet": f"Found: {doc_type} - {matching_docs[0].filename}",
                        "document_type": doc_type
                    })
            
            return {
                "status": "pass",
                "severity": rule.severity,
                "message": "All required documents present",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets,
                    "present_documents": list(present_doc_types)
                }
            }
    
    finally:
        session.close()


def _validate_consistency(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate CONSISTENCY rules.
    Check if key fields match across multiple documents in the same submission.
    """
    submission_id = context.get("submission_id")
    db = context.get("db")
    
    if not submission_id or not db:
        return {
            "status": "needs_review",
            "severity": rule.severity,
            "message": "Cannot validate consistency: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }
    
    # Get consistency fields from rule (fields to check for consistency)
    consistency_fields = rule.required_fields if rule.required_fields else []
    
    if not consistency_fields:
        return None  # No fields specified
    
    # Query extracted fields for this submission
    from planproof.db import ExtractedField, Document
    session = db.get_session()
    
    try:
        conflicts = []
        evidence_snippets = []
        
        for field_key in consistency_fields:
            # Get all extracted values for this field across documents
            extracted_fields = session.query(ExtractedField).filter(
                ExtractedField.submission_id == submission_id,
                ExtractedField.field_name == field_key
            ).all()
            
            if len(extracted_fields) <= 1:
                continue  # No conflict possible with 0 or 1 value
            
            # Group by field_value to detect conflicts
            value_groups = {}
            for ef in extracted_fields:
                value = ef.field_value
                if value not in value_groups:
                    value_groups[value] = []
                value_groups[value].append(ef)
            
            # If more than one unique value, we have a conflict
            if len(value_groups) > 1:
                conflicts.append(field_key)
                
                # Build evidence from all conflicting sources
                for value, efs in value_groups.items():
                    for ef in efs[:2]:  # Max 2 per value
                        # Get document info
                        doc = session.query(Document).filter(Document.id == ef.document_id).first()
                        doc_name = doc.filename if doc else f"document_{ef.document_id}"
                        doc_type = doc.document_type if doc else "unknown"
                        
                        evidence_snippets.append({
                            "page": 1,  # Page info not available in ExtractedField
                            "snippet": f"{field_key}='{value}' in {doc_type} ({doc_name})",
                            "field_key": field_key,
                            "field_value": value,
                            "document_id": ef.document_id,
                            "document_type": doc_type
                        })
        
        if conflicts:
            return {
                "status": "needs_review",
                "severity": rule.severity,
                "message": f"Conflicting values found for: {', '.join(conflicts)}",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets,
                    "conflicting_fields": conflicts
                }
            }
        else:
            # All fields consistent
            return {
                "status": "pass",
                "severity": rule.severity,
                "message": "All checked fields are consistent across documents",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": [],
                    "checked_fields": consistency_fields
                }
            }
    
    finally:
        session.close()


def _validate_modification(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate MODIFICATION rules.
    Check parent reference and delta completeness for modification submissions.
    """
    submission_id = context.get("submission_id")
    db = context.get("db")
    
    if not submission_id or not db:
        return {
            "status": "needs_review",
            "severity": rule.severity,
            "message": "Cannot validate modification: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }
    
    from planproof.db import Submission, ChangeSet
    session = db.get_session()
    
    try:
        # Get submission
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {
                "status": "fail",
                "severity": rule.severity,
                "message": "Submission not found",
                "missing_fields": [],
                "evidence": {}
            }
        
        # Check if this is a modification (V1+)
        is_modification = submission.submission_version != "V0"
        
        if not is_modification:
            # Not a modification, rule doesn't apply
            return {
                "status": "pass",
                "severity": rule.severity,
                "message": "Not a modification submission (V0)",
                "missing_fields": [],
                "evidence": {}
            }
        
        # For modifications, check parent reference
        if not submission.parent_submission_id:
            return {
                "status": "fail",
                "severity": rule.severity,
                "message": "Missing parent reference: modification submissions must reference parent V0",
                "missing_fields": ["parent_submission_id"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"Submission {submission.submission_version} has no parent_submission_id"
                    }]
                }
            }
        
        # Check if ChangeSet exists
        changeset = session.query(ChangeSet).filter(
            ChangeSet.submission_id == submission_id
        ).first()
        
        if not changeset:
            return {
                "status": "fail",
                "severity": rule.severity,
                "message": "Missing delta computation: ChangeSet not found for modification",
                "missing_fields": ["changeset"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"No ChangeSet found for submission {submission.submission_version}"
                    }]
                }
            }
        
        # Check delta completeness (ChangeSet has ChangeItems)
        from planproof.db import ChangeItem
        change_items = session.query(ChangeItem).filter(
            ChangeItem.change_set_id == changeset.id
        ).all()
        
        if not change_items:
            return {
                "status": "needs_review",
                "severity": "warning",
                "message": "Delta computation incomplete: no changes detected",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"ChangeSet {changeset.id} has no ChangeItems"
                    }],
                    "changeset_id": changeset.id
                }
            }
        
        # All checks passed
        return {
            "status": "pass",
            "severity": rule.severity,
            "message": f"Modification valid: {len(change_items)} changes detected, significance={changeset.significance_score:.2f}",
            "missing_fields": [],
            "evidence": {
                "evidence_snippets": [{
                    "page": 1,
                    "snippet": f"ChangeSet {changeset.id}: {len(change_items)} changes, significance={changeset.significance_score:.2f}"
                }],
                "changeset_id": changeset.id,
                "change_count": len(change_items),
                "significance_score": changeset.significance_score
            }
        }
    
    finally:
        session.close()


def _validate_spatial(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate SPATIAL rules.
    Stub - deferred post-MVP.
    """
    # Stub - deferred
    return None


def validate_modification_submission(
    submission_id: int,
    rules: List[Rule],
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Validate a modification submission with targeted revalidation.
    Only re-runs rules impacted by changes in the ChangeSet.
    
    Args:
        submission_id: V1+ submission ID
        rules: List of all validation rules
        db: Optional Database instance
    
    Returns:
        Validation results with impacted_rules metadata
    """
    if db is None:
        db = Database()
    
    from planproof.db import Submission, ChangeSet
    from planproof.services.delta_service import get_impacted_rules
    
    session = db.get_session()
    
    try:
        # Get submission
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {"error": f"Submission {submission_id} not found"}
        
        if submission.submission_version == "V0":
            return {"error": "Not a modification submission"}
        
        # Get ChangeSet
        changeset = session.query(ChangeSet).filter(
            ChangeSet.submission_id == submission_id
        ).first()
        
        if not changeset:
            return {"error": "ChangeSet not found for modification"}
        
        # Get impacted rules
        impacted_rule_ids = get_impacted_rules(changeset.id, db)
        
        # Filter rules to only impacted ones
        impacted_rules = [r for r in rules if r.rule_id in impacted_rule_ids]
        
        LOGGER.info(
            f"Targeted revalidation: {len(impacted_rules)}/{len(rules)} rules impacted "
            f"for submission {submission_id}"
        )
        
        # Get all documents for this submission
        from planproof.db import Document
        documents = session.query(Document).filter(
            Document.submission_id == submission_id
        ).all()
        
        if not documents:
            return {"error": "No documents found for submission"}
        
        # Run validation on impacted rules only
        all_findings = []
        validation_summary = {"pass": 0, "fail": 0, "needs_review": 0, "total": 0}
        
        for doc in documents:
            # Get extraction result for this document
            from planproof.pipeline.extract import get_extraction_result
            extraction = get_extraction_result(doc.id, db=db)
            
            if not extraction:
                continue
            
            # Run validation with only impacted rules
            validation = validate_extraction(
                extraction,
                impacted_rules,
                context={"document_id": doc.id, "submission_id": submission_id},
                db=db,
                write_to_tables=True
            )
            
            # Collect findings
            findings = validation.get("findings", [])
            for finding in findings:
                finding["document_id"] = doc.id
                finding["document_name"] = doc.filename
                finding["revalidated_due_to_change"] = True
            
            all_findings.extend(findings)
            
            # Update summary
            summary = validation.get("summary", {})
            validation_summary["pass"] += summary.get("pass", 0)
            validation_summary["fail"] += summary.get("fail", 0)
            validation_summary["needs_review"] += summary.get("needs_review", 0)
            validation_summary["total"] += summary.get("total", 0)
        
        LOGGER.info(
            f"Targeted revalidation complete: {len(impacted_rules)} rules, "
            f"{len(all_findings)} findings, {validation_summary['pass']} pass, "
            f"{validation_summary['fail']} fail, {validation_summary['needs_review']} needs_review"
        )
        
        return {
            "submission_id": submission_id,
            "changeset_id": changeset.id,
            "significance_score": changeset.significance_score,
            "total_rules": len(rules),
            "impacted_rules": len(impacted_rules),
            "impacted_rule_ids": impacted_rule_ids,
            "revalidation_needed": changeset.requires_validation,
            "findings": all_findings,
            "summary": validation_summary,
            "message": f"Targeted revalidation complete: {len(impacted_rules)} rules evaluated, {len(all_findings)} findings"
        }
    
    finally:
        session.close()


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

            # Dispatch by category for non-FIELD_REQUIRED rules
            # Only run category validators if we have proper context (submission_id and db)
            if rule.rule_category and rule.rule_category.upper() != "FIELD_REQUIRED":
                # Skip category validators if missing required context
                if not submission_id or not db:
                    continue  # Skip this rule - requires submission context
                
                category_context = {
                    "extraction": extraction,
                    "fields": fields,
                    "evidence_index": evidence_index,
                    "document_id": document_id,
                    "submission_id": submission_id,
                    "document_type": document_type,
                    "db": db
                }
                category_finding = _dispatch_by_category(rule, category_context)
                if category_finding:
                    findings.append(category_finding)
                    if category_finding.get("status") in ["fail", "needs_review"] and rule.severity == "error":
                        needs_llm = True
                    
                    # Write to database if enabled
                    if session and document_id:
                        check = ValidationCheck(
                            document_id=document_id,
                            submission_id=submission_id,
                            rule_id=rule.rule_id,
                            rule_category=rule.rule_category,
                            status=ValidationStatus(category_finding.get("status", "needs_review")),
                            severity=rule.severity,
                            message=category_finding.get("message", ""),
                            evidence_summary=category_finding.get("evidence", {})
                        )
                        session.add(check)
                continue  # Skip default field validation for category-specific rules

            # Default FIELD_REQUIRED validation logic
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

    if session:
        try:
            session.commit()
        finally:
            session.close()

    summary = {
        "rule_count": len(rules),
        "pass": sum(1 for f in findings if f["status"] == "pass"),
        "needs_review": sum(1 for f in findings if f["status"] == "needs_review"),
        "fail": sum(1 for f in findings if f["status"] == "fail"),
        "needs_llm": needs_llm,
    }

    return {"summary": summary, "findings": findings, "context": context}
