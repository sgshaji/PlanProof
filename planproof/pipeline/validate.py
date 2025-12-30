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


def _validate_fee(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate FEE_VALIDATION rules (FEE-01, FEE-02)."""
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})
    
    if rule.rule_id == "FEE-01":
        # Check payment status or receipt reference
        payment_status = fields.get("fee_payment_status", "").upper()
        receipt_ref = fields.get("receipt_reference", "")
        valid_statuses = rule_config.get("valid_statuses", ["PAID"])
        
        if payment_status in [s.upper() for s in valid_statuses] or receipt_ref:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"Fee payment verified: {payment_status or 'Receipt: ' + receipt_ref}",
                "missing_fields": [],
                "evidence": {"payment_status": payment_status, "receipt_reference": receipt_ref}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "Fee payment not verified: status is not PAID and no receipt reference",
                "missing_fields": ["fee_payment_status", "receipt_reference"],
                "evidence": {"payment_status": payment_status or "missing"}
            }
    
    elif rule.rule_id == "FEE-02":
        # Check fee amount plausibility
        fee_amount = fields.get("fee_amount")
        application_type = fields.get("application_type", "").lower()
        
        if fee_amount is None:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Fee amount not extracted",
                "missing_fields": ["fee_amount"],
                "evidence": {}
            }
        
        try:
            fee_value = float(fee_amount)
        except (ValueError, TypeError):
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": f"Invalid fee amount: {fee_amount}",
                "missing_fields": [],
                "evidence": {"fee_amount": fee_amount}
            }
        
        min_fee = rule_config.get("min_fee", 0)
        max_fee = rule_config.get("max_fee", 500000)
        
        # Check application-type-specific ranges
        if "householder" in application_type:
            min_fee, max_fee = rule_config.get("householder_range", [100, 500])
        elif "full" in application_type or "major" in application_type:
            min_fee, max_fee = rule_config.get("full_application_range", [200, 100000])
        
        if fee_value <= 0:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": f"Fee amount must be positive: £{fee_value}",
                "missing_fields": [],
                "evidence": {"fee_amount": fee_value}
            }
        
        if fee_value < min_fee or fee_value > max_fee:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": "warning",
                "message": f"Fee amount £{fee_value} outside expected range £{min_fee}-£{max_fee}",
                "missing_fields": [],
                "evidence": {"fee_amount": fee_value, "expected_range": [min_fee, max_fee]}
            }
        
        return {
            "rule_id": rule.rule_id,
            "status": "pass",
            "severity": rule.severity,
            "message": f"Fee amount acceptable: £{fee_value}",
            "missing_fields": [],
            "evidence": {"fee_amount": fee_value}
        }
    
    return None


def _validate_ownership(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate OWNERSHIP_VALIDATION rules (OWN-01, OWN-02)."""
    fields = context.get("fields", {})
    submission_id = context.get("submission_id")
    db = context.get("db")
    rule_config = rule.to_dict().get("config", {})
    
    if rule.rule_id == "OWN-01":
        # Check exactly one certificate type
        cert_type = fields.get("certificate_type", "")
        valid_certs = rule_config.get("valid_certificates", ["A", "B", "C", "D"])
        
        if not cert_type:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "No ownership certificate provided",
                "missing_fields": ["certificate_type"],
                "evidence": {}
            }
        
        # Normalize cert_type (might be "Certificate A" or just "A")
        cert_letter = None
        for c in valid_certs:
            if c in cert_type.upper():
                cert_letter = c
                break
        
        if not cert_letter:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": f"Invalid certificate type: {cert_type}. Must be A, B, C, or D",
                "missing_fields": [],
                "evidence": {"certificate_type": cert_type}
            }
        
        return {
            "rule_id": rule.rule_id,
            "status": "pass",
            "severity": rule.severity,
            "message": f"Valid ownership certificate: Certificate {cert_letter}",
            "missing_fields": [],
            "evidence": {"certificate_type": cert_letter}
        }
    
    elif rule.rule_id == "OWN-02":
        # Check certificate name/address matches applicant
        cert_name = fields.get("certificate_name", "")
        applicant_name = fields.get("applicant_name", "")
        
        if not cert_name or not applicant_name:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Cannot verify certificate match: missing certificate_name or applicant_name",
                "missing_fields": [f for f in ["certificate_name", "applicant_name"] if not fields.get(f)],
                "evidence": {"certificate_name": cert_name, "applicant_name": applicant_name}
            }
        
        # Simple fuzzy match (case-insensitive substring check)
        cert_lower = cert_name.lower()
        app_lower = applicant_name.lower()
        
        if cert_lower in app_lower or app_lower in cert_lower or cert_lower == app_lower:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"Certificate name matches applicant: {cert_name} ≈ {applicant_name}",
                "missing_fields": [],
                "evidence": {"certificate_name": cert_name, "applicant_name": applicant_name, "match": True}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": f"Certificate name may not match applicant: '{cert_name}' vs '{applicant_name}'",
                "missing_fields": [],
                "evidence": {"certificate_name": cert_name, "applicant_name": applicant_name, "match": False}
            }
    
    return None


