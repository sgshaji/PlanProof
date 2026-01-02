"""
Human-in-Loop Review Endpoints
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from planproof.api.dependencies import get_db, get_current_user
from planproof.db import Database, Run, ValidationCheck, ReviewDecision
from planproof.db import utcnow

router = APIRouter()


class ReviewDecisionRequest(BaseModel):
    """Request to submit a review decision."""
    decision: str  # accept, reject, need_info
    comment: Optional[str] = None
    reviewer_id: str


class ReviewDecisionResponse(BaseModel):
    """Response after submitting review."""
    review_id: int
    validation_check_id: int
    decision: str
    reviewed_at: str
    message: str


class ReviewStatusResponse(BaseModel):
    """Review status for a run."""
    run_id: int
    total_findings: int
    reviewed_count: int
    pending_count: int
    decisions: List[dict]


@router.post("/runs/{run_id}/findings/{check_id}/review")
async def submit_review_decision(
    run_id: int,
    check_id: int,
    request: ReviewDecisionRequest,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> ReviewDecisionResponse:
    """
    Submit a Human-in-Loop review decision for a validation finding.
    
    **Path Parameters:**
    - run_id: Run ID
    - check_id: ValidationCheck ID
    
    **Request Body:**
    ```json
    {
        "decision": "accept|reject|need_info",
        "comment": "Optional explanation",
        "reviewer_id": "officer@council.gov"
    }
    ```
    """
    session = db.get_session()
    try:
        # Validate run exists
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Validate check exists and belongs to this run
        check = session.query(ValidationCheck).filter(
            ValidationCheck.id == check_id
        ).first()
        if not check:
            raise HTTPException(status_code=404, detail="Validation check not found")
        
        # Validate decision value
        if request.decision not in ["accept", "reject", "need_info"]:
            raise HTTPException(
                status_code=400,
                detail="Decision must be one of: accept, reject, need_info"
            )
        
        # Check if already reviewed
        existing = session.query(ReviewDecision).filter(
            ReviewDecision.validation_check_id == check_id
        ).first()
        
        if existing:
            # Update existing review
            existing.decision = request.decision
            existing.comment = request.comment
            existing.reviewer_id = request.reviewer_id
            existing.reviewed_at = utcnow()
            session.commit()
            review_id = existing.id
        else:
            # Create new review decision
            review = ReviewDecision(
                validation_check_id=check_id,
                run_id=run_id,
                reviewer_id=request.reviewer_id,
                decision=request.decision,
                comment=request.comment,
                reviewed_at=utcnow()
            )
            session.add(review)
            session.commit()
            session.refresh(review)
            review_id = review.id
        
        return ReviewDecisionResponse(
            review_id=review_id,
            validation_check_id=check_id,
            decision=request.decision,
            reviewed_at=datetime.utcnow().isoformat(),
            message="Review decision saved successfully"
        )
    finally:
        session.close()


@router.get("/runs/{run_id}/review-status")
async def get_review_status(
    run_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
) -> ReviewStatusResponse:
    """
    Get review status for a run - how many findings reviewed vs pending.
    
    **Path Parameters:**
    - run_id: Run ID
    
    **Returns:**
    - Total findings needing review
    - Count of reviewed findings
    - Count of pending findings
    - List of decisions made
    """
    session = db.get_session()
    try:
        # Validate run exists
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get all validation checks that need review for this run's document
        checks_needing_review = []
        if run.document_id:
            checks_needing_review = session.query(ValidationCheck).filter(
                ValidationCheck.document_id == run.document_id,
                ValidationCheck.status == 'needs_review'
            ).all()
        
        total_findings = len(checks_needing_review)
        
        # Get all review decisions for this run
        decisions = session.query(ReviewDecision).filter(
            ReviewDecision.run_id == run_id
        ).all()
        
        reviewed_count = len(decisions)
        pending_count = total_findings - reviewed_count
        
        # Format decisions
        decision_list = []
        for decision in decisions:
            check = session.query(ValidationCheck).filter(
                ValidationCheck.id == decision.validation_check_id
            ).first()
            
            decision_list.append({
                "review_id": decision.id,
                "validation_check_id": decision.validation_check_id,
                "rule_id": check.rule_id_string if check else None,
                "decision": decision.decision,
                "comment": decision.comment,
                "reviewer_id": decision.reviewer_id,
                "reviewed_at": decision.reviewed_at.isoformat() if decision.reviewed_at else None
            })
        
        return ReviewStatusResponse(
            run_id=run_id,
            total_findings=total_findings,
            reviewed_count=reviewed_count,
            pending_count=pending_count,
            decisions=decision_list
        )
    finally:
        session.close()


@router.post("/runs/{run_id}/complete-review")
async def complete_review(
    run_id: int,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Mark a run as fully reviewed after all findings have been addressed.
    
    **Path Parameters:**
    - run_id: Run ID
    
    **Effects:**
    - Updates run status to 'reviewed'
    - Sets completed_at timestamp
    - Triggers report generation (future)
    
    **Requirements:**
    - All findings with status 'needs_review' must have a review decision
    """
    session = db.get_session()
    try:
        # Validate run exists
        run = session.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Check if already reviewed
        if run.status == "reviewed":
            raise HTTPException(
                status_code=400,
                detail="Run has already been marked as reviewed"
            )
        
        # Get findings needing review
        checks_needing_review = []
        if run.document_id:
            checks_needing_review = session.query(ValidationCheck).filter(
                ValidationCheck.document_id == run.document_id,
                ValidationCheck.status == 'needs_review'
            ).all()
        
        total_findings = len(checks_needing_review)
        
        # Get review decisions
        decisions = session.query(ReviewDecision).filter(
            ReviewDecision.run_id == run_id
        ).all()
        
        reviewed_count = len(decisions)
        
        # Ensure all findings have been reviewed
        if reviewed_count < total_findings:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete review: {total_findings - reviewed_count} findings still pending review"
            )
        
        # Update run status
        run.status = "reviewed"
        if not run.completed_at:
            run.completed_at = utcnow()
        
        session.commit()
        
        # TODO: Trigger report generation here
        
        return {
            "run_id": run_id,
            "status": "reviewed",
            "reviewed_findings": reviewed_count,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "message": "Review completed successfully. Report generation initiated."
        }
    finally:
        session.close()
