"""
UX Formatting Service

Provides utilities to transform technical data into human-readable,
user-friendly formats for consistent UX across the application.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union


class FieldFormatter:
    """Formats field names and values for human-readable display."""

    FIELD_LABELS = {
        # Application fields
        "site_address": "Site Address",
        "postcode": "Postcode",
        "application_ref": "Application Reference",
        "applicant_name": "Applicant Name",
        "agent_name": "Agent Name",
        "agent_company": "Agent Company",
        "proposed_use": "Proposed Use",
        "development_description": "Development Description",

        # Certificate fields
        "certificate_type": "Ownership Certificate",
        "certificate_date": "Certificate Date",

        # Fee fields
        "fee_amount": "Application Fee",
        "fee_paid": "Fee Payment Status",
        "fee_exemption": "Fee Exemption",

        # Property details
        "property_type": "Property Type",
        "existing_use": "Existing Use",
        "floor_area": "Floor Area",
        "site_area": "Site Area",

        # Measurements
        "measurements": "Measurements",
        "height": "Height",
        "width": "Width",
        "depth": "Depth",
        "distance_from_boundary": "Distance from Boundary",
        "distance_from_watercourse": "Distance from Watercourse",

        # Heritage/Constraints
        "heritage_asset": "Heritage Asset",
        "conservation_area": "Conservation Area",
        "listed_building": "Listed Building",
        "tree_preservation_order": "Tree Preservation Order",
        "flood_zone": "Flood Zone",

        # Parking
        "parking_spaces": "Parking Spaces",
        "parking_existing": "Existing Parking",
        "parking_proposed": "Proposed Parking",

        # Design
        "materials": "Materials",
        "design_style": "Design Style",
        "scale_ratio": "Scale Ratio",

        # Dates
        "proposal_date": "Proposal Date",
        "submission_date": "Submission Date",
    }

    UNIT_LABELS = {
        "m": "metres",
        "sqm": "square metres",
        "cm": "centimetres",
        "mm": "millimetres",
        "ha": "hectares",
        "ft": "feet",
        "stories": "storeys",
    }

    @classmethod
    def get_field_label(cls, field_name: str) -> str:
        """Convert technical field name to human-readable label."""
        if field_name in cls.FIELD_LABELS:
            return cls.FIELD_LABELS[field_name]

        return field_name.replace("_", " ").title()

    @classmethod
    def format_field_value(cls, field_name: str, value: Any, unit: Optional[str] = None) -> str:
        """
        Format field value for display.
        Handles complex JSON structures, measurements, booleans, etc.
        """
        if value is None:
            return "Not provided"

        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, (int, float)) and unit:
            unit_label = cls.UNIT_LABELS.get(unit, unit)
            return f"{value} {unit_label}"

        if isinstance(value, str):
            if cls._is_json_string(value):
                return cls._format_json_value(value)
            return value

        if isinstance(value, (list, dict)):
            return cls._format_complex_value(value)

        return str(value)

    @classmethod
    def _is_json_string(cls, value: str) -> bool:
        """Check if string is JSON-like."""
        value = value.strip()
        return (value.startswith("{") and value.endswith("}")) or \
               (value.startswith("[") and value.endswith("]"))

    @classmethod
    def _format_json_value(cls, json_str: str) -> str:
        """Parse and format JSON string into readable text."""
        try:
            data = json.loads(json_str.replace("'", '"'))
            return cls._format_complex_value(data)
        except (json.JSONDecodeError, AttributeError):
            return json_str

    @classmethod
    def _format_complex_value(cls, value: Union[dict, list]) -> str:
        """Format complex nested structures."""
        if isinstance(value, dict):
            return cls._format_measurement_dict(value)

        if isinstance(value, list):
            if len(value) == 0:
                return "None"

            if all(isinstance(item, dict) for item in value):
                return cls._format_measurement_list(value)

            return ", ".join(str(item) for item in value)

        return str(value)

    @classmethod
    def _format_measurement_dict(cls, data: dict) -> str:
        """Format measurement dictionary into readable text."""
        if "value" in data and "unit" in data:
            value = data["value"]
            unit = data["unit"]
            unit_label = cls.UNIT_LABELS.get(unit, unit)

            context = data.get("context", "")
            raw_text = data.get("raw_text", "")

            result = f"{value} {unit_label}"
            if context and context != "unknown":
                result += f" ({context})"
            elif raw_text:
                result += f" (from: {raw_text})"

            return result

        parts = []
        for key, val in data.items():
            if key in ["confidence", "bbox", "page", "block_id", "existing_or_proposed"]:
                continue

            label = cls.get_field_label(key)
            formatted_val = cls.format_field_value(key, val)
            parts.append(f"{label}: {formatted_val}")

        return " | ".join(parts) if parts else str(data)

    @classmethod
    def _format_measurement_list(cls, measurements: List[dict]) -> str:
        """Format list of measurements."""
        formatted = []
        for m in measurements:
            formatted.append(cls._format_measurement_dict(m))
        return "\n".join(f"• {item}" for item in formatted)


class FindingFormatter:
    """Formats validation findings for clear user communication."""

    ACTION_GUIDANCE = {
        "missing_field": "Please ensure this information is included in your application documents.",
        "missing_document": "Please upload the required document to proceed.",
        "inconsistency": "Please verify and correct the inconsistent information.",
        "constraint_detected": "This may require additional assessment. Please review the details.",
        "measurement_required": "Please provide accurate measurements with units.",
        "fee_required": "Please confirm the application fee amount.",
        "certificate_required": "Please complete the ownership certificate section.",
    }

    SEVERITY_LABELS = {
        "critical": "Critical Issue",
        "blocker": "Blocking Issue",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
    }

    STATUS_LABELS = {
        "pass": "Passed",
        "fail": "Failed",
        "needs_review": "Needs Review",
    }

    @classmethod
    def get_action_guidance(cls, finding: dict) -> str:
        """Get actionable guidance based on finding type."""
        message = finding.get("message", "").lower()

        if "missing required field" in message:
            return cls.ACTION_GUIDANCE["missing_field"]

        if "missing document" in message or "document required" in message:
            return cls.ACTION_GUIDANCE["missing_document"]

        if "inconsistent" in message or "mismatch" in message:
            return cls.ACTION_GUIDANCE["inconsistency"]

        if any(word in message for word in ["heritage", "conservation", "tpo", "flood"]):
            return cls.ACTION_GUIDANCE["constraint_detected"]

        if "measurement" in message:
            return cls.ACTION_GUIDANCE["measurement_required"]

        if "fee" in message:
            return cls.ACTION_GUIDANCE["fee_required"]

        if "certificate" in message:
            return cls.ACTION_GUIDANCE["certificate_required"]

        return "Please review this item and take appropriate action."

    @classmethod
    def format_finding_message(cls, finding: dict) -> str:
        """Format finding message for clarity."""
        message = finding.get("message", "")

        missing_fields_match = re.search(r"Missing required fields?: (.+)", message)
        if missing_fields_match:
            fields_str = missing_fields_match.group(1)
            fields = [f.strip() for f in fields_str.split(",")]
            formatted_fields = [FieldFormatter.get_field_label(f) for f in fields]

            if len(formatted_fields) == 1:
                return f"Missing required information: {formatted_fields[0]}"
            else:
                return f"Missing required information: {', '.join(formatted_fields)}"

        return message

    @classmethod
    def deduplicate_findings(cls, findings: List[dict]) -> List[dict]:
        """
        Remove duplicate findings based on rule_id, message, and document.
        Keep the first occurrence with the most complete information.
        """
        seen = set()
        deduplicated = []

        for finding in findings:
            key = (
                finding.get("rule_id"),
                finding.get("message"),
                finding.get("document_name", "")
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return deduplicated

    @classmethod
    def group_findings_by_document(cls, findings: List[dict]) -> Dict[str, List[dict]]:
        """Group findings by document for better organization."""
        grouped = {}

        for finding in findings:
            doc_name = finding.get("document_name", "General")
            if doc_name not in grouped:
                grouped[doc_name] = []
            grouped[doc_name].append(finding)

        return grouped


class ExtractedFieldsFormatter:
    """Formats extracted fields data for clean display."""

    @classmethod
    def format_extracted_fields(cls, extracted_fields: dict) -> List[dict]:
        """
        Transform raw extracted_fields dictionary into a list of formatted field objects.

        Args:
            extracted_fields: Dict mapping field_name to field data

        Returns:
            List of formatted field objects with label, value, confidence, etc.
        """
        formatted = []

        for field_name, field_data in extracted_fields.items():
            if field_data is None:
                continue

            value = field_data.get("value")
            confidence = field_data.get("confidence")  # Allow None
            unit = field_data.get("unit")
            extractor = field_data.get("extractor", "unknown")

            formatted_value = FieldFormatter.format_field_value(field_name, value, unit)

            formatted.append({
                "field_name": field_name,
                "label": FieldFormatter.get_field_label(field_name),
                "value": value,
                "formatted_value": formatted_value,
                "confidence": confidence,
                "confidence_label": cls._get_confidence_label(confidence),
                "extractor": extractor,
                "unit": unit,
            })

        formatted.sort(key=lambda x: x["label"])
        return formatted

    @classmethod
    def _get_confidence_label(cls, confidence: float) -> str:
        """Get human-readable confidence label."""
        if confidence is None:
            return "Unknown"
        if confidence >= 0.9:
            return "High"
        elif confidence >= 0.7:
            return "Medium"
        elif confidence >= 0.5:
            return "Low"
        else:
            return "Very Low"


def format_api_response(
    findings: List[dict],
    extracted_fields: dict
) -> tuple[List[dict], List[dict]]:
    """
    Main entry point: Format complete API response for optimal UX.

    Args:
        findings: List of raw validation findings
        extracted_fields: Dict of raw extracted field data

    Returns:
        Tuple of (formatted_findings, formatted_extracted_fields)
    """
    formatted_findings = []
    for finding in findings:
        formatted_finding = finding.copy()
        formatted_finding["formatted_message"] = FindingFormatter.format_finding_message(finding)
        formatted_finding["action_guidance"] = FindingFormatter.get_action_guidance(finding)
        formatted_findings.append(formatted_finding)

    deduplicated_findings = FindingFormatter.deduplicate_findings(formatted_findings)

    formatted_extracted = ExtractedFieldsFormatter.format_extracted_fields(extracted_fields)

    return deduplicated_findings, formatted_extracted
