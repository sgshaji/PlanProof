"""
Ownership validation module.

Handles ownership certificate validation and certificate-applicant matching.
"""

from typing import Dict, Any, Optional

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    FieldName,
    CertificateType,
)


def validate_ownership(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate OWNERSHIP_VALIDATION rules (OWN-01, OWN-02).

    Args:
        rule: Ownership validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})

    if rule.rule_id == "OWN-01":
        return _validate_certificate_type(rule, fields, rule_config)
    elif rule.rule_id == "OWN-02":
        return _validate_certificate_match(rule, fields, rule_config)

    return None


def _validate_certificate_type(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate ownership certificate type (OWN-01).

    Checks that exactly one valid certificate type (A, B, C, or D) is provided.

    Args:
        rule: Validation rule
        fields: Extracted fields dictionary
        rule_config: Rule configuration

    Returns:
        Validation finding dictionary
    """
    cert_type = fields.get(FieldName.CERTIFICATE_TYPE, "")
    valid_certs = rule_config.get("valid_certificates", CertificateType.valid_certificates())

    if not cert_type:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "No ownership certificate provided",
            "missing_fields": [FieldName.CERTIFICATE_TYPE],
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
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": f"Invalid certificate type: {cert_type}. Must be A, B, C, or D",
            "missing_fields": [],
            "evidence": {"certificate_type": cert_type}
        }

    return {
        "rule_id": rule.rule_id,
        "status": ValidationStatus.PASS.value,
        "severity": rule.severity,
        "message": f"Valid ownership certificate: Certificate {cert_letter}",
        "missing_fields": [],
        "evidence": {"certificate_type": cert_letter}
    }


def _validate_certificate_match(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate certificate name matches applicant (OWN-02).

    Performs fuzzy matching between certificate name and applicant name.

    Args:
        rule: Validation rule
        fields: Extracted fields dictionary
        rule_config: Rule configuration

    Returns:
        Validation finding dictionary
    """
    cert_name = fields.get(FieldName.CERTIFICATE_NAME, "")
    applicant_name = fields.get(FieldName.APPLICANT_NAME, "")

    if not cert_name or not applicant_name:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": "Cannot verify certificate match: missing certificate_name or applicant_name",
            "missing_fields": [
                f for f in [FieldName.CERTIFICATE_NAME, FieldName.APPLICANT_NAME]
                if not fields.get(f)
            ],
            "evidence": {
                "certificate_name": cert_name,
                "applicant_name": applicant_name
            }
        }

    # Simple fuzzy match (case-insensitive substring check)
    cert_lower = cert_name.lower()
    app_lower = applicant_name.lower()

    if cert_lower in app_lower or app_lower in cert_lower or cert_lower == app_lower:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"Certificate name matches applicant: {cert_name} ≈ {applicant_name}",
            "missing_fields": [],
            "evidence": {
                "certificate_name": cert_name,
                "applicant_name": applicant_name,
                "match": True
            }
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": f"Certificate name may not match applicant: '{cert_name}' vs '{applicant_name}'",
            "missing_fields": [],
            "evidence": {
                "certificate_name": cert_name,
                "applicant_name": applicant_name,
                "match": False
            }
        }
