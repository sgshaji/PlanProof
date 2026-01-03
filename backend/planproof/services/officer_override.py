"""
Officer override service - manage validation overrides with audit trail.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from planproof.db import Database, OfficerOverride

LOGGER = logging.getLogger(__name__)


def create_override(
    validation_result_id: Optional[int],
    validation_check_id: Optional[int],
    original_status: str,
    override_status: str,
    notes: str,
    officer_id: str,
    run_id: Optional[int] = None,
    db: Optional[Database] = None
) -> int:
    """
    Create an officer override for a validation result.
    
    Args:
        validation_result_id: ID of ValidationResult being overridden (optional)
        validation_check_id: ID of ValidationCheck being overridden (optional)
        original_status: Original system status (pass, fail, needs_review)
        override_status: Officer's override status (pass, fail, needs_review)
        notes: Mandatory explanation for override
        officer_id: User identifier of officer making override
        run_id: Optional run ID for context
        db: Optional Database instance
    
    Returns:
        override_id: ID of created override record
    
    Raises:
        ValueError: If notes is empty or invalid status values
    """
    if not notes or not notes.strip():
        raise ValueError("Notes are mandatory for officer overrides")
    
    if original_status not in ["pass", "fail", "needs_review", "pending"]:
        raise ValueError(f"Invalid original_status: {original_status}")
    
    if override_status not in ["pass", "fail", "needs_review"]:
        raise ValueError(f"Invalid override_status: {override_status}")
    
    if not validation_result_id and not validation_check_id:
        raise ValueError("Either validation_result_id or validation_check_id must be provided")
    
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        override = OfficerOverride(
            run_id=run_id,
            validation_result_id=validation_result_id,
            validation_check_id=validation_check_id,
            original_status=original_status,
            override_status=override_status,
            notes=notes.strip(),
            officer_id=officer_id
        )
        
        session.add(override)
        session.commit()
        session.refresh(override)
        
        override_id = override.override_id
        
        LOGGER.info(
            f"Override created: ID={override_id}, officer={officer_id}, "
            f"original={original_status}, override={override_status}"
        )
        
        return override_id
    
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error creating override: {str(e)}")
        raise
    
    finally:
        session.close()


def get_override_history(
    validation_result_id: Optional[int] = None,
    validation_check_id: Optional[int] = None,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Get override history for a validation result or check.
    
    Args:
        validation_result_id: ID of ValidationResult (optional)
        validation_check_id: ID of ValidationCheck (optional)
        db: Optional Database instance
    
    Returns:
        List of override records as dicts
    """
    if not validation_result_id and not validation_check_id:
        return []
    
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        query = session.query(OfficerOverride)
        
        if validation_result_id:
            query = query.filter(OfficerOverride.validation_result_id == validation_result_id)
        
        if validation_check_id:
            query = query.filter(OfficerOverride.validation_check_id == validation_check_id)
        
        overrides = query.order_by(OfficerOverride.created_at.desc()).all()
        
        return [
            {
                "override_id": o.override_id,
                "run_id": o.run_id,
                "validation_result_id": o.validation_result_id,
                "validation_check_id": o.validation_check_id,
                "original_status": o.original_status,
                "override_status": o.override_status,
                "notes": o.notes,
                "officer_id": o.officer_id,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in overrides
        ]
    
    finally:
        session.close()


def get_overrides_by_officer(
    officer_id: str,
    limit: int = 100,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Get all overrides made by a specific officer.
    
    Args:
        officer_id: User identifier
        limit: Maximum number of records to return
        db: Optional Database instance
    
    Returns:
        List of override records as dicts
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        overrides = session.query(OfficerOverride).filter(
            OfficerOverride.officer_id == officer_id
        ).order_by(
            OfficerOverride.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "override_id": o.override_id,
                "run_id": o.run_id,
                "validation_result_id": o.validation_result_id,
                "validation_check_id": o.validation_check_id,
                "original_status": o.original_status,
                "override_status": o.override_status,
                "notes": o.notes,
                "officer_id": o.officer_id,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in overrides
        ]
    
    finally:
        session.close()

