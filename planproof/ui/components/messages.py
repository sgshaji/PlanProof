"""Reusable message helpers."""

from __future__ import annotations

import streamlit as st


def show_info(message: str) -> None:
    """Display an informational message."""
    st.info(message)
