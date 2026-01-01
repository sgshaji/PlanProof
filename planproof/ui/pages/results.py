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

# Enhanced issue display components
try:
    from planproof.ui.components.enhanced_issue_card import (
        render_enhanced_issue_card,
        render_bulk_action_panel,
        render_resolution_tracker
    )
    from planproof.ui.components.issue_converter import convert_all_findings
    ENHANCED_ISSUES_AVAILABLE = True
except ImportError as e:
    ENHANCED_ISSUES_AVAILABLE = False
    print(f"Enhanced issue components not available: {e}")


def _render_enhanced_issues_view(findings: list, run_id: int) -> None:
    """Render findings using enhanced issue cards."""
    try:
        # Convert findings to enhanced issues
        enhanced_issues = convert_all_findings(findings, run_id)
        
        if not enhanced_issues:
            st.info("No issues to display.")
            return
        
        # Show resolution tracker
        render_resolution_tracker(enhanced_issues)
        
        st.markdown("---")
        
        # Auto-recheck button
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### 🔄 Auto-Recheck")
            st.caption("Check if any issues can be resolved based on actions taken")
        
        with col2:
            from planproof.services.resolution_service import AutoRecheckEngine
            
            if st.button("🔄 Run Recheck", key=f"recheck_btn_{run_id}", type="primary"):
                with st.spinner("Rechecking issues..."):
                    engine = AutoRecheckEngine(run_id)
                    result = engine.trigger_recheck()
                    
                    if result.get("success"):
                        st.success(f"✅ Rechecked {result['issues_checked']} issue(s)")
                        
                        if result.get("results"):
                            for res in result["results"]:
                                if res["status"] == "resolved":
                                    st.success(f"✅ {res['issue_id']}: {res['message']}")
                                else:
                                    st.info(f"ℹ️ {res['issue_id']}: {res['message']}")
                        
                        st.info("Refresh page to see updated statuses")
                    else:
                        st.error("Recheck failed")
        
        st.markdown("---")
        
        # Show bulk action panel for multi-document issues
        upload_issues = [i for i in enhanced_issues 
                        if i.actions and any(a.action_type.value == "upload_document" 
                                           for a in i.actions.items)]
        if len(upload_issues) > 1:
            render_bulk_action_panel(upload_issues)
            st.markdown("---")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            severity_filter = st.selectbox(
                "Filter by Severity",
                ["All", "Blocker", "Critical", "Warning", "Info"],
                index=0,
                key=f"enhanced_severity_filter_{run_id}"
            )
        
        with col2:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Open", "In Progress", "Awaiting Verification", "Resolved", "Dismissed"],
                index=0,
                key=f"enhanced_status_filter_{run_id}"
            )
        
        with col3:
            category_filter = st.selectbox(
                "Filter by Category",
                ["All", "Missing Document", "Data Quality", "Data Conflict", "Completeness", 
                 "Policy Compliance", "Technical Requirement", "Other"],
                index=0,
                key=f"enhanced_category_filter_{run_id}"
            )
        
        # Apply filters
        filtered_issues = enhanced_issues
        
        if severity_filter != "All":
            filtered_issues = [i for i in filtered_issues 
                             if i.severity.value.title() == severity_filter]
        
        if status_filter != "All":
            filtered_issues = [i for i in filtered_issues 
                             if i.resolution and i.resolution.status.value.replace('_', ' ').title() == status_filter]
        
        if category_filter != "All":
            filtered_issues = [i for i in filtered_issues 
                             if i.category.value.replace('_', ' ').title() == category_filter]
        
        # Show count
        st.info(f"Showing {len(filtered_issues)} of {len(enhanced_issues)} issues")
        
        # Render issue cards
        for issue in filtered_issues:
            render_enhanced_issue_card(issue, run_id)
    
    except Exception as e:
        st.error(f"Error rendering enhanced issues: {str(e)}")
        st.exception(e)
        st.info("Falling back to legacy display...")
        _render_legacy_findings_view(findings, run_id, True)


