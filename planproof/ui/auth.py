"""
UI Authentication Module - Simple authentication for Streamlit UI.

For production deployment, configure via environment variables:
- UI_ALLOWED_USERS: Comma-separated list of username:password pairs
- UI_SESSION_TIMEOUT_MINUTES: Session timeout (default: 480 = 8 hours)

Example:
    UI_ALLOWED_USERS=officer1:pass123,officer2:secure456,admin:admin123
"""

import os
import hashlib
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_allowed_users() -> Dict[str, str]:
    """
    Get allowed users from environment variable.

    Returns:
        Dict mapping username to hashed password
    """
    users_env = os.getenv("UI_ALLOWED_USERS", "")

    # If not configured, allow demo login for MVP
    if not users_env:
        return {
            "officer": hash_password("demo123"),
            "admin": hash_password("admin123")
        }

    users = {}
    for user_pass in users_env.split(","):
        if ":" in user_pass:
            username, password = user_pass.split(":", 1)
            users[username.strip()] = hash_password(password.strip())

    return users


def check_authentication() -> bool:
    """
    Check if user is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    # Check if authentication is enabled
    auth_enabled = os.getenv("UI_AUTH_ENABLED", "true").lower() == "true"

    if not auth_enabled:
        # Authentication disabled - allow all access
        return True

    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.login_time = None

    # Check session timeout
    if st.session_state.authenticated and st.session_state.login_time:
        timeout_minutes = int(os.getenv("UI_SESSION_TIMEOUT_MINUTES", "480"))
        session_age = datetime.now() - st.session_state.login_time

        if session_age > timedelta(minutes=timeout_minutes):
            # Session expired
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.login_time = None
            st.warning("⏰ Session expired. Please log in again.")
            return False

    return st.session_state.authenticated


def show_login_page():
    """Display login page."""
    st.markdown(
        """
        <style>
            .login-container {
                max-width: 400px;
                margin: 100px auto;
                padding: 40px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .login-header {
                text-align: center;
                margin-bottom: 32px;
            }
            .login-logo {
                width: 64px;
                height: 64px;
                margin: 0 auto 16px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
            <div class="login-container">
                <div class="login-header">
                    <div class="login-logo">📋</div>
                    <h1 style="margin: 0; font-size: 24px;">PlanProof</h1>
                    <p style="color: #6b7280; margin-top: 8px;">Planning Validation System</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### 🔐 Officer Login")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                submit = st.form_submit_button("🔓 Sign In", use_container_width=True, type="primary")

            with col_btn2:
                if st.form_submit_button("ℹ️ Help", use_container_width=True):
                    st.info("""
                    **Demo Credentials:**
                    - Username: `officer` / Password: `demo123`
                    - Username: `admin` / Password: `admin123`

                    **For Production:**
                    Configure via `UI_ALLOWED_USERS` environment variable.
                    """)

        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                allowed_users = get_allowed_users()
                hashed_password = hash_password(password)

                if username in allowed_users and allowed_users[username] == hashed_password:
                    # Successful login
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.login_time = datetime.now()
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

        st.markdown("---")
        st.caption("PlanProof v1.0 | Planning Validation System")


def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.login_time = None
    st.rerun()


def get_current_username() -> Optional[str]:
    """Get the currently logged-in username."""
    return st.session_state.get("username")


def require_auth(func):
    """
    Decorator to require authentication for a function.

    Usage:
        @require_auth
        def my_page():
            st.write("Protected content")
    """
    def wrapper(*args, **kwargs):
        if not check_authentication():
            show_login_page()
            return None
        return func(*args, **kwargs)
    return wrapper
