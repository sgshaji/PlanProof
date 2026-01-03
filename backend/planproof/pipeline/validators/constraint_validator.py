"""
Constraint validation module.

Handles prior approval, planning constraints, BNG (Biodiversity Net Gain),
and plan quality validation.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    ValidationSeverity,
    FieldName,
    DocumentType,
    ApplicationType,
    Config,
)

if TYPE_CHECKING:
    from planproof.db import Database


def validate_prior_approval(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate PRIOR_APPROVAL rules (PA-01, PA-02).

    Args:
        rule: Prior approval validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")

    # Check if this is a prior approval application
    application_type = fields.get(FieldName.APPLICATION_TYPE, "").lower()
    is_prior_approval = (
        ApplicationType.PRIOR_APPROVAL.value in application_type
        or "prior approval" in application_type
    )

    if not is_prior_approval:
        # Rule doesn't apply
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Not a Prior Approval application - rule does not apply",
            "missing_fields": [],
            "evidence": {"application_type": application_type}
        }

    if rule.rule_id == "PA-01":
        return _validate_pa_manual_registration(rule, fields)
    elif rule.rule_id == "PA-02":
        return _validate_pa_documents(rule, submission_id, db)

    return None


def _validate_pa_manual_registration(
    rule: Rule,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate manual registration flag for prior approval (PA-01)."""
    registered_in_m3 = fields.get("registered_in_m3", False)
    submission_source = fields.get("submission_source", "")

    # Consider registered if either flag is set
    is_registered = registered_in_m3 or "manual" in submission_source.lower()

    if is_registered:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Prior Approval manually registered",
            "missing_fields": [],
            "evidence": {
                "registered_in_m3": registered_in_m3,
                "submission_source": submission_source
            }
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "Prior Approval requires manual registration flag",
            "missing_fields": ["registered_in_m3"],
            "evidence": {"registered_in_m3": False}
        }


def _validate_pa_documents(
    rule: Rule,
    submission_id: Optional[int],
    db: Optional["Database"]
) -> Dict[str, Any]:
    """Validate required document set for prior approval (PA-02)."""
    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
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

        required_docs = rule.required_fields
        missing_docs = [doc for doc in required_docs if doc not in present_doc_types]

        if missing_docs:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": f"Prior Approval missing required documents: {', '.join(missing_docs)}",
                "missing_fields": missing_docs,
                "evidence": {
                    "present_documents": list(present_doc_types),
                    "missing_documents": missing_docs
                }
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": "Prior Approval has all required documents",
                "missing_fields": [],
                "evidence": {"present_documents": list(present_doc_types)}
            }
    finally:
        session.close()


def validate_constraint(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate CONSTRAINT_VALIDATION rules (CON-01 through CON-04).

    Args:
        rule: Constraint validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")
    rule_config = rule.to_dict().get("config", {})

    if rule.rule_id == "CON-01":
        return _validate_constraint_declaration(rule, fields)
    elif rule.rule_id == "CON-02":
        return _validate_heritage_statement(rule, fields, submission_id, db, rule_config)
    elif rule.rule_id == "CON-03":
        return _validate_tree_survey(rule, fields, submission_id, db, rule_config)
    elif rule.rule_id == "CON-04":
        return _validate_flood_risk_assessment(rule, fields, submission_id, db, rule_config)

    return None


def _validate_constraint_declaration(
    rule: Rule,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate constraint declaration completeness (CON-01)."""
    constraint_flags = {
        FieldName.CONSERVATION_AREA: fields.get(FieldName.CONSERVATION_AREA, False),
        FieldName.LISTED_BUILDING: fields.get(FieldName.LISTED_BUILDING, False),
        FieldName.TPO: fields.get(FieldName.TPO, False),
        FieldName.FLOOD_ZONE: fields.get(FieldName.FLOOD_ZONE),
    }

    # Check if any constraint is declared
    active_constraints = [k for k, v in constraint_flags.items() if v]

    if not active_constraints:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
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
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"Constraints declared with evidence: {', '.join(active_constraints)}",
            "missing_fields": [],
            "evidence": {"active_constraints": active_constraints, "has_evidence": True}
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": f"Constraints declared but no supporting evidence: {', '.join(active_constraints)}",
            "missing_fields": ["constraint_evidence"],
            "evidence": {"active_constraints": active_constraints, "has_evidence": False}
        }


def _validate_heritage_statement(
    rule: Rule,
    fields: Dict[str, Any],
    submission_id: Optional[int],
    db: Optional["Database"],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate heritage statement requirement (CON-02)."""
    triggers = rule_config.get("triggers", [FieldName.LISTED_BUILDING, "within_conservation_area"])
    is_triggered = any(fields.get(t, False) for t in triggers)

    if not is_triggered:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Heritage Statement not required (no listed building or conservation area)",
            "missing_fields": [],
            "evidence": {}
        }

    # Check if Heritage Statement document exists
    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
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
            Document.document_type.in_([
                DocumentType.HERITAGE_STATEMENT.value,
                DocumentType.HERITAGE.value
            ])
        ).first()

        if heritage_doc:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": "Heritage Statement present",
                "missing_fields": [],
                "evidence": {"document": heritage_doc.filename}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": "Heritage Statement required but not found (listed building or conservation area)",
                "missing_fields": [DocumentType.HERITAGE_STATEMENT.value],
                "evidence": {"triggers": [t for t in triggers if fields.get(t)]}
            }
    finally:
        session.close()


