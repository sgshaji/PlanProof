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
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed, completed_with_errors
    error_message = Column(Text, nullable=True)
    run_metadata = Column(JSON, nullable=True)  # Additional run context (renamed from metadata to avoid SQLAlchemy conflict)


class Database:
    """Database helper class for common operations."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        # Ensure we use psycopg (psycopg3) driver, not psycopg2
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        # Configure connection pool to prevent exhaustion
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_size=5,  # Limit pool size
            max_overflow=10,  # Allow overflow connections
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600  # Recycle connections after 1 hour
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Create all tables (use Alembic for migrations in production)."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

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

    def create_application(
        self,
        application_ref: str,
        applicant_name: Optional[str] = None,
        application_date: Optional[datetime] = None
    ) -> Application:
        """Create a new application record."""
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

    def get_application_by_ref(self, application_ref: str) -> Optional[Application]:
        """Get an application by reference."""
        session = self.get_session()
        try:
            return session.query(Application).filter(Application.application_ref == application_ref).first()
        finally:
            session.close()

    def create_document(
        self,
        application_id: int,
        blob_uri: str,
        filename: str,
        page_count: Optional[int] = None,
        docintel_model: Optional[str] = None,
        content_hash: Optional[str] = None,
        submission_id: Optional[int] = None
    ) -> Document:
        """Create a new document record."""
        session = self.get_session()
        try:
            doc = Document(
                application_id=application_id,
                submission_id=submission_id,
                blob_uri=blob_uri,
                filename=filename,
                page_count=page_count,
                docintel_model=docintel_model,
                content_hash=content_hash
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            return doc
        finally:
            session.close()

    def get_document_by_blob_uri(self, blob_uri: str) -> Optional[Document]:
        """Get a document by blob URI."""
        session = self.get_session()
        try:
            return session.query(Document).filter(Document.blob_uri == blob_uri).first()
        finally:
            session.close()

    def create_run(
        self,
        run_type: str,
        document_id: Optional[int] = None,
        application_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new run record."""
        session = self.get_session()
        try:
            run = Run(
                run_type=run_type,
                document_id=document_id,
                application_id=application_id,
                run_metadata=metadata or {}
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return {
                "id": run.id,
                "run_type": run.run_type,
                "document_id": run.document_id,
                "application_id": run.application_id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "status": run.status
            }
        finally:
            session.close()

    def create_artefact_record(
        self,
        document_id: int,
        artefact_type: str,
        blob_uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new artefact record."""
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
        finally:
            session.close()

    def link_document_to_run(self, run_id: int, document_id: int):
        """Link a document to a run by updating the run's document_id."""
        session = self.get_session()
        try:
            run = session.query(Run).filter(Run.id == run_id).first()
            if run:
                run.document_id = document_id
                session.commit()
        finally:
            session.close()

    def update_run(
        self,
        run_id: int,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update a run record."""
        session = self.get_session()
        try:
            run = session.query(Run).filter(Run.id == run_id).first()
            if run:
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

    def create_submission(
        self,
        planning_case_id: int,
        submission_version: str = "V0",
        parent_submission_id: Optional[int] = None,
        status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Submission:
        """Create a new submission record."""
        session = self.get_session()
        try:
            submission = Submission(
                planning_case_id=planning_case_id,
                submission_version=submission_version,
                parent_submission_id=parent_submission_id,
                status=status,
                submission_metadata=metadata or {}
            )
            session.add(submission)
            session.commit()
            session.refresh(submission)
            return submission
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
