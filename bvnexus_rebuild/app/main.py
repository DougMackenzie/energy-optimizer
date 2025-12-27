"""
bvNexus - Co-located Power, Energy and Load Optimization
Main Streamlit Application Entry Point

Run with: streamlit run app/main.py
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    APP_NAME, APP_VERSION, APP_ICON, APP_TAGLINE, 
    COLORS, PROBLEM_STATEMENTS
)

# =============================================================================
# Page Configuration
# =============================================================================
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Custom CSS
# =============================================================================
st.markdown(f"""
<style>
    /* Main theme colors */
    :root {{
        --primary: {COLORS['primary']};
        --secondary: {COLORS['secondary']};
        --accent: {COLORS['accent']};
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS['primary']} 0%, #152a45 100%);
    }}
    
    /* Make all sidebar text white */
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton>button {{
        width: 100%;
        border-radius: 6px;
        background-color: rgba(255, 255, 255, 0.1);
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
        text-align: left;
        padding: 8px 12px;
    }}
    
    /* Sidebar button hover */
    [data-testid="stSidebar"] .stButton>button:hover {{
        background-color: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
        transform: translateX(4px);
    }}
    
    /* Active page indicator */
    [data-testid="stSidebar"] .stButton>button[data-active="true"] {{
        background-color: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}
    
    /* Hide default Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Metric cards */
    [data-testid="stMetricValue"] {{
        font-size: 24px;
        font-weight: 700;
    }}
    
    /* Custom card styling */
    .problem-card {{
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 2px solid #e9ecef;
        margin-bottom: 16px;
        transition: all 0.3s ease;
        cursor: pointer;
    }}
    
    .problem-card:hover {{
        border-color: {COLORS['accent']};
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }}
    
    .problem-card-selected {{
        border-color: {COLORS['accent']};
        background: linear-gradient(135deg, #fff 0%, #fff8f0 100%);
    }}
    
    /* Phase indicator badges */
    .phase-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    }}
    
    .phase-1 {{
        background: #e6fffa;
        color: #234e52;
    }}
    
    .phase-2 {{
        background: #ebf4ff;
        color: #2a4365;
    }}
    
    /* Tier indicator */
    .tier-indicator {{
        background: #fef3c7;
        color: #92400e;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }}
    
    /* Results table styling */
    .results-table {{
        width: 100%;
        border-collapse: collapse;
    }}
    
    .results-table th {{
        background: {COLORS['primary']};
        color: white;
        padding: 12px;
        text-align: left;
    }}
    
    .results-table td {{
        padding: 10px 12px;
        border-bottom: 1px solid #e9ecef;
    }}
    
    /* Accent highlight */
    .highlight {{
        border-left: 4px solid {COLORS['accent']};
        padding-left: 12px;
        background: #fffbf5;
    }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Session State Initialization
# =============================================================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

if 'selected_problem' not in st.session_state:
    st.session_state.selected_problem = None

if 'current_site' not in st.session_state:
    st.session_state.current_site = None

if 'load_profile' not in st.session_state:
    st.session_state.load_profile = None

if 'optimization_results' not in st.session_state:
    st.session_state.optimization_results = {}

if 'phase_1_complete' not in st.session_state:
    st.session_state.phase_1_complete = {}

if 'phase_2_complete' not in st.session_state:
    st.session_state.phase_2_complete = {}

# =============================================================================
# Sidebar Navigation
# =============================================================================
with st.sidebar:
    # Logo and branding
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 10px 0 20px 0;">
        <div style="width: 40px; height: 40px; background: {COLORS['accent']}; border-radius: 8px; 
                    display: flex; align-items: center; justify-content: center; font-size: 20px;">
            {APP_ICON}
        </div>
        <div>
            <div style="font-size: 18px; font-weight: 700; color: white;">{APP_NAME}</div>
            <div style="font-size: 10px; color: rgba(255,255,255,0.6);">v{APP_VERSION}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Overview Section
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px;'>Overview</p>", unsafe_allow_html=True)
    
    if st.button("📊 Dashboard", use_container_width=True, key="nav_dashboard"):
        st.session_state.current_page = 'dashboard'
        st.rerun()
    
    if st.button("📍 Sites & Load", use_container_width=True, key="nav_sites"):
        st.session_state.current_page = 'sites'
        st.rerun()
    
    if st.button("⚙️ Equipment Library", use_container_width=True, key="nav_equipment"):
        st.session_state.current_page = 'equipment'
        st.rerun()
    
    st.markdown("---")
    
    # Problem Statements Section
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px;'>Optimization Problems</p>", unsafe_allow_html=True)
    
    if st.button("🎯 Problem Selection", use_container_width=True, key="nav_problem_select"):
        st.session_state.current_page = 'problem_selection'
        st.rerun()
    
    # Show individual problem buttons
    for prob_num, prob_info in PROBLEM_STATEMENTS.items():
        # Show checkmark if Phase 1 complete
        status = "✓" if st.session_state.phase_1_complete.get(prob_num, False) else ""
        button_label = f"{prob_info['icon']} P{prob_num}: {prob_info['short_name']} {status}"
        
        if st.button(button_label, use_container_width=True, key=f"nav_prob_{prob_num}"):
            st.session_state.current_page = f'problem_{prob_num}'
            st.session_state.selected_problem = prob_num
            st.rerun()
    
    st.markdown("---")
    
    # Results Section
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px;'>Outputs & Analysis</p>", unsafe_allow_html=True)
    
    if st.button("📈 Results Dashboard", use_container_width=True, key="nav_results"):
        st.session_state.current_page = 'results'
        st.rerun()
    
    if st.button("📊 8760 Dispatch", use_container_width=True, key="nav_dispatch"):
        st.session_state.current_page = 'dispatch'
        st.rerun()
    
    if st.button("💰 Pro Forma", use_container_width=True, key="nav_proforma"):
        st.session_state.current_page = 'proforma'
        st.rerun()
    
    if st.button("🔧 RAM Analysis", use_container_width=True, key="nav_ram"):
        st.session_state.current_page = 'ram'
        st.rerun()
    
    st.markdown("---")
    
    # Current context indicator
    if st.session_state.selected_problem:
        prob = PROBLEM_STATEMENTS[st.session_state.selected_problem]
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin-top: 10px;">
            <div style="font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px;">Active Problem</div>
            <div style="font-size: 14px; font-weight: 600;">{prob['icon']} {prob['short_name']}</div>
            <div style="font-size: 11px; color: rgba(255,255,255,0.7); margin-top: 4px;">{prob['objective']}</div>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# Page Router
# =============================================================================
def load_page(page_name: str):
    """Load and display the appropriate page"""
    
    try:
        if page_name == 'dashboard':
            from app.pages import page_dashboard
            page_dashboard.render()
            
        elif page_name == 'sites':
            from app.pages import page_sites_load
            page_sites_load.render()
            
        elif page_name == 'equipment':
            from app.pages import page_equipment
            page_equipment.render()
            
        elif page_name == 'problem_selection':
            from app.pages import page_problem_selection
            page_problem_selection.render()
            
        elif page_name == 'problem_1':
            from app.pages import page_problem_1_greenfield
            page_problem_1_greenfield.render()
            
        elif page_name == 'problem_2':
            from app.pages import page_problem_2_brownfield
            page_problem_2_brownfield.render()
            
        elif page_name == 'problem_3':
            from app.pages import page_problem_3_land_dev
            page_problem_3_land_dev.render()
            
        elif page_name == 'problem_4':
            from app.pages import page_problem_4_grid_services
            page_problem_4_grid_services.render()
            
        elif page_name == 'problem_5':
            from app.pages import page_problem_5_bridge
            page_problem_5_bridge.render()
            
        elif page_name == 'results':
            from app.pages import page_results
            page_results.render()
            
        elif page_name == 'dispatch':
            from app.pages import page_dispatch
            page_dispatch.render()
            
        elif page_name == 'proforma':
            from app.pages import page_proforma
            page_proforma.render()
            
        elif page_name == 'ram':
            from app.pages import page_ram
            page_ram.render()
            
        else:
            st.error(f"Unknown page: {page_name}")
            st.info("Returning to dashboard...")
            from app.pages import page_dashboard
            page_dashboard.render()
            
    except ImportError as e:
        st.error(f"Page module not found: {e}")
        st.info("This page is under development. Check back soon!")
        
        # Show placeholder
        st.markdown("---")
        st.markdown("### 🚧 Page Under Construction")
        st.markdown(f"The **{page_name}** page is being built.")
        
        if st.button("← Return to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()

# Load the current page
load_page(st.session_state.current_page)
