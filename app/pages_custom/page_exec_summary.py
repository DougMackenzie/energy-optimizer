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
        
        # Extract optimizer data for chart
        equipment_by_year = result_data.get('equipment_by_year')
        load_trajectory = result_data.get('load_trajectory')
        
        # Get grid constraints
        result_constraints = result_data.get('constraints', {})
        grid_available_year = result_constraints.get('grid_available_year')
        grid_capacity_mw = result_constraints.get('grid_capacity_mw', 0)
        
        # Render chart with full data
        render_energy_stack_forecast(
            equipment=equipment,
            selected_site=selected_site,
            equipment_by_year=equipment_by_year,
            load_trajectory=load_trajectory,
            grid_available_year=grid_available_year,
            grid_capacity_mw=grid_capacity_mw,
        )
    
    # === NEW: Constraint Analysis & Shadow Pricing ===
    if has_results:
        st.markdown("---")
        st.markdown("#### 🔍 Constraint Analysis & Optimization Drivers")
        st.caption("Understanding what's limiting capacity and driving the high unserved load")
        
        # Get constraint data
        peak_load = site_obj.get('facility_mw', 780)  # Target load
        total_installed = total_capacity  # From above
        unserved_pct = max(0, 100 - coverage) if coverage else 100
        
        # Check which constraints are limiting
        binding_constraints = []
        shadow_prices = {}
        
        # LCOE constraint (if optimizer stopped due to cost)
        lcoe_threshold = result_data.get('lcoe_threshold', 100)  # Get from optimization config
        if lcoe > lcoe_threshold * 0.9:  # Within 10% of threshold
            binding_constraints.append({
                'name': 'LCOE Ceiling',
                'current': lcoe,
'limit': lcoe_threshold,
                'utilization': lcoe / lcoe_threshold,
                'description': f'LCOE approaching ${lcoe_threshold:.1f}/MWh threshold',
                'impact': 'HIGH'
            })
            # Shadow price: if we relaxed LCOE by $1/MWh, how much more capacity?
            shadow_prices['lcoe'] = {
                'value': peak_load * 0.05,  # Estimate: 5% more capacity per $/MWh
                'unit': 'MW per $/MWh',
                'explanation': f'Relaxing LCOE constraint by $1/MWh could enable ~{peak_load * 0.05:.0f} MW additional capacity'
            }
        
        # NOx constraint
        nox_limit = constraints.get('nox_limit_tpy', site_obj.get('nox_limit_tpy', 0))
        nox_used = constraints.get('nox_used_tpy', 0)
        if nox_limit > 0:
            nox_util = nox_used / nox_limit
            if nox_util > 0.85:  # Over 85% utilization
                binding_constraints.append({
                    'name': 'NOx Emissions',
                    'current': nox_used,
                    'limit': nox_limit,
                    'utilization': nox_util,
                    'description': f'{nox_used:.1f} tons/yr of {nox_limit:.0f} limit',
                    'impact': 'CRITICAL' if nox_util > 0.95 else 'HIGH'
                })
                # Shadow price: value of 1 additional ton of NOx allowance
                mw_per_ton = 18.3 / 100  # Rough: 18.3 MW recip produces ~100 tons/yr
                shadow_prices['nox'] = {
                    'value': mw_per_ton,
                    'unit': 'MW per ton/yr',
                    'explanation': f'Each additional ton of NOx allowance enables ~{mw_per_ton:.2f} MW capacity'
                }
        
        # Gas constraint
        gas_limit = constraints.get('gas_limit_mcf', site_obj.get('gas_supply_mcf', 0))
        gas_used = constraints.get('gas_used_mcf', 0)
        if gas_limit > 0:
            gas_util = gas_used / gas_limit
            if gas_util > 0.85:
                binding_constraints.append({
                    'name': 'Gas Supply',
                    'current': gas_used,
                    'limit': gas_limit,
                    'utilization': gas_util,
                    'description': f'{gas_used:,.0f} MCF of {gas_limit:,.0f} available',
                    'impact': 'CRITICAL' if gas_util > 0.95 else 'HIGH'
                })
                # Shadow price
                mcf_per_mw = 7000  # Rough: 1 MW recip @ 80% CF uses ~7,000 MCF/yr
                shadow_prices['gas'] = {
                    'value': 1.0 / mcf_per_mw,
                    'unit': 'MW per MCF',
                    'explanation': f'Each additional {mcf_per_mw:,.0f} MCF enables ~1 MW capacity'
                }
        
        # Land constraint
        land_limit = constraints.get('land_limit_acres', site_obj.get('land_acres', 0))
        land_used = constraints.get('land_used_acres', 0)
        if land_limit > 0:
            land_util = land_used / land_limit
            if land_util > 0.85:
                binding_constraints.append({
                    'name': 'Land Availability',
                    'current': land_used,
                    'limit': land_limit,
                    'utilization': land_util,
                    'description': f'{land_used:.1f} of {land_limit:.0f} acres',
                    'impact': 'MEDIUM'
                })
                # Shadow price
                acres_per_mw = 0.25  # Rough: 0.25 acres per MW
                shadow_prices['land'] = {
                    'value': 1.0 / acres_per_mw,
                    'unit': 'MW per acre',
                    'explanation': f'Each additional acre enables ~{1.0/acres_per_mw:.0f} MW capacity'
                }
        
        # Display analysis
        if binding_constraints or unserved_pct > 50:
            # Summary box
            if unserved_pct > 75:
                alert_level = "🔴 CRITICAL"
                alert_color = "#c53030"
            elif unserved_pct > 50:
                alert_level = "🟡 HIGH"
                alert_color = "#d69e2e"
            else:
                alert_level = "🟢 MODERATE"
                alert_color = "#38a169"
            
            st.markdown(f'''
            <div style="background: linear-gradient(135deg, {alert_color}22 0%, {alert_color}11 100%);
                        padding: 16px;
                        border-radius: 8px;
                        border-left: 4px solid {alert_color};
                        margin-bottom: 20px;">
                <div style="color: {alert_color}; font-weight: 700; font-size: 16px; margin-bottom: 8px;">
                    {alert_level}: {unserved_pct:.0f}% Unserved Load ({peak_load - total_installed:.0f} MW gap)
                </div>
                <div style="color: #4a5568; font-size: 14px;">
                    Optimization installed only {total_installed:.0f} MW of the {peak_load:.0f} MW target load.
                    {'<strong>Binding constraints are limiting capacity expansion.</strong>' if binding_constraints else 'Economic optimization favors minimal capacity.'}
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            if binding_constraints:
                st.markdown("**🔗 Binding Constraints** (Currently Limiting Capacity)")
                
                for bc in binding_constraints:
                    # Color based on impact
                    impact_colors = {
                        'CRITICAL': '#c53030',
                        'HIGH': '#d69e2e',
                        'MEDIUM': '#ecc94b'
                    }
                    color = impact_colors.get(bc['impact'], '#718096')
                    
                    col_constraint, col_value = st.columns([3, 1])
                    with col_constraint:
                        st.markdown(f"**{bc['name']}**: {bc['description']}")
                        if bc['name'] in shadow_prices:
                            sp = shadow_prices[bc['name'].lower().replace(' ', '_')]
                            st.caption(f"💰 Shadow Price: {sp['value']:.2f} {sp['unit']} — {sp['explanation']}")
                    with col_value:
                        st.progress(min(bc['utilization'], 1.0), 
                                   text=f"{bc['utilization']*100:.0f}% {bc['impact']}")
            
            
            # What-If Analysis
            with st.expander("📊 What-If Analysis: Relaxing Constraints"):
                st.markdown("**If we could relax key constraints, here's the potential impact:**")
                
                scenarios = []
                
                if 'lcoe' in shadow_prices:
                    new_cap = total_installed + shadow_prices['lcoe']['value'] * 10  # Relax by $10/MWh
                    scenarios.append({
                        'scenario': 'Increase LCOE ceiling by $10/MWh',
                        'additional_mw': shadow_prices['lcoe']['value'] * 10,
                        'new_coverage': min(100, (new_cap / peak_load) * 100),
                        'cost': '+$10/MWh LCOE'
                    })
                
                if 'nox' in shadow_prices:
                    nox_relax = 100  # Add 100 tons/yr
                    add_mw = shadow_prices['nox']['value'] * nox_relax
                    scenarios.append({
                        'scenario': f'Increase NOx allowance by {nox_relax} tons/yr',
                        'additional_mw': add_mw,
                        'new_coverage': min(100, ((total_installed + add_mw) / peak_load) * 100),
                        'cost': f'+{nox_relax} tons/yr emissions'
                    })
                
                if 'gas' in shadow_prices:
                    gas_relax = 50000  # Add 50,000 MCF
                    add_mw = shadow_prices['gas']['value'] * gas_relax
                    scenarios.append({
                        'scenario': f'Increase gas supply by {gas_relax:,} MCF/yr',
                        'additional_mw': add_mw,
                        'new_coverage': min(100, ((total_installed + add_mw) / peak_load) * 100),
                        'cost': f'+{gas_relax:,} MCF/yr fuel'
                    })
                
                if 'land' in shadow_prices:
                    land_relax = 10  # Add 10 acres
                    add_mw = shadow_prices['land']['value'] * land_relax
                    scenarios.append({
                        'scenario': f'Acquire {land_relax} additional acres',
                        'additional_mw': add_mw,
                        'new_coverage': min(100, ((total_installed + add_mw) / peak_load) * 100),
                        'cost': f'+{land_relax} acres land'
                    })
                
                if scenarios:
                    import pandas as pd
                    df = pd.DataFrame(scenarios)
                    df['Capacity Increase'] = df['additional_mw'].apply(lambda x: f"+{x:.0f} MW")
                    df['New Coverage'] = df['new_coverage'].apply(lambda x: f"{x:.0f}%")
                    df = df[['scenario', 'Capacity Increase', 'New Coverage', 'cost']]
                    df.columns = ['Scenario', 'Capacity Increase', 'New Load Coverage', 'Trade-off']
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No binding constraints identified - unserved load is due to economic optimization favoring minimal capital deployment.")
        else:
            st.success("✅ No critical binding constraints detected. Optimization is economics-driven.")
    
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
