"""
My Cases Page - List all applications with version tracking and delta support.
"""

import streamlit as st
import time
from typing import List, Dict, Any
from planproof.db import Database, Application, Submission
from planproof.ui.ui_components import render_status_badge, render_version_badge
from datetime import datetime


def get_all_cases(page: int = 1, page_size: int = 20) -> tuple[List[Dict[str, Any]], int]:
    """
    Fetch all applications with their latest submissions.

    Args:
        page: Page number (1-indexed)
        page_size: Number of cases per page

    Returns:
        tuple: (list of cases, total count)
    """
    db = Database()
    session = db.get_session()

    try:
        query = session.query(Application).order_by(Application.created_at.desc())
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        applications = query.limit(page_size).offset(offset).all()
        
        cases = []
        for app in applications:
            # Get latest submission
            latest_submission = session.query(Submission).filter(
                Submission.planning_case_id == app.id
            ).order_by(Submission.submission_version.desc()).first()
            
            if not latest_submission:
                continue
            
            # Get parent submission if exists
            parent_ref = None
            parent_version = None
            is_modification = False
            
            if latest_submission.parent_submission_id:
                parent_submission = session.query(Submission).filter(
                    Submission.id == latest_submission.parent_submission_id
                ).first()
                
                if parent_submission:
                    parent_version = parent_submission.submission_version
                    parent_ref = f"{app.application_ref}-{parent_version}"
                    is_modification = True
            
            # Count issues and warnings
            from planproof.db import ValidationCheck, ValidationStatus
            validation_checks = session.query(ValidationCheck).filter(
                ValidationCheck.submission_id == latest_submission.id
            ).all()
            
            issues = sum(1 for v in validation_checks if v.status == ValidationStatus.FAIL)
            warnings = sum(1 for v in validation_checks if v.status == ValidationStatus.NEEDS_REVIEW)
            
            # Determine status
            if latest_submission.status == "completed":
                if issues > 0:
                    status = "Issues Found"
                elif warnings > 0:
                    status = "In Review"
                else:
                    status = "Complete"
            else:
                status = "Processing"
            
            # Get latest run_id for this submission
            from planproof.db import Run
            latest_run = session.query(Run).filter(
                Run.application_id == app.id
            ).order_by(Run.created_at.desc()).first()

            run_id = latest_run.id if latest_run else None

            # Count changes if modification
            changes_count = {"fields": 0, "documents": 0}
            if is_modification:
                from planproof.db import ChangeSet, ChangeItem
                changeset = session.query(ChangeSet).filter(
                    ChangeSet.submission_id == latest_submission.id
                ).first()
                
                if changeset:
                    change_items = session.query(ChangeItem).filter(
                        ChangeItem.change_set_id == changeset.id
                    ).all()
                    
                    changes_count['fields'] = sum(1 for c in change_items if c.change_type == 'field_delta')
                    changes_count['documents'] = sum(1 for c in change_items if c.change_type == 'document_delta')
            
            cases.append({
                'id': app.id,
                'ref': app.application_ref,
                'version': latest_submission.submission_version,
                'display_ref': f"{app.application_ref}-{latest_submission.submission_version}",
                'parent_ref': parent_ref,
                'applicant': app.applicant_name or "Unknown",
                'status': status,
                'date': latest_submission.created_at.strftime('%Y-%m-%d') if latest_submission.created_at else "N/A",
                'original_date': app.created_at.strftime('%Y-%m-%d') if app.created_at else "N/A",
                'issues': issues,
                'warnings': warnings,
                'is_modification': is_modification,
                'changes_count': changes_count,
                'submission_id': latest_submission.id,
                'run_id': run_id  # Add run_id to case data
            })


        return cases, total_count

    finally:
        session.close()


