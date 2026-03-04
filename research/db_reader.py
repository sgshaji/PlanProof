"""Read-only database access layer for the research module.

Imports backend SQLAlchemy models and provides query helpers
to read Stage 3 outputs (extracted fields, documents, evidence,
validation checks) without modifying existing data.
"""

import sys
import os
from typing import Optional
from contextlib import contextmanager

# Add backend to sys.path so we can import its models
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from planproof.db import (
    Base,
    Application,
    Submission,
    Document,
    Page,
    Evidence,
    ExtractedField,
    GeometryFeature,
    SpatialMetric,
    ValidationCheck,
    ValidationResult,
    Artefact,
)

from research.config import ResearchConfig


class DBReader:
    """Read-only access to the PlanProof PostgreSQL database."""

    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        self.engine = create_engine(
            self.config.database_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            echo=False,
        )
        self._Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session(self):
        """Yield a read-only session."""
        sess = self._Session()
        try:
            yield sess
        finally:
            sess.close()

    def get_submission(self, submission_id: int) -> Optional[Submission]:
        """Fetch a single submission by ID."""
        with self.session() as sess:
            return sess.query(Submission).filter_by(id=submission_id).first()

    def get_submissions_for_application(self, application_id: int) -> list[Submission]:
        """Fetch all submissions for an application."""
        with self.session() as sess:
            return (
                sess.query(Submission)
                .filter_by(planning_case_id=application_id)
                .order_by(Submission.created_at)
                .all()
            )

    def get_extracted_fields(self, submission_id: int) -> list[ExtractedField]:
        """Fetch all extracted fields for a submission."""
        with self.session() as sess:
            return (
                sess.query(ExtractedField)
                .filter_by(submission_id=submission_id)
                .all()
            )

    def get_documents(self, submission_id: int) -> list[Document]:
        """Fetch all documents for a submission."""
        with self.session() as sess:
            return (
                sess.query(Document)
                .filter_by(submission_id=submission_id)
                .all()
            )

    def get_pages(self, document_id: int) -> list[Page]:
        """Fetch all pages for a document."""
        with self.session() as sess:
            return (
                sess.query(Page)
                .filter_by(document_id=document_id)
                .order_by(Page.page_number)
                .all()
            )

    def get_evidence_for_document(self, document_id: int) -> list[Evidence]:
        """Fetch all evidence records for a document."""
        with self.session() as sess:
            return (
                sess.query(Evidence)
                .filter_by(document_id=document_id)
                .all()
            )

    def get_evidence_for_field(self, field: ExtractedField) -> Optional[Evidence]:
        """Fetch the evidence linked to an extracted field."""
        if field.evidence_id is None:
            return None
        with self.session() as sess:
            return sess.query(Evidence).filter_by(id=field.evidence_id).first()

    def get_geometry_features(self, submission_id: int) -> list[GeometryFeature]:
        """Fetch geometry features for a submission."""
        with self.session() as sess:
            return (
                sess.query(GeometryFeature)
                .filter_by(submission_id=submission_id)
                .all()
            )

    def get_spatial_metrics(self, geometry_feature_id: int) -> list[SpatialMetric]:
        """Fetch spatial metrics for a geometry feature."""
        with self.session() as sess:
            return (
                sess.query(SpatialMetric)
                .filter_by(geometry_feature_id=geometry_feature_id)
                .all()
            )

    def get_validation_checks(self, submission_id: int) -> list[ValidationCheck]:
        """Fetch validation check results for a submission."""
        with self.session() as sess:
            return (
                sess.query(ValidationCheck)
                .filter_by(submission_id=submission_id)
                .all()
            )

    def get_artefacts(self, document_id: int) -> list[Artefact]:
        """Fetch artefacts for a document."""
        with self.session() as sess:
            return (
                sess.query(Artefact)
                .filter_by(document_id=document_id)
                .all()
            )

    def list_applications(self) -> list[Application]:
        """List all applications."""
        with self.session() as sess:
            return sess.query(Application).order_by(Application.created_at).all()

    def get_application(self, application_id: int) -> Optional[Application]:
        """Fetch a single application by ID."""
        with self.session() as sess:
            return sess.query(Application).filter_by(id=application_id).first()
