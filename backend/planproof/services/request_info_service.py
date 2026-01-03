"""
Request Info Service: Complete workflow for requesting additional information.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import logging
from datetime import datetime

if TYPE_CHECKING:
    from planproof.db import Database

LOGGER = logging.getLogger(__name__)


def create_request_info(
    submission_id: int,
    missing_items: List[str],
    notes: str,
    officer_name: str,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Create a comprehensive request-info action: marks case ON_HOLD, captures missing items.
    
    Args:
        submission_id: Submission ID
        missing_items: List of missing items/documents/clarifications
        notes: Additional notes from officer
        officer_name: Name of requesting officer
        db: Optional Database instance
        
    Returns:
        Dictionary with request info details and exportable checklist
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Submission, Case
    
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {"error": "Submission not found"}
        
        # Get case for reference
        case = session.query(Case).filter(Case.id == submission.case_id).first()
        case_ref = case.case_ref if case else f"SUB-{submission_id}"
        
        # Create request record
        request_record = {
            "request_id": f"REQ-{submission_id}-{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "officer_name": officer_name,
            "status": "pending",
            "missing_items": missing_items,
            "notes": notes,
            "due_date": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + 
                        __import__('datetime').timedelta(days=21)).isoformat()  # 21 days standard
        }
        
        # Update submission status to ON_HOLD
        submission.status = "needs_info"
        
        # Store in metadata
        if not submission.metadata:
            submission.metadata = {}
        
        if "info_requests" not in submission.metadata:
            submission.metadata["info_requests"] = []
        
        submission.metadata["info_requests"].append(request_record)
        
        # Mark submission as on hold
        submission.metadata["on_hold"] = True
        submission.metadata["hold_reason"] = "Awaiting additional information from applicant"
        
        session.commit()
        
        # Generate exportable checklist
        checklist_text = f"""
INFORMATION REQUEST - {case_ref}
{'=' * 60}

Request ID: {request_record['request_id']}
Date: {datetime.now().strftime('%Y-%m-%d')}
Officer: {officer_name}
Due Date: {datetime.fromisoformat(request_record['due_date']).strftime('%Y-%m-%d')}

MISSING ITEMS:
{chr(10).join(f'  [ ] {item}' for item in missing_items)}

ADDITIONAL NOTES:
{notes}

{'=' * 60}
Please provide the above items to continue processing your application.
Contact: planning@example.com
"""
        
        # Generate email template
        email_template = f"""
Subject: Planning Application {case_ref} - Additional Information Required

Dear Applicant,

We have reviewed your planning application {case_ref} and require additional information to complete our assessment.

Required Items:
{chr(10).join(f'• {item}' for item in missing_items)}

Additional Information:
{notes}

Please submit the requested information within 21 days. You can submit via:
- Planning Portal (reference: {case_ref})
- Email to: planning@example.com
- Post to: Planning Department, [Address]

If we do not receive this information by {datetime.fromisoformat(request_record['due_date']).strftime('%d %B %Y')}, your application may be refused.

Requesting Officer: {officer_name}
Reference: {request_record['request_id']}

Best regards,
Planning Department
"""
        
        LOGGER.info(
            "request_info_created",
            extra={
                "submission_id": submission_id,
                "request_id": request_record["request_id"],
                "missing_items_count": len(missing_items),
                "officer_name": officer_name
            }
        )
        
        return {
            "success": True,
            "request_record": request_record,
            "checklist_text": checklist_text,
            "email_template": email_template,
            "submission_status": "needs_info",
            "on_hold": True
        }
    
    finally:
        session.close()


def respond_to_request_info(
    submission_id: int,
    request_id: str,
    response_notes: str,
    documents_provided: Optional[List[str]] = None,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Record applicant response to info request and move case back to in_progress.
    
    Args:
        submission_id: Submission ID
        request_id: Request ID to respond to
        response_notes: Response notes
        documents_provided: List of provided documents
        db: Optional Database instance
        
    Returns:
        Dictionary with response status
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Submission
    
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission or not submission.metadata:
            return {"error": "Submission not found"}
        
        info_requests = submission.metadata.get("info_requests", [])
        
        # Find the request
        request = None
        for req in info_requests:
            if req.get("request_id") == request_id:
                request = req
                break
        
        if not request:
            return {"error": "Request not found"}
        
        # Record response
        request["response"] = {
            "responded_at": datetime.now().isoformat(),
            "notes": response_notes,
            "documents_provided": documents_provided or []
        }
        request["status"] = "responded"
        
        # Move case back to in_progress
        submission.status = "in_progress"
        submission.metadata["on_hold"] = False
        submission.metadata["hold_reason"] = None
        
        session.commit()
        
        LOGGER.info(
            "request_info_responded",
            extra={
                "submission_id": submission_id,
                "request_id": request_id,
                "documents_count": len(documents_provided) if documents_provided else 0
            }
        )
        
        return {
            "success": True,
            "submission_status": "in_progress",
            "on_hold": False,
            "request": request
        }
    
    finally:
        session.close()


def get_active_requests(
    submission_id: int,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Get active (pending) info requests for a submission.
    
    Args:
        submission_id: Submission ID
        db: Optional Database instance
        
    Returns:
        List of active requests
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Submission
    
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission or not submission.metadata:
            return []
        
        info_requests = submission.metadata.get("info_requests", [])
        
        # Filter for pending requests
        active = [req for req in info_requests if req.get("status") == "pending"]
        
        return active
    
    finally:
        session.close()
