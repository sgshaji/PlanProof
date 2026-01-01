"""
Reusable UI components for PlanProof Streamlit interface.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime


def render_status_badge(status: str) -> str:
    """
    Return HTML for status badge.
    
    Args:
        status: Status string (Complete, Issues Found, In Review, Processing)
        
    Returns:
        HTML badge string
    """
    colors = {
        'Complete': ('green', '#10b981'),
        'Issues Found': ('red', '#ef4444'),
        'In Review': ('blue', '#3b82f6'),
        'Processing': ('orange', '#f59e0b'),
        'Pending': ('gray', '#6b7280')
    }
    
    color_name, color_hex = colors.get(status, ('gray', '#6b7280'))
    
    return f"""
    <span style="
        background-color: {color_hex}20;
        color: {color_hex};
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    ">
        {status}
    </span>
    """


def render_version_badge(version: str, is_modification: bool = False) -> str:
    """
    Return HTML for version badge.
    
    Args:
        version: Version string (V0, V1, V2)
        is_modification: If True, show as modification badge
        
    Returns:
        HTML badge string
    """
    if is_modification:
        return f"""
        <span style="
            background-color: #9333ea20;
            color: #9333ea;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        ">
            🔀 Revision ({version})
        </span>
        """
    else:
        return f"""
        <span style="
            background-color: #3b82f620;
            color: #3b82f6;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        ">
            {version}
        </span>
        """


def render_delta_card(field_changes: List[Dict], doc_changes: List[Dict], spatial_changes: List[Dict]):
    """
    Render delta/change summary card for modification submissions.
    
    Args:
        field_changes: List of field change dicts with 'field', 'before', 'after', 'significance'
        doc_changes: List of document change dicts with 'name', 'type', 'date'
        spatial_changes: List of spatial change dicts with 'metric', 'before', 'after', 'change'
    """
    st.markdown("""
    <div style="
        background-color: #9333ea10;
        border: 2px solid #9333ea40;
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
    ">
        <h3 style="color: #7e22ce; margin-top: 0;">🔀 Changes from Previous Version</h3>
    """, unsafe_allow_html=True)
    
    # Field changes
    if field_changes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Field Changes")
            for change in field_changes:
                significance_badge = ""
                if change.get('significance') == 'high':
                    significance_badge = '<span style="background-color: #ef444420; color: #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 10px; margin-left: 8px;">High Impact</span>'
                
                st.markdown(f"""
                <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #e5e7eb;">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 4px;">
                        {change['field']} {significance_badge}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 14px;">
                        <span style="color: #ef4444; text-decoration: line-through;">{change['before']}</span>
                        <span style="color: #9ca3af;">→</span>
                        <span style="color: #10b981; font-weight: 600;">{change['after']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Document changes
        with col2:
            st.markdown("#### 📄 Document Changes")
            for doc in doc_changes:
                icon = "➕" if doc['type'] == 'added' else ("🔄" if doc['type'] == 'updated' else "➖")
                color = "#10b981" if doc['type'] == 'added' else ("#f59e0b" if doc['type'] == 'updated' else "#ef4444")
                
                st.markdown(f"""
                <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #e5e7eb;">
                    <div style="display: flex; align-items: start; gap: 8px;">
                        <span style="font-size: 16px;">{icon}</span>
                        <div>
                            <div style="font-weight: 600; color: {color};">{doc['name']}</div>
                            <div style="font-size: 12px; color: #6b7280;">{doc['type'].title()} {doc['date']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Spatial changes
    if spatial_changes:
        st.markdown("#### 📐 Spatial Changes")
        cols = st.columns(2)
        for idx, spatial in enumerate(spatial_changes):
            with cols[idx % 2]:
                st.markdown(f"""
                <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #e5e7eb;">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 4px;">{spatial['metric']}</div>
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 14px;">
                        <span style="color: #6b7280;">{spatial['before']}</span>
                        <span style="color: #9ca3af;">→</span>
                        <span style="font-weight: 600; color: #111827;">{spatial['after']}</span>
                        <span style="color: #6b7280; font-size: 12px;">({spatial['change']})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_metric_card(title: str, value: str, change: Optional[str] = None, color: str = "blue"):
    """
    Render a metric card with optional change indicator.
    
    Args:
        title: Metric title
        value: Main value to display
        change: Optional change text (e.g., "↓ -2 from V0")
        color: Color theme (red, amber, green, blue)
    """
    color_map = {
        'red': ('#ef4444', '#fef2f2', '#fee2e2'),
        'amber': ('#f59e0b', '#fffbeb', '#fef3c7'),
        'green': ('#10b981', '#f0fdf4', '#d1fae5'),
        'blue': ('#3b82f6', '#eff6ff', '#dbeafe')
    }
    
    text_color, bg_color, border_color = color_map.get(color, color_map['blue'])
    
    change_html = ""
    if change:
        change_html = f'<div style="font-size: 12px; color: {text_color}; margin-top: 8px;">{change}</div>'
    
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 24px;
        background-color: {bg_color};
        border: 1px solid {border_color};
        border-radius: 12px;
    ">
        <div style="font-size: 36px; font-weight: bold; color: {text_color}; margin-bottom: 8px;">
            {value}
        </div>
        <div style="font-size: 14px; color: {text_color};">
            {title}
        </div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def render_version_timeline(versions: List[Dict[str, Any]]):
    """
    Render version timeline with changes and validation summaries.
    
    Args:
        versions: List of version dicts with version, date, is_current, status, changes, issues_summary
    """
    st.markdown("""
    <style>
    .timeline {
        position: relative;
        padding-left: 40px;
        border-left: 2px solid #e5e7eb;
    }
    .timeline-item {
        position: relative;
        margin-bottom: 32px;
    }
    .timeline-dot {
        position: absolute;
        left: -45px;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 4px solid white;
    }
    .timeline-dot-current {
        background-color: #3b82f6;
    }
    .timeline-dot-past {
        background-color: #d1d5db;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="timeline">', unsafe_allow_html=True)
    
    for version in versions:
        dot_class = "timeline-dot-current" if version['is_current'] else "timeline-dot-past"
        bg_color = "#eff6ff" if version['is_current'] else "#ffffff"
        border_color = "#3b82f6" if version['is_current'] else "#e5e7eb"
        
        current_badge = ""
        if version['is_current']:
            current_badge = '<span style="background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">Current</span>'
        
        status_badge = render_status_badge(version['status'])
        
        changes_html = "".join([f"<li>{change}</li>" for change in version['changes']])
        
        issues = version.get('issues_summary', {})
        errors = issues.get('errors', 0)
        warnings = issues.get('warnings', 0)
        passed = issues.get('passed', 0)
        
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-dot {dot_class}"></div>
            <div style="
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 20px;
            ">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <h4 style="margin: 0; color: #111827;">{version['version']}</h4>
                    {current_badge}
                    {status_badge}
                </div>
                <div style="color: #6b7280; font-size: 14px; margin-bottom: 12px;">
                    🕐 {version['date']}
                </div>
                <div style="display: flex; gap: 16px; margin-bottom: 12px; font-size: 14px;">
                    <span style="color: #ef4444;">{errors} errors</span>
                    <span style="color: #f59e0b;">{warnings} warnings</span>
                    <span style="color: #10b981;">{passed} passed</span>
                </div>
                <div style="font-size: 12px; font-weight: 600; color: #6b7280; margin-bottom: 8px;">
                    Changes:
                </div>
                <ul style="margin: 0; padding-left: 20px; color: #374151; font-size: 14px;">
                    {changes_html}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_issue_resolved_badge(version: str):
    """Render 'Resolved in Vx' badge."""
    return f"""
    <span style="
        background-color: #10b98120;
        color: #10b981;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    ">
        ✓ Resolved in {version}
    </span>
    """
