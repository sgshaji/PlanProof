"""
Database helpers and table definitions for PostgreSQL with PostGIS.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import json

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from geoalchemy2 import Geometry

from planproof.config import get_settings

Base = declarative_base()


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)



class ValidationStatus(str, Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"


class Application(Base):
    """Planning application record (PlanningCase in requirements)."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_ref = Column(String(100), unique=True, nullable=False, index=True)
    applicant_name = Column(String(255))
    application_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    submissions = relationship("Submission", back_populates="planning_case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")


class Submission(Base):
    """Submission version (V0, V1+) for a PlanningCase."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    planning_case_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    submission_version = Column(String(10), nullable=False, index=True)  # "V0", "V1", "V2", etc.
    parent_submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)  # For modifications
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    submission_metadata = Column(JSON, nullable=True)  # resolved_fields, llm_calls_per_submission, etc.

    # Submission type classification (modification vs new construction)
    submission_type = Column(
        String(50),
        nullable=True,  # Nullable for backward compatibility with existing data
        default="new_construction"
    )  # Values: "modification", "new_construction", "resubmission"
    submission_type_confidence = Column(Float, nullable=True)  # 0.0-1.0 from LLM classification
    submission_type_source = Column(String(20), nullable=True)  # "llm", "user", "heuristic"

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    planning_case = relationship("Application", back_populates="submissions")
    parent_submission = relationship("Submission", remote_side=[id], backref="child_submissions")
    documents = relationship("Document", back_populates="submission", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="submission", cascade="all, delete-orphan")
    change_sets = relationship("ChangeSet", foreign_keys="ChangeSet.submission_id", back_populates="submission", cascade="all, delete-orphan")
    validation_checks = relationship("ValidationCheck", back_populates="submission", cascade="all, delete-orphan")


class Document(Base):
    """Document record (PDFs uploaded for processing)."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)  # NEW: Link to submission
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)  # Keep for backward compat
    blob_uri = Column(String(500), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=True, unique=True, index=True)  # SHA256 hash for deduplication
    uploaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    page_count = Column(Integer, nullable=True)
    docintel_model = Column(String(50), nullable=True)  # e.g., "prebuilt-layout"
    document_type = Column(String(50), nullable=True)  # e.g., "application_form", "site_plan"

    # Relationships
    submission = relationship("Submission", back_populates="documents")
    application = relationship("Application", back_populates="documents")
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")
    artefacts = relationship("Artefact", back_populates="document", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="document", cascade="all, delete-orphan")
    validation_checks = relationship("ValidationCheck", back_populates="document", cascade="all, delete-orphan")
    run_documents = relationship("RunDocument", back_populates="document", cascade="all, delete-orphan")
    runs = relationship("Run", secondary="run_documents", viewonly=True)


class Page(Base):
    """Page record for a document."""
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    page_metadata = Column(JSON, nullable=True)  # OCR confidence, dimensions, etc.
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="pages")
    evidence = relationship("Evidence", back_populates="page", cascade="all, delete-orphan")


class Evidence(Base):
    """Evidence pointer: page + bbox + snippet + confidence."""
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True, index=True)
    page_number = Column(Integer, nullable=False)  # Denormalized for quick access
    evidence_type = Column(String(50), nullable=False)  # "text_block", "table", "field_extraction"
    evidence_key = Column(String(100), nullable=False, index=True)  # e.g., "text_block_0", "site_address_evidence"
    bbox = Column(JSON, nullable=True)  # {x, y, width, height} or PostGIS geometry
    snippet = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Full content if available
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="evidence")
    page = relationship("Page", back_populates="evidence")
    extracted_fields = relationship("ExtractedField", back_populates="evidence", cascade="all, delete-orphan")


