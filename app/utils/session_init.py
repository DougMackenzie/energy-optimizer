"""
Session State Initialization
Preloads default data for faster development/testing
"""

import streamlit as st


def initialize_default_data():
    """
    Initialize session state with default data for faster testing.
    Loads default site and scenario configuration.
    """
    
    # Only run once per session
    if 'initialized' in st.session_state:
        return
    
    # Load default site and configuration
    try:
        from app.utils.site_loader import load_sites, load_site_constraints, load_scenario_templates
        
            # AUTO-LOAD 600MW SAMPLE PROBLEM (Robust Default)
            from sample_problem_600mw import get_sample_problem
            problem = get_sample_problem()
            
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
