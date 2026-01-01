"""
Breadcrumb navigation component.
"""

import streamlit as st


def render_breadcrumb(items: list[tuple[str, str]], current: str):
    """
    Render breadcrumb navigation.

    Args:
        items: List of (label, action_key) tuples
        current: Current page label

    Example:
        render_breadcrumb([("Home", "home"), ("My Cases", "cases")], "Case Details")
    """
    breadcrumb_html = '<div style="margin-bottom: 16px; color: #6b7280; font-size: 14px;">'

    for i, (label, action_key) in enumerate(items):
        if i > 0:
            breadcrumb_html += ' <span style="margin: 0 8px;">/</span> '

        breadcrumb_html += f'<span style="cursor: pointer; color: #3b82f6;" data-action="{action_key}">{label}</span>'

    breadcrumb_html += f' <span style="margin: 0 8px;">/</span> <span style="color: #111827; font-weight: 600;">{current}</span>'
    breadcrumb_html += '</div>'

    st.markdown(breadcrumb_html, unsafe_allow_html=True)


def render_back_button(label: str = "← Back", callback_key: str = "back"):
    """
    Render a back button.

    Args:
        label: Button label
        callback_key: Key for the button action

    Returns:
        bool: True if button was clicked
    """
    return st.button(label, key=callback_key)
