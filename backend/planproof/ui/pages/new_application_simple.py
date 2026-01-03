"""
New Application Page - Simplified version with native Streamlit components.
"""

import streamlit as st
import time
from pathlib import Path
from planproof.ui.utils import (
    handle_ui_errors, safe_db_operation, safe_file_operation,
    show_success, show_warning, show_info,
    with_spinner, validate_required_fields
)
import logging

logger = logging.getLogger(__name__)


def render_processing_screen(run_id: int, app_ref: str):
    """Show real-time processing progress with actual status from orchestrator."""
    from planproof.ui.run_orchestrator import get_run_status

    st.markdown("### 🔄 Processing Your Application")
    st.markdown(f"**Application Reference:** {app_ref}")
    st.markdown(f"**Run ID:** {run_id}")
    st.markdown("---")

    # Get actual run status
    status = get_run_status(run_id)
    state = status.get("state", "unknown")

    # Progress information
    progress_info = status.get("progress", {})
    current = progress_info.get("current", 0)
    total = progress_info.get("total", 1)
    current_file = progress_info.get("current_file", "")

    # Show status
    if state == "running":
        st.info("🔄 Processing in progress...")
        if total > 0:
            progress = current / total
            st.progress(progress)
            st.markdown(f"**Progress:** {current} / {total} documents processed")
            if current_file:
                st.markdown(f"**Current file:** {current_file}")

        # Auto-refresh every 2 seconds
        st.markdown("*Auto-refreshing...*")
        time.sleep(2)
        st.rerun()

    elif state == "completed":
        st.success("✅ Validation complete!")
        st.progress(1.0)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📋 View Results", type="primary", use_container_width=True):
                st.session_state.processing = False
                st.session_state.selected_case = app_ref
                st.rerun()
        with col2:
            if st.button("🆕 New Application", use_container_width=True):
                st.session_state.processing = False
                st.session_state.run_id = None
                st.rerun()

    elif state == "completed_with_errors":
        st.warning("⚠️ Validation completed with some errors")
        st.progress(1.0)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📋 View Results", type="primary", use_container_width=True):
                st.session_state.processing = False
                st.session_state.selected_case = app_ref
                st.rerun()
        with col2:
            if st.button("🆕 New Application", use_container_width=True):
                st.session_state.processing = False
                st.session_state.run_id = None
                st.rerun()

    elif state == "failed":
        st.error("❌ Processing failed")

        error_msg = status.get("error", "Unknown error")
        st.error(f"**Error:** {error_msg}")

        if status.get("traceback"):
            with st.expander("View Error Details"):
                st.code(status.get("traceback"), language="text")

        if st.button("🆕 Start Over", type="primary"):
            st.session_state.processing = False
            st.session_state.run_id = None
            st.rerun()

    elif state == "not_found":
        st.error(f"❌ Run {run_id} not found")
        if st.button("🆕 Start Over", type="primary"):
            st.session_state.processing = False
            st.session_state.run_id = None
            st.rerun()

    else:
        st.warning(f"Unknown state: {state}")
        if st.button("🔄 Refresh"):
            st.rerun()


def render():
    """Render the New Application page."""
    
    # Initialize session state
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    if st.session_state.processing:
        render_processing_screen(
            st.session_state.get('current_run_id'),
            st.session_state.get('current_app_ref')
        )
        return
    
    st.markdown("## 📤 New Planning Application")
    st.markdown("Upload and validate planning application documents")
    st.markdown("---")
    
    # Use Streamlit's native form
    with st.form("upload_form", clear_on_submit=False):
        st.markdown("### Application Details")
        
        app_ref = st.text_input(
            "Application Reference *",
            placeholder="e.g., APP/2024/001",
            help="Use your local authority's application reference format"
        )
        
        applicant_name = st.text_input(
            "Applicant Name (Optional)",
            placeholder="Enter applicant name"
        )
        
        st.markdown("### Upload Documents")
        
        uploaded_files = st.file_uploader(
            "Select PDF files to upload",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload all relevant planning documents"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            submit_button = st.form_submit_button(
                "🚀 Start Validation",
                use_container_width=True,
                type="primary"
            )
    
    # Form validation and submission
    if submit_button:
        # Validation checks
        errors = []

        if not app_ref:
            errors.append("Application Reference is required")

        if not uploaded_files:
            errors.append("Please upload at least one PDF document")
        else:
            # File size validation (max 100MB per file)
            MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes
            for file in uploaded_files:
                if file.size > MAX_FILE_SIZE:
                    errors.append(f"File '{file.name}' is too large ({file.size / 1024 / 1024:.1f}MB). Maximum size is 100MB")

            # File count validation (max 20 files)
            MAX_FILES = 20
            if len(uploaded_files) > MAX_FILES:
                errors.append(f"Too many files. Maximum is {MAX_FILES} files, you uploaded {len(uploaded_files)}")

            # Check for duplicate filenames
            filenames = [f.name for f in uploaded_files]
            duplicates = [name for name in filenames if filenames.count(name) > 1]
            if duplicates:
                errors.append(f"Duplicate filenames found: {', '.join(set(duplicates))}")

        # Check for duplicate application reference
        if app_ref:
            from planproof.db import Database
            db = Database()
            existing_app = db.get_application_by_ref(app_ref)
            if existing_app:
                st.warning(f"⚠️ Application '{app_ref}' already exists. This will create a new revision.")

        # Show errors if any
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Start processing
            with with_spinner("Starting validation..."):
                try:
                    # Start the validation run
                    from planproof.ui.run_orchestrator import start_run

                    # Pass UploadedFile objects directly (not file paths!)
                    run_id = start_run(
                        app_ref=app_ref,  # Correct parameter name
                        files=list(uploaded_files),  # Correct parameter name and type
                        applicant_name=applicant_name if applicant_name else None,
                        parent_submission_id=None  # New application
                    )

                    # Store run ID in session state
                    st.session_state.run_id = run_id  # Use consistent key
                    st.session_state.current_run_id = run_id  # Also set this for compatibility
                    st.session_state.current_app_ref = app_ref
                    st.session_state.processing = True

                    show_success(f"Validation started! Run ID: {run_id}")
                    time.sleep(1)  # Give user time to see message
                    st.rerun()

                except Exception as e:
                    logger.error(f"Error starting validation: {str(e)}", exc_info=True)
                    st.error(f"❌ Unable to start validation. Please ensure all services are running and try again.")
                    with st.expander("🔍 Technical Details"):
                        st.code(str(e))
                    st.session_state.processing = False
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
