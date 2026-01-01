"""
New Application Page - Simplified version with native Streamlit components.
"""

import streamlit as st
import time
from pathlib import Path
import tempfile


def render_processing_screen(run_id: int, app_ref: str):
    """Show real-time processing progress."""
    
    st.markdown("### 🔄 Processing Your Application")
    st.markdown(f"**Application Reference:** {app_ref}")
    st.markdown(f"**Run ID:** {run_id}")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Simulated processing steps
    steps = [
        "Uploading documents...",
        "Extracting text and metadata...",
        "Identifying document types...",
        "Checking required documents...",
        "Validating measurements...",
        "Checking policy compliance...",
        "Analyzing spatial data...",
        "Generating report..."
    ]
    
    for idx, step in enumerate(steps):
        progress = (idx + 1) / len(steps)
        progress_bar.progress(progress)
        status_text.markdown(f"**Step {idx + 1}/{len(steps)}:** {step}")
        time.sleep(0.5)
    
    st.success("✅ Validation complete!")
    
    if st.button("View Results", type="primary"):
        st.session_state.processing = False
        st.session_state.active_tab = "My Cases"
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
        if not app_ref:
            st.error("❌ Application Reference is required")
        elif not uploaded_files:
            st.error("❌ Please upload at least one PDF document")
        else:
            # Start processing
            st.session_state.processing = True
            st.session_state.current_app_ref = app_ref
            
            try:
                # Save files and start run
                from planproof.ui.run_orchestrator import start_run
                
                temp_dir = Path(tempfile.mkdtemp())
                file_paths = []
                
                for uploaded_file in uploaded_files:
                    file_path = temp_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.read())
                    file_paths.append(str(file_path))
                
                # Start the validation run
                run_id = start_run(
                    pdf_paths=file_paths,
                    application_ref=app_ref,
                    applicant_name=applicant_name or None,
                    parent_submission_id=None  # New application
                )
                
                st.session_state.current_run_id = run_id
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error starting validation: {str(e)}")
                st.session_state.processing = False
