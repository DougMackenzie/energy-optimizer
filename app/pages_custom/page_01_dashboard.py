"""
Dashboard Page
Project overview and recent activity
"""

import streamlit as st
from app.utils.site_loader import load_sites, load_scenario_templates


def render():
    st.markdown("### 📊 Dashboard")
    
    # Load data
    sites = load_sites()
    scenarios = load_scenario_templates()
    
    # Check for current configuration
    has_config = 'current_config' in st.session_state
    has_validation = 'validation_result' in st.session_state
    has_optimization = 'optimization_result' in st.session_state
    
    # Key Metrics Row
    st.markdown("#### 📈 Project Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Available Sites", len(sites))
        st.caption("Template & custom sites")
    
    with col2:
        st.metric("Scenario Templates", len(scenarios))
        st.caption("Pre-loaded strategies")
    
    with col3:
        config_status = "Configured" if has_config else "Not Set"
        st.metric("Configuration", config_status)
        if has_config:
            st.caption(f"✓ {st.session_state.current_config['scenario']['Scenario_Name'][:20]}")
        else:
            st.caption("Start in Equipment Library")
    
    with col4:
        if has_optimization:
            result = st.session_state.optimization_result
            lcoe = result['economics']['lcoe_mwh']
            st.metric("Last LCOE", f"${lcoe:.0f}/MWh")
            st.caption("✓ Optimization complete")
        else:
            st.metric("Optimization", "Not Run")
            st.caption("Configure & validate first")
    
    # Current Configuration
    if has_config:
        st.markdown("---")
        st.markdown("#### ⚙️ Current Configuration")
        
        config = st.session_state.current_config
        site = config['site']
        scenario = config['scenario']
        equipment = config['equipment_enabled']
        
        col_site, col_scenario, col_equip = st.columns(3)
        
        with col_site:
            st.markdown("**Site:**")
            st.info(f"**{site.get('Site_Name', 'Unknown')}**\n\n{site.get('ISO', 'N/A')} • {site.get('Total_Facility_MW', 0)} MW")
        
        with col_scenario:
            st.markdown("**Scenario:**")
            st.info(f"**{scenario.get('Scenario_Name', 'Unknown')}**\n\nTarget: ${scenario.get('Target_LCOE_MWh', 0)}/MWh")
        
        with col_equip:
            st.markdown("**Equipment:**")
            enabled = [k.title() for k, v in equipment.items() if v]
            equip_list = ", ".join(enabled) if enabled else "None"
            st.info(f"**{len(enabled)} Technologies**\n\n{equip_list}")
        
        # Quick actions
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button("🔧 Modify Config", use_container_width=True):
                st.session_state.current_page = 'equipment_library'
                st.rerun()
        
        with col_act2:
            if st.button("🎯 Run Optimizer", use_container_width=True, type="primary"):
                st.session_state.current_page = 'optimizer'
                st.rerun()
        
        with col_act3:
            if has_optimization and st.button("📊 View Results", use_container_width=True):
                st.session_state.current_page = 'results'
                st.rerun()
    
    # Constraint Summary (if configured)
    if has_config and 'constraints' in st.session_state.current_config:
        st.markdown("---")
        st.markdown("#### ✅ Site Constraints Overview")
        
        constraints = st.session_state.current_config['constraints']
        
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            st.markdown("**Air Permit**")
            nox = constraints.get('NOx_Limit_tpy', 0)
            st.metric("NOx Limit", f"{nox} tpy", label_visibility="collapsed")
            
        with col_c2:
            st.markdown("**Gas Supply**")
            gas = constraints.get('Gas_Supply_MCF_day', 0)
            st.metric("Gas Supply", f"{gas:,.0f} MCF/d", label_visibility="collapsed")
        
        with col_c3:
            st.markdown("**Grid**")
            grid = constraints.get('Grid_Available_MW', 0)
            timeline = constraints.get('Estimated_Interconnection_Months', 0)
            st.metric("Available", f"{grid} MW", label_visibility="collapsed")
            st.caption(f"{timeline} mo timeline")
        
        with col_c4:
            st.markdown("**Land**")
            land = constraints.get('Available_Land_Acres', 0)
            st.metric("Available", f"{land} acres", label_visibility="collapsed")
            solar_ok = constraints.get('Solar_Feasible', 'Unknown')
            st.caption(f"Solar: {solar_ok}")
    
    # Validation Status (if validated)
    if has_validation:
        st.markdown("---")
        st.markdown("#### 🔍 Latest Validation")
        
        validation = st.session_state.validation_result
        
        if validation['feasible']:
            st.success("✅ **Configuration is FEASIBLE**")
        else:
            st.error(f"❌ **INFEASIBLE** - {len(validation['violations'])} violations")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        
        with col_v1:
            st.metric("Total Capacity", f"{validation['metrics'].get('total_capacity_mw', 0):.1f} MW")
        
        with col_v2:
            st.metric("Est. CAPEX", f"${validation['metrics'].get('total_capex_m', 0):.0f}M")
        
        with col_v3:
            violation_count = len(validation.get('violations', []))
            warning_count = len(validation.get('warnings', []))
            st.metric("Violations", violation_count)
            st.caption(f"{warning_count} warnings")
    
    # Optimization Results (if optimized)
    if has_optimization:
        st.markdown("---")
        st.markdown("#### 🎯 Latest Optimization Results")
        
        result = st.session_state.optimization_result
        economics = result['economics']
        timeline = result['timeline']
        
        col_o1, col_o2, col_o3, col_o4, col_o5 = st.columns(5)
        
        with col_o1:
            lcoe = economics['lcoe_mwh']
            st.metric("LCOE", f"${lcoe:.2f}/MWh")
        
        with col_o2:
            capex = economics['total_capex_m']
            st.metric("CAPEX", f"${capex:.1f}M")
        
        with col_o3:
            deploy = timeline['timeline_months']
            st.metric("Deployment", f"{deploy} mo")
            st.caption(f"{timeline['deployment_speed']}")
        
        with col_o4:
            annual_gen = economics['annual_generation_gwh']
            st.metric("Annual Gen", f"{annual_gen:.0f} GWh")
        
        with col_o5:
            if result['feasible']:
                st.success("✅ Feasible")
            else:
                st.error("❌ Infeasible")
    
    # Quick Start Guide (if nothing configured)
    if not has_config:
        st.markdown("---")
        st.markdown("#### 🚀 Quick Start Guide")
        
        st.info("""
        **Get started with energy optimization in 3 steps:**
        
        1. **Equipment Library** → Select site and scenario
        2. **Optimizer** → Size equipment and validate constraints
        3. **Results** → View LCOE, timeline, and economics
        """)
        
        if st.button("📋 Go to Equipment Library", type="primary"):
            st.session_state.current_page = 'equipment_library'
            st.rerun()
    
    # Recent Activity / Tips
    st.markdown("---")
    st.markdown("#### 💡 Tips & Best Practices")
    
    tip_col1, tip_col2 = st.columns(2)
    
    with tip_col1:
        st.markdown("""
        **Constraint Management:**
        - Stay under 100 tpy NOx for minor source
        - Verify gas supply for peak demand
        - Check N-1 reliability requirements
        - Account for transformer lead times (80-150 weeks)
        """)
    
    with tip_col2:
        st.markdown("""
        **Scenario Selection:**
        - BTM Only: Fastest (18 mo) but higher LCOE
        - All Sources: Most flexible, optimize across all
        - IFOM Bridge: Early revenue while awaiting grid
        - Grid + Solar: Lowest LCOE if grid available
        """)


if __name__ == "__main__":
    render()
