"""Session state helpers for Streamlit UI."""

from __future__ import annotations

import streamlit as st


def initialize_session_state() -> None:
    """Initialize common session state keys."""
    st.session_state.setdefault("run_id", None)
    st.session_state.setdefault("selected_case", None)


def set_current_run(run_id: int) -> None:
    """Store the current run ID."""
    st.session_state["run_id"] = run_id


def get_current_run() -> int | None:
    """Return the current run ID, if set."""
    return st.session_state.get("run_id")
