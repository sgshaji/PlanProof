"""
Custom exception classes for PlanProof.

Provides a hierarchy of exceptions for better error handling and debugging.
"""


class PlanProofException(Exception):
    """Base exception for all PlanProof errors."""
    pass


class ConfigurationError(PlanProofException):
    """Configuration is invalid or missing required values."""
    pass


class StorageError(PlanProofException):
    """Error interacting with Azure Blob Storage."""
    pass


class BlobNotFoundError(StorageError):
    """Requested blob does not exist."""
    pass


class BlobUploadError(StorageError):
    """Failed to upload blob to storage."""
    pass


class DatabaseError(PlanProofException):
    """Error interacting with PostgreSQL database."""
    pass


class DocumentNotFoundError(DatabaseError):
    """Document ID not found in database."""
    pass


class ExtractionError(PlanProofException):
    """Error during document extraction process."""
    pass


class DocumentIntelligenceError(ExtractionError):
    """Azure Document Intelligence API error."""
    pass


class FieldMappingError(ExtractionError):
    """Error mapping extracted fields."""
    pass


class ValidationError(PlanProofException):
    """Validation rule execution error."""
    pass


class RuleNotFoundError(ValidationError):
    """Validation rule not found in catalog."""
    pass


class LLMError(PlanProofException):
    """Error calling Azure OpenAI LLM."""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMQuotaExceededError(LLMError):
    """LLM quota or rate limit exceeded."""
    pass
