"""Export helpers for UI."""

from __future__ import annotations

import csv
import io
from typing import List, Dict, Any

import streamlit as st


def _issues_to_csv(issues: List[Dict[str, Any]]) -> str:
    buffer = io.StringIO()
    if not issues:
        return ""
    writer = csv.DictWriter(buffer, fieldnames=issues[0].keys())
    writer.writeheader()
    writer.writerows(issues)
    return buffer.getvalue()


def render_csv_download(issues: List[Dict[str, Any]]) -> None:
    """Render a CSV download button for issues."""
    csv_data = _issues_to_csv(issues)
    st.download_button(
        label="Download issues CSV",
        data=csv_data,
        file_name="issues.csv",
        mime="text/csv",
    )


def render_decision_package_download(run_id: int) -> None:
    """Render a placeholder for decision package download."""
    st.download_button(
        label=f"Download decision package {run_id}",
        data="{}",
        file_name=f"decision_package_{run_id}.json",
        mime="application/json",
    )
