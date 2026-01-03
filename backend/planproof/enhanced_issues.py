"""
Enhanced Issue Model for PlanProof Validation System.

This module provides a structured, actionable issue format that transforms
validation errors into clear guidance with resolution paths.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    ERROR = "error"  # Blocks validation
    WARNING = "warning"  # Doesn't block but flags risk
    INFO = "info"  # Informational only


class IssueCategory(str, Enum):
    """Issue category types."""
    DOCUMENT_MISSING = "document_missing"
    INFORMATION_MISSING = "information_missing"
    DATA_CONFLICT = "data_conflict"
    OFFICER_ACTION_REQUIRED = "officer_action_required"
    VALIDATION_FAILED = "validation_failed"


class ResolutionStatus(str, Enum):
    """Resolution status for issues."""
    PENDING = "pending"
    RESOLVED = "resolved"
    OFFICER_REVIEW = "officer_review"
    USER_ACKNOWLEDGED = "user_acknowledged"
    AUTO_RESOLVED = "auto_resolved"


class ActionType(str, Enum):
    """Types of actions users can take."""
    UPLOAD = "upload"
    CONFIRM_CANDIDATE = "confirm_candidate"
    MARK_NOT_REQUIRED = "mark_not_required"
    PROVIDE_TEXT = "provide_text"
    SELECT_OPTION = "select_option"
    OFFICER_CONFIRM = "officer_confirm"
    BULK_UPLOAD = "bulk_upload"


@dataclass
class UserMessage:
    """User-facing message for an issue."""
    title: str
    subtitle: str
    description: str
    impact: str
    context: Optional[str] = None
    officer_note: bool = False


@dataclass
class WhatWeChecked:
    """Transparency about validation checks."""
    summary: str
    methods: List[str] = field(default_factory=list)
    documents_scanned: Optional[int] = None
    confidence_threshold: Optional[float] = None


@dataclass
class DocumentCandidate:
    """Potential document match."""
    document_id: int
    filename: str
    confidence: float
    reason: str
    preview_snippet: Optional[str] = None


@dataclass
class EvidenceData:
    """Evidence supporting the issue."""
    candidates: List[DocumentCandidate] = field(default_factory=list)
    checked_locations: List[str] = field(default_factory=list)
    what_we_found: Optional[Dict[str, Any]] = None


@dataclass
class Action:
    """Action a user can take to resolve an issue."""
    type: ActionType
    label: str
    accepts: Optional[str] = None
    help_text: Optional[str] = None
    example: Optional[str] = None
    optional: bool = False
    enabled: bool = True
    disabled_reason: Optional[str] = None
    requires_reason: bool = False
    requires_officer_approval: bool = False
    requires_officer_role: bool = False
    requires_m3_reference: bool = False
    expected_filename_patterns: List[str] = field(default_factory=list)
    options: List[Dict[str, str]] = field(default_factory=list)
    max_length: Optional[int] = None
    document_id: Optional[int] = None
    required_types: List[str] = field(default_factory=list)


@dataclass
class Actions:
    """Available actions for resolving an issue."""
    primary: Action
    secondary: List[Action] = field(default_factory=list)


@dataclass
class MissingItem:
    """Item missing in a composite check."""
    type: str
    label: str
    status: str
    links_to: Optional[str] = None


@dataclass
class Resolution:
    """Resolution tracking for an issue."""
    status: ResolutionStatus = ResolutionStatus.PENDING
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_method: Optional[str] = None
    recheck_rules: List[str] = field(default_factory=list)
    dependent_issues: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    auto_resolve: bool = False


@dataclass
class IssueMetadata:
    """Metadata for tracking issue lifecycle."""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recheck_count: int = 0
    user_viewed: bool = False
    user_dismissed: bool = False


@dataclass
class EnhancedIssue:
    """Enhanced issue with full actionable context."""
    issue_id: str
    rule_id: str
    status: str  # fail, needs_review, pass
    severity: IssueSeverity
    category: IssueCategory
    who_can_fix: Literal["applicant", "officer", "either"]
    user_message: UserMessage
    actions: Actions
    resolution: Resolution
    metadata: IssueMetadata
    what_we_checked: Optional[WhatWeChecked] = None
    evidence: Optional[EvidenceData] = None
    required_upload_types: List[str] = field(default_factory=list)
    missing_items: List[MissingItem] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class IssueGroup:
    """Group of related issues."""
    group_id: str
    title: str
    severity: IssueSeverity
    count: int
    issues: List[str]
    bulk_action: Optional[Action] = None


@dataclass
class ResolutionProgress:
    """Overall resolution progress."""
    total_issues: int
    blocking_errors: int
    warnings: int
    resolved: int
    pending_user: int
    pending_officer: int
    can_proceed: bool


def create_missing_document_issue(
    document_type: str,
    rule_id: str,
    severity: IssueSeverity = IssueSeverity.ERROR,
    candidates: List[DocumentCandidate] = None,
    recheck_rules: List[str] = None,
    optional: bool = False
) -> EnhancedIssue:
    """
    Factory function to create a missing document issue.
    
    Args:
        document_type: Type of missing document (e.g., "application_form", "site_plan")
        rule_id: Rule that detected the issue
        severity: Issue severity
        candidates: Potential document matches
        recheck_rules: Rules to recheck after resolution
        optional: Whether document is optional
    
    Returns:
        EnhancedIssue object
    """
    candidates = candidates or []
    recheck_rules = recheck_rules or [rule_id]
    
    # Document type metadata
    doc_info = {
        "application_form": {
            "title": "Application form missing",
            "description": "We couldn't find the completed planning application form.",
            "impact": "Your application cannot proceed without this document.",
            "help_text": "Upload the completed planning application form PDF",
            "example": "Application_Form_2025.pdf",
            "patterns": ["*application*form*.pdf", "*1APP*.pdf", "*planning*form*.pdf"],
            "search_terms": "'Application Form', '1APP', 'Planning Application Form', PDFs with form fields"
        },
        "site_plan": {
            "title": "Site plan missing",
            "description": "We didn't detect a site plan showing the proposed works on the site boundary.",
            "impact": "Site plans are required to show the location and extent of works.",
            "help_text": "Upload a site plan at scale 1:200 or 1:500 showing the site boundary",
            "example": "Site_Plan_1-500.pdf",
            "patterns": ["*site*plan*.pdf", "*block*plan*.pdf"],
            "search_terms": "Site Plan, Proposed Site Plan, Block Plan, scales 1:200/1:500, red-line boundary"
        },
        "location_plan": {
            "title": "Location plan missing",
            "description": "We didn't find a location plan (usually 1:1250 or 1:2500) showing the site with a red outline.",
            "impact": "Location plans are legally required for all applications.",
            "help_text": "Upload an Ordnance Survey based plan at 1:1250 or 1:2500 with site outlined in red",
            "example": "Location_Plan_1-1250.pdf",
            "patterns": ["*location*plan*.pdf", "*site*location*.pdf"],
            "search_terms": "Location Plan, Site Location Plan, OS map, scales 1:1250/1:2500"
        },
        "elevation": {
            "title": "Elevations missing",
            "description": "Elevation drawings (front/side/rear) weren't found. These show the external appearance of the proposal.",
            "impact": "Elevations are required to assess the visual impact of the development.",
            "help_text": "Upload elevation drawings for all affected sides",
            "example": "Proposed_Elevations.pdf",
            "patterns": ["*elevation*.pdf", "*proposed*elevation*.pdf"],
            "search_terms": "Elevation, Proposed Elevations, Existing/Proposed, façade views, North/South elevation"
        },
        "floor_plan": {
            "title": "Floor plans missing",
            "description": "Floor plan drawings weren't found. These show internal layout by level.",
            "impact": "Floor plans are required to understand the proposed internal arrangement.",
            "help_text": "Upload floor plans for each level (ground/first/loft)",
            "example": "Floor_Plans_All_Levels.pdf",
            "patterns": ["*floor*plan*.pdf", "*GA*.pdf"],
            "search_terms": "Floor Plan, GA, Ground Floor, First Floor, Loft, Scale 1:50/1:100"
        },
        "design_statement": {
            "title": "Design & Access Statement not found",
            "description": "This isn't always required, but it often helps avoid follow-up requests.",
            "impact": "May result in additional information requests during assessment.",
            "help_text": "Upload design and access statement if available",
            "example": "Design_Statement.pdf",
            "patterns": ["*design*statement*.pdf", "*DAS*.pdf"],
            "search_terms": "Design and Access Statement, DAS, Design Statement"
        }
    }
    
    info = doc_info.get(document_type, {
        "title": f"{document_type.replace('_', ' ').title()} missing",
        "description": f"Required document '{document_type}' was not found.",
        "impact": "This document may be required for validation.",
        "help_text": f"Upload {document_type.replace('_', ' ')}",
        "example": f"{document_type}.pdf",
        "patterns": [f"*{document_type}*.pdf"],
        "search_terms": document_type.replace('_', ' ')
    })
    
    issue_id = f"DOC-{hash(document_type) % 1000:03d}-{document_type.upper().replace('_', '-')}"
    
    subtitle = "Optional but recommended" if optional else "Required"
    
    user_message = UserMessage(
        title=info["title"],
        subtitle=subtitle,
        description=info["description"],
        impact=info["impact"]
    )
    
    what_we_checked = WhatWeChecked(
        summary=f"We looked for: {info['search_terms']}",
        methods=["document_classification", "text_pattern_matching", "filename_matching"],
        confidence_threshold=0.7
    )
    
    evidence = EvidenceData(
        candidates=candidates,
        checked_locations=["All uploaded PDFs", "Document metadata", "Text content analysis"]
    )
    
    primary_action = Action(
        type=ActionType.UPLOAD,
        label=f"Upload {document_type.replace('_', ' ').title()}",
        accepts=".pdf",
        help_text=info["help_text"],
        example=info["example"],
        expected_filename_patterns=info["patterns"],
        optional=optional
    )
    
    secondary_actions = []
    
    # Add candidate confirmation actions
    for candidate in candidates[:3]:  # Max 3 candidates
        secondary_actions.append(Action(
            type=ActionType.CONFIRM_CANDIDATE,
            label=f"Confirm {candidate.filename} as {document_type.replace('_', ' ').title()}",
            document_id=candidate.document_id,
            enabled=True
        ))
    
    # Add "not required" option for optional docs
    if optional:
        secondary_actions.append(Action(
            type=ActionType.MARK_NOT_REQUIRED,
            label=f"Not provided (optional for this application)",
            enabled=True
        ))
    else:
        secondary_actions.append(Action(
            type=ActionType.MARK_NOT_REQUIRED,
            label=f"This application doesn't require a {document_type.replace('_', ' ')}",
            requires_reason=True,
            requires_officer_approval=True,
            enabled=False,
            disabled_reason=f"{document_type.replace('_', ' ').title()}s are mandatory for this application type"
        ))
    
    actions = Actions(
        primary=primary_action,
        secondary=secondary_actions
    )
    
    resolution = Resolution(
        status=ResolutionStatus.PENDING,
        recheck_rules=recheck_rules,
        dependent_issues=[]
    )
    
    return EnhancedIssue(
        issue_id=issue_id,
        rule_id=rule_id,
        status="fail",
        severity=severity,
        category=IssueCategory.DOCUMENT_MISSING,
        who_can_fix="applicant",
        user_message=user_message,
        what_we_checked=what_we_checked,
        evidence=evidence,
        actions=actions,
        required_upload_types=[document_type],
        resolution=resolution,
        metadata=IssueMetadata()
    )
