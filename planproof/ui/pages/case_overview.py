"""
Case Overview page - Display case metadata, submission versions, and validation status.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from planproof.db import Database, Application, Submission, ValidationCheck, ChangeSet
from planproof.ui.run_orchestrator import get_run_results


def get_case_overview(application_ref: str, db: Optional[Database] = None) -> Dict[str, Any]:
    """
    Get case overview data including all submissions and their validation status.
    
    Args:
        application_ref: Application reference
        db: Optional Database instance
    
    Returns:
        Dict with case metadata and submission list
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        # Get application
        application = session.query(Application).filter(
            Application.application_ref == application_ref
        ).first()
        
        if not application:
            return {"error": f"Application {application_ref} not found"}
        
        # Get all submissions for this application
        submissions = session.query(Submission).filter(
            Submission.planning_case_id == application.id
        ).order_by(Submission.submission_version).all()
        
        submission_data = []
        
        for sub in submissions:
            # Get validation summary
            validation_checks = session.query(ValidationCheck).filter(
                ValidationCheck.submission_id == sub.id
            ).all()
            
            pass_count = sum(1 for v in validation_checks if v.status.value == "pass")
            fail_count = sum(1 for v in validation_checks if v.status.value == "fail")
            review_count = sum(1 for v in validation_checks if v.status.value == "needs_review")
            
            # Get changeset if modification
            changeset = None
            if sub.submission_version != "V0":
                changeset = session.query(ChangeSet).filter(
                    ChangeSet.submission_id == sub.id
                ).first()
            
            submission_data.append({
                "submission_id": sub.id,
                "version": sub.submission_version,
                "status": sub.status,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "parent_submission_id": sub.parent_submission_id,
                "validation_summary": {
                    "pass": pass_count,
                    "fail": fail_count,
                    "needs_review": review_count,
                    "total": len(validation_checks)
                },
                "changeset": {
                    "changeset_id": changeset.id if changeset else None,
                    "significance_score": changeset.significance_score if changeset else None,
                    "requires_validation": changeset.requires_validation if changeset else None
                } if changeset else None
            })
        
        return {
            "application_id": application.id,
            "application_ref": application.application_ref,
            "applicant_name": application.applicant_name,
            "application_date": application.application_date.isoformat() if application.application_date else None,
            "case_type": application.case_type,
            "status": application.status,
            "created_at": application.created_at.isoformat() if application.created_at else None,
            "submissions": submission_data
        }
    
    finally:
        session.close()


def render():
    """Render the case overview page."""
    st.title("📁 Case & Submission Overview")
    
    st.markdown("View case history, submission versions, and validation status.")
    
    # Search input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        app_ref_input = st.text_input(
            "Application Reference",
            placeholder="APP/2024/001 or PP-14469287",
            help="Enter the planning application reference"
        )
    
    with col2:
        search_button = st.button("🔍 Search", type="primary")
    
    if not app_ref_input:
        st.info("Enter an application reference to view case overview.")
        return
    
    if not search_button and "last_app_ref" not in st.session_state:
        return
    
    # Store last searched ref
    if search_button:
        st.session_state["last_app_ref"] = app_ref_input
    
    app_ref = st.session_state.get("last_app_ref", app_ref_input)
    
    # Fetch case overview
    with st.spinner("Loading case overview..."):
        overview = get_case_overview(app_ref)
    
    if "error" in overview:
        st.error(overview["error"])
        return
    
    # Display case metadata
    st.markdown("---")
    st.markdown("## Case Metadata")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Application Ref", overview["application_ref"])
        st.metric("Case Type", overview.get("case_type", "N/A"))
    
    with col2:
        st.metric("Applicant", overview.get("applicant_name", "N/A"))
        st.metric("Status", overview.get("status", "N/A"))
    
    with col3:
        st.metric("Application Date", overview.get("application_date", "N/A")[:10] if overview.get("application_date") else "N/A")
        st.metric("Submissions", len(overview["submissions"]))
    
    # Display submissions
    st.markdown("---")
    st.markdown("## Submission History")
    
    submissions = overview["submissions"]
    
    if not submissions:
        st.info("No submissions found for this application.")
        return
    
    for sub in submissions:
        version = sub["version"]
        status = sub["status"]
        val_summary = sub["validation_summary"]
        changeset = sub.get("changeset")
        
        # Create expander for each submission
        with st.expander(
            f"📄 {version} - {status.upper()} "
            f"(✅ {val_summary['pass']} | ⚠️ {val_summary['needs_review']} | ❌ {val_summary['fail']})",
            expanded=(version == "V0")
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Submission ID:** {sub['submission_id']}")
                st.markdown(f"**Version:** {version}")
                st.markdown(f"**Status:** {status}")
                st.markdown(f"**Created:** {sub['created_at'][:19] if sub['created_at'] else 'N/A'}")
                
                if sub['parent_submission_id']:
                    st.markdown(f"**Parent Submission:** {sub['parent_submission_id']}")
            
            with col2:
                st.markdown("**Validation Summary:**")
                st.markdown(f"- ✅ Pass: {val_summary['pass']}")
                st.markdown(f"- ⚠️ Needs Review: {val_summary['needs_review']}")
                st.markdown(f"- ❌ Fail: {val_summary['fail']}")
                st.markdown(f"- Total Checks: {val_summary['total']}")
            
            # Show changeset info for modifications
            if changeset:
                st.markdown("---")
                st.markdown("**Modification Delta:**")
                col_delta1, col_delta2, col_delta3 = st.columns(3)
                
                with col_delta1:
                    st.metric("ChangeSet ID", changeset['changeset_id'])
                
                with col_delta2:
                    significance = changeset['significance_score']
                    st.metric(
                        "Significance",
                        f"{significance:.2f}" if significance is not None else "N/A",
                        delta=None,
                        help="0.0 = no change, 1.0 = major change"
                    )
                
                with col_delta3:
                    st.metric("Revalidation", changeset['requires_validation'])
                
                # Link to delta view (future feature)
                if st.button(f"View Delta Details", key=f"delta_{sub['submission_id']}"):
                    st.info("Delta detail view coming soon...")
            
            # Action buttons
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button(f"📋 View Validation Results", key=f"results_{sub['submission_id']}"):
                    # Find run_id for this submission (would need to query runs table)
                    st.info("Validation results view - integrate with results page")
            
            with col_btn2:
                if st.button(f"📄 View Documents", key=f"docs_{sub['submission_id']}"):
                    st.info("Document list view coming soon...")
            
            with col_btn3:
                if st.button(f"🔍 View Extracted Fields", key=f"fields_{sub['submission_id']}"):
                    st.info("Fields viewer coming soon (To-Do #9)...")
    
    # Summary statistics
    st.markdown("---")
    st.markdown("## Summary Statistics")
    
    total_checks = sum(s["validation_summary"]["total"] for s in submissions)
    total_pass = sum(s["validation_summary"]["pass"] for s in submissions)
    total_fail = sum(s["validation_summary"]["fail"] for s in submissions)
    total_review = sum(s["validation_summary"]["needs_review"] for s in submissions)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Checks", total_checks)
    
    with col2:
        st.metric("Pass", total_pass)
    
    with col3:
        st.metric("Needs Review", total_review)
    
    with col4:
        st.metric("Fail", total_fail)

