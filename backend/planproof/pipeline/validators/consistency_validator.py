"""
Consistency and modification validation module.

Handles cross-document consistency checks and modification/versioning validation.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    ValidationSeverity,
    SubmissionVersion,
)

if TYPE_CHECKING:
    from planproof.db import Database


def validate_consistency(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate CONSISTENCY rules.

    Checks if key fields match across multiple documents in the same submission.

    Args:
        rule: Consistency validation rule
        context: Context dictionary with submission_id, db, fields, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")

    if not submission_id or not db:
        return {
            "status": ValidationStatus.NEEDS_REVIEW.value,
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
                        # Get document info through evidence relationship
                        doc = None
                        doc_id = None
                        if ef.evidence_id and ef.evidence:
                            doc_id = ef.evidence.document_id
                            doc = ef.evidence.document

                        doc_name = doc.filename if doc else "unknown document"
                        doc_type = doc.document_type if doc else "unknown"

                        evidence_snippets.append({
                            "page": 1,  # Page info not available in ExtractedField
                            "snippet": f"{field_key}='{value}' in {doc_type} ({doc_name})",
                            "field_key": field_key,
                            "field_value": value,
                            "document_id": doc_id,
                            "document_type": doc_type
                        })

        if conflicts:
            return {
                "status": ValidationStatus.NEEDS_REVIEW.value,
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
                "status": ValidationStatus.PASS.value,
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


def validate_modification(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate MODIFICATION rules.

    Checks parent reference and delta completeness for modification submissions.

    Args:
        rule: Modification validation rule
        context: Context dictionary with submission_id, db, fields, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")

    if not submission_id or not db:
        return {
            "status": ValidationStatus.NEEDS_REVIEW.value,
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
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": "Submission not found",
                "missing_fields": [],
                "evidence": {}
            }

        # Check if this is a modification (V1+)
        is_modification = SubmissionVersion.is_modification(submission.submission_version)

        if not is_modification:
            # Not a modification, rule doesn't apply
            return {
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": f"Not a modification submission ({submission.submission_version})",
                "missing_fields": [],
                "evidence": {}
            }

        # For modifications, check parent reference
        if not submission.parent_submission_id:
            return {
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": f"Missing parent reference: modification submissions must reference parent {SubmissionVersion.V0.value}",
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
                "status": ValidationStatus.FAIL.value,
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
                "status": ValidationStatus.NEEDS_REVIEW.value,
                "severity": ValidationSeverity.WARNING.value,
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
            "status": ValidationStatus.PASS.value,
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