class ExtractedField(Base):
    """Extracted field with value, unit, confidence, and evidence links."""
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)  # e.g., "site_address", "proposed_use"
    field_value = Column(Text, nullable=True)
    field_unit = Column(String(50), nullable=True)  # e.g., "m", "sqm", "stories"
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    extractor = Column(String(50), nullable=True)  # "regex", "heuristic", "llm", etc.
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True, index=True)
    conflict_flag = Column(String(20), nullable=True)  # "none", "detected", "resolved"
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    submission = relationship("Submission", back_populates="extracted_fields")
    evidence = relationship("Evidence", back_populates="extracted_fields")


class GeometryFeature(Base):
    """Geometry feature (outlines) for spatial validation."""
    __tablename__ = "geometry_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    feature_type = Column(String(50), nullable=False)  # "site_boundary", "proposed_extension", "proposed_balcony"
    geometry = Column(Geometry("GEOMETRY"), nullable=True)  # PostGIS geometry
    geometry_json = Column(JSON, nullable=True)  # Fallback JSON representation
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    submission = relationship("Submission")
    spatial_metrics = relationship("SpatialMetric", back_populates="geometry_feature", cascade="all, delete-orphan")


class SpatialMetric(Base):
    """Spatial metric (key measures) derived from geometry."""
    __tablename__ = "spatial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geometry_feature_id = Column(Integer, ForeignKey("geometry_features.id"), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)  # "min_distance_to_boundary", "area", "projection_depth"
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=False)  # "m", "sqm", etc.
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    geometry_feature = relationship("GeometryFeature", back_populates="spatial_metrics")


class ChangeSet(Base):
    """ChangeSet: computed delta between two submissions."""
    __tablename__ = "change_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)  # V1+ submission
    parent_submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)  # V0 submission
    significance_score = Column(Float, nullable=True)  # 0.0 to 1.0
    requires_validation = Column(String(20), nullable=False, default="yes")  # "yes", "no", "partial"
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    submission = relationship("Submission", foreign_keys=[submission_id], back_populates="change_sets")
    parent_submission = relationship("Submission", foreign_keys=[parent_submission_id])
    change_items = relationship("ChangeItem", back_populates="change_set", cascade="all, delete-orphan")


class ChangeItem(Base):
    """ChangeItem: individual change within a ChangeSet."""
    __tablename__ = "change_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_set_id = Column(Integer, ForeignKey("change_sets.id"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)  # "field_delta", "document_delta", "spatial_metric_delta"
    field_key = Column(String(100), nullable=True)  # Field name (for field_delta)
    document_type = Column(String(50), nullable=True)  # Document type (for document_delta)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_metadata = Column(JSON, nullable=True)  # Additional metadata (action, significance, etc.)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    change_set = relationship("ChangeSet", back_populates="change_items")


class Rule(Base):
    """Validation rule (can also be in JSON catalog, but DB allows versioning)."""
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "RULE-1"
    rule_name = Column(String(255), nullable=False)
    rule_category = Column(String(50), nullable=False)  # "DOCUMENT_REQUIRED", "CONSISTENCY", "MODIFICATION", "SPATIAL"
    required_fields = Column(JSON, nullable=False)  # List of field names
    severity = Column(String(20), nullable=False)  # "error", "warning"
    rule_config = Column(JSON, nullable=True)  # Additional rule configuration
    is_active = Column(String(10), nullable=False, default="yes")  # "yes", "no"
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    validation_checks = relationship("ValidationCheck", back_populates="rule", cascade="all, delete-orphan")


class ValidationCheck(Base):
    """ValidationCheck: per-rule execution result (separate from ValidationResult)."""
    __tablename__ = "validation_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=True, index=True)
    rule_id_string = Column(String(100), nullable=True, index=True)  # Denormalized for quick lookup
    status = Column(SQLEnum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING)
    explanation = Column(Text, nullable=True)
    evidence_ids = Column(JSON, nullable=True)  # List of evidence IDs
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    submission = relationship("Submission", back_populates="validation_checks")
    document = relationship("Document", back_populates="validation_checks")
    rule = relationship("Rule", back_populates="validation_checks")