def _render_legacy_findings_view(findings: list, run_id: int, pdf_available: bool = True) -> None:
    """Render findings using the original legacy display."""
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
    
    # Enhanced Issues toggle (only show if available)
    if ENHANCED_ISSUES_AVAILABLE:
        use_enhanced = st.toggle(
            "🎯 Enhanced Issue Display",
            value=st.session_state.get("use_enhanced_issues", False),
            help="Show issues with actionable guidance and resolution tracking"
        )
        st.session_state["use_enhanced_issues"] = use_enhanced
    else:
        use_enhanced = False
    
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
    elif use_enhanced and ENHANCED_ISSUES_AVAILABLE:
        # ENHANCED ISSUE DISPLAY
        _render_enhanced_issues_view(findings, run_id)
    else:
        # LEGACY DISPLAY
        _render_legacy_findings_view(findings, run_id, pdf_available)
    
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
    st.markdown("### 🚨 Request More Information")
    
    # Show active requests first
    try:
        from planproof.services.request_info_service import get_active_requests
        from planproof.db import Submission, Run
        
        # Get submission ID from run
        db_check = Database()
        session_check = db_check.get_session()
        run = session_check.query(Run).filter(Run.id == run_id).first()
        submission_id = None
        
        if run and run.application_id:
            submission = session_check.query(Submission).filter(
                Submission.planning_case_id == run.application_id
            ).order_by(Submission.created_at.desc()).first()
            if submission:
                submission_id = submission.id
        
        session_check.close()
        
        if submission_id:
            active_requests = get_active_requests(submission_id, db_check)
            
            if active_requests:
                st.warning(f"⚠️ {len(active_requests)} active information request(s)")
                for req in active_requests:
                    with st.expander(f"Request {req.get('request_id', 'N/A')}", expanded=True):
                        st.markdown(f"**Created:** {req.get('created_at', 'N/A')}")
                        st.markdown(f"**Officer:** {req.get('officer_name', 'N/A')}")
                        st.markdown(f"**Status:** {req.get('status', 'pending').upper()}")
                        
                        if req.get('missing_items'):
                            st.markdown("**Missing Items:**")
                            for item in req['missing_items']:
                                st.markdown(f"- {item}")
                        
                        if req.get('notes'):
                            st.markdown(f"**Notes:** {req['notes']}")
    except Exception as e:
        st.error(f"Could not load active requests: {str(e)}")
    
    # Create new request
    with st.expander("➕ Create New Information Request", expanded=False):
        officer_name = st.text_input(
            "Your Name",
            key=f"officer_name_{run_id}",
            placeholder="Officer name"
        )
        
        st.markdown("**Select Missing Items:**")
        missing_items = []
        
        col_mi1, col_mi2 = st.columns(2)
        with col_mi1:
            if st.checkbox("Site Plan", key=f"mi_siteplan_{run_id}"):
                missing_items.append("Site Plan")
            if st.checkbox("Location Plan", key=f"mi_locplan_{run_id}"):
                missing_items.append("Location Plan")
            if st.checkbox("Elevations", key=f"mi_elevations_{run_id}"):
                missing_items.append("Elevations")
            if st.checkbox("Floor Plans", key=f"mi_floorplans_{run_id}"):
                missing_items.append("Floor Plans")
        
        with col_mi2:
            if st.checkbox("Heritage Statement", key=f"mi_heritage_{run_id}"):
                missing_items.append("Heritage Statement")
            if st.checkbox("Tree Survey", key=f"mi_tree_{run_id}"):
                missing_items.append("Tree Survey")
            if st.checkbox("Flood Risk Assessment", key=f"mi_fra_{run_id}"):
                missing_items.append("Flood Risk Assessment")
            if st.checkbox("Fee Payment", key=f"mi_fee_{run_id}"):
                missing_items.append("Fee Payment")
        
        custom_item = st.text_input(
            "Other (specify)",
            key=f"mi_custom_{run_id}",
            placeholder="Additional item needed..."
        )
        if custom_item:
            missing_items.append(custom_item)
        
        request_info_notes = st.text_area(
            "Additional Notes",
            key=f"request_info_notes_{run_id}",
            placeholder="Provide additional context or specific requirements...",
            help="Explain why these items are needed"
        )
        
        col_req1, col_req2 = st.columns([1, 3])
        
        with col_req1:
            if st.button("📤 Submit Request", key=f"request_info_btn_{run_id}", type="primary"):
                if not officer_name:
                    st.error("Please enter your name")
                elif not missing_items:
                    st.error("Please select at least one missing item")
                else:
                    try:
                        from planproof.services.request_info_service import create_request_info
                        
                        if submission_id:
                            result = create_request_info(
                                submission_id=submission_id,
                                missing_items=missing_items,
                                notes=request_info_notes or "No additional notes",
                                officer_name=officer_name,
                                db=db_check
                            )
                            
                            if result.get("success"):
                                st.success("✅ Information request created! Case marked as ON_HOLD")
                                
                                # Show exportable checklist
                                st.markdown("**Exportable Checklist:**")
                                st.text_area(
                                    "Checklist",
                                    value=result.get("checklist_text", ""),
                                    height=200,
                                    key=f"checklist_{run_id}"
                                )
                                
                                st.download_button(
                                    "📥 Download Checklist",
                                    data=result.get("checklist_text", ""),
                                    file_name=f"info_request_{result['request_record']['request_id']}.txt",
                                    mime="text/plain"
                                )
                                
                                st.markdown("**Email Template:**")
                                st.text_area(
                                    "Email",
                                    value=result.get("email_template", ""),
                                    height=300,
                                    key=f"email_{run_id}"
                                )
                                
                                st.download_button(
                                    "📧 Download Email Template",
                                    data=result.get("email_template", ""),
                                    file_name=f"email_template_{result['request_record']['request_id']}.txt",
                                    mime="text/plain"
                                )
                            else:
                                st.error(f"Error: {result.get('error', 'Unknown error')}")
                        else:
                            st.error("Could not find submission for this run")
                    
                    except Exception as e:
                        st.error(f"Error creating request: {str(e)}")
                        st.exception(e)
    
    # Export buttons
    st.markdown("---")
    st.markdown("### 📦 Export Decision Package")
    
    st.markdown("Export complete validation results including evidence, overrides, and version comparison")
    
    col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
    
    with col_exp1:
        if st.button("📄 Export JSON (Full)", key=f"export_json_full_{run_id}", use_container_width=True):
            try:
                from planproof.services.export_service import export_decision_package, export_as_json
                
                package = export_decision_package(run_id, db)
                json_data_full = export_as_json(package)
                
                st.download_button(
                    "📥 Download Full JSON",
                    data=json_data_full,
                    file_name=f"decision_package_{run_id}.json",
                    mime="application/json",
                    key=f"download_json_full_{run_id}"
                )
                st.success("✅ JSON package ready")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col_exp2:
        if st.button("📋 Export HTML Report", key=f"export_html_{run_id}", use_container_width=True):
            try:
                from planproof.services.export_service import export_decision_package, export_as_html_report
                
                package = export_decision_package(run_id, db)
                html_data = export_as_html_report(package)
                
                st.download_button(
                    "📥 Download HTML",
                    data=html_data,
                    file_name=f"decision_report_{run_id}.html",
                    mime="text/html",
                    key=f"download_html_{run_id}"
                )
                st.success("✅ HTML report ready")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col_exp3:
        # Download JSON (simple)
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 Download JSON (Simple)",
            data=json_data,
            file_name=f"results_run_{run_id}.json",
            mime="application/json"
        )
    
    with col_exp4:
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
                "📦 Download Bundle (ZIP)",
                data=bundle_data,
                file_name=f"run_{run_id}_bundle.zip",
                mime="application/zip"
            )
        else:
            st.info("Bundle not available")

