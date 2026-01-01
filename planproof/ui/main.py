"""
PlanProof UI - Main Streamlit application entry point.

NEW 3-TAB DESIGN:
- New Application: Upload and process documents
- My Cases: List all applications with version tracking
- Reports: Analytics and insights
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
    initial_sidebar_state="collapsed"  # Collapsed sidebar for cleaner look
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Hide sidebar navigation completely */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Modern header styling */
    .main-header {
        background-color: white;
        padding: 1rem 2rem;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 2rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 32px;
        background-color: white;
        padding: 0 2rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        padding: 0 4px;
        background-color: transparent;
        border-bottom: 2px solid transparent;
        color: #6b7280;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        border-bottom-color: #3b82f6;
        color: #3b82f6;
    }
    
    /* Clean button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* File uploader styling */
    .uploadedFile {
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }
    
    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "run_id" not in st.session_state:
    st.session_state.run_id = None
if "selected_case" not in st.session_state:
    st.session_state.selected_case = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "New Application"
if "processing_status" not in st.session_state:
    st.session_state.processing_status = None

# Header
st.markdown("""
<div class="main-header">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <span style="color: white; font-size: 20px;">📋</span>
        </div>
        <h1 style="margin: 0; font-size: 1.5rem; font-weight: bold; color: #111827;">PlanProof</h1>
        <span style="margin-left: auto; color: #6b7280; font-size: 14px;">👤 Planning Officer</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main 3-tab navigation
tab1, tab2, tab3 = st.tabs(["📤 New Application", "📋 My Cases", "📊 Reports"])

with tab1:
    from planproof.ui.pages import new_application_simple
    new_application_simple.render()

with tab2:
    from planproof.ui.pages import my_cases
    my_cases.render()

with tab3:
    from planproof.ui.pages import reports_dashboard
    reports_dashboard.render()

