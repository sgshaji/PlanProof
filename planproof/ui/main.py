"""
PlanProof UI - Main Streamlit application entry point.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="PlanProof - Planning Validation System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "run_id" not in st.session_state:
    st.session_state.run_id = None
if "stage" not in st.session_state:
    st.session_state.stage = "upload"  # upload, status, results
if "outputs" not in st.session_state:
    st.session_state.outputs = {}

# Navigation sidebar
st.sidebar.title("PlanProof")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Upload", "Status", "Results", "Case Overview", "Fields Viewer"],
    index=0 if st.session_state.stage == "upload" else (1 if st.session_state.stage == "status" else 2)
)

# Route to appropriate page
if page == "Upload":
    from planproof.ui.pages import upload
    upload.render()
elif page == "Status":
    from planproof.ui.pages import status
    status.render()
elif page == "Results":
    from planproof.ui.pages import results
    results.render()
elif page == "Case Overview":
    from planproof.ui.pages import case_overview
    case_overview.render()
elif page == "Fields Viewer":
    from planproof.ui.pages import fields
    fields.render()

