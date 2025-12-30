"""
Dashboard page for team leads with aggregate statistics and analytics.
"""

import streamlit as st
from planproof.db import Database, ValidationCheck, ValidationStatus, Case, Submission, OfficerOverride
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import pandas as pd


def render():
    """Render dashboard page."""
    st.title("📊 Team Dashboard")
    
    db = Database()
    session = db.get_session()
    
    try:
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input(
                "From",
                value=datetime.now() - timedelta(days=30),
                key="dash_date_from"
            )
        with col2:
            date_to = st.date_input(
                "To",
                value=datetime.now(),
                key="dash_date_to"
            )
        
        # Convert to datetime for filtering
        date_from_dt = datetime.combine(date_from, datetime.min.time())
        date_to_dt = datetime.combine(date_to, datetime.max.time())
        
        st.divider()
        
        # Key Metrics
        st.subheader("📈 Key Metrics")
        
        # Get cases in date range
        total_cases = session.query(Case).filter(
            and_(
                Case.created_at >= date_from_dt,
                Case.created_at <= date_to_dt
            )
        ).count()
        
        # Get submissions in date range
        total_submissions = session.query(Submission).filter(
            and_(
                Submission.created_at >= date_from_dt,
                Submission.created_at <= date_to_dt
            )
        ).count()
        
        # Get validation checks in date range
        validation_checks = session.query(ValidationCheck).filter(
            and_(
                ValidationCheck.created_at >= date_from_dt,
                ValidationCheck.created_at <= date_to_dt
            )
        ).all()
        
        # Calculate validation metrics
        total_checks = len(validation_checks)
        pass_count = sum(1 for c in validation_checks if c.status == ValidationStatus.PASS)
        fail_count = sum(1 for c in validation_checks if c.status == ValidationStatus.FAIL)
        needs_review_count = sum(1 for c in validation_checks if c.status == ValidationStatus.NEEDS_REVIEW)
        
        pass_rate = (pass_count / total_checks * 100) if total_checks > 0 else 0
        
        # Display metrics in columns
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("Total Cases", total_cases)
        
        with metric_col2:
            st.metric("Total Submissions", total_submissions)
        
        with metric_col3:
            st.metric("Validation Checks", total_checks)
        
        with metric_col4:
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        
        st.divider()
        
        # Validation Status Breakdown
        st.subheader("✅ Validation Status Breakdown")
        
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            st.metric("✅ Pass", pass_count)
        
        with status_col2:
            st.metric("❌ Fail", fail_count)
        
        with status_col3:
            st.metric("⚠️ Needs Review", needs_review_count)
        
        # Show as bar chart
        if total_checks > 0:
            chart_data = pd.DataFrame({
                "Status": ["Pass", "Fail", "Needs Review"],
                "Count": [pass_count, fail_count, needs_review_count]
            })
            st.bar_chart(chart_data.set_index("Status"))
        
        st.divider()
        
        # Case Status Distribution
        st.subheader("📋 Case Status Distribution")
        
        case_statuses = session.query(
            Case.status,
            func.count(Case.id).label("count")
        ).filter(
            and_(
                Case.created_at >= date_from_dt,
                Case.created_at <= date_to_dt
            )
        ).group_by(Case.status).all()
        
        if case_statuses:
            status_df = pd.DataFrame(case_statuses, columns=["Status", "Count"])
            
            status_display_col1, status_display_col2 = st.columns([1, 2])
            
            with status_display_col1:
                st.dataframe(status_df, hide_index=True, use_container_width=True)
            
            with status_display_col2:
                st.bar_chart(status_df.set_index("Status"))
        else:
            st.info("No cases in selected date range")
        
        st.divider()
        
        # Top Failing Rules
        st.subheader("🔴 Top Failing Rules")
        
        failing_rules = session.query(
            ValidationCheck.rule_id_string,
            func.count(ValidationCheck.id).label("fail_count")
        ).filter(
            and_(
                ValidationCheck.status == ValidationStatus.FAIL,
                ValidationCheck.created_at >= date_from_dt,
                ValidationCheck.created_at <= date_to_dt
            )
        ).group_by(ValidationCheck.rule_id_string).order_by(
            func.count(ValidationCheck.id).desc()
        ).limit(10).all()
        
        if failing_rules:
            rules_df = pd.DataFrame(failing_rules, columns=["Rule ID", "Fail Count"])
            st.dataframe(rules_df, hide_index=True, use_container_width=True)
        else:
            st.info("No failing rules in selected date range")
        
        st.divider()
        
        # Officer Override Statistics
        st.subheader("👤 Officer Override Statistics")
        
        overrides = session.query(OfficerOverride).filter(
            and_(
                OfficerOverride.created_at >= date_from_dt,
                OfficerOverride.created_at <= date_to_dt
            )
        ).all()
        
        override_col1, override_col2 = st.columns(2)
        
        with override_col1:
            st.metric("Total Overrides", len(overrides))
        
        with override_col2:
            unique_officers = len(set(o.officer_name for o in overrides if o.officer_name))
            st.metric("Active Officers", unique_officers)
        
        # Overrides by officer
        if overrides:
            officer_overrides = {}
            for override in overrides:
                officer = override.officer_name or "Unknown"
                officer_overrides[officer] = officer_overrides.get(officer, 0) + 1
            
            officer_df = pd.DataFrame(
                list(officer_overrides.items()),
                columns=["Officer", "Override Count"]
            ).sort_values("Override Count", ascending=False)
            
            st.dataframe(officer_df, hide_index=True, use_container_width=True)
        else:
            st.info("No officer overrides in selected date range")
        
        st.divider()
        
        # Recent Activity
        st.subheader("🕐 Recent Activity")
        
        recent_submissions = session.query(Submission).join(Case).filter(
            Submission.created_at >= date_from_dt
        ).order_by(Submission.created_at.desc()).limit(10).all()
        
        if recent_submissions:
            for submission in recent_submissions:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{submission.case.case_ref if submission.case else 'N/A'}** - {submission.submission_version}")
                        if submission.case and submission.case.site_address:
                            st.markdown(f"_{submission.case.site_address}_")
                    
                    with col2:
                        st.markdown(f"Status: `{submission.status}`")
                        if submission.created_at:
                            st.markdown(f"_{submission.created_at.strftime('%Y-%m-%d %H:%M')}_")
                    
                    with col3:
                        if st.button("View", key=f"recent_{submission.id}"):
                            st.session_state.submission_id = submission.id
                            st.session_state.stage = "results"
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No recent submissions")
        
        st.divider()
        
        # Performance Metrics
        st.subheader("⚡ Performance Metrics")
        
        perf_col1, perf_col2, perf_col3 = st.columns(3)
        
        with perf_col1:
            # Average checks per submission
            avg_checks = total_checks / total_submissions if total_submissions > 0 else 0
            st.metric("Avg Checks per Submission", f"{avg_checks:.1f}")
        
        with perf_col2:
            # Average submissions per case
            avg_submissions = total_submissions / total_cases if total_cases > 0 else 0
            st.metric("Avg Submissions per Case", f"{avg_submissions:.1f}")
        
        with perf_col3:
            # Modification rate (V1+ submissions)
            modifications = session.query(Submission).filter(
                and_(
                    Submission.submission_version != "V0",
                    Submission.created_at >= date_from_dt,
                    Submission.created_at <= date_to_dt
                )
            ).count()
            modification_rate = (modifications / total_submissions * 100) if total_submissions > 0 else 0
            st.metric("Modification Rate", f"{modification_rate:.1f}%")
        
    except Exception as e:
        st.error(f"Failed to load dashboard: {str(e)}")
        st.exception(e)
    
    finally:
        session.close()
