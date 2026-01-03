"""
Extracted Fields Viewer page - Display and resolve field conflicts.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
from planproof.db import Database, ExtractedField, Document, Evidence, FieldResolution


def get_extracted_fields(submission_id: int, db: Optional[Database] = None) -> List[Dict[str, Any]]:
    """
    Get all extracted fields for a submission with conflict detection.
    
    Args:
        submission_id: Submission ID
        db: Optional Database instance
    
    Returns:
        List of field dicts with metadata
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        # Get all extracted fields
        fields = session.query(ExtractedField).filter(
            ExtractedField.submission_id == submission_id
        ).all()
        
        # Group by field_name to detect conflicts
        field_groups = {}
        for field in fields:
            key = field.field_name
            if key not in field_groups:
                field_groups[key] = []
            field_groups[key].append(field)
        
        # Build field data with conflict info
        field_data = []
        
        for field_key, field_list in field_groups.items():
            # Check for conflicts (multiple different values)
            values = {f.field_value for f in field_list if f.field_value}
            has_conflict = len(values) > 1
            
            # Get resolution if exists
            resolution = session.query(FieldResolution).filter(
                FieldResolution.submission_id == submission_id,
                FieldResolution.field_key == field_key
            ).first()
            
            # Get evidence and document info for each field
            field_entries = []
            for field in field_list:
                doc = session.query(Document).filter(Document.id == field.document_id).first()
                evidence = session.query(Evidence).filter(Evidence.id == field.evidence_id).first()
                
                field_entries.append({
                    "extracted_field_id": field.id,
                    "field_value": field.field_value,
                    "confidence": field.confidence,
                    "extractor": field.extractor,
                    "document_id": field.document_id,
                    "document_name": doc.filename if doc else "Unknown",
                    "document_type": doc.document_type if doc else "unknown",
                    "evidence_page": evidence.page_number if evidence else None,
                    "evidence_snippet": evidence.snippet if evidence else None
                })
            
            field_data.append({
                "field_key": field_key,
                "has_conflict": has_conflict,
                "value_count": len(values),
                "entries": field_entries,
                "resolution": {
                    "resolution_id": resolution.resolution_id if resolution else None,
                    "chosen_value": resolution.chosen_value if resolution else None,
                    "officer_id": resolution.officer_id if resolution else None,
                    "notes": resolution.notes if resolution else None,
                    "created_at": resolution.created_at.isoformat() if resolution and resolution.created_at else None
                } if resolution else None
            })
        
        return field_data
    
    finally:
        session.close()


def create_field_resolution(
    submission_id: int,
    field_key: str,
    chosen_extracted_field_id: int,
    chosen_value: str,
    officer_id: str,
    notes: Optional[str] = None,
    db: Optional[Database] = None
) -> int:
    """Create a field resolution."""
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        resolution = FieldResolution(
            submission_id=submission_id,
            field_key=field_key,
            chosen_extracted_field_id=chosen_extracted_field_id,
            chosen_value=chosen_value,
            officer_id=officer_id,
            notes=notes
        )
        
        session.add(resolution)
        session.commit()
        session.refresh(resolution)
        
        return resolution.resolution_id
    
    except Exception as e:
        session.rollback()
        raise
    
    finally:
        session.close()


