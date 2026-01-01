"""Resolution UI components for Streamlit."""

from __future__ import annotations

from typing import Dict, Any

import streamlit as st


def render_document_upload(issue: Dict[str, Any]) -> None:
    """Render file uploader for missing documents."""
    label = f"Upload document for {issue.get('issue_id', 'issue')}"
    st.file_uploader(label, type=["pdf"])


def render_explanation_form(issue: Dict[str, Any]) -> None:
    """Render a free-text explanation form."""
    label = f"Explanation for {issue.get('issue_id', 'issue')}"
    st.text_area(label)
    st.button("Submit explanation")


def render_option_selection(issue: Dict[str, Any]) -> None:
    """Render a radio selection for resolution options."""
    options = issue.get("resolution_options", ["Not Applicable"])
    st.radio("Select an option", options)


def render_dismiss_option(issue: Dict[str, Any]) -> None:
    """Render a dismissal option for officer review."""
    st.warning(f"Dismiss issue {issue.get('issue_id', '')} if appropriate.")
    st.button("Dismiss issue")
