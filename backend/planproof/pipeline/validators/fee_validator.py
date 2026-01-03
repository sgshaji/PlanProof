"""
Fee validation module.

Handles fee payment verification and fee amount plausibility checks.
"""

from typing import Dict, Any, Optional

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    ValidationSeverity,
    FieldName,
    ApplicationType,
)


def validate_fee(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate FEE_VALIDATION rules (FEE-01, FEE-02).

    Args:
        rule: Fee validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})

    if rule.rule_id == "FEE-01":
        return _validate_fee_payment(rule, fields, rule_config)
    elif rule.rule_id == "FEE-02":
        return _validate_fee_amount(rule, fields, rule_config)

    return None


def _validate_fee_payment(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate fee payment status (FEE-01).

    Checks if payment status is "PAID" or if a receipt reference is present.

    Args:
        rule: Validation rule
        fields: Extracted fields dictionary
        rule_config: Rule configuration

    Returns:
        Validation finding dictionary
    """
    payment_status = fields.get(FieldName.FEE_PAYMENT_STATUS, "").upper()
    receipt_ref = fields.get(FieldName.RECEIPT_REFERENCE, "")
    valid_statuses = rule_config.get("valid_statuses", ["PAID"])

    if payment_status in [s.upper() for s in valid_statuses] or receipt_ref:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"Fee payment verified: {payment_status or 'Receipt: ' + receipt_ref}",
            "missing_fields": [],
            "evidence": {
                "payment_status": payment_status,
                "receipt_reference": receipt_ref
            }
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "Fee payment not verified: status is not PAID and no receipt reference",
            "missing_fields": [FieldName.FEE_PAYMENT_STATUS, FieldName.RECEIPT_REFERENCE],
            "evidence": {"payment_status": payment_status or "missing"}
        }


def _validate_fee_amount(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate fee amount plausibility (FEE-02).

    Checks if fee amount is valid and within expected ranges based on application type.

    Args:
        rule: Validation rule
        fields: Extracted fields dictionary
        rule_config: Rule configuration

    Returns:
        Validation finding dictionary
    """
    fee_amount = fields.get(FieldName.FEE_AMOUNT)
    application_type = fields.get(FieldName.APPLICATION_TYPE, "").lower()

    if fee_amount is None:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": "Fee amount not extracted",
            "missing_fields": [FieldName.FEE_AMOUNT],
            "evidence": {}
        }

    try:
        fee_value = float(fee_amount)
    except (ValueError, TypeError):
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": f"Invalid fee amount: {fee_amount}",
            "missing_fields": [],
            "evidence": {"fee_amount": fee_amount}
        }

    min_fee = rule_config.get("min_fee", 0)
    max_fee = rule_config.get("max_fee", 500000)

    # Check application-type-specific ranges
    if ApplicationType.HOUSEHOLDER.value in application_type:
        min_fee, max_fee = rule_config.get("householder_range", [100, 500])
    elif ApplicationType.FULL.value in application_type or ApplicationType.MAJOR.value in application_type:
        min_fee, max_fee = rule_config.get("full_application_range", [200, 100000])

    if fee_value <= 0:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": f"Fee amount must be positive: £{fee_value}",
            "missing_fields": [],
            "evidence": {"fee_amount": fee_value}
        }

    if fee_value < min_fee or fee_value > max_fee:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": ValidationSeverity.WARNING.value,
            "message": f"Fee amount £{fee_value} outside expected range £{min_fee}-£{max_fee}",
            "missing_fields": [],
            "evidence": {
                "fee_amount": fee_value,
                "expected_range": [min_fee, max_fee]
            }
        }

    return {
        "rule_id": rule.rule_id,
        "status": ValidationStatus.PASS.value,
        "severity": rule.severity,
        "message": f"Fee amount acceptable: £{fee_value}",
        "missing_fields": [],
        "evidence": {"fee_amount": fee_value}
    }
