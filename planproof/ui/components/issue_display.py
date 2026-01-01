"""UI helpers for rendering issues in Streamlit."""

from __future__ import annotations

from typing import Dict, Any

import streamlit as st


def display_issue(issue: Dict[str, Any]) -> None:
    """Display an issue using severity-specific styling."""
    severity = (issue.get("severity") or "").lower()
    message = issue.get("message", "Issue detected")
    if severity == "error":
        st.error(message)
    elif severity == "warning":
        st.warning(message)
    else:
        st.info(message)


def format_issue_card(issue: Dict[str, Any]) -> str:
    """Return HTML for a compact issue card."""
    issue_id = issue.get("issue_id", "UNKNOWN")
    severity = issue.get("severity", "info")
    category = issue.get("rule_category", "General")
    message = issue.get("message", "")
    return (
        f"<div class='issue-card {severity}'>"
        f"<strong>{issue_id}</strong> · {category}<br/>"
        f"{message}"
        "</div>"
    )


def display_evidence(issue: Dict[str, Any]) -> None:
    """Render evidence details for an issue."""
    with st.expander("Evidence", expanded=False):
        st.write(f"Page: {issue.get('evidence_page', 'N/A')}")
        if issue.get("evidence_text"):
            st.write(issue["evidence_text"])
        if issue.get("bounding_box"):
            st.write(f"Bounding box: {issue['bounding_box']}")