class Artefact(Base):
    """Extracted JSON artefacts from document processing."""
    __tablename__ = "artefacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    artefact_type = Column(String(50), nullable=False)  # e.g., "extracted_layout", "structured_data"
    blob_uri = Column(String(500), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    artefact_metadata = Column(JSON, nullable=True)  # Additional metadata about the artefact (renamed from metadata to avoid SQLAlchemy conflict)

    # Relationships
    document = relationship("Document", back_populates="artefacts")


class ValidationResult(Base):
    """Validation results for extracted fields (legacy, kept for backward compatibility)."""
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)  # e.g., "site_address", "proposed_use"
    status = Column(SQLEnum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    extracted_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    rule_name = Column(String(100), nullable=True)  # Which validation rule was applied
    error_message = Column(Text, nullable=True)
    evidence_page = Column(Integer, nullable=True)  # Page number where evidence was found
    evidence_location = Column(Text, nullable=True)  # JSON pointer or coordinate reference
    llm_resolution = Column(Text, nullable=True)  # LLM reasoning if used
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    document = relationship("Document", back_populates="validation_results")


class OfficerOverride(Base):
    """Officer override for validation results - preserves system truth while recording officer decisions."""
    __tablename__ = "officer_overrides"
    
    override_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True, index=True)
    validation_result_id = Column(Integer, ForeignKey("validation_results.id"), nullable=True, index=True)
    validation_check_id = Column(Integer, ForeignKey("validation_checks.id"), nullable=True, index=True)
    original_status = Column(String(20), nullable=False)  # Original system result
    override_status = Column(String(20), nullable=False)  # Officer decision (pass, fail, needs_review)
    notes = Column(Text, nullable=False)  # Mandatory explanation
    officer_id = Column(String(100), nullable=False)  # User identifier
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    run = relationship("Run")
    validation_result = relationship("ValidationResult")
    validation_check = relationship("ValidationCheck")


class FieldResolution(Base):
    """Field resolution - officer selection of canonical value when conflicts exist."""
    __tablename__ = "field_resolutions"
    
    resolution_id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    field_key = Column(String(100), nullable=False, index=True)
    chosen_extracted_field_id = Column(Integer, ForeignKey("extracted_fields.id"), nullable=True)
    chosen_value = Column(String(500), nullable=True)  # Denormalized for quick access
    officer_id = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    submission = relationship("Submission")
    extracted_field = relationship("ExtractedField")


