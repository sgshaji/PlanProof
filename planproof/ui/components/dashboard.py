"""Dashboard utilities for metrics and issue summaries."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

import streamlit as st


def calculate_severity_counts(issues: List[Dict]) -> Dict[str, int]:
    """Return counts of issues by severity."""
    counts = Counter(issue.get("severity", "info") for issue in issues)
    return {
        "error": counts.get("error", 0),
        "warning": counts.get("warning", 0),
        "info": counts.get("info", 0),
    }


def calculate_status_distribution(issues: List[Dict]) -> Dict[str, int]:
    """Return counts of issues by status."""
    counts = Counter(issue.get("status", "open") for issue in issues)
    return dict(counts)


def group_by_category(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """Group issues by their rule category."""
    grouped: Dict[str, List[Dict]] = {}
    for issue in issues:
        category = issue.get("rule_category", "Uncategorized")
        grouped.setdefault(category, []).append(issue)
    return grouped


def display_completion_metric(run_data: Dict[str, int]) -> None:
    """Display a completion percentage metric."""
    total = run_data.get("total_issues", 0) or 0
    resolved = run_data.get("resolved_issues", 0) or 0
    percentage = int((resolved / total) * 100) if total else 0
    st.metric("Completion", f"{percentage}%")


def display_progress_bar(completed: int, total: int) -> None:
    """Display a progress bar for completion."""
    progress = completed / total if total else 0
    st.progress(progress)


def display_metrics_row(metrics: Dict[str, int]) -> None:
    """Render metric cards in a row."""
    cols = st.columns(3)
    cols[0].metric("Documents", metrics.get("total_documents", 0))
    cols[1].metric("Issues", metrics.get("total_issues", 0))
    cols[2].metric("Blockers", metrics.get("blockers", 0))
