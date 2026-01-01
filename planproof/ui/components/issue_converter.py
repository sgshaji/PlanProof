"""
Converter to transform legacy validation findings into EnhancedIssue objects.

This module bridges the gap between the existing validation system and the new
enhanced issue model, allowing gradual migration while maintaining backward compatibility.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from enhanced_issues import (
    EnhancedIssue,
    UserMessage,
    WhatWeChecked,
    Actions,
    Action,
    Resolution,
    IssueMetadata,
    IssueSeverity,
    IssueCategory,
    ResolutionStatus,
    ActionType
)
from issue_factory import (
    create_missing_document_issue,
    create_data_conflict_issue,
    create_bng_applicability_issue,
    create_bng_exemption_reason_issue,
    create_m3_registration_issue,
    create_pa_required_docs_issue
)


def convert_validation_finding_to_enhanced_issue(
    finding: Dict[str, Any],
    run_id: int
) -> EnhancedIssue:
    """
    Convert a legacy validation finding dictionary into an EnhancedIssue object.
    
    Args:
        finding: Dictionary containing validation finding data
        run_id: Run ID for tracking
        
    Returns:
        EnhancedIssue object with appropriate factory-generated content
    """
    rule_id = finding.get("rule_id", "unknown")
    status = finding.get("status", "fail")
    message = finding.get("message", "")
    document_name = finding.get("document_name", "unknown")
    
    # Try to map to enhanced issue using factories
    enhanced_issue = _map_rule_to_factory(rule_id, finding, run_id)
    
    if enhanced_issue:
        return enhanced_issue
    
    # Fallback: Create generic enhanced issue
    return _create_generic_enhanced_issue(finding, run_id)


def _map_rule_to_factory(
    rule_id: str,
    finding: Dict[str, Any],
    run_id: int
) -> Optional[EnhancedIssue]:
    """
    Map rule_id to appropriate factory function.
    
    Returns:
        EnhancedIssue if a factory exists, None otherwise
    """
    # Extract key information
    document_name = finding.get("document_name", "unknown")
    missing_fields = finding.get("missing_fields", [])
    
    # Missing document rules
    if "missing" in rule_id.lower() or "required" in rule_id.lower():
        # Try to identify document type from rule_id or message
        doc_type = _identify_document_type(rule_id, finding.get("message", ""))
        if doc_type:
            return create_missing_document_issue(
                document_type=doc_type,
                rule_id=rule_id,
                run_id=run_id
            )
    
    # BNG applicability
    if "bng" in rule_id.lower() and "applicability" in rule_id.lower():
        return create_bng_applicability_issue(
            rule_id=rule_id,
            run_id=run_id
        )
    
    # BNG exemption reason
    if "bng" in rule_id.lower() and "exemption" in rule_id.lower():
        return create_bng_exemption_reason_issue(
            rule_id=rule_id,
            run_id=run_id
        )
    
    # M3 registration
    if "m3" in rule_id.lower() and "registration" in rule_id.lower():
        return create_m3_registration_issue(
            rule_id=rule_id,
            run_id=run_id
        )
    
    # PA required documents
    if "pa" in rule_id.lower() and ("required" in rule_id.lower() or "document" in rule_id.lower()):
        return create_pa_required_docs_issue(
            rule_id=rule_id,
            run_id=run_id
        )
    
    # Data conflicts
    if "conflict" in rule_id.lower() or "mismatch" in rule_id.lower():
        # Extract conflict details from finding
        conflicts = _extract_conflict_data(finding)
        if conflicts:
            return create_data_conflict_issue(
                conflicts=conflicts,
                rule_id=rule_id,
                run_id=run_id
            )
    
    return None


def _identify_document_type(rule_id: str, message: str) -> Optional[str]:
    """Identify document type from rule_id or message."""
    text = f"{rule_id} {message}".lower()
    
    doc_type_keywords = {
        "ownership_certificate": ["ownership", "certificate"],
        "location_plan": ["location", "plan", "site plan"],
        "site_plan": ["site plan", "block plan"],
        "proposed_elevations": ["elevation", "proposed"],
        "existing_elevations": ["elevation", "existing"],
        "proposed_floor_plans": ["floor plan", "proposed"],
        "existing_floor_plans": ["floor plan", "existing"],
        "design_access_statement": ["design", "access", "statement"],
        "planning_statement": ["planning statement"],
        "heritage_statement": ["heritage", "statement"],
        "flood_risk_assessment": ["flood", "risk"],
        "ecological_assessment": ["ecological", "ecology", "biodiversity"],
        "tree_survey": ["tree", "survey", "arboricultural"],
        "transport_statement": ["transport", "traffic"],
        "noise_assessment": ["noise", "acoustic"],
        "air_quality_assessment": ["air quality"],
        "contaminated_land_assessment": ["contaminated", "land", "phase"]
    }
    
    for doc_type, keywords in doc_type_keywords.items():
        if all(kw in text for kw in keywords):
            return doc_type
    
    return None


def _extract_conflict_data(finding: Dict[str, Any]) -> list:
    """Extract conflict data from finding dictionary."""
    # This would need to parse the finding message/evidence
    # For now, return basic structure
    message = finding.get("message", "")
    
    # Simple extraction - in production, would parse evidence
    if "conflict" in message.lower():
        return [{
            "field_name": "unknown",
            "document_a": {"name": "Document 1", "value": "Value A"},
            "document_b": {"name": "Document 2", "value": "Value B"}
        }]
    
    return []


def _create_generic_enhanced_issue(
    finding: Dict[str, Any],
    run_id: int
) -> EnhancedIssue:
    """
    Create a generic enhanced issue as fallback.
    
    This preserves the existing validation finding data while providing
    a minimal enhanced structure.
    """
    rule_id = finding.get("rule_id", "unknown")
    status = finding.get("status", "fail")
    message = finding.get("message", "Validation check failed")
    document_name = finding.get("document_name", "unknown")
    missing_fields = finding.get("missing_fields", [])
    
    # Determine severity from status
    severity = IssueSeverity.WARNING
    if status == "fail":
        severity = IssueSeverity.CRITICAL
    elif status == "needs_review":
        severity = IssueSeverity.WARNING
    
    # Determine category from rule_id
    category = IssueCategory.OTHER
    if "document" in rule_id.lower() or "missing" in rule_id.lower():
        category = IssueCategory.MISSING_DOCUMENT
    elif "data" in rule_id.lower() or "field" in rule_id.lower():
        category = IssueCategory.DATA_QUALITY
    
    # Create basic user message
    user_message = UserMessage(
        title=f"Validation Issue: {rule_id}",
        description=message,
        why_it_matters="This validation check did not pass.",
        impact="The application may not meet planning requirements.",
        what_we_checked=WhatWeChecked(
            search_description=f"Validated {document_name}",
            method_description="Automated validation rules",
            documents_searched=[document_name] if document_name != "unknown" else []
        )
    )
    
    # Create basic actions
    actions_list = []
    
    if missing_fields:
        actions_list.append(Action(
            action_type=ActionType.PROVIDE_EXPLANATION,
            label="Provide Missing Information",
            description=f"Please provide: {', '.join(missing_fields)}",
            parameters={
                "placeholder": f"Enter information for: {', '.join(missing_fields)}",
                "min_length": 10
            }
        ))
    else:
        actions_list.append(Action(
            action_type=ActionType.REVIEW_EVIDENCE,
            label="Review Evidence",
            description="Review the evidence and determine if this is correct.",
            parameters={}
        ))
    
    # Create resolution
    resolution = Resolution(
        status=ResolutionStatus.OPEN,
        auto_recheck_rules=[rule_id]
    )
    
    # Create issue
    issue = EnhancedIssue(
        issue_id=f"{run_id}_{rule_id}_{document_name}",
        run_id=run_id,
        rule_id=rule_id,
        status=status,
        severity=severity,
        category=category,
        who_can_fix="Applicant or Agent",
        user_message=user_message,
        actions=Actions(items=actions_list) if actions_list else None,
        resolution=resolution,
        metadata=IssueMetadata(
            original_finding=finding
        )
    )
    
    return issue


def convert_all_findings(
    findings: list[Dict[str, Any]],
    run_id: int
) -> list[EnhancedIssue]:
    """
    Convert all validation findings to enhanced issues.
    
    Args:
        findings: List of validation finding dictionaries
        run_id: Run ID for tracking
        
    Returns:
        List of EnhancedIssue objects
    """
    enhanced_issues = []
    
    for finding in findings:
        try:
            enhanced_issue = convert_validation_finding_to_enhanced_issue(finding, run_id)
            enhanced_issues.append(enhanced_issue)
        except Exception as e:
            # Log error but continue processing
            print(f"Warning: Failed to convert finding {finding.get('rule_id')}: {e}")
            # Still create a basic issue
            try:
                enhanced_issue = _create_generic_enhanced_issue(finding, run_id)
                enhanced_issues.append(enhanced_issue)
            except Exception as e2:
                print(f"Error: Could not create even basic issue: {e2}")
    
    return enhanced_issues
