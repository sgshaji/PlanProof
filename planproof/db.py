"""
Database helpers and table definitions for PostgreSQL with PostGIS.
"""

from datetime import datetime
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


class ValidationStatus(str, Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"


class Application(Base):
    """Planning application record."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_ref = Column(String(100), unique=True, nullable=False, index=True)
    applicant_name = Column(String(255))
    application_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")


class Document(Base):
    """Document record (PDFs uploaded for processing)."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    blob_uri = Column(String(500), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    page_count = Column(Integer, nullable=True)
    docintel_model = Column(String(50), nullable=True)  # e.g., "prebuilt-layout"

    # Relationships
    application = relationship("Application", back_populates="documents")
    artefacts = relationship("Artefact", back_populates="document", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="document", cascade="all, delete-orphan")


class Artefact(Base):
    """Extracted JSON artefacts from document processing."""
    __tablename__ = "artefacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    artefact_type = Column(String(50), nullable=False)  # e.g., "extracted_layout", "structured_data"
    blob_uri = Column(String(500), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, nullable=True)  # Additional metadata about the artefact

    # Relationships
    document = relationship("Document", back_populates="artefacts")


class ValidationResult(Base):
    """Validation results for extracted fields."""
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="validation_results")


class Run(Base):
    """Audit trail for processing runs (optional but recommended)."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(50), nullable=False)  # e.g., "ingest", "extract", "validate", "llm_gate"
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional run context


class Database:
    """Database helper class for common operations."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Create all tables (use Alembic for migrations in production)."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def execute_raw(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query and return results as dictionaries.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of result dictionaries
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params or {})
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
        docintel_model: Optional[str] = None
    ) -> Document:
        """Create a new document record."""
        session = self.get_session()
        try:
            doc = Document(
                application_id=application_id,
                blob_uri=blob_uri,
                filename=filename,
                page_count=page_count,
                docintel_model=docintel_model
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

