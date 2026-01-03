"""
UI Error Handling and Utilities Module

Provides user-friendly error handling and common UI operations.
"""
import streamlit as st
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def handle_ui_errors(func: Callable = None):
    """
    Decorator for handling errors in UI operations gracefully.
    """
    if func is None:
        # Called with parentheses, return decorator
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    # Log the full error
                    logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
                    
                    # Show user-friendly message
                    st.error(f"❌ An error occurred. Please try again or contact support.")
                    
                    # Show details in expander
                    with st.expander("🔍 Technical Details (for debugging)"):
                        st.code(str(e))
                    
                    return None
            return wrapper
        return decorator
    else:
        # Called without parentheses
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                st.error(f"❌ An error occurred. Please try again or contact support.")
                with st.expander("🔍 Technical Details (for debugging)"):
                    st.code(str(e))
                return None
        return wrapper


def safe_db_operation(func: Callable) -> Callable:
    """Decorator specifically for database operations."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}", exc_info=True)
            st.error(f"❌ Unable to access database. Please check your connection and try again.")
            return None
    return wrapper


def safe_file_operation(func: Callable) -> Callable:
    """Decorator specifically for file operations."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"File error in {func.__name__}: {str(e)}", exc_info=True)
            st.error(f"❌ Unable to process file. Please ensure the file is valid and try again.")
            return None
    return wrapper


def show_success(message: str):
    """Show success message to user."""
    st.success(f"✅ {message}")


def show_error(message: str):
    """Show error message to user."""
    st.error(f"❌ {message}")


def show_warning(message: str):
    """Show warning message to user."""
    st.warning(f"⚠️ {message}")


def show_info(message: str):
    """Show info message to user."""
    st.info(f"ℹ️ {message}")


def with_spinner(message: str = "Processing..."):
    """
    Context manager for showing spinner during operations.
    
    Usage:
        with with_spinner("Loading data..."):
            data = load_data()
    """
    return st.spinner(message)


def validate_required_fields(**fields) -> bool:
    """
    Validate that required fields are not empty.
    
    Returns:
        True if all fields valid, False otherwise (also shows error message)
    
    Usage:
        if not validate_required_fields(
            application_ref=app_ref,
            applicant_name=applicant_name,
            files=uploaded_files
        ):
            return
    """
    for field_name, field_value in fields.items():
        if not field_value:
            st.error(f"❌ {field_name.replace('_', ' ').title()} is required")
            return False
        
        # Check for empty lists
        if isinstance(field_value, (list, tuple)) and len(field_value) == 0:
            st.error(f"❌ {field_name.replace('_', ' ').title()} is required")
            return False
    
    return True


def show_empty_state(icon: str = "📋", title: str = "No Data", message: str = ""):
    """
    Show empty state when no data is available.
    """
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 64px 24px;
        background: white;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    ">
        <div style="font-size: 48px; margin-bottom: 16px;">{icon}</div>
        <h3 style="color: #111827; margin-bottom: 8px;">{title}</h3>
        <p style="color: #6b7280;">{message}</p>
    </div>
    """, unsafe_allow_html=True)
