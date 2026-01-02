"""
Status page - Show processing progress and current status.
"""

import streamlit as st
import time
from planproof.ui.run_orchestrator import get_run_status


def render():
    """Render the status page."""
    st.title("📊 Processing Status")
    
    # Get run_id from session state or allow manual input
    run_id_input = st.text_input(
        "Run ID",
        value=str(st.session_state.run_id) if st.session_state.run_id else "",
        help="Enter the run ID to check status"
    )
    
    if not run_id_input:
        st.info("Enter a run ID to view status, or go to Upload page to start a new run.")
        return
    
    try:
        run_id = int(run_id_input)
    except ValueError:
        st.error("Run ID must be a number")
        return
    
    # Auto-refresh checkbox
    auto_refresh = st.checkbox("Auto-refresh (every 2 seconds)", value=True)
    
    # Status display
    status_placeholder = st.empty()
    
    def update_status():
        """Fetch and display current status."""
        status = get_run_status(run_id)
        
        with status_placeholder.container():
            state = status.get("state", "unknown")
            
            # Status badge
            if state == "completed":
                st.success("✅ Processing Completed")
            elif state == "completed_with_errors":
                st.warning("⚠️ Processing Completed with Errors")
            elif state == "failed":
                st.error("❌ Processing Failed")
            elif state == "running":
                st.info("🔄 Processing in Progress...")
            elif state == "not_found":
                st.error(f"Run {run_id} not found")
                return
            else:
                st.info(f"Status: {state}")
            
            # Progress information
            progress = status.get("progress", {})
            current = progress.get("current", 0)
            total = progress.get("total", 1)
            current_file = progress.get("current_file", "")
            
            if state == "running":
                st.progress(current / total if total > 0 else 0)
                st.markdown(f"**Progress:** {current} / {total} documents processed")
                if current_file:
                    st.markdown(f"**Current file:** {current_file}")
            
            # Show summary if available
            if state in ["completed", "completed_with_errors", "failed"]:
                from pathlib import Path
                import json
                
                summary_file = Path(f"./runs/{run_id}/outputs/summary.json")
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        
                        # Display summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Documents", summary.get("summary", {}).get("total_documents", 0))
                        with col2:
                            st.metric("Processed", summary.get("summary", {}).get("processed", 0))
                        with col3:
                            st.metric("Errors", summary.get("summary", {}).get("errors", 0))
                        
                        # Show errors if any
                        if summary.get("errors"):
                            st.error(f"**{len(summary['errors'])} Error(s) Occurred:**")
                            for err in summary["errors"]:
                                with st.expander(f"❌ {err.get('filename', 'Unknown file')} - {err.get('step', 'unknown step')}"):
                                    st.markdown(f"**Error Type:** `{err.get('error_type', 'Unknown')}`")
                                    st.markdown(f"**Step:** {err.get('step', 'unknown')}")
                                    st.markdown(f"**Message:** {err.get('error', 'No message')}")
                                    if err.get('traceback'):
                                        st.code(err['traceback'], language='python')
                    except Exception as e:
                        st.warning(f"Could not load summary: {e}")
            
            # Error information from database
            if status.get("error"):
                st.error(f"**Error:** {status.get('error')}")
                
                if status.get("traceback"):
                    with st.expander("View Full Error Details"):
                        st.code(status.get("traceback"), language="text")
                    
                    # Download logs button
                    st.download_button(
                        "📥 Download Error Logs",
                        data=status.get("traceback", ""),
                        file_name=f"error_run_{run_id}.txt",
                        mime="text/plain"
                    )
            
            # Action buttons
            if state in ["completed", "completed_with_errors", "failed"]:
                st.session_state.run_id = run_id
                st.session_state.stage = "results"
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 View Results", use_container_width=True):
                        st.rerun()
                with col2:
                    # Download summary button
                    from pathlib import Path
                    summary_file = Path(f"./runs/{run_id}/outputs/summary.json")
                    if summary_file.exists():
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary_content = f.read()
                        st.download_button(
                            "📥 Download Summary",
                            data=summary_content,
                            file_name=f"run_{run_id}_summary.json",
                            mime="application/json",
                            use_container_width=True
                        )
    
    # Initial status fetch
    update_status()
    
    # Auto-refresh loop
    if auto_refresh:
        time.sleep(2)
        st.rerun()
