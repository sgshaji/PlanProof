"""
Constants and enumerations for validation.

This module centralizes all hard-coded strings used throughout the validation
pipeline to improve maintainability and reduce typos.
"""

from enum import Enum
from typing import List


class ValidationStatus(str, Enum):
    """Validation check status values."""
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"

    def __str__(self) -> str:
        return self.value


class ValidationSeverity(str, Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value


class DocumentType(str, Enum):
    """Common document types in planning applications."""
    APPLICATION_FORM = "application_form"
    LOCATION_PLAN = "location_plan"
    SITE_PLAN = "site_plan"
    HERITAGE_STATEMENT = "heritage_statement"
    HERITAGE = "heritage"
    TREE_SURVEY = "tree_survey"
    FLOOD_RISK_ASSESSMENT = "flood_risk_assessment"
    DESIGN_ACCESS_STATEMENT = "design_access_statement"
    PLANS_DRAWINGS = "plans_drawings"
    ELEVATIONS = "elevations"
    FLOOR_PLANS = "floor_plans"
    OWNERSHIP_CERTIFICATE = "ownership_certificate"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


class CertificateType(str, Enum):
    """Ownership certificate types."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def valid_certificates(cls) -> List[str]:
        """Return list of valid certificate types."""
        return [cert.value for cert in cls]


class ApplicationType(str, Enum):
    """Planning application types."""
    HOUSEHOLDER = "householder"
    FULL = "full"
    MAJOR = "major"
    PRIOR_APPROVAL = "prior_approval"
    OUTLINE = "outline"
    RESERVED_MATTERS = "reserved_matters"
    LISTED_BUILDING_CONSENT = "listed_building_consent"
    CONSERVATION_AREA_CONSENT = "conservation_area_consent"

    def __str__(self) -> str:
        return self.value


class SubmissionVersion(str, Enum):
    """Submission version identifiers."""
    V0 = "V0"
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def is_modification(cls, version: str) -> bool:
        """Check if a version represents a modification (not V0)."""
        return version != cls.V0.value


class SubmissionSource(str, Enum):
    """Submission source/origin identifiers."""
    UI_BATCH = "ui_batch"
    MANUAL = "manual"
    API = "api"

    def __str__(self) -> str:
        return self.value


class RunStatus(str, Enum):
    """Processing run status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class IssueCategory(str, Enum):
    """Issue/finding categories for UI display."""
    ISSUES_FOUND = "Issues Found"
    WARNINGS = "Warnings"
    INFORMATION = "Information"
    PASSED = "Passed"

    def __str__(self) -> str:
        return self.value


class RuleCategory(str, Enum):
    """Rule category types for validation dispatching."""
    FIELD_REQUIRED = "FIELD_REQUIRED"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    CONSISTENCY = "CONSISTENCY"
    MODIFICATION = "MODIFICATION"
    SPATIAL = "SPATIAL"
    FEE_VALIDATION = "FEE_VALIDATION"
    OWNERSHIP_VALIDATION = "OWNERSHIP_VALIDATION"
    PRIOR_APPROVAL = "PRIOR_APPROVAL"
    CONSTRAINT_VALIDATION = "CONSTRAINT_VALIDATION"
    BNG_VALIDATION = "BNG_VALIDATION"
    PLAN_QUALITY = "PLAN_QUALITY"

    def __str__(self) -> str:
        return self.value


# Common field names
class FieldName:
    """Common field names used in validation."""
    SITE_ADDRESS = "site_address"
    PROPOSED_USE = "proposed_use"
    APPLICATION_REF = "application_ref"
    APPLICATION_TYPE = "application_type"
    FEE_PAYMENT_STATUS = "fee_payment_status"
    FEE_AMOUNT = "fee_amount"
    RECEIPT_REFERENCE = "receipt_reference"
    CERTIFICATE_TYPE = "certificate_type"
    CERTIFICATE_NAME = "certificate_name"
    APPLICANT_NAME = "applicant_name"
    BNG_APPLICABLE = "bng_applicable"
    BNG_PERCENTAGE = "bng_percentage"
    BNG_EXEMPTION_REASON = "bng_exemption_reason"
    CONSERVATION_AREA = "conservation_area"
    LISTED_BUILDING = "listed_building"
    TPO = "tpo"
    FLOOD_ZONE = "flood_zone"
    LOCATION_PLAN_SCALE = "location_plan_scale"
    DOCUMENT_TYPE = "document_type"


# Common configuration values
class Config:
    """Common configuration constants."""
    DEFAULT_CONFIDENCE = 0.8
    MIN_EVIDENCE_CONFIDENCE = 0.6
    MAX_EVIDENCE_SNIPPETS = 5
    DEFAULT_MIN_FEE = 0
    DEFAULT_MAX_FEE = 500000
    BNG_MIN_PERCENTAGE = 10