def _validate_tree_survey(
    rule: Rule,
    fields: Dict[str, Any],
    submission_id: Optional[int],
    db: Optional["Database"],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate tree survey requirement (CON-03)."""
    triggers = rule_config.get("triggers", [FieldName.TPO, "trees_affected"])
    is_triggered = any(fields.get(t, False) for t in triggers)

    if not is_triggered:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Tree Survey not required (no TPO or trees affected)",
            "missing_fields": [],
            "evidence": {}
        }

    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
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
            Document.document_type == DocumentType.TREE_SURVEY.value
        ).first()

        if tree_doc:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": "Tree Survey present",
                "missing_fields": [],
                "evidence": {"document": tree_doc.filename}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": "Tree Survey required but not found (TPO or trees affected)",
                "missing_fields": [DocumentType.TREE_SURVEY.value],
                "evidence": {"triggers": [t for t in triggers if fields.get(t)]}
            }
    finally:
        session.close()


def _validate_flood_risk_assessment(
    rule: Rule,
    fields: Dict[str, Any],
    submission_id: Optional[int],
    db: Optional["Database"],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate flood risk assessment requirement (CON-04)."""
    triggers = rule_config.get("triggers", ["flood_zone_2", "flood_zone_3"])
    flood_zone = str(fields.get(FieldName.FLOOD_ZONE, "")).lower()
    is_triggered = any(t.replace("flood_zone_", "") in flood_zone for t in triggers)

    if not is_triggered:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Flood Risk Assessment not required (not in flood zone 2 or 3)",
            "missing_fields": [],
            "evidence": {"flood_zone": flood_zone}
        }

    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
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
            Document.document_type == DocumentType.FLOOD_RISK_ASSESSMENT.value
        ).first()

        if fra_doc:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": "Flood Risk Assessment present",
                "missing_fields": [],
                "evidence": {"document": fra_doc.filename, "flood_zone": flood_zone}
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": f"Flood Risk Assessment required but not found (flood zone {flood_zone})",
                "missing_fields": [DocumentType.FLOOD_RISK_ASSESSMENT.value],
                "evidence": {"flood_zone": flood_zone}
            }
    finally:
        session.close()


def validate_bng(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate BNG_VALIDATION rules (BNG-01 through BNG-03).

    BNG = Biodiversity Net Gain

    Args:
        rule: BNG validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})

    application_type = fields.get(FieldName.APPLICATION_TYPE, "").lower()
    is_householder = ApplicationType.HOUSEHOLDER.value in application_type

    if rule.rule_id == "BNG-01":
        return _validate_bng_applicability(rule, fields, is_householder, application_type)
    elif rule.rule_id == "BNG-02":
        return _validate_bng_percentage(rule, fields, rule_config)
    elif rule.rule_id == "BNG-03":
        return _validate_bng_exemption(rule, fields)

    return None


def _validate_bng_applicability(
    rule: Rule,
    fields: Dict[str, Any],
    is_householder: bool,
    application_type: str
) -> Dict[str, Any]:
    """Validate BNG applicability decision (BNG-01)."""
    if is_householder:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "BNG not applicable to householder applications",
            "missing_fields": [],
            "evidence": {"application_type": application_type}
        }

    bng_applicable = fields.get(FieldName.BNG_APPLICABLE)

    if bng_applicable is None or bng_applicable == "":
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "BNG applicability decision missing for non-householder application",
            "missing_fields": [FieldName.BNG_APPLICABLE],
            "evidence": {"application_type": application_type}
        }

    return {
        "rule_id": rule.rule_id,
        "status": ValidationStatus.PASS.value,
        "severity": rule.severity,
        "message": f"BNG applicability recorded: {bng_applicable}",
        "missing_fields": [],
        "evidence": {"bng_applicable": bng_applicable}
    }


