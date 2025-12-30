"""
Results page - Display validation results and findings.
"""

import streamlit as st
import json
import zipfile
from pathlib import Path
from datetime import datetime
from planproof.ui.run_orchestrator import get_run_results
from planproof.ui.components.document_viewer import render_document_viewer, check_pdf_library
from planproof.services.officer_override import create_override, get_override_history


def _render_document_viewer_section():
    """Render the document viewer in a dedicated section."""
    st.title("📄 Document Viewer")
    
    document_path = st.session_state.get("viewer_document_path")
    document_id = st.session_state.get("viewer_document_id")
    page = st.session_state.get("viewer_page", 1)
    bbox = st.session_state.get("viewer_bbox")
    
    if not document_path or not Path(document_path).exists():
        st.error("Document not found")
        return
    
    st.info(f"📍 Viewing evidence at Page {page}")
    
    render_document_viewer(
        document_path=document_path,
        page_number=page,
        bbox=bbox,
        document_id=document_id,
        zoom_level="fit-width"
    )


def render():
    """Render the results page."""
    st.title("📋 Validation Results")
    
    # Check PDF library availability
    pdf_available, pdf_library = check_pdf_library()
    if not pdf_available:
        st.warning("⚠️ PDF viewer not available. Install PyMuPDF or pdf2image to view documents.")
    
    # Get run_id from session state or allow manual input
    run_id_input = st.text_input(
        "Run ID",
        value=str(st.session_state.run_id) if st.session_state.run_id else "",
        help="Enter the run ID to view results"
    )
    
    if not run_id_input:
        st.info("Enter a run ID to view results, or go to Upload page to start a new run.")
        return
    
    try:
        run_id = int(run_id_input)
    except ValueError:
        st.error("Run ID must be a number")
        return
    
    # Fetch results
    results = get_run_results(run_id)
    
    if "error" in results:
        st.error(results["error"])
        return
    
    # Check if document viewer should be shown
    if st.session_state.get("show_viewer", False):
        _render_document_viewer_section()
        if st.button("← Back to Results"):
            st.session_state["show_viewer"] = False
            st.rerun()
        return
    
    # Summary cards
    st.markdown("### Summary")
    summary = results.get("summary", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", summary.get("total_documents", 0))
    
    with col2:
        st.metric("Processed", summary.get("processed", 0))
    
    with col3:
        st.metric("Errors", summary.get("errors", 0))
    
    with col4:
        st.metric("LLM Calls", results.get("llm_calls_per_run", 0))
    
    # Validation summary by status
    findings = results.get("validation_findings", [])
    
    if findings:
        # Count by status
        pass_count = sum(1 for f in findings if f.get("status") == "pass")
        needs_review_count = sum(1 for f in findings if f.get("status") == "needs_review")
        fail_count = sum(1 for f in findings if f.get("status") == "fail")
        
        st.markdown("### Validation Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success(f"✅ PASS: {pass_count}")
        
        with col2:
            st.warning(f"⚠️ NEEDS REVIEW: {needs_review_count}")
        
        with col3:
            st.error(f"❌ FAIL: {fail_count}")
    
    # Findings table
    st.markdown("### Validation Findings")
    
    if not findings:
        st.info("No validation findings available.")
    else:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "pass", "needs_review", "fail"],
                index=0
            )
        
        with col2:
            severity_filter = st.selectbox(
                "Filter by Severity",
                ["All", "error", "warning"],
                index=0
            )
        
        # Apply filters
        filtered_findings = findings
        if status_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.get("status") == status_filter]
        if severity_filter != "All":
            filtered_findings = [f for f in filtered_findings if f.get("severity") == severity_filter]
        
        # Display findings
        for idx, finding in enumerate(filtered_findings):
            # Check for existing overrides
            finding_key = f"{finding.get('rule_id')}_{finding.get('document_id')}"
            override_history = st.session_state.get(f"override_history_{finding_key}", [])
            
            # Determine display status (show override if exists)
            display_status = finding.get('status', 'unknown')
            if override_history:
                latest_override = override_history[0]
                display_status = f"{latest_override['override_status']} (OVERRIDDEN)"
            
            with st.expander(
                f"{finding.get('rule_id', 'Unknown')} - {display_status.upper()} "
                f"({finding.get('document_name', 'unknown')})"
            ):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Rule ID:** {finding.get('rule_id', 'N/A')}")
                    st.markdown(f"**Status:** {finding.get('status', 'N/A')}")
                    st.markdown(f"**Severity:** {finding.get('severity', 'N/A')}")
                    st.markdown(f"**Document:** {finding.get('document_name', 'N/A')}")
                
                with col2:
                    st.markdown(f"**Message:** {finding.get('message', 'N/A')}")
                    if finding.get('missing_fields'):
                        st.markdown(f"**Missing Fields:** {', '.join(finding['missing_fields'])}")
                
                # Override section
                st.markdown("---")
                st.markdown("### Officer Override")
                
                # Show existing overrides
                if override_history:
                    with st.expander(f"📋 Override History ({len(override_history)} override(s))"):
                        for override in override_history:
                            st.markdown(f"**Override by:** {override['officer_id']}")
                            st.markdown(f"**Original:** {override['original_status']} → **Override:** {override['override_status']}")
                            st.markdown(f"**Notes:** {override['notes']}")
                            st.markdown(f"**Date:** {override['created_at']}")
                            st.markdown("---")
                
                # Override form
                override_col1, override_col2, override_col3 = st.columns([2, 2, 1])
                
                with override_col1:
                    override_status = st.selectbox(
                        "Override Status",
                        ["pass", "fail", "needs_review"],
                        key=f"override_status_{finding_key}_{idx}",
                        help="Select the override status"
                    )
                
                with override_col2:
                    officer_id = st.text_input(
                        "Officer ID",
                        key=f"officer_id_{finding_key}_{idx}",
                        placeholder="Enter your officer ID",
                        help="Your user identifier"
                    )
                
                override_notes = st.text_area(
                    "Override Notes (Required)",
                    key=f"override_notes_{finding_key}_{idx}",
                    placeholder="Explain why you are overriding this result...",
                    help="Mandatory explanation for the override"
                )
                
                with override_col3:
                    if st.button(
                        "✓ Override",
                        key=f"override_btn_{finding_key}_{idx}",
                        type="primary"
                    ):
                        if not override_notes or not override_notes.strip():
                            st.error("Override notes are required")
                        elif not officer_id or not officer_id.strip():
                            st.error("Officer ID is required")
                        else:
                            try:
                                # Create override (using validation_result_id if available)
                                override_id = create_override(
                                    validation_result_id=None,  # Would need to get from finding
                                    validation_check_id=None,  # Would need to get from finding
                                    original_status=finding.get('status', 'unknown'),
                                    override_status=override_status,
                                    notes=override_notes.strip(),
                                    officer_id=officer_id.strip(),
                                    run_id=run_id
                                )
                                
                                st.success(f"Override created successfully! ID: {override_id}")
                                
                                # Refresh override history
                                # Note: In production, this would query the database
                                st.session_state[f"override_history_{finding_key}"] = [{
                                    "override_id": override_id,
                                    "original_status": finding.get('status'),
                                    "override_status": override_status,
                                    "notes": override_notes.strip(),
                                    "officer_id": officer_id.strip(),
                                    "created_at": datetime.now().isoformat()
                                }] + override_history
                                
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"Error creating override: {str(e)}")
                
                # Evidence section
                evidence_enhanced = finding.get("evidence_enhanced", [])
                evidence = finding.get("evidence", {})
                
                if evidence_enhanced or evidence:
                    st.markdown("**Evidence:**")
                    
                    # Use enhanced evidence if available
                    if evidence_enhanced:
                        for idx, ev in enumerate(evidence_enhanced[:5]):  # Show top 5
                            page = ev.get("page", "?")
                            snippet = ev.get("snippet", "")
                            document_path = ev.get("document_path")
                            document_id = ev.get("document_id")
                            bbox = ev.get("bbox")
                            
                            col_ev1, col_ev2 = st.columns([4, 1])
                            
                            with col_ev1:
                                st.code(f"Page {page}: {snippet}", language="text")
                            
                            with col_ev2:
                                if pdf_available and document_path and Path(document_path).exists():
                                    if st.button(
                                        "📄 View",
                                        key=f"view_evidence_{finding.get('rule_id')}_{document_id}_{page}_{idx}",
                                        help="Open document at this evidence location"
                                    ):
                                        # Store viewer state
                                        st.session_state["show_viewer"] = True
                                        st.session_state["viewer_document_path"] = document_path
                                        st.session_state["viewer_document_id"] = document_id
                                        st.session_state["viewer_page"] = page
                                        st.session_state["viewer_bbox"] = bbox
                                        st.rerun()
                    else:
                        # Fallback to old evidence format
                        evidence_snippets = evidence.get("evidence_snippets", [])
                        if evidence_snippets:
                            for ev in evidence_snippets[:3]:  # Show top 3
                                page = ev.get("page", "?")
                                snippet = ev.get("snippet", "")
                                st.code(f"Page {page}: {snippet}", language="text")
                        else:
                            st.info("No evidence snippets available")
    
    # Errors section
    errors = results.get("errors", [])
    if errors:
        st.markdown("### Processing Errors")
        for error in errors:
            with st.expander(f"❌ {error.get('filename', 'Unknown file')}"):
                st.error(error.get("error", "Unknown error"))
                if error.get("traceback"):
                    st.code(error.get("traceback"), language="text")
    
    # Request Info section
    st.markdown("---")
    st.markdown("### Request More Information")
    
    request_info_col1, request_info_col2 = st.columns([3, 1])
    
    with request_info_col1:
        request_info_notes = st.text_area(
            "Information Needed",
            key=f"request_info_notes_{run_id}",
            placeholder="Describe what additional information is required from the applicant...",
            help="Specify what documents or clarifications are needed"
        )
    
    with request_info_col2:
        if st.button("📤 Request Info", key=f"request_info_btn_{run_id}", type="secondary"):
            if not request_info_notes or not request_info_notes.strip():
                st.error("Please specify what information is needed")
            else:
                try:
                    # Update submission status to needs_info
                    from planproof.db import Database, Submission
                    db = Database()
                    session = db.get_session()
                    
                    try:
                        # Find submission for this run
                        from planproof.db import Run
                        run = session.query(Run).filter(Run.id == run_id).first()
                        
                        if run and run.application_id:
                            # Get latest submission for application
                            submission = session.query(Submission).filter(
                                Submission.planning_case_id == run.application_id
                            ).order_by(Submission.created_at.desc()).first()
                            
                            if submission:
                                # Update status
                                submission.status = "needs_info"
                                
                                # Store request in metadata
                                metadata = submission.submission_metadata or {}
                                if "info_requests" not in metadata:
                                    metadata["info_requests"] = []
                                
                                metadata["info_requests"].append({
                                    "requested_at": datetime.now().isoformat(),
                                    "notes": request_info_notes.strip(),
                                    "run_id": run_id
                                })
                                
                                submission.submission_metadata = metadata
                                session.commit()
                                
                                st.success("✅ Information request recorded! Submission marked as 'needs_info'")
                            else:
                                st.error("Could not find submission for this run")
                        else:
                            st.error("Could not find run details")
                    finally:
                        session.close()
                
                except Exception as e:
                    st.error(f"Error recording request: {str(e)}")
    
    # Export buttons
    st.markdown("---")
    st.markdown("### Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download JSON
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"results_run_{run_id}.json",
            mime="application/json"
        )
    
    with col2:
        # Download run bundle (zip)
        def create_run_bundle():
            """Create a zip file with all run artifacts."""
            run_dir = Path(f"./runs/{run_id}")
            if not run_dir.exists():
                return None
            
            import io
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Add inputs
                inputs_dir = run_dir / "inputs"
                if inputs_dir.exists():
                    for file_path in inputs_dir.glob("*"):
                        zip_file.write(file_path, f"inputs/{file_path.name}")
                
                # Add outputs
                outputs_dir = run_dir / "outputs"
                if outputs_dir.exists():
                    for file_path in outputs_dir.glob("*"):
                        zip_file.write(file_path, f"outputs/{file_path.name}")
                
                # Add results JSON
                zip_file.writestr("results.json", json_data)
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
        
        bundle_data = create_run_bundle()
        if bundle_data:
            st.download_button(
                "📦 Download Run Bundle (ZIP)",
                data=bundle_data,
                file_name=f"run_{run_id}_bundle.zip",
                mime="application/zip"
            )
        else:
            st.info("Run bundle not available")

