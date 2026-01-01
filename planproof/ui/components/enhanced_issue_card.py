"""
Enhanced Issue Card Components for PlanProof UI.

This module provides Streamlit components for displaying enhanced validation issues
with actionable guidance, transparency, and resolution tracking.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

# Import enhanced issue types
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from enhanced_issues import (
    EnhancedIssue,
    Action,
    ActionType,
    IssueSeverity,
    IssueCategory,
    ResolutionStatus
)

# Import resolution service
from planproof.services.resolution_service import ResolutionService


def render_severity_badge(severity: IssueSeverity) -> str:
    """Render severity badge with appropriate styling."""
    severity_config = {
        IssueSeverity.BLOCKER: ("🚫", "BLOCKER", "#ff4444"),
        IssueSeverity.CRITICAL: ("❗", "CRITICAL", "#ff6b6b"),
        IssueSeverity.WARNING: ("⚠️", "WARNING", "#ffa500"),
        IssueSeverity.INFO: ("ℹ️", "INFO", "#4a90e2")
    }
    
    icon, label, color = severity_config.get(severity, ("", "UNKNOWN", "#666"))
    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{icon} {label}</span>'


def render_status_badge(status: ResolutionStatus) -> str:
    """Render resolution status badge."""
    status_config = {
        ResolutionStatus.OPEN: ("🔴", "OPEN", "#ff4444"),
        ResolutionStatus.IN_PROGRESS: ("🟡", "IN PROGRESS", "#ffa500"),
        ResolutionStatus.AWAITING_VERIFICATION: ("🔵", "VERIFYING", "#4a90e2"),
        ResolutionStatus.RESOLVED: ("✅", "RESOLVED", "#00c851"),
        ResolutionStatus.DISMISSED: ("⭕", "DISMISSED", "#999")
    }
    
    icon, label, color = status_config.get(status, ("", "UNKNOWN", "#666"))
    return f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 0.85em;">{icon} {label}</span>'


def render_action_button(action: Action, issue_id: str, index: int) -> None:
    """Render action button with appropriate handler."""
    # Map action types to button styles
    button_config = {
        ActionType.UPLOAD_DOCUMENT: ("📤", "primary"),
        ActionType.CONFIRM_DATA: ("✓", "secondary"),
        ActionType.SELECT_OPTION: ("🔘", "secondary"),
        ActionType.PROVIDE_EXPLANATION: ("💬", "secondary"),
        ActionType.REVIEW_EVIDENCE: ("🔍", "secondary"),
        ActionType.CONTACT_SUPPORT: ("📞", "secondary")
    }
    
    icon, btn_type = button_config.get(action.action_type, ("⚙️", "secondary"))
    button_key = f"action_{issue_id}_{index}"
    
    # Create columns for button and status
    col1, col2 = st.columns([3, 1])
    
    with col1:
        button_label = f"{icon} {action.label}"
        if st.button(button_label, key=button_key, type=btn_type, use_container_width=True):
            # Store the action request in session state
            st.session_state[f"action_request_{issue_id}"] = action
            st.rerun()
    
    with col2:
        if action.completed_at:
            st.success("✓ Done")
        elif st.session_state.get(f"action_request_{issue_id}"):
            st.info("⏳")


def render_upload_widget(issue_id: str, action: Action, run_id: int) -> None:
    """Render file upload widget for document actions."""
    st.markdown("---")
    st.markdown(f"#### {action.label}")
    st.markdown(action.description)
    
    # Initialize resolution service
    resolution_service = ResolutionService(run_id)
    
    # Check if this is for multiple documents
    if action.parameters.get("document_types"):
        # Bulk upload
        uploaded_files = st.file_uploader(
            "Select PDF files to upload",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"upload_{issue_id}"
        )
        
        if uploaded_files:
            st.success(f"✓ {len(uploaded_files)} file(s) selected")
            
            # Document type assignment
            st.markdown("##### Assign Document Types")
            assignments = {}
            
            for file in uploaded_files:
                doc_type = st.selectbox(
                    f"Type for: {file.name}",
                    options=action.parameters["document_types"],
                    key=f"doctype_{issue_id}_{file.name}"
                )
                assignments[file.name] = doc_type
            
            if st.button("Upload All", key=f"upload_confirm_{issue_id}", type="primary"):
                # Process uploads
                with st.spinner("Uploading files..."):
                    uploads = [(file, assignments[file.name]) for file in uploaded_files]
                    result = resolution_service.process_bulk_document_upload(
                        uploads=uploads,
                        issue_ids=[issue_id]
                    )
                    
                    if result.get("success"):
                        st.success(f"✅ Uploaded {result['successful']} file(s)")
                        st.session_state[f"action_completed_{issue_id}"] = True
                        st.info("🔄 Issues marked for automatic recheck. Refresh to see updates.")
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {result.get('failed')} file(s) had errors")
    else:
        # Single file upload
        uploaded_file = st.file_uploader(
            f"Select {action.parameters.get('document_type', 'document')}",
            type=["pdf"],
            key=f"upload_{issue_id}"
        )
        
        if uploaded_file:
            st.success(f"✓ {uploaded_file.name} selected")
            
            if st.button("Upload", key=f"upload_confirm_{issue_id}", type="primary"):
                # Process upload
                with st.spinner("Uploading file..."):
                    result = resolution_service.process_document_upload(
                        uploaded_file=uploaded_file,
                        document_type=action.parameters.get('document_type', 'document'),
                        issue_id=issue_id
                    )
                    
                    if result.get("success"):
                        st.success(f"✅ {result['message']}")
                        st.session_state[f"action_completed_{issue_id}"] = True
                        st.info("🔄 Issue marked for automatic recheck. Refresh to see updates.")
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {result.get('error')}")


def render_select_option_widget(issue_id: str, action: Action, run_id: int) -> None:
    """Render selection widget for option-based actions."""
    st.markdown("---")
    st.markdown(f"#### {action.label}")
    st.markdown(action.description)
    
    # Initialize resolution service
    resolution_service = ResolutionService(run_id)
    
    options = action.parameters.get("options", [])
    
    if options:
        selected = st.radio(
            "Choose an option:",
            options=[opt["value"] for opt in options],
            format_func=lambda x: next((opt["label"] for opt in options if opt["value"] == x), x),
            key=f"select_{issue_id}"
        )
        
        # Show description for selected option
        selected_option = next((opt for opt in options if opt["value"] == selected), None)
        if selected_option and selected_option.get("description"):
            st.info(selected_option["description"])
        
        if st.button("Confirm Selection", key=f"select_confirm_{issue_id}", type="primary"):
            # Process selection
            with st.spinner("Recording selection..."):
                result = resolution_service.process_option_selection(
                    issue_id=issue_id,
                    selected_option=selected,
                    option_label=selected_option.get('label', selected) if selected_option else selected
                )
                
                if result.get("success"):
                    st.success(f"✅ {result['message']}")
                    st.session_state[f"action_completed_{issue_id}"] = True
                    st.info("Selection recorded. Issue status updated.")
                    st.rerun()
                else:
                    st.error(f"Selection failed: {result.get('error')}")


def render_provide_explanation_widget(issue_id: str, action: Action, run_id: int) -> None:
    """Render text input widget for explanation actions."""
    st.markdown("---")
    st.markdown(f"#### {action.label}")
    st.markdown(action.description)
    
    # Initialize resolution service
    resolution_service = ResolutionService(run_id)
    
    explanation = st.text_area(
        "Your explanation:",
        placeholder=action.parameters.get("placeholder", "Enter explanation..."),
        key=f"explanation_{issue_id}",
        height=150
    )
    
    min_length = action.parameters.get("min_length", 10)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("Submit Explanation", key=f"explanation_confirm_{issue_id}", type="primary"):
            if len(explanation.strip()) < min_length:
                st.error(f"Please provide at least {min_length} characters")
            else:
                # Process explanation
                with st.spinner("Submitting explanation..."):
                    result = resolution_service.process_explanation(
                        issue_id=issue_id,
                        explanation_text=explanation.strip()
                    )
                    
                    if result.get("success"):
                        st.success(f"✅ {result['message']}")
                        st.session_state[f"action_completed_{issue_id}"] = True
                        st.info("Explanation recorded. Issue status updated.")
                        st.rerun()
                    else:
                        st.error(f"Submission failed: {result.get('error')}")
    
    with col2:
        st.caption(f"{len(explanation)}/{min_length} chars")


def render_action_handler(issue_id: str, action: Action, run_id: int) -> None:
    """Render appropriate widget based on action type."""
    if action.action_type == ActionType.UPLOAD_DOCUMENT:
        render_upload_widget(issue_id, action, run_id)
    elif action.action_type == ActionType.SELECT_OPTION:
        render_select_option_widget(issue_id, action, run_id)
    elif action.action_type == ActionType.PROVIDE_EXPLANATION:
        render_provide_explanation_widget(issue_id, action, run_id)
    elif action.action_type == ActionType.REVIEW_EVIDENCE:
        # Evidence review handled by document viewer
        if st.button("View Evidence", key=f"view_evidence_{issue_id}", type="secondary"):
            st.info("Opening document viewer...")
    elif action.action_type == ActionType.CONTACT_SUPPORT:
        st.info(f"📞 Contact: {action.parameters.get('contact_info', 'planning@council.gov.uk')}")


def render_what_we_checked_section(issue: EnhancedIssue) -> None:
    """Render transparency section showing what was checked."""
    with st.expander("🔍 What We Checked"):
        st.markdown(f"**Search Area:** {issue.user_message.what_we_checked.search_description}")
        
        if issue.user_message.what_we_checked.method_description:
            st.markdown(f"**How We Checked:** {issue.user_message.what_we_checked.method_description}")
        
        if issue.user_message.what_we_checked.evidence_found:
            st.markdown("**Evidence Found:**")
            for evidence in issue.user_message.what_we_checked.evidence_found:
                st.markdown(f"- **{evidence.field_name}**: {evidence.value}")
                st.caption(f"   📄 {evidence.document_name} (Page {evidence.page_number}, Confidence: {evidence.confidence:.0%})")
        
        if issue.user_message.what_we_checked.documents_searched:
            with st.expander("📚 Documents Searched"):
                for doc in issue.user_message.what_we_checked.documents_searched:
                    st.markdown(f"- {doc}")


def render_resolution_progress(issue: EnhancedIssue) -> None:
    """Render resolution progress and dependencies."""
    if not issue.resolution:
        return
    
    st.markdown("---")
    st.markdown("### 📊 Resolution Progress")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Status**")
        st.markdown(render_status_badge(issue.resolution.status), unsafe_allow_html=True)
    
    with col2:
        if issue.resolution.attempted_at:
            st.markdown("**Last Attempt**")
            st.caption(issue.resolution.attempted_at.strftime("%Y-%m-%d %H:%M"))
    
    with col3:
        if issue.resolution.resolved_at:
            st.markdown("**Resolved**")
            st.caption(issue.resolution.resolved_at.strftime("%Y-%m-%d %H:%M"))
    
    # Show dependencies
    if issue.resolution.depends_on_issues:
        st.markdown("**⛓️ Dependencies**")
        st.info(f"This issue depends on resolving: {', '.join(issue.resolution.depends_on_issues)}")
    
    # Show auto-recheck info
    if issue.resolution.auto_recheck_on_upload:
        st.markdown("**🔄 Auto-Recheck**")
        st.success("✓ Will automatically recheck when documents are uploaded")
    
    # Show resolution notes
    if issue.resolution.resolution_notes:
        with st.expander("📝 Resolution Notes"):
            for note in issue.resolution.resolution_notes:
                st.markdown(note)


def render_enhanced_issue_card(issue: EnhancedIssue, run_id: int) -> None:
    """
    Render a complete enhanced issue card with all sections.
    
    Args:
        issue: EnhancedIssue object containing all issue data
        run_id: Run ID for resolution tracking
    """
    # Check if action was completed
    action_completed = st.session_state.get(f"action_completed_{issue.issue_id}", False)
    
    # Create expander title with status and severity
    expander_title = f"{issue.rule_id} - {issue.user_message.title}"
    
    # Add status indicator
    if action_completed or (issue.resolution and issue.resolution.status == ResolutionStatus.RESOLVED):
        expander_title = f"✅ {expander_title}"
    elif issue.severity == IssueSeverity.BLOCKER:
        expander_title = f"🚫 {expander_title}"
    elif issue.severity == IssueSeverity.CRITICAL:
        expander_title = f"❗ {expander_title}"
    elif issue.severity == IssueSeverity.WARNING:
        expander_title = f"⚠️ {expander_title}"
    
    with st.expander(expander_title, expanded=(issue.severity in [IssueSeverity.BLOCKER, IssueSeverity.CRITICAL] and not action_completed)):
        # Header with badges
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(render_severity_badge(issue.severity), unsafe_allow_html=True)
        
        with col2:
            st.caption(f"📁 {issue.category.value}")
        
        with col3:
            st.caption(f"👤 {issue.who_can_fix}")
        
        # User message section
        st.markdown("---")
        st.markdown(f"### {issue.user_message.title}")
        st.markdown(issue.user_message.description)
        
        if issue.user_message.why_it_matters:
            st.info(f"💡 **Why it matters:** {issue.user_message.why_it_matters}")
        
        if issue.user_message.impact:
            st.warning(f"⚠️ **Impact:** {issue.user_message.impact}")
        
        # What we checked section
        render_what_we_checked_section(issue)
        
        # Show action completed message
        if action_completed:
            st.success("✅ Action completed! This issue has been addressed.")
        
        # Actions section
        if issue.actions and issue.actions.items and not action_completed:
            st.markdown("---")
            st.markdown("### 🎯 What You Can Do")
            
            for idx, action in enumerate(issue.actions.items):
                st.markdown(f"#### {idx + 1}. {action.label}")
                st.markdown(action.description)
                
                # Check if action is already in progress
                if st.session_state.get(f"action_request_{issue.issue_id}") == action:
                    render_action_handler(issue.issue_id, action, run_id)
                else:
                    # Show button to start action
                    render_action_button(action, issue.issue_id, idx)
                
                st.markdown("")  # Spacing
        
        # Resolution progress
        if issue.resolution:
            render_resolution_progress(issue)
        
        # Officer dismiss option
        if issue.who_can_fix in ["Planning Officer", "Senior Officer"]:
            st.markdown("---")
            with st.expander("🔐 Officer Override: Dismiss Issue"):
                st.warning("**Officer Action**: Dismiss this issue if it does not apply.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    officer_id = st.text_input(
                        "Officer ID",
                        key=f"dismiss_officer_{issue.issue_id}",
                        placeholder="Your officer ID"
                    )
                
                with col2:
                    reason = st.text_input(
                        "Dismissal Reason",
                        key=f"dismiss_reason_{issue.issue_id}",
                        placeholder="Brief explanation"
                    )
                
                if st.button("Dismiss Issue", key=f"dismiss_btn_{issue.issue_id}", type="secondary"):
                    if not officer_id or not reason:
                        st.error("Both Officer ID and reason are required")
                    else:
                        resolution_service = ResolutionService(run_id)
                        result = resolution_service.dismiss_issue(
                            issue_id=issue.issue_id,
                            officer_id=officer_id,
                            reason=reason
                        )
                        
                        if result.get("success"):
                            st.success(f"✅ Issue dismissed by {officer_id}")
                            st.session_state[f"action_completed_{issue.issue_id}"] = True
                            st.rerun()
                        else:
                            st.error(f"Dismissal failed: {result.get('error')}")


def render_bulk_action_panel(issues: List[EnhancedIssue]) -> None:
    """
    Render bulk action panel for handling multiple issues at once.
    
    Args:
        issues: List of EnhancedIssue objects that can be resolved together
    """
    st.markdown("### 📦 Bulk Actions")
    
    # Group issues by action type
    upload_issues = [i for i in issues if i.actions and any(
        a.action_type == ActionType.UPLOAD_DOCUMENT for a in i.actions.items
    )]
    
    if upload_issues:
        with st.expander(f"📤 Upload Multiple Documents ({len(upload_issues)} issues)"):
            st.markdown("Upload all required documents at once:")
            
            # Collect all required document types
            required_docs = set()
            for issue in upload_issues:
                for action in issue.actions.items:
                    if action.action_type == ActionType.UPLOAD_DOCUMENT:
                        doc_type = action.parameters.get("document_type")
                        if doc_type:
                            required_docs.add(doc_type)
            
            st.markdown("**Required Documents:**")
            for doc in sorted(required_docs):
                st.markdown(f"- {doc}")
            
            # Bulk upload
            uploaded_files = st.file_uploader(
                "Select all PDF files",
                type=["pdf"],
                accept_multiple_files=True,
                key="bulk_upload"
            )
            
            if uploaded_files:
                st.success(f"✓ {len(uploaded_files)} file(s) selected")
                
                # Document type assignment
                assignments = {}
                for file in uploaded_files:
                    doc_type = st.selectbox(
                        f"Type for: {file.name}",
                        options=sorted(required_docs),
                        key=f"bulk_doctype_{file.name}"
                    )
                    assignments[file.name] = doc_type
                
                if st.button("Upload All & Revalidate", key="bulk_upload_confirm", type="primary"):
                    st.session_state["bulk_upload_data"] = {
                        "files": uploaded_files,
                        "assignments": assignments,
                        "issue_ids": [i.issue_id for i in upload_issues]
                    }
                    st.success("✓ Files ready for processing. Revalidation will start automatically.")


def render_resolution_tracker(issues: List[EnhancedIssue]) -> None:
    """
    Render resolution tracker showing overall progress.
    
    Args:
        issues: List of all EnhancedIssue objects in the current run
    """
    st.markdown("### 📊 Resolution Tracker")
    
    # Calculate statistics
    total = len(issues)
    resolved = sum(1 for i in issues if i.resolution and i.resolution.status == ResolutionStatus.RESOLVED)
    in_progress = sum(1 for i in issues if i.resolution and i.resolution.status == ResolutionStatus.IN_PROGRESS)
    open_issues = sum(1 for i in issues if i.resolution and i.resolution.status == ResolutionStatus.OPEN)
    
    # Progress bar
    progress = resolved / total if total > 0 else 0
    st.progress(progress, text=f"{resolved}/{total} issues resolved ({progress:.0%})")
    
    # Status breakdown
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Issues", total)
    
    with col2:
        st.metric("✅ Resolved", resolved)
    
    with col3:
        st.metric("🟡 In Progress", in_progress)
    
    with col4:
        st.metric("🔴 Open", open_issues)
    
    # Group by severity
    st.markdown("**By Severity:**")
    severity_counts = {}
    for issue in issues:
        if issue.resolution and issue.resolution.status != ResolutionStatus.RESOLVED:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚫 Blocker", severity_counts.get(IssueSeverity.BLOCKER, 0))
    
    with col2:
        st.metric("❗ Critical", severity_counts.get(IssueSeverity.CRITICAL, 0))
    
    with col3:
        st.metric("⚠️ Warning", severity_counts.get(IssueSeverity.WARNING, 0))
    
    with col4:
        st.metric("ℹ️ Info", severity_counts.get(IssueSeverity.INFO, 0))
