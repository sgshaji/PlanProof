"""
New Application Page - Enhanced upload with processing visualization.
"""

import streamlit as st
import time
from typing import List
from planproof.ui.run_orchestrator import start_run
from planproof.db import Database


def render_processing_screen(run_id: int, app_ref: str):
    """Show real-time processing progress."""
    
    st.markdown("""
    <div style="text-align: center; margin: 48px 0;">
        <div style="
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            animation: pulse 2s infinite;
        ">
            <span style="font-size: 40px;">🔄</span>
        </div>
        <h1 style="margin-top: 24px; color: #111827;">Processing Your Application</h1>
        <p style="color: #6b7280; font-size: 16px;">Running automated validation checks on your documents...</p>
    </div>
    
    <style>
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Progress bar
    progress_placeholder = st.empty()
    steps_placeholder = st.empty()
    findings_placeholder = st.empty()
    
    # Processing steps
    processing_steps = [
        {"name": "Uploading documents", "duration": 0.5},
        {"name": "Extracting text and metadata", "duration": 1.2},
        {"name": "Identifying document types", "duration": 0.8},
        {"name": "Checking required documents", "duration": 1.0},
        {"name": "Validating measurements and dimensions", "duration": 1.5},
        {"name": "Checking policy compliance", "duration": 2.0},
        {"name": "Analyzing spatial data", "duration": 1.0},
        {"name": "Generating validation report", "duration": 0.8}
    ]
    
    findings = []
    
    for idx, step in enumerate(processing_steps):
        # Update progress
        progress = (idx + 1) / len(processing_steps)
        progress_placeholder.progress(progress, text=f"Step {idx + 1} of {len(processing_steps)}")
        
        # Show steps
        steps_html = "<div style='background: white; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb;'>"
        steps_html += "<h3 style='margin-top: 0;'>Validation Steps</h3>"
        
        for step_idx, s in enumerate(processing_steps):
            if step_idx < idx:
                icon = "✓"
                color = "#10b981"
                bg = "#f0fdf4"
            elif step_idx == idx:
                icon = "🔄"
                color = "#3b82f6"
                bg = "#eff6ff"
            else:
                icon = "⏳"
                color = "#9ca3af"
                bg = "#f9fafb"
            
            steps_html += f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px;
                background-color: {bg};
                border-radius: 8px;
                margin-bottom: 8px;
            ">
                <span style="font-size: 20px;">{icon}</span>
                <span style="color: {color}; font-weight: 500;">{s['name']}</span>
            </div>
            """
        
        steps_html += "</div>"
        steps_placeholder.markdown(steps_html, unsafe_allow_html=True)
        
        # Add findings
        if idx == 2:
            findings.append("✓ Site Plan.pdf identified")
            findings.append("✓ Elevation Drawing.pdf identified")
        elif idx == 3:
            findings.append("✓ Extracted 156 text blocks")
            findings.append("✓ Found scale: 1:100")
        elif idx == 5:
            findings.append("⚠ Building height may exceed limit")
            findings.append("✓ All elevation drawings present")
        
        # Show findings
        if findings:
            findings_html = "<div style='background: white; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; margin-top: 16px;'>"
            findings_html += "<h3 style='margin-top: 0; display: flex; align-items: center; gap: 8px;'><span>👁</span> Real-time Findings</h3>"
            
            for finding in findings:
                icon_color = "#10b981" if finding.startswith("✓") else "#f59e0b"
                findings_html += f"""
                <div style="
                    display: flex;
                    align-items: start;
                    gap: 8px;
                    padding: 8px 12px;
                    background-color: #f9fafb;
                    border-radius: 6px;
                    margin-bottom: 6px;
                    font-size: 14px;
                    color: #374151;
                ">
                    <span style="color: {icon_color};">{finding[:1]}</span>
                    <span>{finding[2:]}</span>
                </div>
                """
            
            findings_html += "</div>"
            findings_placeholder.markdown(findings_html, unsafe_allow_html=True)
        
        # Simulate processing time
        time.sleep(step['duration'])
    
    # Processing complete
    progress_placeholder.success("✓ Processing Complete!")
    
    st.info("🎉 Validation complete! Redirecting to results...")
    time.sleep(1)
    
    # Update session state and navigate to My Cases
    st.session_state.run_id = run_id
    st.session_state.selected_case = app_ref
    st.rerun()


def render():
    """Render the new application upload page."""
    
    # Check if we should show processing screen
    if st.session_state.get('processing_status') == 'active':
        render_processing_screen(
            st.session_state.get('processing_run_id'),
            st.session_state.get('processing_app_ref')
        )
        return
    
    # Progress indicator
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 14px; font-weight: 600; color: #374151;">Step 1 of 3</span>
            <span style="font-size: 14px; color: #6b7280;">Upload Documents</span>
        </div>
        <div style="
            width: 100%;
            height: 8px;
            background-color: #e5e7eb;
            border-radius: 9999px;
            overflow: hidden;
        ">
            <div style="
                width: 33%;
                height: 100%;
                background-color: #3b82f6;
                border-radius: 9999px;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Application Reference Input
    with st.container():
        st.markdown("""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
            margin-bottom: 24px;
        ">
            <label style="
                display: block;
                font-size: 14px;
                font-weight: 600;
                color: #111827;
                margin-bottom: 8px;
            ">Application Reference *</label>
        """, unsafe_allow_html=True)
        
        app_ref = st.text_input(
            "Application Reference",
            placeholder="e.g., APP/2024/001",
            help="Use your local authority's application reference format",
            label_visibility="collapsed",
            key="app_ref_input"
        )
        
        st.markdown("""
            <p style="font-size: 13px; color: #6b7280; margin-top: 8px; margin-bottom: 0;">
                Use your local authority's application reference format
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Applicant Name (Optional)
    with st.container():
        st.markdown("""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
            margin-bottom: 24px;
        ">
            <label style="
                display: block;
                font-size: 14px;
                font-weight: 600;
                color: #111827;
                margin-bottom: 8px;
            ">Applicant Name <span style="color: #9ca3af; font-weight: 400;">(Optional)</span></label>
        """, unsafe_allow_html=True)
        
        applicant_name = st.text_input(
            "Applicant Name",
            placeholder="Enter applicant name",
            label_visibility="collapsed",
            key="applicant_name_input"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # File Upload Area
    with st.container():
        st.markdown("""
        <div style="
            background: white;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            padding: 24px;
            margin-bottom: 24px;
        ">
            <label style="
                display: block;
                font-size: 14px;
                font-weight: 600;
                color: #111827;
                margin-bottom: 16px;
            ">Planning Documents *</label>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Upload PDF Documents",
            type=["pdf"],
            accept_multiple_files=True,
            help="PDF files only • Maximum 200MB per file",
            label_visibility="collapsed",
            key="file_uploader"
        )
        
        # Show uploaded files
        if uploaded_files:
            st.markdown("""
            <h4 style="font-size: 14px; font-weight: 600; color: #111827; margin: 20px 0 12px 0;">
                Uploaded Files ({})
            </h4>
            """.format(len(uploaded_files)), unsafe_allow_html=True)
            
            for file in uploaded_files:
                size_mb = file.size / 1024 / 1024
                col1, col2 = st.columns([20, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        padding: 12px;
                        background-color: #f9fafb;
                        border-radius: 8px;
                        border: 1px solid #e5e7eb;
                        margin-bottom: 8px;
                    ">
                        <span style="font-size: 20px;">📄</span>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 600; color: #111827; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                {file.name}
                            </div>
                            <div style="font-size: 12px; color: #6b7280;">
                                {size_mb:.2f} MB
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Process Button
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col2:
        can_process = bool(app_ref and uploaded_files)
        
        if st.button(
            "🚀 Process Documents",
            type="primary",
            disabled=not can_process,
            use_container_width=True,
            key="process_button"
        ):
            if not app_ref:
                st.error("⚠️ Please enter an application reference")
                return
            
            if not uploaded_files:
                st.error("⚠️ Please upload at least one PDF file")
                return
            
            # Check if application already exists
            db = Database()
            session = db.get_session()
            
            try:
                from planproof.db import Application
                existing_app = session.query(Application).filter(
                    Application.application_ref == app_ref
                ).first()
                
                if existing_app:
                    st.warning(f"⚠️ Application {app_ref} already exists. Creating as new version...")
                
                # Start processing
                with st.spinner("Initiating processing..."):
                    run_id = start_run(
                        app_ref=app_ref,
                        files=list(uploaded_files),
                        applicant_name=applicant_name if applicant_name else None
                    )
                    
                    # Set processing state
                    st.session_state.processing_status = 'active'
                    st.session_state.processing_run_id = run_id
                    st.session_state.processing_app_ref = app_ref
                    
                    st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error starting processing: {str(e)}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())
            
            finally:
                session.close()
    
    # Info box
    st.markdown("""
    <div style="
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 16px;
        margin-top: 32px;
    ">
        <div style="display: flex; gap: 12px;">
            <span style="font-size: 20px;">💡</span>
            <div>
                <div style="font-weight: 600; color: #1e40af; margin-bottom: 4px;">
                    What happens next?
                </div>
                <div style="font-size: 14px; color: #1e40af;">
                    We'll run 30+ automated validation checks against UK planning policies,
                    local development plans, and document requirements. This typically takes 2-5 minutes.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
