"""
Antigravity Energy Optimizer
Main Streamlit Application Entry Point

Run with: streamlit run app/main.py
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import APP_NAME, APP_VERSION, APP_ICON, COLORS

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
    }}
    
    /* Sidebar button hover */
    [data-testid="stSidebar"] .stButton>button:hover {{
        background-color: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
        transform: translateX(4px);
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
    .card {{
        background: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
        margin-bottom: 12px;
    }}
    
    .card-title {{
        font-size: 14px;
        font-weight: 600;
        color: {COLORS['text']};
        margin-bottom: 8px;
    }}
    
    /* Accent highlight */
    .highlight {{
        border-left: 4px solid {COLORS['accent']};
        padding-left: 12px;
    }}
    
    /* Status badges */
    .badge {{
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    .badge-success {{
        background: #d4edda;
        color: #155724;
    }}
    
    .badge-warning {{
        background: #fff3cd;
        color: #856404;
    }}
    
    .badge-danger {{
        background: #f8d7da;
        color: #721c24;
    }}
    
    /* Main content buttons */
    .stButton>button {{
        border-radius: 6px;
    }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Session State Initialization
# =============================================================================
if 'project' not in st.session_state:
    st.session_state.project = {
        'name': 'New Project',
        'site': None,
        'load_profile': None,
        'equipment': [],
        'constraints': {},
        'results': None,
    }

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

# Preload default data for faster testing (runs once per session)
from app.utils.session_init import initialize_default_data
initialize_default_data()

# =============================================================================
# Sidebar Navigation
# =============================================================================
with st.sidebar:
    # Logo
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0 20px 0;">
        <div style="width: 32px; height: 32px; background: {COLORS['accent']}; border-radius: 6px; 
                    display: flex; align-items: center; justify-content: center; font-size: 16px;">
            {APP_ICON}
        </div>
        <div>
            <div style="font-size: 16px; font-weight: 700; color: white;">Antigravity</div>
            <div style="font-size: 10px; color: rgba(255,255,255,0.6);">v{APP_VERSION}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation sections
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px;'>Overview</p>", unsafe_allow_html=True)
    
    if st.button("📊 Dashboard", use_container_width=True, key="nav_dashboard"):
        st.session_state.current_page = 'dashboard'
        st.rerun()
    
    if st.button("📚 Tutorial & Overview", use_container_width=True, key="nav_tutorial"):
        st.session_state.current_page = 'tutorial'
        st.rerun()
    
    if st.button("⚙️ Global Parameters", use_container_width=True, key="nav_global_params"):
        st.session_state.current_page = 'global_params'
        st.rerun()
    
    if st.button("📈 Load", use_container_width=True, key="nav_load_unified"):
        st.session_state.current_page = 'load_composer'
        st.rerun()
    
    
    # =============================================================================
    # Optimizer Section
    # =============================================================================
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Optimizer</p>", unsafe_allow_html=True)
    
    if st.button("📊 Executive Summary", use_container_width=True, key="nav_exec_summary"):
        st.session_state.current_page = 'exec_summary'
        st.rerun()
    
    if st.button("⚙️ Configuration", use_container_width=True, key="nav_configuration"):
        st.session_state.current_page = 'configuration'
        st.rerun()
    
    if st.button("📈 Dispatch", use_container_width=True, key="nav_dispatch_opt"):
        st.session_state.current_page = 'dispatch_opt'
        st.rerun()
    
    if st.button("💰 Financial Overview", use_container_width=True, key="nav_financial"):
        st.session_state.current_page = 'financial'
        st.rerun()
    
    if st.button("🔄 Comparison", use_container_width=True, key="nav_comparison"):
        st.session_state.current_page = 'comparison'
        st.rerun()
    
    # ARCHIVED:     st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Optimization</p>", unsafe_allow_html=True)
    # ARCHIVED:     
    # ARCHIVED:     if st.button("🔧 Equipment Library", use_container_width=True, key="nav_equip"):
    # ARCHIVED:         st.session_state.current_page = 'equipment'
    # ARCHIVED:         st.rerun()
    # ARCHIVED:         
    # ARCHIVED:     # ARCHIVED:     if st.button("🎯 Multi-Scenario Optimizer", use_container_width=True, key="nav_opt"):
    # ARCHIVED:     # ARCHIVED:         st.session_state.current_page = 'optimizer'
    # ARCHIVED:     # ARCHIVED:         st.rerun()
    # ARCHIVED:         
    # ARCHIVED:     if st.button("🛡️ RAM Analysis", use_container_width=True, key="nav_ram"):
    # ARCHIVED:         st.session_state.current_page = 'ram'
    # ARCHIVED:         st.rerun()
    
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Results</p>", unsafe_allow_html=True)
    
    if st.button("💰 Investor Portal", use_container_width=True, key="nav_investor_portal"):
        st.session_state.current_page = 'investor_portal'
        st.rerun()
        
    if st.button("🏢 Portfolio Overview", use_container_width=True, key="nav_portfolio_overview"):
        st.session_state.current_page = 'portfolio_overview'
        st.rerun()
    
    if st.button("📄 Detailed Reports", use_container_width=True, key="nav_detailed_reports"):
        st.session_state.current_page = 'detailed_reports'
        st.rerun()
    
    # Validation section
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Validation</p>", unsafe_allow_html=True)
    
    if st.button("🔗 Integration Export", use_container_width=True, key="nav_integration_export"):
        st.session_state.current_page = 'integration_export'
        st.rerun()
    
    if st.button("📥 Integration Import", use_container_width=True, key="nav_integration_import"):
        st.session_state.current_page = 'integration_import'
        st.rerun()
    
    # Debug section
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Developer</p>", unsafe_allow_html=True)
    
    if st.button("🐛 Debug", use_container_width=True, key="nav_debug"):
        st.session_state.current_page = 'debug'
        st.rerun()

# =============================================================================
# Page Router
# =============================================================================
def load_page(page_name: str):
    """Load and display the appropriate page"""
    
    if page_name == 'dashboard':
        from pages_custom import page_01_dashboard
        page_01_dashboard.render()
    
    elif page_name == 'tutorial':
        from pages_custom import page_tutorial
        page_tutorial.render()
    
    elif page_name == 'global_params':
        from pages_custom import page_global_params
        page_global_params.render()
        
    elif page_name == 'sites':
        from pages_custom import page_02_sites
        page_02_sites.render()
        
    elif page_name == 'load_composer':
        from pages_custom import page_03_load_composer
        page_03_load_composer.render()
        
    elif page_name == 'variability':
        from pages_custom import page_04_variability
        page_04_variability.render()
        
    elif page_name == 'transient':
        from pages_custom import page_05_transient
        page_05_transient.render()
        
    elif page_name == 'equipment' or page_name == 'equipment_library':
        from pages_custom import page_06_equipment
        page_06_equipment.render()
        
    elif page_name == 'optimizer':
        from pages_custom import page_07_optimizer
        page_07_optimizer.render()
        
    elif page_name == 'ram':
        from pages_custom import page_08_ram
        page_08_ram.render()
        
    
    # =============================================================================
    # Results Portal Pages
    # =============================================================================
    elif page_name == 'investor_portal':
        from pages_custom import page_investor_portal
        page_investor_portal.render()
    
    elif page_name == 'portfolio_overview':
        from pages_custom import page_portfolio_overview
        page_portfolio_overview.render()
    
    elif page_name == 'detailed_reports':
        from pages_custom import page_detailed_reports
        page_detailed_reports.render()
        
    # =============================================================================
    # Problem Statement Pages (bvNexus)
    # =============================================================================
    elif page_name == 'problem_selection':
        from pages_custom import page_problem_selection
        page_problem_selection.render()
    
    elif page_name == 'problem_1':
        from pages_custom import page_problem_1_greenfield
        page_problem_1_greenfield.render()
    
    elif page_name == 'problem_2':
        from pages_custom import page_problem_2_brownfield
        page_problem_2_brownfield.render()
    
    elif page_name == 'problem_3':
        from pages_custom import page_problem_3_land_dev
        page_problem_3_land_dev.render()
    
    elif page_name == 'problem_4':
        from pages_custom import page_problem_4_grid_services
        page_problem_4_grid_services.render()
    
    elif page_name == 'problem_5':
        from pages_custom import page_problem_5_bridge
        page_problem_5_bridge.render()
    
    # =============================================================================
    # New Optimizer Pages
    # =============================================================================
    elif page_name == 'exec_summary':
        from pages_custom import page_exec_summary
        page_exec_summary.render()
    
    elif page_name == 'configuration':
        from pages_custom import page_configuration
        page_configuration.render()
    
    elif page_name == 'dispatch_opt':
        from pages_custom import page_dispatch_opt
        page_dispatch_opt.render()
    
    elif page_name == 'financial':
        from pages_custom import page_financial
        page_financial.render()
    
    elif page_name == 'comparison':
        from pages_custom import page_comparison
        page_comparison.render()
    
    elif page_name == 'proforma':
        from pages_custom import page_proforma
        page_proforma.render()
    
    # =============================================================================
    # Integration Pages (Validation)
    # =============================================================================
    elif page_name == 'integration_export':
        from pages_custom import page_integration_export
        page_integration_export.render_integration_export_page()
    
    elif page_name == 'integration_import':
        from pages_custom import page_integration_import
        page_integration_import.render_integration_import_page()
        
    elif page_name == 'debug':
        from pages_custom import page_99_debug
        page_99_debug.render()
        
    else:
        st.error(f"Unknown page: {page_name}")

# Load the current page
load_page(st.session_state.current_page)