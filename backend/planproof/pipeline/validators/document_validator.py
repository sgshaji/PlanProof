"""
Document validation module.

Handles document presence and completeness checks.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    FieldName,
)

if TYPE_CHECKING:
    from planproof.db import Database


def validate_document_required(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate DOCUMENT_REQUIRED rules.

    Checks if required documents are present for the submission.

    Args:
        rule: Document validation rule
        context: Context dictionary with submission_id, db, fields, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")
    fields = context.get("fields", {})
    rule_config = rule.to_dict().get("config", {})

    if not submission_id or not db:
        return {
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": "Cannot validate document requirements: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }

    # Get required documents from rule
    required_docs = rule.required_fields if rule.required_fields else []
    application_type = str(fields.get(FieldName.APPLICATION_TYPE, "")).lower().strip()
    application_type_requirements = rule_config.get("application_type_required_fields", {})

    if application_type_requirements:
        if application_type in application_type_requirements:
            required_docs = application_type_requirements.get(application_type, [])
        elif "default" in application_type_requirements:
            required_docs = application_type_requirements.get("default", [])
        else:
            return {
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": "Document requirement does not apply for this application type",
                "missing_fields": [],
                "evidence": {"application_type": application_type}
            }

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
                "status": ValidationStatus.FAIL.value,
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
                "status": ValidationStatus.PASS.value,
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
