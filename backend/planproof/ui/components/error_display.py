"""Error display helpers."""

from __future__ import annotations

import streamlit as st


def show_database_error(message: str) -> None:
    """Display a database error message."""
    st.error(f"Database error: {message}")


def show_validation_warning(message: str) -> None:
    """Display a validation warning message."""
    st.warning(message)
