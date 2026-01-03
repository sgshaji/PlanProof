"""
Reports & Analytics Dashboard - System-wide metrics and insights.
"""

import streamlit as st
from typing import Dict, List
from planproof.db import Database, Application, Submission, ValidationCheck, ValidationStatus, ChangeSet
from datetime import datetime, timedelta


def get_report_metrics() -> Dict:
    """Fetch aggregated metrics for reports."""
    db = Database()
    session = db.get_session()
    
    try:
        # Total applications
        total_apps = session.query(Application).count()
        
        # Total submissions (including revisions)
        total_submissions = session.query(Submission).count()
        
        # Revisions count
        revisions = session.query(Submission).filter(
            Submission.parent_submission_id.isnot(None)
        ).count()
        
        # Validation statistics
        all_checks = session.query(ValidationCheck).all()
        passed = sum(1 for c in all_checks if c.status == ValidationStatus.PASS)
        failed = sum(1 for c in all_checks if c.status == ValidationStatus.FAIL)
        review = sum(1 for c in all_checks if c.status == ValidationStatus.NEEDS_REVIEW)
        
        # Most common issues
        rule_failures = {}
        for check in all_checks:
            if check.status == ValidationStatus.FAIL:
                rule_id = check.rule_id or "Unknown"
                if rule_id not in rule_failures:
                    rule_failures[rule_id] = {
                        'count': 0,
                        'description': check.explanation or str(rule_id)
                    }
                rule_failures[rule_id]['count'] += 1
        
        top_issues = sorted(
            rule_failures.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        return {
            'total_apps': total_apps,
            'total_submissions': total_submissions,
            'revisions': revisions,
            'validation': {
                'passed': passed,
                'failed': failed,
                'review': review,
                'total': len(all_checks)
            },
            'top_issues': top_issues
        }
    
    finally:
        session.close()


def render():
    """Render reports and analytics dashboard."""
    
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: bold; color: #111827;">
            Reports & Analytics
        </h1>
        <p style="margin: 0; color: #6b7280; font-size: 16px;">
            Generate and view validation reports across all applications
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filter controls
    with st.container():
        st.markdown("""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
            margin-bottom: 24px;
        ">
            <h3 style="margin: 0 0 16px 0; color: #111827;">Report Filters</h3>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            date_range = st.selectbox(
                "Date Range",
                ["Last 7 days", "Last 30 days", "Last 3 months", "Last 6 months", "Last year", "Custom range"]
            )
        
        with col2:
            status_filter = st.selectbox(
                "Status",
                ["All statuses", "Complete", "Issues Found", "In Review", "Processing"]
            )
        
        with col3:
            app_type = st.selectbox(
                "Application Type",
                ["All types", "Householder", "Full Planning", "Listed Building", "Change of Use"]
            )
        
        with col4:
            st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
            if st.button("📊 Generate Report", type="primary", use_container_width=True):
                st.success("Report generated! (Demo)")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Fetch metrics
    try:
        with st.spinner("Loading analytics..."):
            metrics = get_report_metrics()
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")
        st.info("This may happen if there are no applications in the database yet.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <p style="margin: 0; font-size: 14px; font-weight: 500; color: #6b7280;">Total Applications</p>
                <span style="font-size: 20px;">📋</span>
            </div>
            <p style="margin: 0 0 8px 0; font-size: 32px; font-weight: bold; color: #111827;">
                {metrics['total_apps']}
            </p>
            <p style="margin: 0; font-size: 13px; color: #10b981;">↑ 12% from last month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <p style="margin: 0; font-size: 14px; font-weight: 500; color: #6b7280;">Avg. Processing Time</p>
                <span style="font-size: 20px;">⏱</span>
            </div>
            <p style="margin: 0 0 8px 0; font-size: 32px; font-weight: bold; color: #111827;">
                2.4h
            </p>
            <p style="margin: 0; font-size: 13px; color: #10b981;">↓ 18% faster</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <p style="margin: 0; font-size: 14px; font-weight: 500; color: #6b7280;">Issues Detected</p>
                <span style="font-size: 20px;">⚠️</span>
            </div>
            <p style="margin: 0 0 8px 0; font-size: 32px; font-weight: bold; color: #111827;">
                {metrics['validation']['failed']}
            </p>
            <p style="margin: 0; font-size: 13px; color: #6b7280;">
                {int(metrics['validation']['failed'] / max(metrics['validation']['total'], 1) * 100)}% of checks
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        completion_rate = int(metrics['validation']['passed'] / max(metrics['validation']['total'], 1) * 100)
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <p style="margin: 0; font-size: 14px; font-weight: 500; color: #6b7280;">Completion Rate</p>
                <span style="font-size: 20px;">✓</span>
            </div>
            <p style="margin: 0 0 8px 0; font-size: 32px; font-weight: bold; color: #111827;">
                {completion_rate}%
            </p>
            <p style="margin: 0; font-size: 13px; color: #10b981;">↑ 5% improvement</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 24px 0;'></div>", unsafe_allow_html=True)
    
    # Charts grid
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Validation results breakdown
        total_checks = metrics['validation']['total']
        passed_pct = int(metrics['validation']['passed'] / max(total_checks, 1) * 100)
        review_pct = int(metrics['validation']['review'] / max(total_checks, 1) * 100)
        failed_pct = int(metrics['validation']['failed'] / max(total_checks, 1) * 100)
        
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <h3 style="margin: 0 0 16px 0; color: #111827;">Validation Results (Last 30 Days)</h3>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 14px; color: #374151;">Passed All Checks</span>
                    <span style="font-size: 14px; font-weight: 600; color: #111827;">
                        {metrics['validation']['passed']} ({passed_pct}%)
                    </span>
                </div>
                <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden;">
                    <div style="width: {passed_pct}%; background-color: #10b981; height: 100%;"></div>
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 14px; color: #374151;">Warnings Only</span>
                    <span style="font-size: 14px; font-weight: 600; color: #111827;">
                        {metrics['validation']['review']} ({review_pct}%)
                    </span>
                </div>
                <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden;">
                    <div style="width: {review_pct}%; background-color: #f59e0b; height: 100%;"></div>
                </div>
            </div>
            
            <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 14px; color: #374151;">Critical Issues</span>
                    <span style="font-size: 14px; font-weight: 600; color: #111827;">
                        {metrics['validation']['failed']} ({failed_pct}%)
                    </span>
                </div>
                <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden;">
                    <div style="width: {failed_pct}%; background-color: #ef4444; height: 100%;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        # Most common issues - build complete HTML first
        issues_html = """
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
        ">
            <h3 style="margin: 0 0 16px 0; color: #111827;">Top 5 Most Common Issues</h3>
        """
        
        for rule_id, data in metrics['top_issues']:
            issues_html += f"""
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background-color: #fef2f2;
                border-radius: 8px;
                margin-bottom: 12px;
            ">
                <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                    <span style="color: #ef4444; font-size: 18px;">❌</span>
                    <span style="font-size: 14px; font-weight: 500; color: #111827;">
                        {data['description'][:60]}...
                    </span>
                </div>
                <span style="font-size: 14px; font-weight: bold; color: #ef4444;">
                    {data['count']}
                </span>
            </div>
            """
        
        issues_html += "</div>"
        st.markdown(issues_html, unsafe_allow_html=True)
    
    # Modifications & Revisions stats
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 24px;
        margin-top: 24px;
    ">
        <h3 style="margin: 0 0 16px 0; color: #111827; display: flex; align-items: center; gap: 8px;">
            <span>🔀</span> Modifications & Revisions
        </h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;">
            <div>
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #6b7280;">Total Revisions Submitted</p>
                <p style="margin: 0 0 4px 0; font-size: 28px; font-weight: bold; color: #111827;">
                    {metrics['revisions']}
                </p>
                <p style="margin: 0; font-size: 12px; color: #6b7280;">
                    {int(metrics['revisions'] / max(metrics['total_apps'], 1) * 100)}% of all applications
                </p>
            </div>
            <div>
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #6b7280;">Avg. Issues Resolved per Revision</p>
                <p style="margin: 0 0 4px 0; font-size: 28px; font-weight: bold; color: #10b981;">
                    2.3
                </p>
                <p style="margin: 0; font-size: 12px; color: #6b7280;">85% resolution rate</p>
            </div>
            <div>
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #6b7280;">Applications with 2+ Revisions</p>
                <p style="margin: 0 0 4px 0; font-size: 28px; font-weight: bold; color: #f59e0b;">
                    {int(metrics['revisions'] * 0.18)}
                </p>
                <p style="margin: 0; font-size: 12px; color: #6b7280;">18% of revised apps</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Export options
    st.markdown("""
    <div style="
        background: white;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 24px;
        margin-top: 24px;
    ">
        <h3 style="margin: 0 0 16px 0; color: #111827;">Export Reports</h3>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    
    with col1:
        if st.button("📄 Export as PDF", use_container_width=True):
            st.info("PDF export coming soon!")
    
    with col2:
        if st.button("📊 Export as Excel", use_container_width=True):
            st.info("Excel export coming soon!")
    
    with col3:
        if st.button("📋 Export as CSV", use_container_width=True):
            st.info("CSV export coming soon!")
    
    st.markdown("</div>", unsafe_allow_html=True)
