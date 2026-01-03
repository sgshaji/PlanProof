"""
Upload page - Document upload and application reference input.
"""

import streamlit as st
from planproof.ui.run_orchestrator import start_run


def render():
    """Render the upload page."""
    st.title("📤 Upload Planning Documents")
    st.markdown("Upload PDF documents for validation processing.")
    
    # Application reference input
    app_ref = st.text_input(
        "Application Reference",
        placeholder="APP/2024/001",
        help="Enter the planning application reference number"
    )
    
    # Applicant name (optional)
    applicant_name = st.text_input(
        "Applicant Name (Optional)",
        placeholder="John Smith",
        help="Optional: Enter the applicant name"
    )
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload PDF Documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to process"
    )
    
    # Show uploaded files
    if uploaded_files:
        st.markdown("### Uploaded Files")
        for file in uploaded_files:
            st.text(f"📄 {file.name} ({file.size:,} bytes)")
    
    # Process button
    col1, col2 = st.columns([1, 4])
    
    with col1:
        process_button = st.button(
            "🚀 Process Documents",
            type="primary",
            disabled=not (app_ref and uploaded_files)
        )
    
    if process_button:
        if not app_ref:
            st.error("Please enter an application reference")
            return
        
        if not uploaded_files:
            st.error("Please upload at least one PDF file")
            return
        
        # Start processing
        with st.spinner("Starting processing run..."):
            try:
                run_id = start_run(
                    app_ref=app_ref,
                    files=list(uploaded_files),
                    applicant_name=applicant_name if applicant_name else None
                )
                
                # Store in session state
                st.session_state.run_id = run_id
                st.session_state.stage = "status"
                
                # Redirect to status page
                st.success(f"Processing started! Run ID: {run_id}")
                st.info("Redirecting to status page...")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error starting processing: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

