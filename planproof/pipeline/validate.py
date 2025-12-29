"""
Validate module: Apply deterministic validation rules to extracted fields.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from planproof.db import Database, Document, ValidationResult, ValidationStatus
from planproof.pipeline.extract import get_extraction_result


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
    extraction_result = get_extraction_result(document_id, db=db)
    if extraction_result is None:
        raise ValueError(f"No extraction result found for document {document_id}")

    # Use default rules if not provided
    if validation_rules is None:
        validation_rules = _get_default_validation_rules()

    # Extract text content for field matching
    all_text = _extract_all_text(extraction_result)

    # Apply validation rules
    validation_results = []
    session = db.get_session()

    try:
        for field_name, rule in validation_rules.items():
            result = _validate_field(
                field_name=field_name,
                rule=rule,
                extraction_result=extraction_result,
                all_text=all_text
            )

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
            validation_results.append(result)

        session.commit()

        # Refresh to get IDs
        for vr in validation_results:
            session.refresh(vr)

    finally:
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

