"""
Base validator utilities and shared functions.

This module contains common utilities used across all validators, including
text extraction, field matching, and evidence location functions.
"""

from typing import Dict, Any, List, Optional, Tuple


def normalize_label(label: str) -> str:
    """
    Normalize a label for matching (lowercase, strip, replace separators).

    Args:
        label: Label to normalize

    Returns:
        Normalized label string
    """
    return " ".join(
        label.strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace(":", "")
        .split()
    )


def extract_all_text(extraction_result: Dict[str, Any]) -> str:
    """
    Extract all text content from extraction result.

    Args:
        extraction_result: Document extraction result dictionary

    Returns:
        All extracted text concatenated with newlines
    """
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


def build_text_index(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build an index of text content for efficient field extraction.

    Creates:
    - blocks: List of content blocks with lowercase variants
    - label_value_index: Map of normalized labels to their values
    - full_text: All text concatenated

    Args:
        extraction_result: Document extraction result dictionary

    Returns:
        Text index dictionary with blocks, label_value_index, and full_text
    """
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
                    label_value_index[normalize_label(label)] = value
                    continue

            if line.endswith(":") and idx + 1 < len(lines):
                label = line[:-1].strip()
                value = lines[idx + 1].strip()
                if label and value:
                    label_value_index[normalize_label(label)] = value

    return {
        "blocks": blocks,
        "label_value_index": label_value_index,
        "full_text": extract_all_text(extraction_result)
    }


def extract_field_value(
    field_name: str,
    text_index: Dict[str, Any],
    extraction_result: Dict[str, Any]
) -> Optional[str]:
    """
    Extract field value from document text using keyword-based extraction.

    This is a basic implementation. In production, you might use:
    - Named entity recognition (NER)
    - LLM-based extraction
    - Structured form extraction

    Args:
        field_name: Name of the field to extract
        text_index: Pre-built text index from build_text_index
        extraction_result: Original extraction result

    Returns:
        Extracted field value or None if not found
    """
    # Simple keyword matching (case-insensitive)
    keywords = [
        field_name.replace("_", " "),
        field_name.replace("_", "-"),
        field_name
    ]

    label_value_index = text_index.get("label_value_index", {})

    for keyword in keywords:
        normalized = normalize_label(keyword)
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


def find_evidence_location(
    field_name: str,
    field_value: Optional[str],
    extraction_result: Dict[str, Any]
) -> Tuple[Optional[int], Optional[str]]:
    """
    Find the page number and location where field evidence was found.

    Args:
        field_name: Name of the field
        field_value: Value of the field
        extraction_result: Document extraction result

    Returns:
        Tuple of (page_number, location_string) or (None, None) if not found
    """
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


def get_default_validation_rules() -> Dict[str, Dict[str, Any]]:
    """
    Get default validation rules.

    In production, these should be loaded from validation_requirements.md
    or a configuration file.

    Returns:
        Dictionary mapping field names to validation rule configurations
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


def validate_field(
    field_name: str,
    rule: Dict[str, Any],
    extraction_result: Dict[str, Any],
    text_index: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a single field against a rule.

    This is the legacy field validation function. For new code, use the
    rule-based validation system via validate_extraction.

    Args:
        field_name: Name of the field
        rule: Validation rule dictionary
        extraction_result: Document extraction result
        text_index: Pre-built text index

    Returns:
        Validation result dictionary with status, message, confidence, etc.
    """
    # Import here to avoid circular imports
    from planproof.db import ValidationStatus
    from planproof.pipeline.validators.constants import Config

    rule_type = rule.get("type", "presence")
    required = rule.get("required", False)
    pattern = rule.get("pattern")
    min_length = rule.get("min_length")
    max_length = rule.get("max_length")

    # Try to extract field value
    extracted_value = extract_field_value(
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
    evidence_page, evidence_location = find_evidence_location(
        field_name, extracted_value, extraction_result
    )

    return {
        "status": ValidationStatus.PASS,
        "extracted_value": extracted_value,
        "rule_name": rule.get("name", field_name),
        "confidence": Config.DEFAULT_CONFIDENCE,
        "evidence_page": evidence_page,
        "evidence_location": evidence_location
    }
