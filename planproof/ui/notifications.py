"""
Notification System for Streamlit UI - Display in-app alerts and messages.
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Any


def init_notifications():
    """Initialize notification system in session state."""
    if "notifications" not in st.session_state:
        st.session_state.notifications = []


def add_notification(message: str, type: str = "info", duration: int = 5):
    """
    Add a notification to the session.

    Args:
        message: Notification message
        type: Type of notification (success, info, warning, error)
        duration: How long to show the notification (seconds), 0 = permanent
    """
    init_notifications()

    notification = {
        "message": message,
        "type": type,
        "timestamp": datetime.now(),
        "duration": duration,
        "id": len(st.session_state.notifications)
    }

    st.session_state.notifications.append(notification)


def show_notifications():
    """Display all active notifications."""
    init_notifications()

    if not st.session_state.notifications:
        return

    # Container for notifications
    notification_container = st.container()

    with notification_container:
        # Display notifications in reverse order (newest first)
        for notification in reversed(st.session_state.notifications[-5:]):  # Show last 5
            age = (datetime.now() - notification["timestamp"]).total_seconds()

            # Skip expired notifications
            if notification["duration"] > 0 and age > notification["duration"]:
                continue

            # Render notification based on type
            if notification["type"] == "success":
                st.success(f"✅ {notification['message']}", icon="✅")
            elif notification["type"] == "info":
                st.info(f"ℹ️ {notification['message']}", icon="ℹ️")
            elif notification["type"] == "warning":
                st.warning(f"⚠️ {notification['message']}", icon="⚠️")
            elif notification["type"] == "error":
                st.error(f"❌ {notification['message']}", icon="❌")


def clear_notifications():
    """Clear all notifications."""
    st.session_state.notifications = []


def add_success(message: str):
    """Convenience function to add success notification."""
    add_notification(message, "success")


def add_info(message: str):
    """Convenience function to add info notification."""
    add_notification(message, "info")


def add_warning(message: str):
    """Convenience function to add warning notification."""
    add_notification(message, "warning")


def add_error(message: str):
    """Convenience function to add error notification."""
    add_notification(message, "error")