def render():
    """Render the extracted fields viewer page."""
    st.title("🔍 Extracted Fields Viewer")
    
    st.markdown("Review extracted fields, filter by confidence, and resolve conflicts.")
    
    # Input for submission ID
    submission_id_input = st.text_input(
        "Submission ID",
        placeholder="Enter submission ID",
        help="Enter the submission ID to view extracted fields"
    )
    
    if not submission_id_input:
        st.info("Enter a submission ID to view extracted fields.")
        return
    
    try:
        submission_id = int(submission_id_input)
    except ValueError:
        st.error("Submission ID must be a number")
        return
    
    # Fetch fields
    with st.spinner("Loading extracted fields..."):
        fields = get_extracted_fields(submission_id)
    
    if not fields:
        st.warning("No extracted fields found for this submission.")
        return
    
    # Summary metrics
    st.markdown("---")
    st.markdown("### Summary")
    
    total_fields = len(fields)
    conflict_fields = sum(1 for f in fields if f["has_conflict"])
    resolved_fields = sum(1 for f in fields if f["resolution"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Fields", total_fields)
    
    with col2:
        st.metric("Conflicts", conflict_fields)
    
    with col3:
        st.metric("Resolved", resolved_fields)
    
    with col4:
        st.metric("Unresolved", conflict_fields - resolved_fields)
    
    # Filters
    st.markdown("---")
    st.markdown("### Filters")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        confidence_filter = st.selectbox(
            "Confidence Level",
            ["All", "Low (<0.6)", "Medium (0.6-0.8)", "High (>0.8)"],
            index=0
        )
    
    with col_filter2:
        conflict_filter = st.selectbox(
            "Conflict Status",
            ["All", "Conflicts Only", "No Conflicts"],
            index=0
        )
    
    with col_filter3:
        resolution_filter = st.selectbox(
            "Resolution Status",
            ["All", "Resolved", "Unresolved"],
            index=0
        )
    
    # Apply filters
    filtered_fields = fields
    
    if conflict_filter == "Conflicts Only":
        filtered_fields = [f for f in filtered_fields if f["has_conflict"]]
    elif conflict_filter == "No Conflicts":
        filtered_fields = [f for f in filtered_fields if not f["has_conflict"]]
    
    if resolution_filter == "Resolved":
        filtered_fields = [f for f in filtered_fields if f["resolution"]]
    elif resolution_filter == "Unresolved":
        filtered_fields = [f for f in filtered_fields if not f["resolution"]]
    
    # Display fields
    st.markdown("---")
    st.markdown(f"### Extracted Fields ({len(filtered_fields)} shown)")
    
    for field in filtered_fields:
        field_key = field["field_key"]
        has_conflict = field["has_conflict"]
        resolution = field["resolution"]
        entries = field["entries"]
        
        # Determine display status
        status_icon = "⚠️" if has_conflict else "✅"
        status_text = "CONFLICT" if has_conflict else "OK"
        
        if resolution:
            status_icon = "✓"
            status_text = "RESOLVED"
        
        with st.expander(
            f"{status_icon} {field_key} - {status_text} ({len(entries)} source(s))",
            expanded=has_conflict and not resolution
        ):
            # Show resolution if exists
            if resolution:
                st.success(f"**Resolved by:** {resolution['officer_id']}")
                st.markdown(f"**Chosen Value:** `{resolution['chosen_value']}`")
                if resolution['notes']:
                    st.markdown(f"**Notes:** {resolution['notes']}")
                st.markdown(f"**Date:** {resolution['created_at'][:19] if resolution['created_at'] else 'N/A'}")
                st.markdown("---")
            
            # Show all entries
            st.markdown("**All Extracted Values:**")
            
            for idx, entry in enumerate(entries):
                col_entry1, col_entry2 = st.columns([3, 1])
                
                with col_entry1:
                    st.markdown(f"**Value:** `{entry['field_value']}`")
                    st.markdown(f"**Source:** {entry['document_type']} - {entry['document_name']}")
                    st.markdown(f"**Confidence:** {entry['confidence']:.2f}" if entry['confidence'] else "**Confidence:** N/A")
                    
                    if entry['evidence_snippet']:
                        st.code(f"Page {entry['evidence_page']}: {entry['evidence_snippet']}", language="text")
                
                with col_entry2:
                    # Resolution button for conflicts
                    if has_conflict and not resolution:
                        if st.button(
                            "✓ Choose",
                            key=f"choose_{field_key}_{entry['extracted_field_id']}",
                            help="Select this value as canonical"
                        ):
                            st.session_state[f"resolve_{field_key}"] = entry
                
                if idx < len(entries) - 1:
                    st.markdown("---")
            
            # Resolution form (if conflict and not resolved)
            if has_conflict and not resolution:
                st.markdown("---")
                st.markdown("### Resolve Conflict")
                
                # Check if user clicked a "Choose" button
                selected_entry = st.session_state.get(f"resolve_{field_key}")
                
                if selected_entry:
                    st.info(f"Selected value: `{selected_entry['field_value']}`")
                    
                    col_res1, col_res2 = st.columns(2)
                    
                    with col_res1:
                        officer_id = st.text_input(
                            "Officer ID",
                            key=f"officer_{field_key}",
                            placeholder="Enter your officer ID"
                        )
                    
                    with col_res2:
                        resolution_notes = st.text_area(
                            "Notes (Optional)",
                            key=f"notes_{field_key}",
                            placeholder="Explain why you chose this value..."
                        )
                    
                    if st.button(f"✓ Confirm Resolution", key=f"confirm_{field_key}", type="primary"):
                        if not officer_id:
                            st.error("Officer ID is required")
                        else:
                            try:
                                resolution_id = create_field_resolution(
                                    submission_id=submission_id,
                                    field_key=field_key,
                                    chosen_extracted_field_id=selected_entry['extracted_field_id'],
                                    chosen_value=selected_entry['field_value'],
                                    officer_id=officer_id,
                                    notes=resolution_notes if resolution_notes else None
                                )
                                
                                st.success(f"Resolution created! ID: {resolution_id}")
                                
                                # Clear selection
                                del st.session_state[f"resolve_{field_key}"]
                                
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"Error creating resolution: {str(e)}")
                else:
                    st.info("Click 'Choose' next to a value to resolve this conflict.")