def _validate_prior_approval(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate PRIOR_APPROVAL rules (PA-01, PA-02)."""
    fields = context.get("fields", {})
    submission_id = context.get("submission_id")
    db = context.get("db")
    
    # Check if this is a prior approval application
    application_type = fields.get("application_type", "").lower()
    is_prior_approval = "prior approval" in application_type or "prior_approval" in application_type
    
    if not is_prior_approval:
        # Rule doesn't apply
        return {
            "rule_id": rule.rule_id,
            "status": "pass",
            "severity": rule.severity,
            "message": "Not a Prior Approval application - rule does not apply",
            "missing_fields": [],
            "evidence": {"application_type": application_type}
        }
    
    if rule.rule_id == "PA-01":
        # Check manual registration flag
        registered_in_m3 = fields.get("registered_in_m3", False)
        submission_source = fields.get("submission_source", "")
        
        # Consider registered if either flag is set
        is_registered = registered_in_m3 or "manual" in submission_source.lower()
        
        if is_registered:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "Prior Approval manually registered",
                "missing_fields": [],
                "evidence": {"registered_in_m3": registered_in_m3, "submission_source": submission_source}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "Prior Approval requires manual registration flag",
                "missing_fields": ["registered_in_m3"],
                "evidence": {"registered_in_m3": False}
            }
    
    elif rule.rule_id == "PA-02":
        # Check required document set for Prior Approval
        if not submission_id or not db:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Cannot validate Prior Approval documents: missing submission context",
                "missing_fields": [],
                "evidence": {}
            }
        
        from planproof.db import Document
        session = db.get_session()
        try:
            documents = session.query(Document).filter(Document.submission_id == submission_id).all()
            present_doc_types = {doc.document_type for doc in documents if doc.document_type}
            
            required_docs = rule.required_fields  # ["application_form", "location_plan"]
            missing_docs = [doc for doc in required_docs if doc not in present_doc_types]
            
            if missing_docs:
                return {
                    "rule_id": rule.rule_id,
                    "status": "fail",
                    "severity": rule.severity,
                    "message": f"Prior Approval missing required documents: {', '.join(missing_docs)}",
                    "missing_fields": missing_docs,
                    "evidence": {"present_documents": list(present_doc_types), "missing_documents": missing_docs}
                }
            else:
                return {
                    "rule_id": rule.rule_id,
                    "status": "pass",
                    "severity": rule.severity,
                    "message": "Prior Approval has all required documents",
                    "missing_fields": [],
                    "evidence": {"present_documents": list(present_doc_types)}
                }
        finally:
            session.close()
    
    return None


def _validate_constraint(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate CONSTRAINT_VALIDATION rules (CON-01 through CON-04)."""
    fields = context.get("fields", {})
    submission_id = context.get("submission_id")
    db = context.get("db")
    rule_config = rule.to_dict().get("config", {})
    
    if rule.rule_id == "CON-01":
        # Check constraint declaration completeness
        constraint_flags = {
            "conservation_area": fields.get("conservation_area", False),
            "listed_building": fields.get("listed_building", False),
            "tpo": fields.get("tpo", False),
            "flood_zone": fields.get("flood_zone"),
        }
        
        # Check if any constraint is declared
        active_constraints = [k for k, v in constraint_flags.items() if v]
        
        if not active_constraints:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "No constraints declared",
                "missing_fields": [],
                "evidence": {"constraints": constraint_flags}
            }
        
        # Check if constraint evidence/basis is present
        constraint_evidence = fields.get("constraint_evidence", "")
        constraint_basis = fields.get("constraint_basis", "")
        
        if constraint_evidence or constraint_basis:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"Constraints declared with evidence: {', '.join(active_constraints)}",
                "missing_fields": [],
                "evidence": {"active_constraints": active_constraints, "has_evidence": True}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": f"Constraints declared but no supporting evidence: {', '.join(active_constraints)}",
                "missing_fields": ["constraint_evidence"],
                "evidence": {"active_constraints": active_constraints, "has_evidence": False}
            }
    
    elif rule.rule_id == "CON-02":
        # Listed building → Heritage Statement required
        triggers = rule_config.get("triggers", ["listed_building", "within_conservation_area"])
        is_triggered = any(fields.get(t, False) for t in triggers)
        
        if not is_triggered:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "Heritage Statement not required (no listed building or conservation area)",
                "missing_fields": [],
                "evidence": {}
            }
        
        # Check if Heritage Statement document exists
        if not submission_id or not db:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Cannot verify Heritage Statement: missing submission context",
                "missing_fields": [],
                "evidence": {}
            }
        
        from planproof.db import Document
        session = db.get_session()
        try:
            heritage_doc = session.query(Document).filter(
                Document.submission_id == submission_id,
                Document.document_type.in_(["heritage_statement", "heritage"])
            ).first()
            
            if heritage_doc:
                return {
                    "rule_id": rule.rule_id,
                    "status": "pass",
                    "severity": rule.severity,
                    "message": "Heritage Statement present",
                    "missing_fields": [],
                    "evidence": {"document": heritage_doc.filename}
                }
            else:
                return {
                    "rule_id": rule.rule_id,
                    "status": "fail",
                    "severity": rule.severity,
                    "message": "Heritage Statement required but not found (listed building or conservation area)",
                    "missing_fields": ["heritage_statement"],
                    "evidence": {"triggers": [t for t in triggers if fields.get(t)]}
                }
        finally:
            session.close()
    
    elif rule.rule_id == "CON-03":
        # TPO → Tree Survey required
        triggers = rule_config.get("triggers", ["tpo", "trees_affected"])
        is_triggered = any(fields.get(t, False) for t in triggers)
        
        if not is_triggered:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "Tree Survey not required (no TPO or trees affected)",
                "missing_fields": [],
                "evidence": {}
            }
        
        if not submission_id or not db:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Cannot verify Tree Survey: missing submission context",
                "missing_fields": [],
                "evidence": {}
            }
        
        from planproof.db import Document
        session = db.get_session()
        try:
            tree_doc = session.query(Document).filter(
                Document.submission_id == submission_id,
                Document.document_type == "tree_survey"
            ).first()
            
            if tree_doc:
                return {
                    "rule_id": rule.rule_id,
                    "status": "pass",
                    "severity": rule.severity,
                    "message": "Tree Survey present",
                    "missing_fields": [],
                    "evidence": {"document": tree_doc.filename}
                }
            else:
                return {
                    "rule_id": rule.rule_id,
                    "status": "fail",
                    "severity": rule.severity,
                    "message": "Tree Survey required but not found (TPO or trees affected)",
                    "missing_fields": ["tree_survey"],
                    "evidence": {"triggers": [t for t in triggers if fields.get(t)]}
                }
        finally:
            session.close()
    
    elif rule.rule_id == "CON-04":
        # Flood zone → FRA required
        triggers = rule_config.get("triggers", ["flood_zone_2", "flood_zone_3"])
        flood_zone = str(fields.get("flood_zone", "")).lower()
        is_triggered = any(t.replace("flood_zone_", "") in flood_zone for t in triggers)
        
        if not is_triggered:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "Flood Risk Assessment not required (not in flood zone 2 or 3)",
                "missing_fields": [],
                "evidence": {"flood_zone": flood_zone}
            }
        
        if not submission_id or not db:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Cannot verify Flood Risk Assessment: missing submission context",
                "missing_fields": [],
                "evidence": {}
            }
        
        from planproof.db import Document
        session = db.get_session()
        try:
            fra_doc = session.query(Document).filter(
                Document.submission_id == submission_id,
                Document.document_type == "flood_risk_assessment"
            ).first()
            
            if fra_doc:
                return {
                    "rule_id": rule.rule_id,
                    "status": "pass",
                    "severity": rule.severity,
                    "message": "Flood Risk Assessment present",
                    "missing_fields": [],
                    "evidence": {"document": fra_doc.filename, "flood_zone": flood_zone}
                }
            else:
                return {
                    "rule_id": rule.rule_id,
                    "status": "fail",
                    "severity": rule.severity,
                    "message": f"Flood Risk Assessment required but not found (flood zone {flood_zone})",
                    "missing_fields": ["flood_risk_assessment"],
                    "evidence": {"flood_zone": flood_zone}
                }
        finally:
            session.close()
    
    return None


