"""
Issue factory functions for all validation issue types.
"""

from typing import List, Dict, Any, Optional
from planproof.enhanced_issues import (
    EnhancedIssue, IssueSeverity, IssueCategory, ActionType,
    UserMessage, WhatWeChecked, EvidenceData, Actions, Action,
    Resolution, ResolutionStatus, IssueMetadata, MissingItem,
    DocumentCandidate
)


def create_data_conflict_issue(
    field_name: str,
    conflicting_values: List[Dict[str, Any]],
    rule_id: str
) -> EnhancedIssue:
    """Create issue for conflicting data across documents."""
    
    issue_id = f"CONFLICT-{hash(field_name) % 1000:03d}-{field_name.upper().replace('_', '-')}"
    
    field_label = field_name.replace('_', ' ').title()
    
    # Build conflict summary
    unique_values = set(v['field_value'] for v in conflicting_values)
    conflict_summary = ", ".join([f"'{v}'" for v in list(unique_values)[:3]])
    
    user_message = UserMessage(
        title=f"Conflicting values found for {field_label}",
        subtitle="Clarification needed",
        description=f"We found {len(unique_values)} different values for {field_label} across your documents: {conflict_summary}.",
        impact="Conflicts must be resolved to ensure data accuracy.",
        context="This usually happens when documents contain slightly different information. Please select the correct value or provide clarification."
    )
    
    what_we_checked = WhatWeChecked(
        summary=f"We extracted {field_label} from all documents and found {len(conflicting_values)} instances with {len(unique_values)} different values",
        methods=["field_extraction", "cross_document_comparison"],
        documents_scanned=len(set(v.get('document_id') for v in conflicting_values))
    )
    
    evidence = EvidenceData(
        what_we_found={
            "field_name": field_name,
            "total_instances": len(conflicting_values),
            "unique_values": len(unique_values),
            "conflicts": conflicting_values[:10]  # Limit to 10
        }
    )
    
    # Create options for selection
    options = []
    for value in unique_values:
        sources = [v for v in conflicting_values if v['field_value'] == value]
        source_docs = ", ".join(set(s.get('snippet', 'Unknown')[:50] for s in sources[:2]))
        options.append({
            "value": value,
            "label": f"{value} (found in {len(sources)} location(s))",
            "sources": source_docs
        })
    
    primary_action = Action(
        type=ActionType.SELECT_OPTION,
        label=f"Select Correct {field_label}",
        options=options
    )
    
    secondary_actions = [
        Action(
            type=ActionType.PROVIDE_TEXT,
            label=f"Provide Correct {field_label}",
            help_text=f"Enter the correct {field_label} if none of the options are accurate",
            max_length=500
        )
    ]
    
    actions = Actions(
        primary=primary_action,
        secondary=secondary_actions
    )
    
    resolution = Resolution(
        status=ResolutionStatus.PENDING,
        recheck_rules=[rule_id],
        dependent_issues=[]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="needs_review",
        severity=IssueSeverity.ERROR,
        category=IssueCategory.DATA_CONFLICT,
        who_can_fix="applicant",
        user_message=user_message,
        what_we_checked=what_we_checked,
        evidence=evidence,
        actions=actions,
        resolution=resolution,
        metadata=IssueMetadata()
    )


def create_bng_applicability_issue(rule_id: str) -> EnhancedIssue:
    """Create issue for BNG applicability not determined."""
    
    issue_id = "BNG-001-APPLICABILITY"
    
    user_message = UserMessage(
        title="Biodiversity Net Gain (BNG) status not stated",
        subtitle="Clarification needed",
        description="We couldn't find a clear statement on whether BNG applies or is exempt. This often triggers follow-up during validation.",
        impact="May delay application assessment.",
        context="Since February 2024, most developments require 10% biodiversity net gain or must demonstrate exemption."
    )
    
    options = [
        {
            "value": "applies",
            "label": "BNG applies to this development",
            "next_action": "upload_bng_assessment"
        },
        {
            "value": "exempt",
            "label": "Claim BNG exemption",
            "next_action": "provide_exemption_reason"
        },
        {
            "value": "not_sure",
            "label": "Not sure - request guidance",
            "next_action": "officer_review"
        }
    ]
    
    primary_action = Action(
        type=ActionType.SELECT_OPTION,
        label="Specify BNG Status",
        options=options
    )
    
    actions = Actions(
        primary=primary_action,
        secondary=[]
    )
    
    resolution = Resolution(
        status=ResolutionStatus.PENDING,
        recheck_rules=[rule_id, "BNG-02", "BNG-03"]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="fail",
        severity=IssueSeverity.WARNING,
        category=IssueCategory.INFORMATION_MISSING,
        who_can_fix="applicant",
        user_message=user_message,
        actions=actions,
        resolution=resolution,
        metadata=IssueMetadata()
    )


