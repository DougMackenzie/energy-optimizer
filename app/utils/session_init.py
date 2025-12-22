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
        
        sites = load_sites()
        
        if sites and len(sites) > 0:
            # Use Dallas Datacenter Campus (first site) as default
            default_site = sites[0]
            
            # Load constraints for this site
            constraints = load_site_constraints(default_site.get('Site_Name', ''))
            
            # Load scenario templates
            from app.utils.site_loader import load_scenario_templates
            scenarios = load_scenario_templates()
            
            # Use "Grid + Solar (Renewable)" as default scenario
            default_scenario = next(
                (s for s in scenarios if 'Grid' in s.get('Scenario_Name', '') and 'Solar' in s.get('Scenario_Name', '')), 
                scenarios[0] if scenarios else None
            )
            
            if default_scenario:
                # Set up equipment enabled flags
                equipment_enabled = {
                    'recip': default_scenario.get('Recip_Engines') == 'True',
                    'turbine': default_scenario.get('Gas_Turbines') == 'True',
                    'bess': default_scenario.get('BESS') == 'True',
                    'solar': default_scenario.get('Solar_PV') == 'True',
                    'grid': default_scenario.get('Grid_Connection') == 'True',
                }
                
                objectives = {
                    'Primary_Objective': 'LCOE',
                    'Deployment_Max_Months': 36,
                    'LCOE_Weight': 0.5,
                    'Timeline_Weight': 0.3,
                    'Emissions_Weight': 0.2
                }
                
                # Store in session state (but don't run optimization yet)
                st.session_state.current_config = {
                    'site': default_site,
                    'scenario': default_scenario,
                    'constraints': constraints,
                    'equipment_enabled': equipment_enabled,
                    'objectives': objectives
                }
                
                # Note: User can run "Run All Scenarios" button once to get results
                # This avoids slow initialization and potential errors
    
    except Exception as e:
        # Silently fail - user can manually select
        import traceback
        print(f"Initialization warning: {e}")
        print(traceback.format_exc())
    
    # Mark as initialized
    st.session_state.initialized = True
