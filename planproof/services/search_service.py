"""
Search Service: Full-text search across cases, submissions, and documents.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from planproof.db import Database

LOGGER = logging.getLogger(__name__)

from planproof.db import Database


class SearchService:
    """Convenience wrapper for search helpers."""

    def __init__(self, db: Optional["Database"] = None) -> None:
        self._db = db

    def search_applications(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search applications using the shared search helper."""
        return search_cases(
            query=query,
            filters=filters,
            limit=limit,
            offset=offset,
            db=self._db,
        )


def search_cases(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Full-text search across cases and submissions.
    
    Args:
        query: Search query string
        filters: Optional filters (status, date_range, case_ref, etc.)
        limit: Maximum number of results
        offset: Offset for pagination
        db: Optional Database instance
        
    Returns:
        Dictionary with search results and metadata
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Application, Submission, Document, ExtractedField
    from sqlalchemy import or_
    
    session = db.get_session()
    filters = filters or {}
    
    try:
        # Build base query for cases
        case_query = session.query(Application)
        
        # Apply text search on case fields
        if query:
            search_term = f"%{query}%"
            case_query = case_query.filter(
                or_(
                    Application.application_ref.ilike(search_term),
                    Application.applicant_name.ilike(search_term)
                )
            )
        
        # Apply filters
        if filters.get("application_ref"):
            case_query = case_query.filter(Application.application_ref == filters["application_ref"])

        if filters.get("date_from"):
            case_query = case_query.filter(Application.created_at >= filters["date_from"])

        if filters.get("date_to"):
            case_query = case_query.filter(Application.created_at <= filters["date_to"])
        
        # Get total count before pagination
        total_count = case_query.count()
        
        # Apply pagination
        cases = case_query.limit(limit).offset(offset).all()
        
        # Build results
        results = []
        for case in cases:
            # Get latest submission for this application
            latest_submission = session.query(Submission).filter(
                Submission.planning_case_id == case.id
            ).order_by(Submission.created_at.desc()).first()
            
            # Get validation summary for latest submission
            validation_summary = {}
            if latest_submission:
                from planproof.db import ValidationCheck, ValidationStatus
                checks = session.query(ValidationCheck).filter(
                    ValidationCheck.submission_id == latest_submission.id
                ).all()
                
                validation_summary = {
                    "pass": sum(1 for c in checks if c.status == ValidationStatus.PASS),
                    "fail": sum(1 for c in checks if c.status == ValidationStatus.FAIL),
                    "needs_review": sum(1 for c in checks if c.status == ValidationStatus.NEEDS_REVIEW),
                    "total": len(checks)
                }
            
            results.append({
                "application_id": case.id,
                "application_ref": case.application_ref,
                "applicant_name": case.applicant_name,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "latest_submission_id": latest_submission.id if latest_submission else None,
                "latest_submission_version": latest_submission.submission_version if latest_submission else None,
                "validation_summary": validation_summary
            })
        
        return {
            "results": results,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "query": query,
            "filters": filters
        }
    
    finally:
        session.close()


def search_submissions(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Search across submissions.
    
    Args:
        query: Search query string
        filters: Optional filters (case_id, version, status, etc.)
        limit: Maximum number of results
        offset: Offset for pagination
        db: Optional Database instance
        
    Returns:
        Dictionary with search results and metadata
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Submission, Application
    from sqlalchemy import or_
    
    session = db.get_session()
    filters = filters or {}
    
    try:
        # Build base query for submissions
        submission_query = session.query(Submission).join(Application, Submission.planning_case_id == Application.id)
        
        # Apply text search
        if query:
            search_term = f"%{query}%"
            submission_query = submission_query.filter(
                or_(
                    Application.application_ref.ilike(search_term),
                    Application.applicant_name.ilike(search_term),
                    Submission.submission_version.ilike(search_term)
                )
            )
        
        # Apply filters
        if filters.get("application_id"):
            submission_query = submission_query.filter(Submission.planning_case_id == filters["application_id"])
        
        if filters.get("version"):
            submission_query = submission_query.filter(Submission.submission_version == filters["version"])
        
        if filters.get("status"):
            submission_query = submission_query.filter(Submission.status == filters["status"])
        
        # Get total count
        total_count = submission_query.count()
        
        # Apply pagination
        submissions = submission_query.order_by(Submission.created_at.desc()).limit(limit).offset(offset).all()
        
        # Build results
        results = []
        for submission in submissions:
            from planproof.db import ValidationCheck, ValidationStatus
            checks = session.query(ValidationCheck).filter(
                ValidationCheck.submission_id == submission.id
            ).all()
            
            validation_summary = {
                "pass": sum(1 for c in checks if c.status == ValidationStatus.PASS),
                "fail": sum(1 for c in checks if c.status == ValidationStatus.FAIL),
                "needs_review": sum(1 for c in checks if c.status == ValidationStatus.NEEDS_REVIEW),
                "total": len(checks)
            }
            
            results.append({
                "submission_id": submission.id,
                "application_id": submission.planning_case_id,
                "application_ref": submission.planning_case.application_ref if submission.planning_case else None,
                "submission_version": submission.submission_version,
                "status": submission.status,
                "created_at": submission.created_at.isoformat() if submission.created_at else None,
                "validation_summary": validation_summary
            })
        
        return {
            "results": results,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "query": query,
            "filters": filters
        }
    
    finally:
        session.close()


def search_documents(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Search across documents.
    
    Args:
        query: Search query string
        filters: Optional filters (submission_id, document_type, etc.)
        limit: Maximum number of results
        offset: Offset for pagination
        db: Optional Database instance
        
    Returns:
        Dictionary with search results and metadata
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Document, Submission
    from sqlalchemy import or_
    
    session = db.get_session()
    filters = filters or {}
    
    try:
        # Build base query
        doc_query = session.query(Document)
        
        # Apply text search
        if query:
            search_term = f"%{query}%"
            doc_query = doc_query.filter(
                or_(
                    Document.filename.ilike(search_term),
                    Document.document_type.ilike(search_term)
                )
            )
        
        # Apply filters
        if filters.get("submission_id"):
            doc_query = doc_query.filter(Document.submission_id == filters["submission_id"])
        
        if filters.get("document_type"):
            doc_query = doc_query.filter(Document.document_type == filters["document_type"])
        
        # Get total count
        total_count = doc_query.count()
        
        # Apply pagination
        documents = doc_query.order_by(Document.created_at.desc()).limit(limit).offset(offset).all()
        
        # Build results
        results = []
        for doc in documents:
            results.append({
                "document_id": doc.id,
                "submission_id": doc.submission_id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            })
        
        return {
            "results": results,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "query": query,
            "filters": filters
        }
    
    finally:
        session.close()


def search_extracted_fields(
    field_name: Optional[str] = None,
    field_value: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Search extracted fields.
    
    Args:
        field_name: Optional field name to filter
        field_value: Optional field value to search
        filters: Optional filters (submission_id, document_id, etc.)
        limit: Maximum number of results
        offset: Offset for pagination
        db: Optional Database instance
        
    Returns:
        Dictionary with search results
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import ExtractedField
    
    session = db.get_session()
    filters = filters or {}
    
    try:
        # Build base query
        field_query = session.query(ExtractedField)
        
        # Apply filters
        if field_name:
            field_query = field_query.filter(ExtractedField.field_name == field_name)
        
        if field_value:
            search_term = f"%{field_value}%"
            field_query = field_query.filter(ExtractedField.field_value.ilike(search_term))
        
        if filters.get("submission_id"):
            field_query = field_query.filter(ExtractedField.submission_id == filters["submission_id"])
        
        if filters.get("document_id"):
            field_query = field_query.filter(ExtractedField.document_id == filters["document_id"])
        
        # Get total count
        total_count = field_query.count()
        
        # Apply pagination
        fields = field_query.limit(limit).offset(offset).all()
        
        # Build results
        results = []
        for field in fields:
            results.append({
                "field_id": field.id,
                "submission_id": field.submission_id,
                "document_id": field.document_id,
                "field_name": field.field_name,
                "field_value": field.field_value,
                "confidence": field.confidence,
                "created_at": field.created_at.isoformat() if field.created_at else None
            })
        
        return {
            "results": results,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "field_name": field_name,
            "field_value": field_value,
            "filters": filters
        }
    
    finally:
        session.close()
