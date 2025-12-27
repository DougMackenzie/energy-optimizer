"""
Session State Initialization
Preloads default data for faster development/testing
Supports both traditional multi-scenario and bvNexus problem-statement approaches
"""

import streamlit as st


def initialize_default_data():
    """
    Initialize session state with default data for faster testing.
    Loads default site and scenario configuration.
    Supports both existing MILP and new bvNexus problem-statement workflows.
    """
    
    # Only run once per session
    if 'initialized' in st.session_state:
        return
    
    # =============================================================================
    # bvNexus Problem-Statement State
    # =============================================================================
    
    # Current page and problem selection
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    
    if 'selected_problem' not in st.session_state:
        st.session_state.selected_problem = None
    
    # Problem completion tracking
    if 'phase_1_complete' not in st.session_state:
        st.session_state.phase_1_complete = {}  # {problem_num: bool}
    
    if 'phase_2_complete' not in st.session_state:
        st.session_state.phase_2_complete = {}  # {problem_num: bool}
    
    # Problem-specific results
    if 'optimization_results' not in st.session_state:
        st.session_state.optimization_results = {}  # {problem_num: result_dict}
    
    # Current site and load configuration
    if 'current_site' not in st.session_state:
        st.session_state.current_site = None
    
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = None  # screening, concept, preliminary, detailed
    
    # Site optimization stages tracking (per-site EPC workflow)
    if 'site_optimization_stages' not in st.session_state:
        st.session_state.site_optimization_stages = {}  # {site_name: {stages}}
    
    # Load sites from Google Sheets
    if 'sites_list' not in st.session_state:
        try:
            from app.utils.site_backend import load_all_sites
            st.session_state.sites_list = load_all_sites(use_cache=False)
            # Check if empty
            if not st.session_state.sites_list:
                raise ValueError("No sites loaded")
        except Exception as e:
            # Initialize sample optimization data if needed
            try:
                from app.utils.sample_optimization_data import save_sample_data_to_sheets
                save_sample_data_to_sheets()
                print("✓ Sample optimization data initialized")
            except Exception as e2:
                print(f"Could not initialize sample data: {e2}")
            print(f"Could not load sites from Google Sheets: {e}")
            # Initialize with sample sites from dashboard
            st.session_state.sites_list = [
                {
                    'name': 'Phoenix AI Campus',
                    'location': 'Phoenix, AZ',
                    'iso': 'CAISO',
                    'it_capacity_mw': 750,
                    'pue': 1.20,
                    'facility_mw': 900,
                    'land_acres': 450,
                    'nox_limit_tpy': 120,
                    'gas_supply_mcf': 150000,
                    'voltage_kv': 500,
                    'coordinates': [33.448, -112.074],
                    'geojson_prefix': 'phoenix'
                },
                {
                    'name': 'Dallas Hyperscale DC',
                    'location': 'Dallas, TX',
                    'iso': 'ERCOT',
                    'it_capacity_mw': 600,
                    'pue': 1.25,
                    'facility_mw': 750,
                    'land_acres': 600,
                    'nox_limit_tpy': 150,
                    'gas_supply_mcf': 200000,
                    'voltage_kv': 345,
                    'coordinates': [32.776, -96.797],
                    'geojson_prefix': 'dallas'
                }
                ,
                {
                    'name': 'Austin Greenfield DC',
                    'location': 'Austin, TX',
                    'iso': 'ERCOT',
                    'it_capacity_mw': 500,
                    'pue': 1.22,
                    'facility_mw': 610,
                    'land_acres': 380,
                    'nox_limit_tpy': 95,
                    'gas_supply_mcf': 125000,
                    'voltage_kv': 345,
                    'coordinates': [30.267, -97.743],
                    'geojson_prefix': 'austin',
                    'problem_num': 1,
                    'problem_name': 'Greenfield Datacenter'
                }
            ]
            print(f"✓ Using {len(st.session_state.sites_list)} fallback sites")
    
    if 'load_trajectory' not in st.session_state:
        st.session_state.load_trajectory = None
    
    if 'facility_trajectory' not in st.session_state:
        st.session_state.facility_trajectory = None
    
    if 'workload_mix' not in st.session_state:
        st.session_state.workload_mix = None
    
    # =============================================================================
    # Existing MILP State (Preserve Compatibility)
    # =============================================================================
    
    # Load default site and configuration
    try:
        from app.utils.site_loader import load_sites, load_site_constraints, load_scenario_templates
        
        # AUTO-LOAD 600MW SAMPLE PROBLEM (Robust Default)
        from sample_problem_600mw import get_sample_problem
        problem = get_sample_problem()
        
        # Load scenarios to pick "All Technologies"
        scenarios = load_scenario_templates()
        
        # Set default config
        st.session_state.current_config = {
            'site': problem['site'],
            'scenario': scenarios[1] if len(scenarios) > 1 else scenarios[0], # All Technologies
            'constraints': {
                **problem['constraints'],
                'N_Minus_1_Required': False # Ensure feasibility
            },
            'objectives': {
                'Primary_Objective': 'Minimize_LCOE',
                'LCOE_Max_MWh': 100,
                'Deployment_Max_Months': 36,
            },
            'equipment_enabled': {
                'recip': True, 'turbine': True, 'bess': True, 'solar': True, 'grid': True
            }
        }
        
        # Set Load Profile (CRITICAL for MILP)
        st.session_state.load_profile_dr = problem['load_profile']
        
        # Also add to current_config for consistency
        st.session_state.current_config['load_profile_dr'] = problem['load_profile']
        
        # Force Accurate Mode
        st.session_state.use_fast_milp = False
        
        print("✅ Auto-loaded 600MW Sample Problem & Forced Accurate Mode")
    
    except Exception as e:
        # Silently fail - user can manually select
        import traceback
        print(f"Initialization warning: {e}")
        print(traceback.format_exc())
    
    # Mark as initialized
    st.session_state.initialized = True