def render():
    """Render the My Cases page."""

    # Initialize pagination
    if "cases_page" not in st.session_state:
        st.session_state.cases_page = 1
    if "cases_status_filter" not in st.session_state:
        st.session_state.cases_status_filter = "all"

    # Search and filters
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="🔍 Search by application reference or applicant name...",
            label_visibility="collapsed",
            key="case_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["all", "Complete", "Issues Found", "In Review", "Processing"],
            key="case_status_filter_select"
        )

    with col3:
        sort_by = st.selectbox(
            "Sort By",
            options=["Date (Newest)", "Date (Oldest)", "Reference A-Z", "Reference Z-A"],
            key="case_sort"
        )

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    # Fetch cases with pagination
    page_size = 20
    with st.spinner("Loading cases..."):
        cases, total_count = get_all_cases(page=st.session_state.cases_page, page_size=page_size)
    
    if not cases:
        st.markdown("""
        <div style="
            text-align: center;
            padding: 64px 24px;
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        ">
            <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
            <h3 style="color: #111827; margin-bottom: 8px;">No Applications Yet</h3>
            <p style="color: #6b7280;">Upload your first planning application to get started</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filter cases by search query
    if search_query:
        cases = [
            c for c in cases
            if search_query.lower() in c['ref'].lower()
            or search_query.lower() in c['applicant'].lower()
        ]

    # Filter by status
    if status_filter != "all":
        cases = [c for c in cases if c['status'] == status_filter]

    # Apply sorting
    if sort_by == "Date (Newest)":
        cases.sort(key=lambda x: x['date'], reverse=True)
    elif sort_by == "Date (Oldest)":
        cases.sort(key=lambda x: x['date'])
    elif sort_by == "Reference A-Z":
        cases.sort(key=lambda x: x['ref'])
    elif sort_by == "Reference Z-A":
        cases.sort(key=lambda x: x['ref'], reverse=True)
    
    # Display cases using native Streamlit components
    for case in cases:
        # Use container with border
        with st.container():
            # Create case card with columns
            col_main, col_actions = st.columns([3, 1])
            
            with col_main:
                # Title row with better visual distinction
                title_col1, title_col2, title_col3, title_col4 = st.columns([2, 1, 1, 0.5])
                
                with title_col1:
                    # Add icon to distinguish between new and modification
                    if case['is_modification']:
                        st.markdown(f"### 🔄 {case['display_ref']}")
                    else:
                        st.markdown(f"### 📋 {case['display_ref']}")
                
                with title_col2:
                    # Status badge
                    status_colors = {
                        'Complete': '🟢',
                        'Issues Found': '🔴',
                        'In Review': '🔵',
                        'Processing': '🟠'
                    }
                    st.markdown(f"{status_colors.get(case['status'], '⚪')} **{case['status']}**")
                
                with title_col3:
                    if case['is_modification']:
                        st.markdown("🔀 **Revision**")
                    else:
                        st.markdown("✨ **New Application**")
                
                with title_col4:
                    # Planning officer icon for logging
                    st.markdown("👤")
                
                # Applicant info with better styling
                if case['is_modification']:
                    st.markdown(f"👤 **Applicant:** {case['applicant']} | 🔗 *Revision of {case['parent_ref']}*")
                else:
                    st.markdown(f"👤 **Applicant:** {case['applicant']}")
                
                # Metadata row
                info_parts = [f"📅 {case['date']}"]
                
                if case['is_modification'] and case['original_date']:
                    info_parts.append(f"Original: {case['original_date']}")
                
                if case['issues'] > 0:
                    info_parts.append(f"❌ {case['issues']} {'issue' if case['issues'] == 1 else 'issues'}")
                
                if case['warnings'] > 0:
                    info_parts.append(f"⚠️ {case['warnings']} {'warning' if case['warnings'] == 1 else 'warnings'}")
                
                if case['is_modification']:
                    total_changes = case['changes_count']['fields'] + case['changes_count']['documents']
                    info_parts.append(f"🔄 {total_changes} changes")

                # Add run ID
                if case.get('run_id'):
                    info_parts.append(f"🔢 Run #{case['run_id']}")

                st.markdown(" | ".join(info_parts))
            
            with col_actions:
                # View Results button (navigates to Results tab with run_id)
                if case.get('run_id'):
                    if st.button("📋 View Results", key=f"view_{case['id']}", use_container_width=True, type="primary"):
                        st.session_state.run_id = case['run_id']
                        st.session_state.current_tab = "Results"
                        st.rerun()
                else:
                    if st.button("View Details", key=f"view_{case['id']}", use_container_width=True):
                        st.session_state.selected_case = case
                        st.session_state.show_case_details = True
                        st.rerun()
                
                # Show "Submit Revision" button for V0 cases with issues
                if case['version'] == 'V0' and case['issues'] > 0:
                    if st.button("📤 Submit Revision", key=f"revise_{case['id']}", type="primary", use_container_width=True):
                        st.session_state.revision_parent_case = case
                        st.session_state.show_revision_form = True
                        st.rerun()
            
            st.markdown("---")

    # Pagination controls
    total_pages = (total_count + page_size - 1) // page_size

    if total_pages > 1:
        st.markdown("### 📄 Pagination")

        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.button("← Previous", disabled=st.session_state.cases_page == 1, use_container_width=True):
                st.session_state.cases_page -= 1
                st.rerun()

        with col_info:
            st.markdown(
                f"<div style='text-align: center; padding: 8px;'>"
                f"Page {st.session_state.cases_page} of {total_pages} (Total: {total_count} cases)"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_next:
            if st.button("Next →", disabled=st.session_state.cases_page >= total_pages, use_container_width=True):
                st.session_state.cases_page += 1
                st.rerun()

    # Show case details modal
    if st.session_state.get('show_case_details'):
        render_case_details(st.session_state.selected_case)

    # Show revision form modal
    if st.session_state.get('show_revision_form'):
        render_revision_form(st.session_state.revision_parent_case)


def render_case_details(case: Dict[str, Any]):
    """Render case details in a dialog-like view."""
    from planproof.ui.pages import case_details
    
    # Back button
    if st.button("← Back to My Cases"):
        st.session_state.show_case_details = False
        st.session_state.selected_case = None
        st.rerun()
    
    # Render full case details
    case_details.render(case)


def render_revision_form(parent_case: Dict[str, Any]):
    """Render form to create a new revision."""
    
    st.markdown("---")
    
    st.markdown(f"""
    <div style="
        background: #eff6ff;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 24px;
        margin: 24px 0;
    ">
        <h2 style="margin: 0 0 16px 0; color: #1e40af;">🔀 Create Revision for {parent_case['display_ref']}</h2>
        <p style="margin: 0; color: #1e40af;">
            You are creating <strong>V1</strong> based on <strong>{parent_case['display_ref']}</strong>
        </p>
        <p style="margin: 8px 0 0 0; color: #1e40af; font-size: 14px;">
            Original submitted: {parent_case['original_date']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # What changed?
    st.markdown("### 📝 What Changed?")
    st.markdown("Check all that apply:")
    
    col1, col2 = st.columns(2)
    with col1:
        updated_height = st.checkbox("Updated building height", key="rev_height")
        added_site_plan = st.checkbox("Added site plan", key="rev_site_plan")
        changed_parking = st.checkbox("Changed parking layout", key="rev_parking")
    
    with col2:
        changed_applicant = st.checkbox("Changed applicant details", key="rev_applicant")
        added_documents = st.checkbox("Added missing documents", key="rev_docs")
        updated_drawings = st.checkbox("Updated drawings", key="rev_drawings")
    
    # Upload documents
    st.markdown("### 📄 Upload Updated Documents")
    
    uploaded_files = st.file_uploader(
        "Upload revised PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload only the documents that have changed",
        key="revision_files"
    )
    
    # Buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_revision_form = False
            st.session_state.revision_parent_case = None
            st.rerun()
    
    with col2:
        if st.button("Submit Revision", type="primary", disabled=not uploaded_files, use_container_width=True):
            if not uploaded_files:
                st.error("Please upload at least one document")
                return
            
            try:
                # Create V1 submission linked to V0
                from planproof.ui.run_orchestrator import start_run
                
                run_id = start_run(
                    app_ref=parent_case['ref'],
                    files=list(uploaded_files),
                    parent_submission_id=parent_case['submission_id']
                )
                
                st.success(f"✓ Revision created successfully! Processing V1...")
                st.session_state.show_revision_form = False
                st.session_state.revision_parent_case = None
                st.session_state.processing_status = 'active'
                st.session_state.processing_run_id = run_id
                st.session_state.processing_app_ref = f"{parent_case['ref']}-V1"
                
                time.sleep(1)
                st.rerun()
            
            except Exception as e:
                st.error(f"Error creating revision: {str(e)}")
