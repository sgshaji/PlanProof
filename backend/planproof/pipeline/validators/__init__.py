"""
Validators package: Split validation logic into smaller, focused modules.
"""

from planproof.pipeline.validators.constants import (
    ValidationStatus,
    ValidationSeverity,
    DocumentType,
    CertificateType,
    ApplicationType,
    SubmissionVersion,
)
from planproof.pipeline.validators.base_validator import (
    normalize_label,
    build_text_index,
    extract_field_value,
    find_evidence_location,
    extract_all_text,
)
from planproof.pipeline.validators.fee_validator import validate_fee
from planproof.pipeline.validators.ownership_validator import validate_ownership
from planproof.pipeline.validators.document_validator import validate_document_required
from planproof.pipeline.validators.constraint_validator import (
    validate_prior_approval,
    validate_constraint,
    validate_bng,
    validate_plan_quality,
)
from planproof.pipeline.validators.consistency_validator import (
    validate_consistency,
    validate_modification,
)
from planproof.pipeline.validators.spatial_validator import validate_spatial

__all__ = [
    # Constants
    "ValidationStatus",
    "ValidationSeverity",
    "DocumentType",
    "CertificateType",
    "ApplicationType",
    "SubmissionVersion",
    # Base utilities
    "normalize_label",
    "build_text_index",
    "extract_field_value",
    "find_evidence_location",
    "extract_all_text",
    # Validators
    "validate_fee",
    "validate_ownership",
    "validate_document_required",
    "validate_prior_approval",
    "validate_constraint",
    "validate_bng",
    "validate_plan_quality",
    "validate_consistency",
    "validate_modification",
    "validate_spatial",
]
