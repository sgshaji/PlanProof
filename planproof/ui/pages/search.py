"""
Search page for PlanProof UI.
"""

import streamlit as st
from planproof.services.search_service import search_cases, search_submissions, search_documents
from planproof.db import Database


def render():
    """Render search page."""
    st.title("🔍 Search Cases & Submissions")
    
    # Search input
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Search",
            placeholder="Enter case reference, address, postcode, or description...",
            label_visibility="collapsed"
        )
    
    with col2:
        search_type = st.selectbox(
            "Search in",
            ["Cases", "Submissions", "Documents"],
            label_visibility="collapsed"
        )
    
    # Filters
    with st.expander("🎯 Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            status_filter = st.multiselect(
                "Status",
                ["pending", "in_progress", "needs_info", "approved", "rejected"],
                default=[]
            )
        
        with filter_col2:
            date_from = st.date_input("From date", value=None)
        
        with filter_col3:
            date_to = st.date_input("To date", value=None)
    
    # Build filters dict
    filters = {}
    if status_filter:
        filters["status"] = status_filter[0]  # Single status for now
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    
    # Search button
    if st.button("🔍 Search", type="primary") or query:
        if not query and not filters:
            st.warning("Please enter a search query or select filters.")
            return
        
        # Perform search
        db = Database()
        
        try:
            with st.spinner(f"Searching {search_type.lower()}..."):
                if search_type == "Cases":
                    results = search_cases(query, filters=filters, limit=50, db=db)
                elif search_type == "Submissions":
                    results = search_submissions(query, filters=filters, limit=50, db=db)
                else:  # Documents
                    results = search_documents(query, filters=filters, limit=50, db=db)
            
            # Display results
            total_count = results.get("total_count", 0)
            
            if total_count == 0:
                st.info("No results found. Try a different search query or filters.")
                return
            
            st.success(f"Found {total_count} {search_type.lower()}")
            
            # Display results based on type
            if search_type == "Cases":
                display_case_results(results["results"])
            elif search_type == "Submissions":
                display_submission_results(results["results"])
            else:  # Documents
                display_document_results(results["results"])
        
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            st.exception(e)


def display_case_results(results):
    """Display case search results."""
    for result in results:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### 📋 {result['case_ref']}")
                if result['site_address']:
                    st.markdown(f"**Address:** {result['site_address']}")
                if result['postcode']:
                    st.markdown(f"**Postcode:** {result['postcode']}")
                if result['description']:
                    st.markdown(f"**Description:** {result['description'][:100]}...")
            
            with col2:
                st.markdown(f"**Status:** `{result['status']}`")
                if result['latest_submission_version']:
                    st.markdown(f"**Latest Version:** {result['latest_submission_version']}")
                
                # Validation summary
                val_summary = result.get('validation_summary', {})
                if val_summary.get('total', 0) > 0:
                    st.markdown(f"**Validation:** ✅ {val_summary.get('pass', 0)} / "
                              f"❌ {val_summary.get('fail', 0)} / "
                              f"⚠️ {val_summary.get('needs_review', 0)}")
            
            with col3:
                if result['latest_submission_id']:
                    if st.button("View", key=f"view_case_{result['case_id']}"):
                        st.session_state.submission_id = result['latest_submission_id']
                        st.session_state.stage = "results"
                        st.rerun()
            
            st.divider()


def display_submission_results(results):
    """Display submission search results."""
    for result in results:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### 📄 {result['case_ref']} - {result['submission_version']}")
                st.markdown(f"**Submission ID:** {result['submission_id']}")
            
            with col2:
                st.markdown(f"**Status:** `{result['status']}`")
                
                # Validation summary
                val_summary = result.get('validation_summary', {})
                if val_summary.get('total', 0) > 0:
                    st.markdown(f"**Validation:** ✅ {val_summary.get('pass', 0)} / "
                              f"❌ {val_summary.get('fail', 0)} / "
                              f"⚠️ {val_summary.get('needs_review', 0)}")
            
            with col3:
                if st.button("View", key=f"view_submission_{result['submission_id']}"):
                    st.session_state.submission_id = result['submission_id']
                    st.session_state.stage = "results"
                    st.rerun()
            
            st.divider()


def display_document_results(results):
    """Display document search results."""
    for result in results:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### 📎 {result['filename']}")
                st.markdown(f"**Type:** {result['document_type']}")
                st.markdown(f"**Pages:** {result.get('page_count', 'N/A')}")
            
            with col2:
                st.markdown(f"**Submission ID:** {result['submission_id']}")
                if result.get('created_at'):
                    st.markdown(f"**Uploaded:** {result['created_at'][:10]}")
            
            with col3:
                if st.button("View", key=f"view_doc_{result['document_id']}"):
                    st.session_state.submission_id = result['submission_id']
                    st.session_state.stage = "results"
                    st.rerun()
            
            st.divider()