class Run(Base):
    """Audit trail for processing runs (optional but recommended)."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(50), nullable=False)  # e.g., "ingest", "extract", "validate", "llm_gate"
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed, reviewed, completed_with_errors
    error_message = Column(Text, nullable=True)
    run_metadata = Column(JSON, nullable=True)  # Additional run context (renamed from metadata to avoid SQLAlchemy conflict)

    # Relationships
    run_documents = relationship("RunDocument", back_populates="run", cascade="all, delete-orphan")
    documents = relationship("Document", secondary="run_documents", viewonly=True)


class RunDocument(Base):
    """Join table linking runs to multiple documents."""
    __tablename__ = "run_documents"

    run_id = Column(Integer, ForeignKey("runs.id"), primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    run = relationship("Run", back_populates="run_documents")
    document = relationship("Document", back_populates="run_documents")


class IssueResolution(Base):
    """Track resolution of validation issues."""
    __tablename__ = "issue_resolutions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    issue_id = Column(String(255), nullable=False, index=True)
    rule_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)  # open, in_progress, awaiting_verification, resolved, dismissed
    severity = Column(String(50))
    category = Column(String(100))
    recheck_pending = Column(Integer, default=0)  # Boolean as integer
    last_action_at = Column(DateTime(timezone=True))
    last_recheck_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    dismissed_at = Column(DateTime(timezone=True))
    dismissed_by = Column(String(255))
    dismissal_reason = Column(Text)
    metadata_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    # Relationships
    run = relationship("Run", back_populates="issue_resolutions")
    actions = relationship("ResolutionAction", back_populates="issue_resolution", cascade="all, delete-orphan")


class ReviewDecision(Base):
    """Human-in-Loop review decisions for validation findings."""
    __tablename__ = "review_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    validation_check_id = Column(Integer, ForeignKey("validation_checks.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    reviewer_id = Column(String(255), nullable=False)  # User ID or email of reviewer
    decision = Column(String(50), nullable=False)  # accept, reject, need_info
    comment = Column(Text, nullable=True)  # Reviewer's explanation
    reviewed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    validation_check = relationship("ValidationCheck")
    run = relationship("Run")


class ResolutionAction(Base):
    """Track actions taken to resolve issues."""
    __tablename__ = "resolution_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_resolution_id = Column(Integer, ForeignKey("issue_resolutions.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # document_upload, option_selection, explanation_provided, dismissed
    action_data = Column(JSON)  # Store action-specific data
    performed_by = Column(String(255))
    performed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    issue_resolution = relationship("IssueResolution", back_populates="actions")


class RecheckHistory(Base):
    """Track recheck attempts for issues."""
    __tablename__ = "recheck_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    issue_resolution_id = Column(Integer, ForeignKey("issue_resolutions.id"), nullable=False, index=True)
    rule_id = Column(String(255), nullable=False)
    previous_status = Column(String(50))
    new_status = Column(String(50))
    triggered_by = Column(String(50))  # document_upload, manual, dependency_cascade
    recheck_result = Column(JSON)
    rechecked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    run = relationship("Run", back_populates="recheck_history")
    issue_resolution = relationship("IssueResolution", back_populates="recheck_history")


class IssueDependency(Base):
    """Track dependencies between issues."""
    __tablename__ = "issue_dependencies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    issue_id = Column(String(255), nullable=False, index=True)
    depends_on_issue_id = Column(String(255), nullable=False)
    dependency_type = Column(String(50))  # blocking, suggested, informational
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationships
    run = relationship("Run", back_populates="issue_dependencies")


# Add relationships to Run model
Run.issue_resolutions = relationship("IssueResolution", back_populates="run", cascade="all, delete-orphan")
Run.recheck_history = relationship("RecheckHistory", back_populates="run", cascade="all, delete-orphan")
Run.issue_dependencies = relationship("IssueDependency", back_populates="run", cascade="all, delete-orphan")


class Database:
    """Database operations class."""

    def __init__(self):
        settings = get_settings()
        # Convert postgresql:// to postgresql+psycopg:// to use psycopg3 driver instead of psycopg2
        db_url = settings.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        self.database_url = db_url  # Store for reference (renamed from conn_str for consistency)
        # Configure connection pool to prevent exhaustion under load
        self.engine = create_engine(
            db_url,
            echo=False,
            pool_size=20,          # Increased from 5 for better concurrency
            max_overflow=30,       # Increased from 10 for burst traffic
            pool_pre_ping=True,    # Verify connections before using
            pool_recycle=1800      # Recycle connections every 30 min
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def init_db(self):
        """Initialize database, creating tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def create_application(
        self,
        application_ref: str,
        applicant_name: Optional[str] = None,
        application_date: Optional[datetime] = None
    ) -> Application:
        """Create a new application."""
        session = self.get_session()
        try:
            app = Application(
                application_ref=application_ref,
                applicant_name=applicant_name,
                application_date=application_date
            )
            session.add(app)
            session.commit()
            session.refresh(app)
            return app
        finally:
            session.close()

    def get_or_create_application(
        self,
        application_ref: str,
        applicant_name: Optional[str] = None,
        application_date: Optional[datetime] = None
    ) -> Application:
        """Get existing application or create new one."""
        session = self.get_session()
        try:
            app = session.query(Application).filter(
                Application.application_ref == application_ref
            ).first()
            
            if not app:
                app = Application(
                    application_ref=application_ref,
                    applicant_name=applicant_name,
                    application_date=application_date
                )
                session.add(app)
                session.commit()
                session.refresh(app)
            
            return app
        finally:
            session.close()

    def create_submission(
        self,
        planning_case_id: int,
        submission_version: str,
        parent_submission_id: Optional[int] = None,
        status: str = "pending",
        submission_metadata: Optional[Dict] = None
    ) -> Submission:
        """Create a new submission."""
        session = self.get_session()
        try:
            submission = Submission(
                planning_case_id=planning_case_id,
                submission_version=submission_version,
                parent_submission_id=parent_submission_id,
                status=status,
                submission_metadata=submission_metadata or {}
            )
            session.add(submission)
            session.commit()
            session.refresh(submission)
            return submission
        finally:
            session.close()

    def create_document(
        self,
        blob_uri: str,
        filename: str,
        submission_id: Optional[int] = None,
        application_id: Optional[int] = None,
        content_hash: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Document:
        """Create a new document."""
        session = self.get_session()
        try:
            document = Document(
                blob_uri=blob_uri,
                filename=filename,
                submission_id=submission_id,
                application_id=application_id,
                content_hash=content_hash,
                document_type=document_type
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document
        finally:
            session.close()

    def create_run(
        self,
        run_type: str = "ui_single",
        application_id: Optional[int] = None,
        document_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        metadata: Optional[Dict] = None
    ) -> Run:
        """Create a new run - matches Run model fields exactly."""
        session = self.get_session()
        try:
            doc_ids: List[int] = list(document_ids or [])
            if document_id is not None and document_id not in doc_ids:
                doc_ids.insert(0, document_id)

            run = Run(
                run_type=run_type,
                application_id=application_id,
                document_id=doc_ids[0] if doc_ids else None,
                run_metadata=metadata or {},
                status="pending"
            )
            session.add(run)
            session.flush()

            for doc_id in doc_ids:
                session.add(RunDocument(run_id=run.id, document_id=doc_id))
            session.commit()
            session.refresh(run)
            return run
        finally:
            session.close()

    def update_run_status(
        self,
        run_id: int,
        status: str
    ) -> Run:
        """Update run status."""
        session = self.get_session()
        try:
            run = session.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = status
                run.updated_at = utcnow()
                session.commit()
                session.refresh(run)
            return run
        finally:
            session.close()

    def create_extracted_fields_bulk(
        self,
        fields: List[ExtractedField],
        session: Optional[Session] = None
    ) -> List[ExtractedField]:
        """Create multiple extracted field records in a single transaction."""
        owns_session = session is None
        if session is None:
            session = self.get_session()
        try:
            session.add_all(fields)
            session.commit()
            for field in fields:
                session.refresh(field)
            return fields
        finally:
            if owns_session:
                session.close()

    def get_extracted_fields_for_submission(
        self,
        submission_id: int
    ) -> Dict[str, Any]:
        """Get all extracted fields for a submission as a dict (for backward compatibility)."""
        session = self.get_session()
        try:
            fields = session.query(ExtractedField).filter(
                ExtractedField.submission_id == submission_id
            ).all()
            
            result = {}
            for field in fields:
                result[field.field_name] = field.field_value
            
            return result
        finally:
            session.close()

    def get_evidence_index_for_document(
        self,
        document_id: int
    ) -> Dict[str, Any]:
        """Get all evidence for a document as a dict (for backward compatibility)."""
        session = self.get_session()
        try:
            evidence_list = session.query(Evidence).filter(
                Evidence.document_id == document_id
            ).all()
            
            result = {}
            for ev in evidence_list:
                ev_dict = {
                    "type": ev.evidence_type,
                    "page_number": ev.page_number,
                    "snippet": ev.snippet,
                    "content": ev.content,
                    "confidence": ev.confidence,
                    "bbox": ev.bbox
                }
                result[ev.evidence_key] = ev_dict
            
            return result
        finally:
            session.close()
    
    # Resolution tracking methods
    
    def create_issue_resolution(
        self,
        run_id: int,
        issue_id: str,
        rule_id: str,
        status: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        metadata_json: Optional[Dict] = None
    ) -> IssueResolution:
        """Create a new issue resolution record."""
        session = self.get_session()
        try:
            resolution = IssueResolution(
                run_id=run_id,
                issue_id=issue_id,
                rule_id=rule_id,
                status=status,
                severity=severity,
                category=category,
                metadata_json=metadata_json or {}
            )
            session.add(resolution)
            session.commit()
            session.refresh(resolution)
            return resolution
        finally:
            session.close()
    
    def update_issue_resolution_status(
        self,
        issue_resolution_id: int,
        status: str,
        **kwargs
    ) -> IssueResolution:
        """Update issue resolution status."""
        session = self.get_session()
        try:
            resolution = session.query(IssueResolution).filter(
                IssueResolution.id == issue_resolution_id
            ).first()
            
            if resolution:
                resolution.status = status
                resolution.updated_at = utcnow()
                
                for key, value in kwargs.items():
                    if hasattr(resolution, key):
                        setattr(resolution, key, value)
                
                session.commit()
                session.refresh(resolution)
            
            return resolution
        finally:
            session.close()
    
    def create_resolution_action(
        self,
        issue_resolution_id: int,
        action_type: str,
        action_data: Optional[Dict] = None,
        performed_by: Optional[str] = None
    ) -> ResolutionAction:
        """Record a resolution action."""
        session = self.get_session()
        try:
            action = ResolutionAction(
                issue_resolution_id=issue_resolution_id,
                action_type=action_type,
                action_data=action_data or {},
                performed_by=performed_by
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            return action
        finally:
            session.close()
    
    def create_recheck_history(
        self,
        run_id: int,
        issue_resolution_id: int,
        rule_id: str,
        previous_status: Optional[str],
        new_status: str,
        triggered_by: str,
        recheck_result: Optional[Dict] = None
    ) -> RecheckHistory:
        """Record a recheck event."""
        session = self.get_session()
        try:
            recheck = RecheckHistory(
                run_id=run_id,
                issue_resolution_id=issue_resolution_id,
                rule_id=rule_id,
                previous_status=previous_status,
                new_status=new_status,
                triggered_by=triggered_by,
                recheck_result=recheck_result or {}
            )
            session.add(recheck)
            session.commit()
            session.refresh(recheck)
            return recheck
        finally:
            session.close()

    # Methods from first Database class that were missing

    def create_tables(self):
        """Create all tables (use Alembic for migrations in production)."""
        Base.metadata.create_all(self.engine)

    def execute_raw(self, query: str, params: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results as dictionaries.

        Args:
            query: SQL query string
            params: Optional query parameters (tuple, dict, or None)

        Returns:
            List of result dictionaries
        """
        # Get raw database URL (psycopg needs postgresql:// not postgresql+psycopg://)
        raw_url = self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(raw_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if params is None:
                    cur.execute(query)
                else:
                    cur.execute(query, params)
                return cur.fetchall()

    def get_application_by_ref(self, application_ref: str) -> Optional[Application]:
        """Get an application by reference."""
        session = self.get_session()
        try:
            return session.query(Application).filter(Application.application_ref == application_ref).first()
        finally:
            session.close()

    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """Get an application by ID."""
        session = self.get_session()
        try:
            return session.query(Application).filter(Application.id == application_id).first()
        finally:
            session.close()

    def get_submission_by_id(self, submission_id: int) -> Optional[Submission]:
        """Get a submission by ID."""
        session = self.get_session()
        try:
            return session.query(Submission).filter(Submission.id == submission_id).first()
        finally:
            session.close()

    def get_document_by_blob_uri(self, blob_uri: str) -> Optional[Document]:
        """Get a document by blob URI."""
        session = self.get_session()
        try:
            return session.query(Document).filter(Document.blob_uri == blob_uri).first()
        finally:
            session.close()

    def create_artefact_record(
        self,
        document_id: int,
        artefact_type: str,
        blob_uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new artefact record.

        Args:
            document_id: Document ID
            artefact_type: Type of artefact
            blob_uri: URI of the blob storage location
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with artefact details

        Raises:
            RuntimeError: If database operation fails
        """
        session = self.get_session()
        try:
            artefact = Artefact(
                document_id=document_id,
                artefact_type=artefact_type,
                blob_uri=blob_uri,
                artefact_metadata=metadata or {}
            )
            session.add(artefact)
            session.commit()
            session.refresh(artefact)
            return {
                "id": artefact.id,
                "document_id": artefact.document_id,
                "artefact_type": artefact.artefact_type,
                "blob_uri": artefact.blob_uri,
                "created_at": artefact.created_at.isoformat() if artefact.created_at else None
            }
        except Exception as e:
            session.rollback()
            error_msg = f"Failed to create artefact record: {str(e)}"
            raise RuntimeError(error_msg) from e
        finally:
            session.close()

    def link_document_to_run(self, run_id: int, document_id: int):
        """Link a document to a run by creating a RunDocument entry.

        Args:
            run_id: Run ID
            document_id: Document ID to link

        Raises:
            RuntimeError: If database operation fails
            ValueError: If run not found
        """
        session = self.get_session()
        try:
            run = session.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")
            existing = session.query(RunDocument).filter(
                RunDocument.run_id == run_id,
                RunDocument.document_id == document_id
            ).first()
            if not existing:
                session.add(RunDocument(run_id=run_id, document_id=document_id))
            if not run.document_id:
                run.document_id = document_id
            session.commit()
        except ValueError:
            # Re-raise ValueError without rollback (no changes made)
            raise
        except Exception as e:
            session.rollback()
            error_msg = f"Failed to link document {document_id} to run {run_id}: {str(e)}"
            raise RuntimeError(error_msg) from e
        finally:
            session.close()

    def update_run(
        self,
        run_id: int,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update a run record.

        Args:
            run_id: Run ID to update
            status: Optional status to set
            error_message: Optional error message
            metadata: Optional metadata to merge with existing

        Raises:
            RuntimeError: If database operation fails
            ValueError: If run not found
        """
        session = self.get_session()
        try:
            run = session.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")

            if status:
                run.status = status
            if error_message:
                run.error_message = error_message
            if metadata:
                # Merge with existing metadata
                existing = run.run_metadata or {}
                existing.update(metadata)
                run.run_metadata = existing
            run.completed_at = datetime.now(timezone.utc)
            session.commit()
        except ValueError:
            # Re-raise ValueError without rollback (no changes made)
            raise
        except Exception as e:
            session.rollback()
            error_msg = f"Failed to update run {run_id}: {str(e)}"
            raise RuntimeError(error_msg) from e
        finally:
            session.close()

    def get_resolved_fields_for_submission(self, submission_id: int) -> Dict[str, Any]:
        """Get resolved fields cache for a submission."""
        session = self.get_session()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if submission and submission.submission_metadata:
                return submission.submission_metadata.get("resolved_fields", {})
            return {}
        finally:
            session.close()

    def get_resolved_fields_for_application(self, application_ref: str) -> Dict[str, Any]:
        """
        Get all resolved fields from previous submissions for a given application_ref.

        This implements application-level caching: if a field was resolved in any
        previous submission for this application, it won't be asked again.

        Args:
            application_ref: Application reference string

        Returns:
            Dictionary of resolved fields {field_name: value}
        """
        session = self.get_session()
        try:
            # Get planning case (application)
            app = session.query(Application).filter(Application.application_ref == application_ref).first()
            if not app:
                return {}

            # Query all submissions for this planning case
            submissions = session.query(Submission).filter(
                Submission.planning_case_id == app.id
            ).order_by(Submission.created_at.desc()).all()

            resolved_fields = {}
            for submission in submissions:
                if submission.submission_metadata:
                    submission_resolved = submission.submission_metadata.get("resolved_fields", {})
                    if submission_resolved:
                        resolved_fields.update(submission_resolved)

            return resolved_fields
        finally:
            session.close()

    def update_submission_metadata(
        self,
        submission_id: int,
        metadata_updates: Dict[str, Any]
    ):
        """
        Update submission metadata by merging with existing metadata.

        Args:
            submission_id: Submission ID
            metadata_updates: Dictionary of metadata fields to update/merge
        """
        session = self.get_session()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                # Merge with existing metadata
                existing_metadata = submission.submission_metadata or {}
                existing_metadata.update(metadata_updates)
                submission.submission_metadata = existing_metadata
                submission.updated_at = datetime.now(timezone.utc)
                session.commit()
        finally:
            session.close()

    def get_submission_by_version(
        self,
        planning_case_id: int,
        submission_version: str
    ) -> Optional[Submission]:
        """Get a submission by planning case and version."""
        session = self.get_session()
        try:
            return session.query(Submission).filter(
                Submission.planning_case_id == planning_case_id,
                Submission.submission_version == submission_version
            ).first()
        finally:
            session.close()

    def create_page(
        self,
        document_id: int,
        page_number: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Page:
        """Create a new page record."""
        session = self.get_session()
        try:
            page = Page(
                document_id=document_id,
                page_number=page_number,
                page_metadata=metadata or {}
            )
            session.add(page)
            session.commit()
            session.refresh(page)
            return page
        finally:
            session.close()

    def create_pages_bulk(
        self,
        pages: List[Page],
        session: Optional[Session] = None
    ) -> List[Page]:
        """Create multiple page records in a single transaction."""
        owns_session = session is None
        if session is None:
            session = self.get_session()
        try:
            session.add_all(pages)
            session.commit()
            for page in pages:
                session.refresh(page)
            return pages
        finally:
            if owns_session:
                session.close()

    def create_evidence(
        self,
        document_id: int,
        page_number: int,
        evidence_type: str,
        evidence_key: str,
        snippet: Optional[str] = None,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        bbox: Optional[Dict[str, Any]] = None,
        page_id: Optional[int] = None
    ) -> Evidence:
        """Create a new evidence record."""
        session = self.get_session()
        try:
            evidence = Evidence(
                document_id=document_id,
                page_id=page_id,
                page_number=page_number,
                evidence_type=evidence_type,
                evidence_key=evidence_key,
                snippet=snippet,
                content=content,
                confidence=confidence,
                bbox=bbox
            )
            session.add(evidence)
            session.commit()
            session.refresh(evidence)
            return evidence
        finally:
            session.close()

    def create_evidence_bulk(
        self,
        evidence_items: List[Evidence],
        session: Optional[Session] = None
    ) -> List[Evidence]:
        """Create multiple evidence records in a single transaction."""
        owns_session = session is None
        if session is None:
            session = self.get_session()
        try:
            session.add_all(evidence_items)
            session.commit()
            for evidence in evidence_items:
                session.refresh(evidence)
            return evidence_items
        finally:
            if owns_session:
                session.close()

    def create_extracted_field(
        self,
        submission_id: int,
        field_name: str,
        field_value: Optional[str] = None,
        field_unit: Optional[str] = None,
        confidence: Optional[float] = None,
        extractor: Optional[str] = None,
        evidence_id: Optional[int] = None
    ) -> ExtractedField:
        """Create a new extracted field record."""
        session = self.get_session()
        try:
            field = ExtractedField(
                submission_id=submission_id,
                field_name=field_name,
                field_value=field_value,
                field_unit=field_unit,
                confidence=confidence,
                extractor=extractor,
                evidence_id=evidence_id
            )
            session.add(field)
            session.commit()
            session.refresh(field)
            return field
        finally:
            session.close()
