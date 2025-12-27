"""
Executive Summary Page
High-level overview of optimization results
"""

import streamlit as st
from app.utils.site_context_helper import display_site_context


def render():
    st.markdown("### 📊 Executive Summary")
    st.caption("High-level overview of optimization results and 15-year energy forecast")
    
    # Site selector
    col_site1, col_site2 = st.columns([2, 1])
    
    with col_site1:
        if 'sites_list' in st.session_state and st.session_state.sites_list:
            site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
            selected_site = st.selectbox(
                "Select Site",
                options=site_names,
                index=0 if not st.session_state.get('current_site') else 
                      (site_names.index(st.session_state.current_site) if st.session_state.current_site in site_names else 0),
                key="exec_summary_site_selector"
            )
            
            # Display site context AFTER selected_site is defined
            display_site_context(selected_site)
            
            # Update current site
            if selected_site != st.session_state.get('current_site'):
                st.session_state.current_site = selected_site
                st.rerun()
        else:
            st.warning("No sites configured. Please create a site in Dashboard → Sites & Infrastructure")
            return
    
    with col_site2:
        # Stage selector
        stage = st.selectbox(
            "EPC Stage",
            options=["Screening Study", "Concept Development", "Preliminary Design", "Detailed Design"],
            key="exec_summary_stage"
        )
    
    st.markdown("---")
    
    
    # Get site object from selected site name
    site_obj = next((s for s in st.session_state.sites_list if s.get('name') == selected_site), {})
    
    # Display problem type prominently
    problem_num_display = site_obj.get('problem_num', 1)  # Load from site data (Google Sheets)
    from config.settings import PROBLEM_STATEMENTS
    problem_info_display = PROBLEM_STATEMENTS.get(problem_num_display, PROBLEM_STATEMENTS[1])
    
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
                padding: 16px 24px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #2b6cb0;">
        <div style="color: white; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
            {problem_info_display['icon']} PROBLEM STATEMENT
        </div>
        <div style="color: #bee3f8; font-size: 18px; font-weight: 700;">
            P{problem_num_display}: {problem_info_display['name']}
        </div>
        <div style="color: #90cdf4; font-size: 13px; margin-top: 4px;">
            {problem_info_display['objective']} — {problem_info_display['question']}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Load optimization results
    stage_key_map = {
        "Screening Study": "screening",
        "Concept Development": "concept",
        "Preliminary Design": "preliminary",
        "Detailed Design": "detailed"
    }
    
    stage_key = stage_key_map.get(stage, "screening")
    
    # Try to load results from Google Sheets
    try:
        from app.utils.site_backend import load_site_stage_result
        # Check session_state for unsaved results first
        if ('optimization_result' in st.session_state and \
            st.session_state.get('optimization_site') == selected_site and \
            st.session_state.get('optimization_stage') == stage_key):
            result_data = st.session_state.optimization_result
            st.info("📝 Showing unsaved results. Go to Configuration to save.")
        else:
                    result_data = load_site_stage_result(selected_site, stage_key)
                    
        if result_data:
            lcoe = result_data.get('lcoe', 0)
            npv = result_data.get('npv', 0) / 1_000_000  # Convert to millions
            equipment = result_data.get('equipment', {})
            total_capacity = sum([equipment.get('recip_mw', 0), equipment.get('turbine_mw', 0), 
                                equipment.get('solar_mw', 0), equipment.get('grid_mw', 0)])
            # Ensure coverage is always a float
            try:
                coverage = float(result_data.get('load_coverage_pct', 0))
            except (ValueError, TypeError):
                coverage = 0.0
            constraints = result_data.get('constraints', {})
            
            has_results = True
        else:
            has_results = False
            lcoe = npv = total_capacity = coverage = 0
            equipment = {}
            constraints = {}
    except Exception as e:
        print(f"Error loading results: {e}")
        has_results = False
        lcoe = npv = total_capacity = coverage = 0
        equipment = {}
        constraints = {}
    
    # Key Metrics Cards
    st.markdown("#### Key Metrics")
    
    if not has_results:
        st.warning(f"⚠️ No optimization results found for {selected_site} - {stage}")
        st.info("💡 Go to Configuration page to run an optimization")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("LCOE", f"${lcoe:.1f}/MWh" if has_results else "Not run", help="Levelized Cost of Energy ($/MWh)")
    
    with col_m2:
        st.metric("NPV", f"${npv:.0f}M" if has_results else "Not run", help="Net Present Value ($M)")
    
    with col_m3:
        st.metric("Total Capacity", f"{total_capacity:.0f} MW" if has_results else "Not run", help="Total installed generation capacity")
    
    with col_m4:
        st.metric("Load Coverage", f"{coverage:.1f}%" if has_results else "Not run", help="% of load served by on-site generation")
    
    if has_results:
        st.markdown("---")
        
        # Equipment Breakdown
        st.markdown("#### Equipment Mix")
        
        col_eq1, col_eq2, col_eq3, col_eq4, col_eq5 = st.columns(5)
        
        with col_eq1:
            st.metric("Recip Engines", f"{equipment.get('recip_mw', 0):.0f} MW")
        
        with col_eq2:
            st.metric("Turbines", f"{equipment.get('turbine_mw', 0):.0f} MW")
        
        with col_eq3:
            st.metric("BESS", f"{equipment.get('bess_mwh', 0):.0f} MWh")
        
        with col_eq4:
            st.metric("Solar PV", f"{equipment.get('solar_mw', 0):.0f} MW")
        
        with col_eq5:
            st.metric("Grid", f"{equipment.get('grid_mw', 0):.0f} MW")
    
    st.markdown("---")
    
    # 15-Year Energy Stack Forecast
    st.markdown("#### 15-Year Energy Stack Forecast")
    if has_results:
        from app.utils.energy_stack_chart import render_energy_stack_forecast
        render_energy_stack_forecast(equipment, selected_site)
    else:
        st.info("📊 Interactive chart showing energy source mix progression over 15 years will appear here")
        st.caption("Breakdown: Reciprocating Engines, Turbines, BESS, Solar PV, Grid")
    
    st.markdown("---")
    
    # Constraint Utilization
    if has_results and constraints:
        st.markdown("#### Constraint Utilization")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        
        with col_c1:
            st.markdown("**NOx Emissions**")
            nox_pct = constraints.get('nox_utilization', 0)
            st.progress(nox_pct, text=f"{constraints.get('nox_used_tpy', 0):.1f} tons/yr of {constraints.get('nox_limit_tpy', 0):.0f} limit ({nox_pct*100:.1f}%)")
        
        with col_c2:
            st.markdown("**Gas Supply**")
            gas_pct = constraints.get('gas_utilization', 0)
            st.progress(gas_pct, text=f"{constraints.get('gas_used_mcf', 0):.0f} MCF of {constraints.get('gas_limit_mcf', 0):.0f} available ({gas_pct*100:.1f}%)")
        
        with col_c3:
            st.markdown("**Land Use**")
            land_pct = constraints.get('land_utilization', 0)
            st.progress(land_pct, text=f"{constraints.get('land_used_acres', 0):.0f} acres of {constraints.get('land_limit_acres', 0):.0f} available ({land_pct*100:.1f}%)")
    
    st.markdown("---")
    
    # Actions
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        if st.button("⚙️ Go to Configuration", use_container_width=True):
            st.session_state.current_page = 'configuration'
            st.rerun()
    
    with col_a2:
        if st.button("📈 View Dispatch", use_container_width=True):
            st.session_state.current_page = 'dispatch_opt'
            st.rerun()
    
    with col_a3:
        if st.button("💰 Financial Details", use_container_width=True):
            st.session_state.current_page = 'financial'
            st.rerun()