def _validate_bng_percentage(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate BNG 10% requirement (BNG-02)."""
    bng_applicable = fields.get(FieldName.BNG_APPLICABLE)

    if not bng_applicable or str(bng_applicable).lower() in ["false", "no", "0"]:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "BNG not applicable - no 10% requirement",
            "missing_fields": [],
            "evidence": {"bng_applicable": bng_applicable}
        }

    bng_percentage = fields.get(FieldName.BNG_PERCENTAGE)
    bng_metric_doc = fields.get("bng_metric_doc")
    min_percentage = rule_config.get("min_percentage", Config.BNG_MIN_PERCENTAGE)

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
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"BNG 10% requirement met: {bng_percentage}%" if has_claim else "BNG metric document present",
            "missing_fields": [],
            "evidence": {"bng_percentage": bng_percentage, "bng_metric_doc": bool(bng_metric_doc)}
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "BNG applicable but no 10% claim or metric evidence found",
            "missing_fields": [FieldName.BNG_PERCENTAGE, "bng_metric_doc"],
            "evidence": {"bng_applicable": True}
        }


def _validate_bng_exemption(
    rule: Rule,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate BNG exemption reason (BNG-03)."""
    bng_applicable = fields.get(FieldName.BNG_APPLICABLE)

    if bng_applicable and str(bng_applicable).lower() not in ["false", "no", "0"]:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "BNG applicable - exemption not claimed",
            "missing_fields": [],
            "evidence": {"bng_applicable": bng_applicable}
        }

    exemption_reason = fields.get(FieldName.BNG_EXEMPTION_REASON, "")

    if exemption_reason:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"BNG exemption reason provided: {exemption_reason}",
            "missing_fields": [],
            "evidence": {"exemption_reason": exemption_reason}
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.FAIL.value,
            "severity": rule.severity,
            "message": "BNG exemption claimed but no reason provided",
            "missing_fields": [FieldName.BNG_EXEMPTION_REASON],
            "evidence": {"bng_applicable": False}
        }


def validate_plan_quality(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate PLAN_QUALITY rules (PLAN-01, PLAN-02).

    Args:
        rule: Plan quality validation rule
        context: Context dictionary with fields, submission_id, db, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})

    if rule.rule_id == "PLAN-01":
        return _validate_location_plan_scale(rule, fields, rule_config)
    elif rule.rule_id == "PLAN-02":
        return _validate_site_plan_features(rule, fields)

    return None


def _validate_location_plan_scale(
    rule: Rule,
    fields: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate location plan scale (PLAN-01)."""
    location_plan_scale = fields.get(FieldName.LOCATION_PLAN_SCALE, "")
    acceptable_scales = rule_config.get("acceptable_scales", ["1:1250", "1:2500"])

    if not location_plan_scale:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": "Location plan scale not extracted",
            "missing_fields": [FieldName.LOCATION_PLAN_SCALE],
            "evidence": {}
        }

    # Normalize scale format
    scale_normalized = location_plan_scale.replace(" ", "").replace("@", "")

    if any(scale in scale_normalized for scale in acceptable_scales):
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": f"Location plan scale acceptable: {location_plan_scale}",
            "missing_fields": [],
            "evidence": {"scale": location_plan_scale}
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": f"Location plan scale may not be acceptable: {location_plan_scale} (expected: {', '.join(acceptable_scales)})",
            "missing_fields": [],
            "evidence": {"scale": location_plan_scale, "acceptable_scales": acceptable_scales}
        }


def _validate_site_plan_features(
    rule: Rule,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate site plan north arrow and scale bar (PLAN-02)."""
    north_arrow = fields.get("site_plan_north_arrow", False)
    scale_bar = fields.get("site_plan_scale_bar", False)

    missing = []
    if not north_arrow:
        missing.append("north arrow")
    if not scale_bar:
        missing.append("scale bar")

    if missing:
        missing_fields = []
        if not north_arrow:
            missing_fields.append("site_plan_north_arrow")
        if not scale_bar:
            missing_fields.append("site_plan_scale_bar")

        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": f"Site plan missing: {', '.join(missing)}",
            "missing_fields": missing_fields,
            "evidence": {"north_arrow": north_arrow, "scale_bar": scale_bar}
        }
    else:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.PASS.value,
            "severity": rule.severity,
            "message": "Site plan has north arrow and scale bar",
            "missing_fields": [],
            "evidence": {"north_arrow": True, "scale_bar": True}
        }
