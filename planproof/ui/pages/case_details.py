"""
Case Details Page - Full case view with Overview, Validation, Documents, History tabs.
Includes delta visualization for modification submissions.
"""

import streamlit as st
from typing import Dict, Any, List
from planproof.db import Database, Submission, ValidationCheck, ChangeSet, ChangeItem, Document
from planproof.ui.ui_components import (
    render_status_badge, render_version_badge, render_delta_card,
    render_metric_card, render_version_timeline, render_issue_resolved_badge
)


def get_case_data(case: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch complete case data including validation results and delta."""
    db = Database()
    session = db.get_session()
    
    try:
        submission = session.query(Submission).filter(
            Submission.id == case['submission_id']
        ).first()
        
        if not submission:
            return {}
        
        # Get validation checks
        validation_checks = session.query(ValidationCheck).filter(
            ValidationCheck.submission_id == submission.id
        ).all()
        
        from planproof.db import ValidationStatus
        pass_count = sum(1 for v in validation_checks if v.status == ValidationStatus.PASS)
        fail_count = sum(1 for v in validation_checks if v.status == ValidationStatus.FAIL)
        review_count = sum(1 for v in validation_checks if v.status == ValidationStatus.NEEDS_REVIEW)
        
        # Get delta if modification
        delta_data = None
        if case['is_modification']:
            delta_data = get_delta_data(submission.id, session)
        
        # Get documents
        documents = session.query(Document).filter(
            Document.submission_id == submission.id
        ).all()
        
        doc_list = []
        for doc in documents:
            doc_list.append({
                'name': doc.filename,
                'size': 'N/A',  # Size not stored currently
                'uploaded_at': doc.uploaded_at.strftime('%Y-%m-%d') if doc.uploaded_at else 'N/A',
                'doc_type': doc.document_type or 'Unknown'
            })
        
        # Get version timeline if modification
        version_timeline = []
        if case['is_modification']:
            version_timeline = get_version_timeline(submission, session)
        
        return {
            'validation': {
                'pass': pass_count,
                'fail': fail_count,
                'review': review_count,
                'checks': validation_checks
            },
            'delta': delta_data,
            'documents': doc_list,
            'timeline': version_timeline
        }
    
    finally:
        session.close()


def get_delta_data(submission_id: int, session) -> Dict[str, Any]:
    """Get delta/change data for a modification submission."""
    changeset = session.query(ChangeSet).filter(
        ChangeSet.submission_id == submission_id
    ).first()
    
    if not changeset:
        return None
    
    change_items = session.query(ChangeItem).filter(
        ChangeItem.change_set_id == changeset.id
    ).all()
    
    field_changes = []
    doc_changes = []
    spatial_changes = []
    
    for item in change_items:
        if item.change_type == 'field_delta':
            field_changes.append({
                'field': item.field_key or 'Unknown field',
                'before': item.old_value or 'N/A',
                'after': item.new_value or 'N/A',
                'significance': 'high' if 'height' in (item.field_key or '').lower() else 'medium'
            })
        elif item.change_type == 'document_delta':
            action = item.change_metadata.get('action', 'unknown') if item.change_metadata else 'unknown'
            doc_changes.append({
                'name': item.document_type or 'Unknown document',
                'type': action,
                'date': item.created_at.strftime('%Y-%m-%d') if item.created_at else 'N/A'
            })
        elif item.change_type == 'spatial_metric_delta':
            spatial_changes.append({
                'metric': item.field_key or 'Unknown metric',
                'before': item.old_value or 'N/A',
                'after': item.new_value or 'N/A',
                'change': f"-{item.old_value}" if item.old_value else 'N/A'
            })
    
    return {
        'field_changes': field_changes,
        'doc_changes': doc_changes,
        'spatial_changes': spatial_changes,
        'significance_score': changeset.significance_score
    }


def get_version_timeline(submission: Submission, session) -> List[Dict[str, Any]]:
    """Get full version timeline for a submission."""
    timeline = []
    
    # Walk back to V0
    current = submission
    while current:
        from planproof.db import ValidationCheck, ValidationStatus
        
        validation_checks = session.query(ValidationCheck).filter(
            ValidationCheck.submission_id == current.id
        ).all()
        
        errors = sum(1 for v in validation_checks if v.status == ValidationStatus.FAIL)
        warnings = sum(1 for v in validation_checks if v.status == ValidationStatus.NEEDS_REVIEW)
        passed = sum(1 for v in validation_checks if v.status == ValidationStatus.PASS)
        
        # Get changes for this version
        changes = ["Original submission"] if current.submission_version == "V0" else []
        
        if current.submission_version != "V0":
            changeset = session.query(ChangeSet).filter(
                ChangeSet.submission_id == current.id
            ).first()
            
            if changeset:
                change_items = session.query(ChangeItem).filter(
                    ChangeItem.change_set_id == changeset.id
                ).all()
                
                for item in change_items:
                    if item.change_type == 'field_delta':
                        changes.append(f"Changed {item.field_key}: {item.old_value} → {item.new_value}")
                    elif item.change_type == 'document_delta':
                        action = item.change_metadata.get('action', 'modified') if item.change_metadata else 'modified'
                        changes.append(f"{action.title()} document: {item.document_type}")
        
        timeline.insert(0, {
            'version': current.submission_version,
            'date': current.created_at.strftime('%Y-%m-%d %H:%M') if current.created_at else 'N/A',
            'is_current': current.id == submission.id,
            'status': 'Complete' if errors == 0 and warnings == 0 else ('Issues Found' if errors > 0 else 'In Review'),
            'changes': changes[:5],  # Limit to 5 changes
            'issues_summary': {
                'errors': errors,
                'warnings': warnings,
                'passed': passed
            }
        })
        
        # Move to parent
        if current.parent_submission_id:
            current = session.query(Submission).filter(
                Submission.id == current.parent_submission_id
            ).first()
        else:
            break
    
    return timeline


def render(case: Dict[str, Any]):
    """Render case details page."""
    
    # Fetch full case data
    case_data = get_case_data(case)
    
    if not case_data:
        st.error("Failed to load case data")
        return
    
    # Header
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 24px;
        margin-bottom: 24px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 24px;">
            <div>
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: bold; color: #111827;">
                        {case['display_ref']}
                    </h1>
                    {render_version_badge(case['version'], case['is_modification'])}
                </div>
    """, unsafe_allow_html=True)
    
    if case['is_modification'] and case['parent_ref']:
        st.markdown(f"""
                <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">
                    Revision of <a href="#" style="color: #3b82f6; font-weight: 500;">{case['parent_ref']}</a>
                    • Original submitted {case['original_date']}
                </p>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
                {render_status_badge(case['status'])}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Case metadata
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="padding: 16px; background-color: #f9fafb; border-radius: 8px;">
            <p style="font-size: 13px; color: #6b7280; margin: 0 0 4px 0;">Applicant</p>
            <p style="font-size: 15px; font-weight: 600; color: #111827; margin: 0;">{case['applicant']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="padding: 16px; background-color: #f9fafb; border-radius: 8px;">
            <p style="font-size: 13px; color: #6b7280; margin: 0 0 4px 0;">Date Submitted</p>
            <p style="font-size: 15px; font-weight: 600; color: #111827; margin: 0;">{case['date']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="padding: 16px; background-color: #f9fafb; border-radius: 8px;">
            <p style="font-size: 13px; color: #6b7280; margin: 0 0 4px 0;">Version</p>
            <p style="font-size: 15px; font-weight: 600; color: #111827; margin: 0;">{case['version']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "✓ Validation Results", "📄 Documents", "🕐 History"])
    
    with tab1:
        render_overview_tab(case, case_data)
    
    with tab2:
        render_validation_tab(case, case_data)
    
    with tab3:
        render_documents_tab(case, case_data)
    
    with tab4:
        render_history_tab(case, case_data)


def render_overview_tab(case: Dict[str, Any], case_data: Dict[str, Any]):
    """Render overview tab with metrics and delta."""
    
    # Validation summary metrics
    val_data = case_data['validation']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        change = f"↓ -{case['issues']} from V0" if case['is_modification'] and case['issues'] < 2 else None
        render_metric_card("Critical Issues", str(val_data['fail']), change, "red")
    
    with col2:
        change = f"↓ -{case['warnings']} from V0" if case['is_modification'] and case['warnings'] < 2 else None
        render_metric_card("Warnings", str(val_data['review']), change, "amber")
    
    with col3:
        change = f"↑ +{val_data['pass']} from V0" if case['is_modification'] and val_data['pass'] > 1 else None
        render_metric_card("Checks Passed", str(val_data['pass']), change, "green")
    
    st.markdown("<div style='margin: 32px 0;'></div>", unsafe_allow_html=True)
    
    # Delta summary for modifications
    if case['is_modification'] and case_data['delta']:
        delta = case_data['delta']
        render_delta_card(
            delta['field_changes'],
            delta['doc_changes'],
            delta['spatial_changes']
        )
    
    # Key findings
    st.markdown("""
    <div style="
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 20px;
        margin-top: 24px;
    ">
        <h3 style="color: #1e40af; margin: 0 0 12px 0;">💡 Key Findings</h3>
        <ul style="margin: 0; padding-left: 20px; color: #1e40af;">
            <li style="margin-bottom: 8px;">Building height now complies (reduced to 10m)</li>
            <li style="margin-bottom: 8px;">Site plan provided</li>
            <li style="margin-bottom: 0;">Heritage statement could include more detailed analysis</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def render_validation_tab(case: Dict[str, Any], case_data: Dict[str, Any]):
    """Render validation results with enhanced issue display."""
    
    val_data = case_data['validation']
    
    if not val_data['checks']:
        st.info("No validation checks found for this submission")
        return
    
    for check in val_data['checks']:
        # Determine severity
        from planproof.db import ValidationStatus
        
        if check.status == ValidationStatus.FAIL:
            severity = "error"
        elif check.status == ValidationStatus.NEEDS_REVIEW:
            severity = "warning"
        else:
            severity = "success"
        
        # Severity styling
        if severity == "error":
            border_color = "#ef4444"
            bg_color = "#fef2f2"
            icon = "❌"
        elif severity == "warning":
            border_color = "#f59e0b"
            bg_color = "#fffbeb"
            icon = "⚠️"
        else:
            border_color = "#10b981"
            bg_color = "#f0fdf4"
            icon = "✓"
        
        st.markdown(f"""
        <div style="
            border-left: 4px solid {border_color};
            background-color: {bg_color};
            border-radius: 0 8px 8px 0;
            margin-bottom: 16px;
        ">
            <div style="background: white; padding: 20px; border-radius: 0 8px 8px 0;">
                <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 20px;">{icon}</span>
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: bold; color: #111827;">
                            {check.rule_id}: {check.rule_description or 'Validation Check'}
                        </h3>
                        <p style="margin: 0; font-size: 14px; color: #6b7280;">
                            {check.message or 'No details available'}
                        </p>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_documents_tab(case: Dict[str, Any], case_data: Dict[str, Any]):
    """Render documents list."""
    
    docs = case_data['documents']
    
    if not docs:
        st.info("No documents found for this submission")
        return
    
    cols = st.columns(3)
    
    for idx, doc in enumerate(docs):
        with cols[idx % 3]:
            st.markdown(f"""
            <div style="
                padding: 16px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: white;
                margin-bottom: 16px;
            ">
                <div style="font-size: 32px; margin-bottom: 12px;">📄</div>
                <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #111827;">
                    {doc['name']}
                </h4>
                <p style="margin: 0; font-size: 12px; color: #6b7280;">
                    {doc['doc_type']} • Uploaded {doc['uploaded_at']}
                </p>
            </div>
            """, unsafe_allow_html=True)


def render_history_tab(case: Dict[str, Any], case_data: Dict[str, Any]):
    """Render version history timeline."""
    
    timeline = case_data.get('timeline', [])
    
    if not timeline or len(timeline) == 1:
        st.markdown("""
        <div style="text-align: center; padding: 64px 24px;">
            <div style="font-size: 48px; margin-bottom: 16px;">🕐</div>
            <h3 style="color: #111827; margin-bottom: 8px;">No Modifications Yet</h3>
            <p style="color: #6b7280; margin-bottom: 16px;">
                This is the original version (V0) of the application
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if case['issues'] > 0:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("📤 Submit Revised Application", type="primary", use_container_width=True):
                    st.session_state.revision_parent_case = case
                    st.session_state.show_revision_form = True
                    st.rerun()
        
        return
    
    # Render timeline
    render_version_timeline(timeline)
    
    # Compare versions button
    if len(timeline) > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔀 Compare V0 ↔ V1", use_container_width=True):
                st.info("Version comparison view coming soon!")
