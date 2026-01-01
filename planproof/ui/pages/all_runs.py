"""
All Runs Page - Complete run history with filters and search.
"""

import streamlit as st
from typing import List, Dict, Any
from planproof.db import Database, Run
from datetime import datetime, timedelta
import json


def get_all_runs(
    search_query: str = "",
    status_filter: str = "all",
    date_from: datetime = None,
    date_to: datetime = None,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[Dict[str, Any]], int]:
    """
    Fetch all runs with filters and pagination.

    Returns:
        tuple: (list of runs, total count)
    """
    db = Database()
    session = db.get_session()

    try:
        query = session.query(Run).order_by(Run.created_at.desc())

        # Apply filters
        if status_filter != "all":
            query = query.filter(Run.status == status_filter)

        if date_from:
            query = query.filter(Run.created_at >= date_from)

        if date_to:
            query = query.filter(Run.created_at <= date_to)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        runs = query.limit(page_size).offset(offset).all()

        result = []
        for run in runs:
            # Parse metadata
            metadata = run.metadata or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            app_ref = metadata.get("application_ref", "N/A")

            # Apply search filter
            if search_query:
                if (search_query.lower() not in app_ref.lower() and
                    search_query.lower() not in str(run.id)):
                    continue

            # Get progress info
            progress_info = metadata.get("progress", {})

            result.append({
                "id": run.id,
                "application_ref": app_ref,
                "status": run.status,
                "run_type": run.run_type or "unknown",
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "error_message": run.error_message,
                "file_count": metadata.get("file_count", 0),
                "progress": progress_info,
                "is_modification": metadata.get("is_modification", False),
                "applicant_name": metadata.get("applicant_name", "Unknown")
            })

        return result, total_count

    finally:
        session.close()


def render():
    """Render the All Runs page."""

    st.markdown("## 🔍 All Validation Runs")
    st.markdown("Complete history of all processing runs")
    st.markdown("---")

    # Initialize session state for pagination
    if "runs_page" not in st.session_state:
        st.session_state.runs_page = 1

    # Filters and search
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="🔍 Search by run ID or application reference...",
            label_visibility="collapsed",
            key="runs_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["all", "running", "completed", "failed"],
            key="runs_status_filter"
        )

    with col3:
        date_range = st.selectbox(
            "Date Range",
            options=["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom"],
            key="runs_date_range"
        )

    # Date range calculation
    date_from = None
    date_to = None

    if date_range == "Today":
        date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = datetime.now()
    elif date_range == "Last 7 Days":
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()
    elif date_range == "Last 30 Days":
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now()
    elif date_range == "Custom":
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            date_from = st.date_input("From", value=datetime.now() - timedelta(days=30))
            date_from = datetime.combine(date_from, datetime.min.time())
        with col_date2:
            date_to = st.date_input("To", value=datetime.now())
            date_to = datetime.combine(date_to, datetime.max.time())

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    # Fetch runs
    page_size = 20
    with st.spinner("Loading runs..."):
        runs, total_count = get_all_runs(
            search_query=search_query,
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to,
            page=st.session_state.runs_page,
            page_size=page_size
        )

    # Summary metrics
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric("Total Runs", total_count)

    with metric_col2:
        running_count = len([r for r in runs if r["status"] == "running"])
        st.metric("🔄 Running", running_count)

    with metric_col3:
        completed_count = len([r for r in runs if r["status"] == "completed"])
        st.metric("✅ Completed", completed_count)

    with metric_col4:
        failed_count = len([r for r in runs if r["status"] == "failed"])
        st.metric("❌ Failed", failed_count)

    st.markdown("---")

    # Display runs
    if not runs:
        st.info("📭 No runs found matching your filters")
        return

    for run in runs:
        with st.container():
            # Run card
            col_main, col_actions = st.columns([3, 1])

            with col_main:
                # Status icon
                status_icons = {
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "pending": "⏳"
                }
                icon = status_icons.get(run["status"], "⚪")

                # Title
                title = f"{icon} Run #{run['id']} - {run['application_ref']}"
                if run["is_modification"]:
                    title += " (Revision)"

                st.markdown(f"### {title}")

                # Metadata
                info_parts = []
                info_parts.append(f"📅 {run['created_at'].strftime('%Y-%m-%d %H:%M')}")
                info_parts.append(f"📂 {run['file_count']} file(s)")
                info_parts.append(f"🏷️ {run['run_type']}")

                if run["applicant_name"] != "Unknown":
                    info_parts.append(f"👤 {run['applicant_name']}")

                st.markdown(" | ".join(info_parts))

                # Progress bar for running jobs
                if run["status"] == "running" and run["progress"]:
                    current = run["progress"].get("current", 0)
                    total = run["progress"].get("total", 1)
                    if total > 0:
                        progress = current / total
                        st.progress(progress, text=f"Processing: {current}/{total}")

                # Error message if failed
                if run["status"] == "failed" and run["error_message"]:
                    with st.expander("❌ Error Details"):
                        st.error(run["error_message"])

            with col_actions:
                # View Results button
                if st.button("📋 View", key=f"view_run_{run['id']}", use_container_width=True):
                    st.session_state.run_id = run["id"]
                    st.session_state.current_tab = "Results"
                    st.rerun()

                # Auto-refresh for running jobs
                if run["status"] == "running":
                    st.caption("Auto-refreshing...")

            st.markdown("---")

    # Pagination
    total_pages = (total_count + page_size - 1) // page_size

    if total_pages > 1:
        st.markdown("### 📄 Pagination")

        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.button("← Previous", disabled=st.session_state.runs_page == 1, use_container_width=True):
                st.session_state.runs_page -= 1
                st.rerun()

        with col_info:
            st.markdown(
                f"<div style='text-align: center; padding: 8px;'>"
                f"Page {st.session_state.runs_page} of {total_pages}"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_next:
            if st.button("Next →", disabled=st.session_state.runs_page >= total_pages, use_container_width=True):
                st.session_state.runs_page += 1
                st.rerun()

    # Auto-refresh for running jobs
    if any(r["status"] == "running" for r in runs):
        import time
        time.sleep(3)
        st.rerun()
