"""Filtering UI components."""

from __future__ import annotations

from typing import List

import streamlit as st


def render_severity_filter() -> str:
    """Render a severity dropdown."""
    return st.selectbox("Severity", ["all", "error", "warning", "info"])


def render_category_filter(categories: List[str]) -> List[str]:
    """Render a category multi-select."""
    return st.multiselect("Categories", options=categories)
