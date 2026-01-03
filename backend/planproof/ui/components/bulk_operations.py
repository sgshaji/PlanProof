"""Bulk operations UI components."""

from __future__ import annotations

from typing import List, Dict, Any

import streamlit as st


def render_bulk_selector(issues: List[Dict[str, Any]]) -> List[str]:
    """Render checkboxes to select issues for bulk actions."""
    selected = []
    for issue in issues:
        issue_id = issue.get("issue_id", "unknown")
        if st.checkbox(f"Select {issue_id}", key=f"select_{issue_id}"):
            selected.append(issue_id)
    if selected:
        st.button("Apply bulk action")
    return selected


def render_bulk_upload() -> None:
    """Render a bulk document uploader."""
    st.file_uploader("Upload multiple documents", type=["pdf"], accept_multiple_files=True)
    st.button("Process uploads")
