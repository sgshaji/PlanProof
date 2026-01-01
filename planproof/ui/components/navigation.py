"""Navigation components for Streamlit UI."""

from __future__ import annotations

from typing import List

import streamlit as st


def render_sidebar() -> str:
    """Render sidebar navigation."""
    sidebar = st.sidebar
    if callable(sidebar):
        sidebar = sidebar()
    return sidebar.radio("Navigate", ["Dashboard", "Cases", "Reports"])


def render_tabs(tabs: List[str]):
    """Render tab navigation."""
    return st.tabs(tabs)
