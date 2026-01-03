"""
Conflict Resolution page - Officer chooses preferred values for consistency conflicts.
"""

import streamlit as st
from planproof.db import Database, ExtractedField, Document, FieldResolution
from typing import Dict, Any, List
from datetime import datetime


def render():
    """Render conflict resolution page."""
    st.title("🔧 Field Conflict Resolution")
    
    st.markdown("""
    When the same field is extracted with different values from multiple documents, 
    you can select the correct value here. The resolved value becomes the "truth" for all validation rules.
    """)
    
    # Submission selector
    submission_id = st.number_input(
        "Submission ID",
        min_value=1,
        value=st.session_state.get("submission_id", 1),
        help="Enter submission ID to review conflicts"
    )
    
    if st.button("🔍 Load Conflicts"):
        st.session_state.submission_id = submission_id
        st.rerun()
    
    if not st.session_state.get("submission_id"):
        st.info("Enter a submission ID to start resolving conflicts")
        return
    
    # Get conflicts
    db = Database()
    conflicts = find_conflicts(submission_id, db)
    
    if not conflicts:
        st.success("✅ No conflicts found for this submission!")
        return
    
    st.markdown(f"### Found {len(conflicts)} field(s) with conflicts")
    
    # Display each conflict for resolution
    for field_name, conflict_data in conflicts.items():
        with st.expander(f"⚠️ {field_name} ({len(conflict_data['values'])} different values)", expanded=True):
            render_conflict_resolution(submission_id, field_name, conflict_data, db)
    
    st.divider()
    
    # Summary of resolutions
    st.markdown("### Resolution Summary")
    
    session = db.get_session()
    try:
        resolutions = session.query(FieldResolution).filter(
            FieldResolution.submission_id == submission_id
        ).all()
        
        if resolutions:
            st.success(f"✅ {len(resolutions)} fields resolved")
            
            for resolution in resolutions:
                st.markdown(f"**{resolution.field_name}:** `{resolution.resolved_value}`")
                if resolution.resolved_by:
                    st.caption(f"Resolved by: {resolution.resolved_by} on {resolution.created_at.strftime('%Y-%m-%d %H:%M') if resolution.created_at else 'N/A'}")
        else:
            st.info("No resolutions recorded yet")
    
    finally:
        session.close()


def find_conflicts(submission_id: int, db: Database) -> Dict[str, Any]:
    """
    Find all field conflicts for a submission.
    
    Args:
        submission_id: Submission ID
        db: Database instance
        
    Returns:
        Dict mapping field_name to conflict data
    """
    session = db.get_session()
    
    try:
        # Get all extracted fields for this submission
        extracted_fields = session.query(ExtractedField).filter(
            ExtractedField.submission_id == submission_id
        ).all()
        
        # Group by field name
        field_groups = {}
        for ef in extracted_fields:
            if ef.field_name not in field_groups:
                field_groups[ef.field_name] = []
            field_groups[ef.field_name].append(ef)
        
        # Find conflicts (multiple different values)
        conflicts = {}
        
        for field_name, field_list in field_groups.items():
            # Group by value
            value_groups = {}
            for ef in field_list:
                value = ef.field_value
                if value not in value_groups:
                    value_groups[value] = []
                value_groups[value].append(ef)
            
            # If more than one unique value, it's a conflict
            if len(value_groups) > 1:
                # Get document info for each value
                sources = []
                for value, efs in value_groups.items():
                    for ef in efs:
                        doc = session.query(Document).filter(Document.id == ef.document_id).first()
                        sources.append({
                            "value": value,
                            "document_id": ef.document_id,
                            "document_name": doc.filename if doc else f"doc_{ef.document_id}",
                            "document_type": doc.document_type if doc else "unknown",
                            "confidence": ef.confidence or 0.0,
                            "page": ef.page_number
                        })
                
                conflicts[field_name] = {
                    "values": list(value_groups.keys()),
                    "sources": sources,
                    "count": len(field_list)
                }
        
        return conflicts
    
    finally:
        session.close()


