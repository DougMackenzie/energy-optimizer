"""
Equipment Library & Scenario Configuration Page
Complete redesign with site constraints and scenario-based selection
"""

import streamlit as st
from app.components.grid_config import render_grid_configuration


def render():
    st.markdown("### ⚙️ Energy Stack Configuration")
    
    # Load data
    from app.utils.site_loader import (
        load_sites, 
        load_scenario_templates, 
        load_site_constraints, 
        load_optimization_objectives
    )
    from app.utils.data_io import load_equipment_from_sheets
    
    with st.spinner("Loading configuration data..."):
        sites = load_sites()
        scenarios = load_scenario_templates()
        equipment_data = load_equipment_from_sheets()
    
    # === SITE SELECTION ===
    st.markdown("#### 1️⃣ Select Site")
    
    if not sites:
        st.warning("⚠️ No sites available. Please add sites to the Sites worksheet in Google Sheets.")
        return
    
    site_names = [f"{s['Site_Name']} ({s['ISO']})" for s in sites]
    selected_site_idx = st.selectbox(
        "Choose site to configure",
        range(len(sites)),
        format_func=lambda i: site_names[i],
        key="selected_site_idx"
    )
    
    selected_site = sites[selected_site_idx]
    site_id = selected_site['Site_ID']
    
    # Load site-specific data
    constraints = load_site_constraints(site_id)
    objectives = load_optimization_objectives(site_id)
    
    # Display Site Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("IT Capacity", f"{selected_site.get('IT_Capacity_MW', 0)} MW")
    with col2:
        st.metric("Total Facility", f"{selected_site.get('Total_Facility_MW', 0)} MW")
    with col3:
        st.metric("PUE", f"{selected_site.get('Design_PUE', 0)}")
    with col4:
        st.metric("ISO/RTO", selected_site.get('ISO', 'N/A'))
    
    st.markdown("---")
    
    # === SCENARIO SELECTION ===
    st.markdown("#### 2️⃣ Select Energy Strategy")
    
    if not scenarios:
        st.warning("⚠️ No scenarios available. Please add scenarios to the Scenario_Templates worksheet.")
        return
    
    scenario_names = [f"{s['Scenario_Name']}" for s in scenarios]
    scenario_col1, scenario_col2 = st.columns([2, 1])
    
    with scenario_col1:
        selected_scenario_idx = st.selectbox(
            "Choose deployment strategy",
            range(len(scenarios)),
            format_func=lambda i: scenario_names[i],
            key="selected_scenario_idx"
        )
    
    selected_scenario = scenarios[selected_scenario_idx]
    
    with scenario_col2:
        st.info(f"**Target LCOE:** ${selected_scenario.get('Target_LCOE_MWh', 0)}/MWh\n\n**Timeline:** {selected_scenario.get('Target_Deployment_Months', 0)} months")
    
    # Show scenario description
    st.markdown(f"*{selected_scenario.get('Description', '')}*")
    
    # === EQUIPMENT TOGGLES ===
    st.markdown("---")
    st.markdown("#### 3️⃣ Equipment Stack")
    
    # Helper to convert string bool
    def to_bool(val):
        return str(val).lower() in ['true', '1', 'yes']
    
    equip_col1, equip_col2, equip_col3, equip_col4, equip_col5 = st.columns(5)
    
    with equip_col1:
        recip_enabled = st.checkbox(
            "🔋 Recip Engines",
            value=to_bool(selected_scenario.get('Recip_Enabled', 'False')),
            key="enable_recip"
        )
    
    with equip_col2:
        turbine_enabled = st.checkbox(
            "⚡ Gas Turbines",
            value=to_bool(selected_scenario.get('Turbine_Enabled', 'False')),
            key="enable_turbine"
        )
    
    with equip_col3:
        bess_enabled = st.checkbox(
            "🔋 BESS",
            value=to_bool(selected_scenario.get('BESS_Enabled', 'False')),
            key="enable_bess"
        )
    
    with equip_col4:
        solar_enabled = st.checkbox(
            "☀️ Solar PV",
            value=to_bool(selected_scenario.get('Solar_Enabled', 'False')),
            key="enable_solar"
        )
    
    with equip_col5:
        grid_enabled = st.checkbox(
            "🔌 Grid",
            value=to_bool(selected_scenario.get('Grid_Enabled', 'False')),
            key="enable_grid"
        )
    
    # === SITE CONSTRAINTS ===
    st.markdown("---")
    st.markdown("#### 4️⃣ Site Constraints")
    
    const_col1, const_col2, const_col3 = st.columns(3)
    
    with const_col1:
        st.markdown("##### 🌫️ Air Permitting")
        if constraints:
            st.metric("NOx Limit", f"{constraints.get('NOx_Limit_tpy', 0)} tpy")
            st.metric("CO Limit", f"{constraints.get('CO_Limit_tpy', 0)} tpy")
            if constraints.get('Nonattainment_Area', 'No') != 'No':
                st.warning(f"⚠️ {constraints.get('Nonattainment_Area')}")
            else:
                st.success("✅ Attainment Area")
        else:
            st.info("No constraints loaded")
    
    with const_col2:
        st.markdown("##### ⛽ Gas & Grid")
        if constraints:
            gas_mcf = constraints.get('Gas_Supply_MCF_day', 0)
            st.metric("Gas Supply", f"{gas_mcf:,.0f} MCF/day")
            st.metric("Grid Available", f"{constraints.get('Grid_Available_MW', 0)} MW")
            
            queue_pos = constraints.get('Queue_Position', 'N/A')
            timeline_mo = constraints.get('Estimated_Interconnection_Months', 0)
            st.caption(f"📋 Queue Position: {queue_pos}")
            st.caption(f"⏱️ Interconnection: ~{timeline_mo} months ({timeline_mo/12:.1f} yrs)")
            
            if timeline_mo > 48:
                st.warning(f"⚠️ Long interconnection timeline")
        else:
            st.info("No constraints loaded")
    
    with const_col3:
        st.markdown("##### 🏞️ Land & Reliability")
        if constraints:
            avail_land = constraints.get('Available_Land_Acres', 0)
            st.metric("Available Land", f"{avail_land:,.0f} acres")
            
            solar_feasible = constraints.get('Solar_Feasible', 'Unknown')
            if solar_feasible == 'Yes':
                st.success(f"☀️ Solar: {solar_feasible}")
            elif solar_feasible == 'Limited':
                st.warning(f"⚠️ Solar: {solar_feasible}")
            else:
                st.caption(f"☀️ Solar: {solar_feasible}")
            
            n1_req = constraints.get('N_Minus_1_Required', 'No')
            st.metric("N-1 Required", "Yes ✓" if n1_req == 'Yes' else "No")
            st.caption(f"Max Transient: {constraints.get('Max_Transient_pct', 0)}%")
        else:
            st.info("No constraints loaded")
    
    # === GRID INTERCONNECTION CONFIGURATION ===
    st.markdown("---")
    if constraints:
        grid_config = render_grid_configuration(constraints, grid_enabled)
        st.session_state.grid_config = grid_config
    else:
        # Default grid config
        st.session_state.grid_config = {
            'voltage_level': '345kV',
            'transformer_lead_months': 24,
            'breaker_lead_months': 18,
            'total_timeline_months': 96,
            'grid_capacity_override': None,
            'timeline_override': None,
            'grid_available_mw': 200
        }
    
    # === EQUIPMENT SPECIFICATIONS ===
    st.markdown("---")
    with st.expander("📚 View Equipment Specifications", expanded=False):
        equip_tabs = st.tabs(["Recip Engines", "Gas Turbines", "BESS", "Solar PV"])
        
        # Recip Engines
        with equip_tabs[0]:
            if recip_enabled:
                recip_engines = equipment_data.get("Reciprocating_Engines", [])
                if recip_engines:
                    st.markdown("**Available Reciprocating Engines:**")
                    for idx, equip in enumerate(recip_engines[:5]):
                        if equip:
                            model = equip.get('Model', 'Unknown')
                            cap = equip.get('Capacity_MW', 0)
                            eff = equip.get('Efficiency_Pct', 0)
                            lead = equip.get('Lead_Time_Months_Min', 0)
                            st.markdown(f"• **{model}** - {cap} MW | {eff}% eff | {lead}+ mo lead")
                else:
                    st.info("No reciprocating engines in library")
            else:
                st.info("❌ Reciprocating engines not enabled in this scenario")
        
        # Gas Turbines
        with equip_tabs[1]:
            if turbine_enabled:
                turbines = equipment_data.get("Gas_Turbines", [])
                if turbines:
                    st.markdown("**Available Gas Turbines:**")
                    for idx, equip in enumerate(turbines[:5]):
                        if equip:
                            model = equip.get('Model', 'Unknown')
                            cap = equip.get('Capacity_MW', 0)
                            eff = equip.get('Efficiency_Pct', 0)
                            lead = equip.get('Lead_Time_Months_Min', 0)
                            st.markdown(f"• **{model}** - {cap} MW | {eff}% eff | {lead}+ mo lead")
                else:
                    st.info("No gas turbines in library")
            else:
                st.info("❌ Gas turbines not enabled in this scenario")
        
        # BESS
        with equip_tabs[2]:
            if bess_enabled:
                bess_systems = equipment_data.get("BESS", [])
                if bess_systems:
                    st.markdown("**Available BESS Systems:**")
                    for idx, equip in enumerate(bess_systems[:5]):
                        if equip:
                            model = equip.get('Model', 'Unknown')
                            energy = equip.get('Energy_MWh', 0)
                            power = equip.get('Power_MW', 0)
                            lead = equip.get('Lead_Time_Months', 0)
                            st.markdown(f"• **{model}** - {energy} MWh / {power} MW | {lead} mo lead")
                else:
                    st.info("No BESS systems in library")
            else:
                st.info("❌ BESS not enabled in this scenario")
        
        # Solar PV
        with equip_tabs[3]:
            if solar_enabled:
                solar_systems = equipment_data.get("Solar_PV", [])
                if solar_systems:
                    st.markdown("**Available Solar PV Configurations:**")
                    for idx, equip in enumerate(solar_systems):
                        if equip:
                            sys_type = equip.get('System_Type', 'Unknown')
                            region = equip.get('Region', '')
                            cf = equip.get('Capacity_Factor_Pct', 0)
                            land = equip.get('Land_Use_acres_per_MW', 0)
                            st.markdown(f"• **{sys_type} - {region}** - {cf}% CF | {land} acres/MW")
                else:
                    st.info("No solar systems in library")
            else:
                st.info("❌ Solar PV not enabled in this scenario")
    
    # === OPTIMIZATION ===
    st.markdown("---")
    st.markdown("#### 5️⃣ Optimize Configuration")
    
    opt_col1, opt_col2, opt_col3 = st.columns([2, 1, 1])
    
    with opt_col1:
        if objectives:
            primary_obj = objectives.get('Primary_Objective', 'Not set')
            max_lcoe = objectives.get('LCOE_Max_MWh', 0)
            max_timeline = objectives.get('Deployment_Max_Months', 0)
            st.info(f"**Primary Objective:** {primary_obj}\n\n**Max LCOE:** ${max_lcoe}/MWh | **Max Timeline:** {max_timeline} months")
        else:
            st.warning("⚠️ No optimization objectives defined for this site")
    
    with opt_col2:
        if st.button("🎯 Run Optimizer", type="primary", use_container_width=True):
            st.success("✅ Configuration ready. Navigate to Optimizer page to run analysis.")
            # Store in session state for optimizer
            st.session_state.current_config = {
                'site': selected_site,
                'scenario': selected_scenario,
                'equipment_enabled': {
                    'recip': recip_enabled,
                    'turbine': turbine_enabled,
                    'bess': bess_enabled,
                    'solar': solar_enabled,
                    'grid': grid_enabled
                },
                'constraints': constraints,
                'objectives': objectives
            }
    
    with opt_col3:
        if st.button("💾 Save Config", use_container_width=True):
            # Store in session state
            st.session_state.current_config = {
                'site': selected_site,
                'scenario': selected_scenario,
                'equipment_enabled': {
                    'recip': recip_enabled,
                    'turbine': turbine_enabled,
                    'bess': bess_enabled,
                    'solar': solar_enabled,
                    'grid': grid_enabled
                },
                'constraints': constraints,
                'objectives': objectives
            }
            st.success("✅ Configuration saved to session state")
    
    # === RESEARCH & SOURCES ===
    st.markdown("---")
    with st.expander("📚 Research & Data Sources", expanded=False):
        st.markdown("### 📊 Data Validation & Sources")
        st.info("Equipment specifications validated against industry standards and OEM data as of **December 2025**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🟢 High Confidence Sources")
            st.markdown("""
            **OEM Specifications:**
            - Wärtsilä, INNIO Jenbacher, Caterpillar (recip engines)
            - GE Vernova, Siemens Energy, Mitsubishi (turbines)
            - Tesla, CATL, BYD, Fluence (BESS)
            
            **Government & Standards:**
            - NREL ATB 2024, EIA AEO 2025
            - EPA AP-42, IEEE 493, NERC GADS
            - LBNL Queued Up 2025
            """)
        
        with col2:
            st.markdown("##### 🟡 Medium Confidence Sources")
            st.markdown("""
            **Industry Reports:**
            - BloombergNEF (BESS pricing, market data)
            - Lazard LCOE v10.0 / LCOS v10.0
            - Gas Turbine World
            - Wood Mackenzie
            
            **Market Data:**
            - Current pricing reflects 2024-2025 market
            - Lead times subject to supply chain volatility
            """)
        
        st.markdown("---")
        st.markdown("##### ⚠️ Critical Market Constraints (2025)")
        
        st.warning("""
        **Transformer Lead Times - CRITICAL PATH:**
        - 20 MVA: 80-100 weeks | 50 MVA: 100-150 weeks | 200 MVA: 150-210 weeks
        - Prices increased 80%+ since 2020
        """)
        
        st.warning("""
        **Grid Interconnection Backlogs:**
        - ERCOT: 2-3 years (fastest) | SPP: 3-5 years | MISO: 4-5 years | PJM: 8+ years
        """)


if __name__ == "__main__":
    render()
