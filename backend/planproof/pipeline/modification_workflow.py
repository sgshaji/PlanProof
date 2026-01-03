"""
Modification workflow - handles V1+ submissions with auto-delta and revalidation.
"""

import logging
from typing import Dict, Any, Optional, List

from planproof.db import Database, Submission
from planproof.services.delta_service import compute_changeset
from planproof.pipeline.validate import validate_modification_submission, load_rule_catalog

LOGGER = logging.getLogger(__name__)


def process_modification_submission(
    submission_id: int,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Process a modification submission (V1+) with auto-delta and targeted revalidation.
    
    This is the main entry point for modification workflow:
    1. Verify submission is V1+
    2. Compute delta (if not already done)
    3. Run targeted revalidation on impacted rules
    
    Args:
        submission_id: V1+ submission ID
        db: Optional Database instance
    
    Returns:
        Dict with delta and validation results
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        # Get submission
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {"error": f"Submission {submission_id} not found"}
        
        if submission.submission_version == "V0":
            return {"error": "Not a modification submission (V0)"}
        
        if not submission.parent_submission_id:
            return {"error": "Missing parent_submission_id"}
        
        # Check if delta already computed
        from planproof.db import ChangeSet
        changeset = session.query(ChangeSet).filter(
            ChangeSet.submission_id == submission_id
        ).first()
        
        changeset_id = None
        
        if not changeset:
            LOGGER.info(f"Computing delta for submission {submission_id}")
            
            # Compute delta
            try:
                changeset_id = compute_changeset(
                    v0_submission_id=submission.parent_submission_id,
                    v1_submission_id=submission_id,
                    db=db
                )
                LOGGER.info(f"Delta computed: ChangeSet {changeset_id}")
            
            except Exception as e:
                LOGGER.error(f"Delta computation failed: {str(e)}")
                return {
                    "error": f"Delta computation failed: {str(e)}",
                    "submission_id": submission_id
                }
        else:
            changeset_id = changeset.id
            LOGGER.info(f"Delta already exists: ChangeSet {changeset_id}")
        
        # Load rules
        rules = load_rule_catalog()
        
        # Run targeted revalidation
        LOGGER.info(f"Running targeted revalidation for submission {submission_id}")
        
        validation_result = validate_modification_submission(
            submission_id=submission_id,
            rules=rules,
            db=db
        )
        
        return {
            "submission_id": submission_id,
            "changeset_id": changeset_id,
            "validation": validation_result,
            "status": "complete"
        }
    
    finally:
        session.close()


def trigger_modification_workflow_if_needed(
    submission_id: int,
    db: Optional[Database] = None
) -> Optional[Dict[str, Any]]:
    """
    Auto-trigger modification workflow if submission is V1+.
    Called after submission creation/ingestion.
    
    Guardrails:
    - Submission must be V1+ (not V0)
    - Parent submission must exist
    - Extraction must be complete
    
    Args:
        submission_id: Submission ID
        db: Optional Database instance
    
    Returns:
        Workflow result or None if not applicable
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            LOGGER.warning(f"Submission {submission_id} not found")
            return None
        
        # Guardrail: Only for V1+
        if submission.submission_version == "V0":
            return None
        
        # Guardrail: Must have parent
        if not submission.parent_submission_id:
            LOGGER.warning(f"Submission {submission_id} is V1+ but missing parent_submission_id")
            submission.status = "needs_review"
            session.commit()
            return None
        
        # Guardrail: Parent must exist
        parent = session.query(Submission).filter(Submission.id == submission.parent_submission_id).first()
        if not parent:
            LOGGER.error(f"Parent submission {submission.parent_submission_id} not found")
            submission.status = "needs_review"
            session.commit()
            return None
        
        # Guardrail: Extraction must be complete (check if documents exist)
        from planproof.db import Document
        docs = session.query(Document).filter(Document.submission_id == submission_id).all()
        
        if not docs:
            LOGGER.info(f"Submission {submission_id} has no documents yet, deferring modification workflow")
            return None
        
        LOGGER.info(f"Auto-triggering modification workflow for submission {submission_id}")
        
        # All guardrails passed - process modification
        result = process_modification_submission(submission_id, db)
        
        return result
    
    except Exception as e:
        LOGGER.error(f"Error in modification workflow trigger: {str(e)}")
        return {"error": str(e)}
    
    finally:
        session.close()

