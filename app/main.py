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
    
    if st.button("📍 Sites", use_container_width=True, key="nav_sites"):
        st.session_state.current_page = 'sites'
        st.rerun()
    
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Load Analysis</p>", unsafe_allow_html=True)
    
    if st.button("📈 Load Composer", use_container_width=True, key="nav_load"):
        st.session_state.current_page = 'load_composer'
        st.rerun()
        
    if st.button("📊 Variability", use_container_width=True, key="nav_var"):
        st.session_state.current_page = 'variability'
        st.rerun()
        
    if st.button("⚡ Transient Screen", use_container_width=True, key="nav_trans"):
        st.session_state.current_page = 'transient'
        st.rerun()
    
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Optimization</p>", unsafe_allow_html=True)
    
    if st.button("🔧 Equipment Library", use_container_width=True, key="nav_equip"):
        st.session_state.current_page = 'equipment'
        st.rerun()
        
    if st.button("🎯 Optimizer", use_container_width=True, key="nav_opt"):
        st.session_state.current_page = 'optimizer'
        st.rerun()
        
    if st.button("🛡️ RAM Analysis", use_container_width=True, key="nav_ram"):
        st.session_state.current_page = 'ram'
        st.rerun()
    
    st.markdown("<p style='font-size: 10px; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px; margin-top: 16px;'>Results</p>", unsafe_allow_html=True)
    
    if st.button("📊 Results", use_container_width=True, key="nav_results"):
        st.session_state.current_page = 'results'
        st.rerun()
        
    if st.button("⚙️ Dispatch", use_container_width=True, key="nav_dispatch"):
        st.session_state.current_page = 'dispatch'
        st.rerun()

# =============================================================================
# Page Router
# =============================================================================
def load_page(page_name: str):
    """Load and display the appropriate page"""
    
    if page_name == 'dashboard':
        from pages_custom import page_01_dashboard
        page_01_dashboard.render()
        
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
        
    elif page_name == 'results':
        from pages_custom import page_09_results
        page_09_results.render()
        
    elif page_name == 'dispatch':
        from pages_custom import page_10_dispatch
        page_10_dispatch.render()
        
    elif page_name == 'debug':
        from pages_custom import page_99_debug
        page_99_debug.render()
        
    else:
        st.error(f"Unknown page: {page_name}")

# Load the current page
load_page(st.session_state.current_page)