def create_bng_exemption_reason_issue(rule_id: str, found_snippet: Optional[str] = None) -> EnhancedIssue:
    """Create issue for BNG exemption reason missing."""
    
    issue_id = "BNG-003-EXEMPTION"
    
    user_message = UserMessage(
        title="BNG exemption reason missing",
        subtitle="Justification required",
        description="You've indicated BNG is exempt, but we couldn't find the exemption reason. Please provide the specific exemption basis.",
        impact="Exemption claims must be justified to avoid assessment delays."
    )
    
    evidence = None
    if found_snippet:
        evidence = EvidenceData(
            what_we_found={
                "snippet": found_snippet,
                "confidence": 0.7
            }
        )
    
    examples = [
        "Householder application (residential extension)",
        "Site area under 25 square metres",
        "Self-build or custom housebuilding",
        "Development of existing dwelling"
    ]
    
    primary_action = Action(
        type=ActionType.PROVIDE_TEXT,
        label="Provide Exemption Reason",
        help_text="Explain why BNG does not apply to this development",
        example="; ".join(examples),
        max_length=500
    )
    
    secondary_actions = [
        Action(
            type=ActionType.UPLOAD,
            label="Upload BNG Exemption Statement",
            accepts=".pdf",
            optional=True
        )
    ]
    
    actions = Actions(
        primary=primary_action,
        secondary=secondary_actions
    )
    
    resolution = Resolution(
        status=ResolutionStatus.PENDING,
        recheck_rules=[rule_id]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="fail",
        severity=IssueSeverity.WARNING,
        category=IssueCategory.INFORMATION_MISSING,
        who_can_fix="applicant",
        user_message=user_message,
        evidence=evidence,
        actions=actions,
        resolution=resolution,
        metadata=IssueMetadata()
    )


def create_m3_registration_issue(rule_id: str) -> EnhancedIssue:
    """Create issue for M3 registration not confirmed."""
    
    issue_id = "PA-001-M3-REG"
    
    user_message = UserMessage(
        title="M3 registration not confirmed",
        subtitle="Officer check required",
        description="Prior Approval cases require manual registration in M3. Please confirm registration status.",
        impact="Application cannot proceed until M3 registration is confirmed.",
        officer_note=True
    )
    
    primary_action = Action(
        type=ActionType.OFFICER_CONFIRM,
        label="Confirm M3 Registration",
        requires_officer_role=True,
        requires_m3_reference=True
    )
    
    actions = Actions(
        primary=primary_action,
        secondary=[]
    )
    
    resolution = Resolution(
        status=ResolutionStatus.OFFICER_REVIEW,
        recheck_rules=[rule_id]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="fail",
        severity=IssueSeverity.ERROR,
        category=IssueCategory.OFFICER_ACTION_REQUIRED,
        who_can_fix="officer",
        user_message=user_message,
        actions=actions,
        resolution=resolution,
        metadata=IssueMetadata()
    )


def create_pa_required_docs_issue(
    rule_id: str,
    pa_type: str,
    missing_docs: List[str],
    linked_issues: Optional[Dict[str, str]] = None
) -> EnhancedIssue:
    """Create issue for PA required documents missing."""
    
    issue_id = "PA-002-REQ-DOCS"
    linked_issues = linked_issues or {}
    
    doc_labels = [doc.replace('_', ' ').title() for doc in missing_docs]
    docs_str = " and ".join(doc_labels)
    
    user_message = UserMessage(
        title="Prior Approval mandatory documents missing",
        subtitle="Required",
        description=f"Prior Approval {pa_type} applications must include: {docs_str}. One or more are missing.",
        impact="Prior Approval cannot be determined without these mandatory documents."
    )
    
    # Create missing items list
    missing_items = []
    for doc_type in missing_docs:
        missing_items.append(MissingItem(
            type=doc_type,
            label=doc_type.replace('_', ' ').title(),
            status="missing",
            links_to=linked_issues.get(doc_type)
        ))
    
    primary_action = Action(
        type=ActionType.BULK_UPLOAD,
        label="Upload Missing PA Documents",
        required_types=missing_docs
    )
    
    actions = Actions(
        primary=primary_action,
        secondary=[]
    )
    
    resolution = Resolution(
        status=ResolutionStatus.PENDING,
        depends_on=list(linked_issues.values()),
        auto_resolve=True,
        recheck_rules=[rule_id]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="fail",
        severity=IssueSeverity.ERROR,
        category=IssueCategory.DOCUMENT_MISSING,
        who_can_fix="applicant",
        user_message=user_message,
        actions=actions,
        missing_items=missing_items,
        resolution=resolution,
        metadata=IssueMetadata()
    )
