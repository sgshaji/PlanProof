"""
Export Service: Generate decision packages with validation summary, evidence, overrides, and delta.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import logging
from datetime import datetime
import json
from pathlib import Path

if TYPE_CHECKING:
    from planproof.db import Database

LOGGER = logging.getLogger(__name__)


def export_decision_package(
    submission_id: int,
    include_evidence: bool = True,
    include_documents: bool = False,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive decision export package.
    
    Includes:
    - Validation summary (pass/fail/needs-review counts per rule)
    - Per-rule evidence with page numbers and snippets
    - Officer overrides with audit trail
    - Delta summary for modifications (V1+)
    - Case metadata
    
    Args:
        submission_id: Submission ID
        include_evidence: Include evidence snippets
        include_documents: Include full documents (large)
        db: Optional Database instance
        
    Returns:
        Dictionary with complete decision package
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import (
        Submission, Case, ValidationCheck, OfficerOverride, 
        ChangeSet, ChangeItem, Document, Evidence, ValidationStatus
    )
    
    session = db.get_session()
    
    try:
        # Get submission and case
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {"error": "Submission not found"}
        
        case = session.query(Case).filter(Case.id == submission.case_id).first()
        
        # Build package
        package = {
            "export_metadata": {
                "generated_at": datetime.now().isoformat(),
                "submission_id": submission_id,
                "case_ref": case.case_ref if case else None,
                "submission_version": submission.submission_version,
                "status": submission.status
            },
            "case_info": {},
            "validation_summary": {},
            "rules": [],
            "overrides": [],
            "delta": None,
            "documents": []
        }
        
        # Case info
        if case:
            package["case_info"] = {
                "case_ref": case.case_ref,
                "site_address": case.site_address,
                "postcode": case.postcode,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None
            }
        
        # Validation checks
        checks = session.query(ValidationCheck).filter(
            ValidationCheck.submission_id == submission_id
        ).all()
        
        # Summary counts
        package["validation_summary"] = {
            "total_checks": len(checks),
            "pass": sum(1 for c in checks if c.status == ValidationStatus.PASS),
            "fail": sum(1 for c in checks if c.status == ValidationStatus.FAIL),
            "needs_review": sum(1 for c in checks if c.status == ValidationStatus.NEEDS_REVIEW),
            "pending": sum(1 for c in checks if c.status == ValidationStatus.PENDING)
        }
        
        # Per-rule details
        for check in checks:
            rule_detail = {
                "rule_id": check.rule_id_string,
                "rule_category": check.rule_category,
                "status": check.status.value if check.status else "unknown",
                "severity": check.severity,
                "message": check.explanation,
                "evidence": []
            }
            
            # Add evidence if requested
            if include_evidence and check.evidence_ids:
                evidences = session.query(Evidence).filter(
                    Evidence.id.in_(check.evidence_ids)
                ).all()
                
                for evidence in evidences:
                    rule_detail["evidence"].append({
                        "page": evidence.page_number,
                        "snippet": evidence.evidence_snippet[:200] if evidence.evidence_snippet else None,
                        "confidence": evidence.confidence_score,
                        "document_id": evidence.document_id
                    })
            
            package["rules"].append(rule_detail)
        
        # Officer overrides
        overrides = session.query(OfficerOverride).filter(
            OfficerOverride.submission_id == submission_id
        ).all()
        
        for override in overrides:
            package["overrides"].append({
                "rule_id": override.rule_id,
                "original_status": override.original_status,
                "override_status": override.override_status,
                "officer_name": override.officer_name,
                "notes": override.notes,
                "created_at": override.created_at.isoformat() if override.created_at else None
            })
        
        # Delta summary for modifications
        if submission.submission_version != "V0":
            changeset = session.query(ChangeSet).filter(
                ChangeSet.submission_id == submission_id
            ).first()
            
            if changeset:
                change_items = session.query(ChangeItem).filter(
                    ChangeItem.change_set_id == changeset.id
                ).all()
                
                package["delta"] = {
                    "changeset_id": changeset.id,
                    "parent_submission_id": submission.parent_submission_id,
                    "significance_score": changeset.significance_score,
                    "requires_validation": changeset.requires_validation,
                    "change_count": len(change_items),
                    "changes": []
                }
                
                for item in change_items:
                    package["delta"]["changes"].append({
                        "change_type": item.change_type,
                        "entity_type": item.entity_type,
                        "entity_id": item.entity_id,
                        "field_name": item.field_name,
                        "old_value": item.old_value,
                        "new_value": item.new_value,
                        "significance": item.significance_score
                    })
        
        # Document list
        documents = session.query(Document).filter(
            Document.submission_id == submission_id
        ).all()
        
        for doc in documents:
            doc_info = {
                "document_id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            
            if include_documents and doc.storage_path:
                # Include document path (actual file inclusion would be via zip)
                doc_info["storage_path"] = doc.storage_path
            
            package["documents"].append(doc_info)
        
        LOGGER.info(
            "decision_package_exported",
            extra={
                "submission_id": submission_id,
                "checks_count": len(checks),
                "overrides_count": len(overrides),
                "has_delta": package["delta"] is not None
            }
        )
        
        return package
    
    finally:
        session.close()


def export_as_json(package: Dict[str, Any], filepath: Optional[str] = None) -> str:
    """
    Export package as JSON.
    
    Args:
        package: Decision package dict
        filepath: Optional filepath to save
        
    Returns:
        JSON string
    """
    json_str = json.dumps(package, indent=2, ensure_ascii=False)
    
    if filepath:
        Path(filepath).write_text(json_str, encoding='utf-8')
        LOGGER.info(f"Decision package exported to {filepath}")
    
    return json_str


def export_as_html_report(package: Dict[str, Any], filepath: Optional[str] = None) -> str:
    """
    Export package as HTML report.
    
    Args:
        package: Decision package dict
        filepath: Optional filepath to save
        
    Returns:
        HTML string
    """
    meta = package.get("export_metadata", {})
    case_info = package.get("case_info", {})
    validation_summary = package.get("validation_summary", {})
    rules = package.get("rules", [])
    overrides = package.get("overrides", [])
    delta = package.get("delta")
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Decision Package - {meta.get('case_ref', 'N/A')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .needs-review {{ color: orange; }}
        .summary-box {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Planning Decision Package</h1>
    
    <div class="summary-box">
        <h2>Case Information</h2>
        <p><strong>Case Reference:</strong> {case_info.get('case_ref', 'N/A')}</p>
        <p><strong>Address:</strong> {case_info.get('site_address', 'N/A')}</p>
        <p><strong>Status:</strong> {case_info.get('status', 'N/A')}</p>
        <p><strong>Generated:</strong> {meta.get('generated_at', 'N/A')}</p>
    </div>
    
    <h2>Validation Summary</h2>
    <table>
        <tr>
            <th>Total Checks</th>
            <th>Pass</th>
            <th>Fail</th>
            <th>Needs Review</th>
        </tr>
        <tr>
            <td>{validation_summary.get('total_checks', 0)}</td>
            <td class="pass">{validation_summary.get('pass', 0)}</td>
            <td class="fail">{validation_summary.get('fail', 0)}</td>
            <td class="needs-review">{validation_summary.get('needs_review', 0)}</td>
        </tr>
    </table>
    
    <h2>Validation Rules</h2>
    <table>
        <tr>
            <th>Rule ID</th>
            <th>Status</th>
            <th>Severity</th>
            <th>Message</th>
        </tr>
"""
    
    for rule in rules:
        status_class = rule['status'].replace('_', '-')
        html += f"""
        <tr>
            <td>{rule['rule_id']}</td>
            <td class="{status_class}">{rule['status']}</td>
            <td>{rule['severity']}</td>
            <td>{rule['message']}</td>
        </tr>
"""
    
    html += """
    </table>
"""
    
    if overrides:
        html += """
    <h2>Officer Overrides</h2>
    <table>
        <tr>
            <th>Rule ID</th>
            <th>Original</th>
            <th>Override</th>
            <th>Officer</th>
            <th>Notes</th>
        </tr>
"""
        for override in overrides:
            html += f"""
        <tr>
            <td>{override['rule_id']}</td>
            <td>{override['original_status']}</td>
            <td>{override['override_status']}</td>
            <td>{override['officer_name']}</td>
            <td>{override['notes']}</td>
        </tr>
"""
        html += """
    </table>
"""
    
    if delta:
        html += f"""
    <h2>Modification Summary</h2>
    <div class="summary-box">
        <p><strong>Change Count:</strong> {delta['change_count']}</p>
        <p><strong>Significance Score:</strong> {delta['significance_score']}</p>
        <p><strong>Requires Revalidation:</strong> {delta['requires_validation']}</p>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    if filepath:
        Path(filepath).write_text(html, encoding='utf-8')
        LOGGER.info(f"HTML report exported to {filepath}")
    
    return html
