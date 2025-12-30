"""
Notification Service: Handle email notifications for request-info workflow.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import logging
from datetime import datetime

if TYPE_CHECKING:
    from planproof.db import Database

LOGGER = logging.getLogger(__name__)


def send_request_info_notification(
    submission_id: int,
    case_ref: str,
    applicant_email: Optional[str],
    request_details: str,
    officer_name: str,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Send email notification for request-info workflow.
    
    Args:
        submission_id: Submission ID
        case_ref: Case reference number
        applicant_email: Applicant email address
        request_details: Details of what information is requested
        officer_name: Name of requesting officer
        db: Optional Database instance
        
    Returns:
        Dictionary with notification status
    """
    if not applicant_email:
        LOGGER.warning(f"No applicant email for submission {submission_id}, cannot send notification")
        return {
            "sent": False,
            "error": "No applicant email address available"
        }
    
    # In MVP, log the notification (actual email sending requires SMTP/SendGrid setup)
    notification = {
        "to": applicant_email,
        "subject": f"Planning Application {case_ref} - Additional Information Required",
        "body": f"""
Dear Applicant,

We have reviewed your planning application {case_ref} and require additional information to proceed with the assessment.

Required Information:
{request_details}

Please submit the requested information through the planning portal or contact us directly.

Requesting Officer: {officer_name}
Date: {datetime.now().strftime('%Y-%m-%d')}

Best regards,
Planning Department
""",
        "sent_at": datetime.now().isoformat(),
        "submission_id": submission_id
    }
    
    # Log notification
    LOGGER.info(
        "request_info_notification",
        extra={
            "submission_id": submission_id,
            "case_ref": case_ref,
            "applicant_email": applicant_email,
            "officer_name": officer_name
        }
    )
    
    # Store notification record in database
    if db:
        from planproof.db import Submission
        session = db.get_session()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                # Update metadata with notification info
                if not submission.metadata:
                    submission.metadata = {}
                
                if "notifications" not in submission.metadata:
                    submission.metadata["notifications"] = []
                
                submission.metadata["notifications"].append({
                    "type": "request_info",
                    "sent_at": notification["sent_at"],
                    "to": applicant_email,
                    "subject": notification["subject"],
                    "officer": officer_name
                })
                
                session.commit()
        finally:
            session.close()
    
    # TODO: Integrate with actual email service (SMTP, SendGrid, etc.)
    # For now, return success status with logged notification
    return {
        "sent": True,
        "notification": notification,
        "note": "Notification logged (email sending not yet configured)"
    }


def send_status_update_notification(
    submission_id: int,
    case_ref: str,
    applicant_email: Optional[str],
    new_status: str,
    officer_name: str,
    notes: Optional[str] = None,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Send email notification for status updates.
    
    Args:
        submission_id: Submission ID
        case_ref: Case reference number
        applicant_email: Applicant email address
        new_status: New status (approved, rejected, etc.)
        officer_name: Name of officer
        notes: Optional notes to include
        db: Optional Database instance
        
    Returns:
        Dictionary with notification status
    """
    if not applicant_email:
        LOGGER.warning(f"No applicant email for submission {submission_id}, cannot send notification")
        return {
            "sent": False,
            "error": "No applicant email address available"
        }
    
    status_messages = {
        "approved": "Your planning application has been approved.",
        "rejected": "Your planning application has been rejected.",
        "needs_info": "Additional information is required for your planning application.",
        "in_progress": "Your planning application is currently being reviewed."
    }
    
    status_message = status_messages.get(new_status, f"Status updated to: {new_status}")
    
    notification = {
        "to": applicant_email,
        "subject": f"Planning Application {case_ref} - Status Update",
        "body": f"""
Dear Applicant,

{status_message}

Application Reference: {case_ref}
New Status: {new_status}
{"Notes: " + notes if notes else ""}

Officer: {officer_name}
Date: {datetime.now().strftime('%Y-%m-%d')}

Best regards,
Planning Department
""",
        "sent_at": datetime.now().isoformat(),
        "submission_id": submission_id
    }
    
    LOGGER.info(
        "status_update_notification",
        extra={
            "submission_id": submission_id,
            "case_ref": case_ref,
            "new_status": new_status,
            "applicant_email": applicant_email,
            "officer_name": officer_name
        }
    )
    
    # Store notification record
    if db:
        from planproof.db import Submission
        session = db.get_session()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                if not submission.metadata:
                    submission.metadata = {}
                
                if "notifications" not in submission.metadata:
                    submission.metadata["notifications"] = []
                
                submission.metadata["notifications"].append({
                    "type": "status_update",
                    "sent_at": notification["sent_at"],
                    "to": applicant_email,
                    "subject": notification["subject"],
                    "status": new_status,
                    "officer": officer_name
                })
                
                session.commit()
        finally:
            session.close()
    
    return {
        "sent": True,
        "notification": notification,
        "note": "Notification logged (email sending not yet configured)"
    }


def get_notification_history(
    submission_id: int,
    db: Optional[Database] = None
) -> List[Dict[str, Any]]:
    """
    Get notification history for a submission.
    
    Args:
        submission_id: Submission ID
        db: Optional Database instance
        
    Returns:
        List of notifications
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
        
        notifications = submission.metadata.get("notifications", [])
        return notifications
    
    finally:
        session.close()


def track_applicant_response(
    submission_id: int,
    response_details: str,
    documents_uploaded: Optional[List[str]] = None,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Track applicant response to request-info.
    
    Args:
        submission_id: Submission ID
        response_details: Details of applicant response
        documents_uploaded: Optional list of uploaded document names
        db: Optional Database instance
        
    Returns:
        Dictionary with tracking status
    """
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import Submission
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(Submission.id == submission_id).first()
        
        if not submission:
            return {"error": "Submission not found"}
        
        # Update metadata with response
        if not submission.metadata:
            submission.metadata = {}
        
        if "applicant_responses" not in submission.metadata:
            submission.metadata["applicant_responses"] = []
        
        response_record = {
            "received_at": datetime.now().isoformat(),
            "details": response_details,
            "documents": documents_uploaded or []
        }
        
        submission.metadata["applicant_responses"].append(response_record)
        
        # Update status back to in_progress
        submission.status = "in_progress"
        
        session.commit()
        
        LOGGER.info(
            "applicant_response_tracked",
            extra={
                "submission_id": submission_id,
                "response_details": response_details,
                "document_count": len(documents_uploaded) if documents_uploaded else 0
            }
        )
        
        return {
            "success": True,
            "submission_id": submission_id,
            "status_updated": "in_progress",
            "response": response_record
        }
    
    finally:
        session.close()