def _validate_bng(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate BNG_VALIDATION rules (BNG-01 through BNG-03)."""
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})
    
    application_type = fields.get("application_type", "").lower()
    is_householder = "householder" in application_type
    
    if rule.rule_id == "BNG-01":
        # BNG applicability decision must be present for non-householder
        if is_householder:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "BNG not applicable to householder applications",
                "missing_fields": [],
                "evidence": {"application_type": application_type}
            }
        
        bng_applicable = fields.get("bng_applicable")
        
        if bng_applicable is None or bng_applicable == "":
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "BNG applicability decision missing for non-householder application",
                "missing_fields": ["bng_applicable"],
                "evidence": {"application_type": application_type}
            }
        
        return {
            "rule_id": rule.rule_id,
            "status": "pass",
            "severity": rule.severity,
            "message": f"BNG applicability recorded: {bng_applicable}",
            "missing_fields": [],
            "evidence": {"bng_applicable": bng_applicable}
        }
    
    elif rule.rule_id == "BNG-02":
        # If BNG applicable → 10% claim or metric evidence
        bng_applicable = fields.get("bng_applicable")
        
        if not bng_applicable or str(bng_applicable).lower() in ["false", "no", "0"]:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "BNG not applicable - no 10% requirement",
                "missing_fields": [],
                "evidence": {"bng_applicable": bng_applicable}
            }
        
        bng_percentage = fields.get("bng_percentage")
        bng_metric_doc = fields.get("bng_metric_doc")
        min_percentage = rule_config.get("min_percentage", 10)
        
        # Check if 10% claim or metric document present
        has_claim = False
        if bng_percentage:
            try:
                pct = float(bng_percentage)
                has_claim = pct >= min_percentage
            except (ValueError, TypeError):
                pass
        
        if has_claim or bng_metric_doc:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"BNG 10% requirement met: {bng_percentage}%" if has_claim else "BNG metric document present",
                "missing_fields": [],
                "evidence": {"bng_percentage": bng_percentage, "bng_metric_doc": bool(bng_metric_doc)}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "BNG applicable but no 10% claim or metric evidence found",
                "missing_fields": ["bng_percentage", "bng_metric_doc"],
                "evidence": {"bng_applicable": True}
            }
    
    elif rule.rule_id == "BNG-03":
        # If BNG NOT applicable → exemption reason
        bng_applicable = fields.get("bng_applicable")
        
        if bng_applicable and str(bng_applicable).lower() not in ["false", "no", "0"]:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "BNG applicable - exemption not claimed",
                "missing_fields": [],
                "evidence": {"bng_applicable": bng_applicable}
            }
        
        exemption_reason = fields.get("bng_exemption_reason", "")
        
        if exemption_reason:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"BNG exemption reason provided: {exemption_reason}",
                "missing_fields": [],
                "evidence": {"exemption_reason": exemption_reason}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": "BNG exemption claimed but no reason provided",
                "missing_fields": ["bng_exemption_reason"],
                "evidence": {"bng_applicable": False}
            }
    
    return None


def _validate_plan_quality(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate PLAN_QUALITY rules (PLAN-01, PLAN-02)."""
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})
    
    if rule.rule_id == "PLAN-01":
        # Location plan scale check
        location_plan_scale = fields.get("location_plan_scale", "")
        acceptable_scales = rule_config.get("acceptable_scales", ["1:1250", "1:2500"])
        
        if not location_plan_scale:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": "Location plan scale not extracted",
                "missing_fields": ["location_plan_scale"],
                "evidence": {}
            }
        
        # Normalize scale format
        scale_normalized = location_plan_scale.replace(" ", "").replace("@", "")
        
        if any(scale in scale_normalized for scale in acceptable_scales):
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"Location plan scale acceptable: {location_plan_scale}",
                "missing_fields": [],
                "evidence": {"scale": location_plan_scale}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": f"Location plan scale may not be acceptable: {location_plan_scale} (expected: {', '.join(acceptable_scales)})",
                "missing_fields": [],
                "evidence": {"scale": location_plan_scale, "acceptable_scales": acceptable_scales}
            }
    
    elif rule.rule_id == "PLAN-02":
        # Site plan north arrow and scale bar check
        north_arrow = fields.get("site_plan_north_arrow", False)
        scale_bar = fields.get("site_plan_scale_bar", False)
        
        missing = []
        if not north_arrow:
            missing.append("north arrow")
        if not scale_bar:
            missing.append("scale bar")
        
        if missing:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": rule.severity,
                "message": f"Site plan missing: {', '.join(missing)}",
                "missing_fields": ["site_plan_north_arrow"] if not north_arrow else [] + ["site_plan_scale_bar"] if not scale_bar else [],
                "evidence": {"north_arrow": north_arrow, "scale_bar": scale_bar}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": "Site plan has north arrow and scale bar",
                "missing_fields": [],
                "evidence": {"north_arrow": True, "scale_bar": True}
            }
    
    return None


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
    elif category == "FEE_VALIDATION":
        return _validate_fee(rule, context)
    elif category == "OWNERSHIP_VALIDATION":
        return _validate_ownership(rule, context)
    elif category == "PRIOR_APPROVAL":
        return _validate_prior_approval(rule, context)
    elif category == "CONSTRAINT_VALIDATION":
        return _validate_constraint(rule, context)
    elif category == "BNG_VALIDATION":
        return _validate_bng(rule, context)
    elif category == "PLAN_QUALITY":
        return _validate_plan_quality(rule, context)
    elif category == "FIELD_REQUIRED":
        # Default field validation (existing logic)
        return None  # Will be handled by existing logic
    else:
        LOGGER.warning(f"Unknown rule category: {category} for rule {rule.rule_id}")
        return None
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
    Check spatial metrics (setback distances, heights, areas) against policy thresholds.
    """
    submission_id = context.get("submission_id")
    db = context.get("db")
    rule_config = rule.to_dict().get("config", {})
    
    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": "needs_review",
            "severity": rule.severity,
            "message": "Cannot validate spatial rules: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }
    
    from planproof.db import GeometryFeature, SpatialMetric
    session = db.get_session()
    
    try:
        # Get geometry features for this submission
        features = session.query(GeometryFeature).filter(
            GeometryFeature.submission_id == submission_id
        ).all()
        
        if not features:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": "warning",
                "message": "No geometry features available for spatial validation",
                "missing_fields": ["geometry_features"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": "Spatial validation requires geometry features to be defined"
                    }]
                }
            }
        
        # Get spatial metrics
        all_metrics = []
        metrics_by_name = {}
        for feature in features:
            metrics = session.query(SpatialMetric).filter(
                SpatialMetric.geometry_feature_id == feature.id
            ).all()
            all_metrics.extend(metrics)
            for metric in metrics:
                metrics_by_name[metric.metric_name.lower()] = metric
        
        if not all_metrics:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": "warning",
                "message": "No spatial metrics computed for validation",
                "missing_fields": ["spatial_metrics"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"Found {len(features)} geometry features but no computed metrics"
                    }]
                }
            }
        
        # Check spatial constraints from rule config
        violations = []
        evidence_snippets = []
        passed_checks = []
        
        # Get thresholds from config
        thresholds = rule_config.get("thresholds", {})
        
        # Check setback distances
        if "min_setback" in thresholds:
            min_setback = thresholds["min_setback"]
            setback_metrics = [m for m in all_metrics if "setback" in m.metric_name.lower() or "distance_to_boundary" in m.metric_name.lower()]
            
            for metric in setback_metrics:
                try:
                    value = float(metric.metric_value)
                    if value < min_setback:
                        violations.append(f"{metric.metric_name}: {value}{metric.metric_unit} < {min_setback}{metric.metric_unit} (minimum)")
                        evidence_snippets.append({
                            "page": 1,
                            "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} < {min_setback}{metric.metric_unit}",
                            "metric_name": metric.metric_name,
                            "metric_value": value,
                            "metric_unit": metric.metric_unit,
                            "threshold": min_setback
                        })
                    else:
                        passed_checks.append(f"{metric.metric_name}: {value}{metric.metric_unit} >= {min_setback}{metric.metric_unit}")
                        evidence_snippets.append({
                            "page": 1,
                            "snippet": f"OK: {metric.metric_name}: {value}{metric.metric_unit}",
                            "metric_name": metric.metric_name,
                            "metric_value": value,
                            "metric_unit": metric.metric_unit
                        })
                except (ValueError, TypeError):
                    pass
        
        # Check height limits
        if "max_height" in thresholds:
            max_height = thresholds["max_height"]
            height_metrics = [m for m in all_metrics if "height" in m.metric_name.lower()]
            
            for metric in height_metrics:
                try:
                    value = float(metric.metric_value)
                    if value > max_height:
                        violations.append(f"{metric.metric_name}: {value}{metric.metric_unit} > {max_height}{metric.metric_unit} (maximum)")
                        evidence_snippets.append({
                            "page": 1,
                            "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} > {max_height}{metric.metric_unit}",
                            "metric_name": metric.metric_name,
                            "metric_value": value,
                            "metric_unit": metric.metric_unit,
                            "threshold": max_height
                        })
                    else:
                        passed_checks.append(f"{metric.metric_name}: {value}{metric.metric_unit} <= {max_height}{metric.metric_unit}")
                        evidence_snippets.append({
                            "page": 1,
                            "snippet": f"OK: {metric.metric_name}: {value}{metric.metric_unit}",
                            "metric_name": metric.metric_name,
                            "metric_value": value,
                            "metric_unit": metric.metric_unit
                        })
                except (ValueError, TypeError):
                    pass
        
        # Check area limits
        if "max_area" in thresholds or "min_area" in thresholds:
            area_metrics = [m for m in all_metrics if "area" in m.metric_name.lower() or "footprint" in m.metric_name.lower()]
            
            for metric in area_metrics:
                try:
                    value = float(metric.metric_value)
                    
                    if "max_area" in thresholds:
                        max_area = thresholds["max_area"]
                        if value > max_area:
                            violations.append(f"{metric.metric_name}: {value}{metric.metric_unit} > {max_area}{metric.metric_unit} (maximum)")
                            evidence_snippets.append({
                                "page": 1,
                                "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} > {max_area}{metric.metric_unit}",
                                "metric_name": metric.metric_name,
                                "metric_value": value,
                                "metric_unit": metric.metric_unit,
                                "threshold": max_area
                            })
                        else:
                            passed_checks.append(f"{metric.metric_name}: {value}{metric.metric_unit} <= {max_area}{metric.metric_unit}")
                    
                    if "min_area" in thresholds:
                        min_area = thresholds["min_area"]
                        if value < min_area:
                            violations.append(f"{metric.metric_name}: {value}{metric.metric_unit} < {min_area}{metric.metric_unit} (minimum)")
                            evidence_snippets.append({
                                "page": 1,
                                "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} < {min_area}{metric.metric_unit}",
                                "metric_name": metric.metric_name,
                                "metric_value": value,
                                "metric_unit": metric.metric_unit,
                                "threshold": min_area
                            })
                        else:
                            passed_checks.append(f"{metric.metric_name}: {value}{metric.metric_unit} >= {min_area}{metric.metric_unit}")
                except (ValueError, TypeError):
                    pass
        
        # If no thresholds configured, mark as needs_review
        if not thresholds:
            return {
                "rule_id": rule.rule_id,
                "status": "needs_review",
                "severity": "warning",
                "message": f"Spatial metrics present ({len(all_metrics)} metrics) but no policy thresholds configured",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"{m.metric_name}: {m.metric_value} {m.metric_unit}"
                    } for m in all_metrics[:5]],
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }
        
        # Determine status based on violations
        if violations:
            return {
                "rule_id": rule.rule_id,
                "status": "fail",
                "severity": rule.severity,
                "message": f"Spatial violations found: {', '.join(violations[:3])}",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets,
                    "violations": violations,
                    "passed_checks": passed_checks,
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": "pass",
                "severity": rule.severity,
                "message": f"All spatial checks passed ({len(passed_checks)} checks)",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets[:10],
                    "passed_checks": passed_checks,
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }
        
    finally:
        session.close()


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
