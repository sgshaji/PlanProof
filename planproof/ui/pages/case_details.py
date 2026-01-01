"""
Case Details Page - Complete view of a specific case/application.
"""

import streamlit as st
from typing import Dict, Any
from planproof.db import Database, Submission, ValidationCheck, ValidationStatus
from planproof.ui.components.breadcrumbs import render_back_button


def render(case: Dict[str, Any]):
    """
    Render detailed view of a case.

    Args:
        case: Case dictionary with all metadata
    """
    # Back button
    if render_back_button("← Back to My Cases", "back_to_cases"):
        st.session_state.show_case_details = False
        st.session_state.selected_case = None
        st.rerun()

    st.markdown("---")

    # Header
    st.markdown(f"# {case['display_ref']}")

    if case['is_modification']:
        st.info(f"🔄 This is a revision of {case['parent_ref']}")

    # Metadata grid
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Status", case['status'])

    with col2:
        st.metric("Issues", case['issues'])

    with col3:
        st.metric("Warnings", case['warnings'])

    with col4:
        if case.get('run_id'):
            st.metric("Run ID", f"#{case['run_id']}")

    st.markdown("---")

    # Application Details
    st.markdown("## 📋 Application Details")

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        st.markdown(f"**Application Reference:** {case['ref']}")
        st.markdown(f"**Version:** {case['version']}")
        st.markdown(f"**Applicant:** {case['applicant']}")

    with detail_col2:
        st.markdown(f"**Submitted:** {case['date']}")
        if case['is_modification']:
            st.markdown(f"**Original Date:** {case['original_date']}")
            total_changes = case['changes_count']['fields'] + case['changes_count']['documents']
            st.markdown(f"**Changes Made:** {total_changes} ({case['changes_count']['fields']} fields, {case['changes_count']['documents']} documents)")

    st.markdown("---")

    # Validation Results
    st.markdown("## ✅ Validation Results")

    db = Database()
    session = db.get_session()

    try:
        # Get validation checks
        validation_checks = session.query(ValidationCheck).filter(
            ValidationCheck.submission_id == case['submission_id']
        ).all()

        if not validation_checks:
            st.info("No validation checks found for this submission")
        else:
            # Group by status
            passed = [v for v in validation_checks if v.status == ValidationStatus.PASS]
            failed = [v for v in validation_checks if v.status == ValidationStatus.FAIL]
            needs_review = [v for v in validation_checks if v.status == ValidationStatus.NEEDS_REVIEW]

            # Show summary tabs
            tab1, tab2, tab3 = st.tabs([
                f"❌ Failed ({len(failed)})",
                f"⚠️ Needs Review ({len(needs_review)})",
                f"✅ Passed ({len(passed)})"
            ])

            with tab1:
                if failed:
                    for check in failed:
                        with st.expander(f"❌ {check.rule_id_string}", expanded=True):
                            if check.message:
                                st.markdown(f"**Issue:** {check.message}")
                            if check.severity:
                                st.markdown(f"**Severity:** {check.severity}")
                            if check.evidence_text:
                                st.markdown("**Evidence:**")
                                st.code(check.evidence_text[:500])
                else:
                    st.success("✅ No failed checks!")

            with tab2:
                if needs_review:
                    for check in needs_review:
                        with st.expander(f"⚠️ {check.rule_id_string}"):
                            if check.message:
                                st.markdown(f"**Warning:** {check.message}")
                            if check.evidence_text:
                                st.markdown("**Evidence:**")
                                st.code(check.evidence_text[:500])
                else:
                    st.info("No items need review")

            with tab3:
                st.success(f"✅ {len(passed)} checks passed successfully")
                if passed:
                    with st.expander("View Passed Checks"):
                        for check in passed[:20]:  # Show first 20
                            st.markdown(f"- ✅ {check.rule_id_string}")

    finally:
        session.close()

    st.markdown("---")

    # Actions
    st.markdown("## 🎯 Actions")

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if case.get('run_id'):
            if st.button("📋 View Full Results", use_container_width=True, type="primary"):
                st.session_state.run_id = case['run_id']
                st.session_state.current_tab = "Results"
                st.session_state.show_case_details = False
                st.rerun()

    with action_col2:
        if case['issues'] > 0 and case['version'] == 'V0':
            if st.button("📤 Submit Revision", use_container_width=True):
                st.session_state.show_case_details = False
                st.session_state.revision_parent_case = case
                st.session_state.show_revision_form = True
                st.rerun()

    with action_col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
