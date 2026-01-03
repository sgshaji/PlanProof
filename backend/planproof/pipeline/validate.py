"""
Validate module: Apply deterministic validation rules to extracted fields.

This module has been refactored to use smaller, focused validator modules.
See planproof/pipeline/validators/ for specific validation logic.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
import logging
from pathlib import Path

# Import validators
from planproof.pipeline.validators import (
    validate_fee,
    validate_ownership,
    validate_document_required,
    validate_prior_approval,
    validate_constraint,
    validate_bng,
    validate_plan_quality,
    validate_consistency,
    validate_modification as validate_modification_rule,
    validate_spatial,
)
from planproof.pipeline.validators.base_validator import (
    normalize_label,
    build_text_index,
    extract_field_value,
    find_evidence_location,
    get_default_validation_rules,
    validate_field as _validate_field,
)
from planproof.pipeline.validators.constants import RuleCategory

if TYPE_CHECKING:
    from planproof.db import Database, ValidationCheck, ValidationStatus

LOGGER = logging.getLogger(__name__)

# Re-export for backwards compatibility
_normalize_label = normalize_label
_build_text_index = build_text_index
_extract_field_value = extract_field_value
_find_evidence_location = find_evidence_location
_get_default_validation_rules = get_default_validation_rules


def validate_document(
    document_id: int,
    validation_rules: Optional[Dict[str, Any]] = None,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Apply deterministic validation rules to extracted document fields.

    This is a legacy function maintained for backwards compatibility.
    New code should use validate_extraction() with the rule catalog.

    Args:
        document_id: Document ID
        validation_rules: Optional dictionary of validation rules.
                         If not provided, uses default rules.
        db: Optional Database instance

    Returns:
        List of validation result dictionaries
    """
    if db is None:
        from planproof.db import Database
        db = Database()

    # Get extraction result
    from planproof.pipeline.extract import get_extraction_result
    from planproof.db import ValidationResult

    extraction_result = get_extraction_result(document_id, db=db)
    if extraction_result is None:
        raise ValueError(f"No extraction result found for document {document_id}")

    # Use default rules if not provided
    if validation_rules is None:
        validation_rules = get_default_validation_rules()

    # Extract text content for field matching
    text_index = build_text_index(extraction_result)

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


# New rule catalog-based validation functions
from planproof.rules.catalog import Rule


def load_rule_catalog(path: str | Path = "artefacts/rule_catalog.json") -> List[Rule]:
    """
    Load rule catalog from JSON file.

    Args:
        path: Path to rule catalog JSON file

    Returns:
        List of Rule objects

    Raises:
        FileNotFoundError: If catalog file doesn't exist
    """
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
                required_fields_any=r.get("required_fields_any", False),
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

    if category == RuleCategory.DOCUMENT_REQUIRED.value:
        return validate_document_required(rule, context)
    elif category == RuleCategory.CONSISTENCY.value:
        return validate_consistency(rule, context)
    elif category == RuleCategory.MODIFICATION.value:
        return validate_modification_rule(rule, context)
    elif category == RuleCategory.SPATIAL.value:
        return validate_spatial(rule, context)
    elif category == RuleCategory.FEE_VALIDATION.value:
        return validate_fee(rule, context)
    elif category == RuleCategory.OWNERSHIP_VALIDATION.value:
        return validate_ownership(rule, context)
    elif category == RuleCategory.PRIOR_APPROVAL.value:
        return validate_prior_approval(rule, context)
    elif category == RuleCategory.CONSTRAINT_VALIDATION.value:
        return validate_constraint(rule, context)
    elif category == RuleCategory.BNG_VALIDATION.value:
        return validate_bng(rule, context)
    elif category == RuleCategory.PLAN_QUALITY.value:
        return validate_plan_quality(rule, context)
    elif category == RuleCategory.FIELD_REQUIRED.value:
        # Default field validation (handled by main validation logic)
        return None
    else:
        LOGGER.warning(f"Unknown rule category: {category} for rule {rule.rule_id}")
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
        from planproof.db import Database
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

    if not fields.get("application_type") and submission_id and db:
        from planproof.db import Submission
        app_type_session = session or db.get_session()
        try:
            submission = app_type_session.query(Submission).filter(Submission.id == submission_id).first()
            if submission and submission.application_type:
                fields["application_type"] = submission.application_type
        finally:
            if app_type_session is not session:
                app_type_session.close()

    try:
        for rule in rules:
            # Skip rule if it doesn't apply to this document type
            if rule.applies_to and len(rule.applies_to) > 0:
                if document_type not in rule.applies_to:
                    # Rule doesn't apply to this document type - skip it
                    continue

            # Dispatch by category for non-FIELD_REQUIRED rules
            # Only run category validators if we have proper context (submission_id and db)
            if rule.rule_category and rule.rule_category.upper() != RuleCategory.FIELD_REQUIRED.value:
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
                        from planproof.db import ValidationStatus
                        check = ValidationCheck(
                            document_id=document_id,
                            submission_id=submission_id,
                            rule_id_string=rule.rule_id,
                            status=ValidationStatus(category_finding.get("status", "needs_review")),
                            explanation=category_finding.get("message", "")
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
                        from planproof.db import Evidence, ValidationStatus
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

                        # Prepare detailed evidence with page/line/bbox info
                        evidence_details = []
                        for snippet in evidence_snippets[:10]:  # Top 10 evidence snippets
                            evidence_details.append({
                                "page": snippet.get("page"),
                                "snippet": snippet.get("snippet"),
                                "evidence_key": snippet.get("evidence_key")
                            })

                        # Prepare candidate documents list (documents that were scanned)
                        candidate_documents = []
                        if document_id:
                            # Add the current document being validated
                            from planproof.db import Document
                            doc = session.query(Document).filter(Document.id == document_id).first()
                            if doc:
                                candidate_documents.append({
                                    "document_id": doc.id,
                                    "document_name": doc.filename,
                                    "confidence": 1.0,
                                    "reason": "Primary document being validated",
                                    "scanned": True
                                })

                        validation_check = ValidationCheck(
                            submission_id=submission_id,
                            document_id=document_id,
                            rule_id_string=rule.rule_id,
                            status=check_status,
                            explanation=finding["message"],
                            evidence_ids=evidence_ids if evidence_ids else None,
                            evidence_details=evidence_details if evidence_details else None,
                            candidate_documents=candidate_documents if candidate_documents else None
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
                        from planproof.db import ValidationStatus, Document
                        # Prepare candidate documents list (documents that were scanned)
                        candidate_documents = []
                        if document_id:
                            doc = session.query(Document).filter(Document.id == document_id).first()
                            if doc:
                                candidate_documents.append({
                                    "document_id": doc.id,
                                    "document_name": doc.filename,
                                    "confidence": 1.0,
                                    "reason": "Primary document being validated",
                                    "scanned": True
                                })

                        validation_check = ValidationCheck(
                            submission_id=submission_id,
                            document_id=document_id,
                            rule_id_string=rule.rule_id,
                            status=ValidationStatus.PASS,
                            explanation="All required fields present.",
                            candidate_documents=candidate_documents if candidate_documents else None
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
