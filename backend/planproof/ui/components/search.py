"""Search UI components."""

from __future__ import annotations

import streamlit as st

from planproof.services import search_service


def render_search_interface() -> None:
    """Render a simple search box for applications."""
    query = st.text_input("Search applications")
    if not query:
        return
    service = search_service.SearchService()
    results = service.search_applications(query=query)
    if isinstance(results, list):
        st.write(results)
    else:
        st.write(results.get("results", []))