def render_conflict_resolution(
    submission_id: int,
    field_name: str,
    conflict_data: Dict[str, Any],
    db: Database
):
    """
    Render UI for resolving a single field conflict.
    
    Args:
        submission_id: Submission ID
        field_name: Field name with conflict
        conflict_data: Conflict data dict
        db: Database instance
    """
    st.markdown(f"**Field:** `{field_name}`")
    
    # Check if already resolved
    session = db.get_session()
    try:
        existing_resolution = session.query(FieldResolution).filter(
            FieldResolution.submission_id == submission_id,
            FieldResolution.field_name == field_name
        ).first()
        
        if existing_resolution:
            st.info(f"✅ Already resolved to: **{existing_resolution.resolved_value}**")
            st.caption(f"Resolved by: {existing_resolution.resolved_by or 'N/A'} | "
                      f"Reason: {existing_resolution.resolution_reason or 'N/A'}")
            
            if st.button(f"🔄 Re-resolve", key=f"reresolve_{field_name}"):
                session.delete(existing_resolution)
                session.commit()
                st.rerun()
            return
    finally:
        session.close()
    
    # Display all conflicting values with their sources
    st.markdown("**Conflicting Values:**")
    
    # Group sources by value for display
    value_sources = {}
    for source in conflict_data["sources"]:
        value = source["value"]
        if value not in value_sources:
            value_sources[value] = []
        value_sources[value].append(source)
    
    # Display each value with its sources
    for value, sources in value_sources.items():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Value:** `{value}`")
                st.markdown(f"**Found in {len(sources)} location(s):**")
                for src in sources:
                    confidence_emoji = "🟢" if src["confidence"] >= 0.8 else "🟡" if src["confidence"] >= 0.6 else "🔴"
                    st.markdown(f"  {confidence_emoji} {src['document_type']} - {src['document_name']} "
                              f"(page {src['page']}, confidence: {src['confidence']:.2f})")
            
            with col2:
                if st.button("✅ Select", key=f"select_{field_name}_{value}"):
                    resolve_conflict(
                        submission_id=submission_id,
                        field_name=field_name,
                        selected_value=value,
                        reason=f"Selected from {sources[0]['document_type']}",
                        officer_name=st.session_state.get("officer_name", "Officer"),
                        db=db
                    )
                    st.success(f"Resolved {field_name} to: {value}")
                    st.rerun()
    
    st.divider()
    
    # Custom value option
    with st.expander("🖊️ Enter Custom Value"):
        custom_value = st.text_input(f"Custom value for {field_name}", key=f"custom_{field_name}")
        custom_reason = st.text_area("Reason for custom value", key=f"reason_{field_name}")
        
        if st.button("Save Custom Value", key=f"save_custom_{field_name}"):
            if custom_value:
                resolve_conflict(
                    submission_id=submission_id,
                    field_name=field_name,
                    selected_value=custom_value,
                    reason=custom_reason or "Custom value entered by officer",
                    officer_name=st.session_state.get("officer_name", "Officer"),
                    db=db
                )
                st.success(f"Resolved {field_name} to custom value: {custom_value}")
                st.rerun()
            else:
                st.error("Please enter a custom value")


def resolve_conflict(
    submission_id: int,
    field_name: str,
    selected_value: str,
    reason: str,
    officer_name: str,
    db: Database
) -> bool:
    """
    Resolve a field conflict by recording the officer's choice.
    
    Args:
        submission_id: Submission ID
        field_name: Field name
        selected_value: The value officer selected as correct
        reason: Reason for selection
        officer_name: Officer name
        db: Database instance
        
    Returns:
        True if successful
    """
    session = db.get_session()
    
    try:
        # Check if resolution already exists
        existing = session.query(FieldResolution).filter(
            FieldResolution.submission_id == submission_id,
            FieldResolution.field_name == field_name
        ).first()
        
        if existing:
            # Update existing resolution
            existing.resolved_value = selected_value
            existing.resolution_reason = reason
            existing.resolved_by = officer_name
            existing.created_at = datetime.utcnow()
        else:
            # Create new resolution
            resolution = FieldResolution(
                submission_id=submission_id,
                field_name=field_name,
                resolved_value=selected_value,
                resolution_reason=reason,
                resolved_by=officer_name
            )
            session.add(resolution)
        
        session.commit()
        
        # Log the resolution
        import logging
        LOGGER = logging.getLogger(__name__)
        LOGGER.info(
            "field_conflict_resolved",
            extra={
                "submission_id": submission_id,
                "field_name": field_name,
                "selected_value": selected_value,
                "officer_name": officer_name
            }
        )
        
        return True
    
    except Exception as e:
        session.rollback()
        st.error(f"Failed to resolve conflict: {str(e)}")
        return False
    
    finally:
        session.close()
