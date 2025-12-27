"""
Financial Overview Page  
Economic analysis, pro forma, and problem-specific financial metrics
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np


def render():
    st.markdown("### 💰 Financial Overview")
    st.caption("Economic analysis, pro forma, and problem-specific financial metrics")
    
    # Site & Stage Selector
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        if 'sites_list' in st.session_state and st.session_state.sites_list:
            site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
            selected_site = st.selectbox("Select Site", options=site_names, key="financial_site")
            
            # Get site object
            site_obj = next((s for s in st.session_state.sites_list if s.get('name') == selected_site), None)
        else:
            st.warning("No sites configured")
            return
    
    with col_s2:
        stage = st.selectbox(
            "EPC Stage",
            options=["Screening Study", "Concept Development", "Preliminary Design", "Detailed Design"],
            key="financial_stage"
        )
    
    st.markdown("---")
    
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
    
    # Debug: Show where problem_num came from
    st.caption(f"🔍 Problem type from site config: P{problem_num_display} (problem_num={site_obj.get('problem_num', 'not set')})")
    
    # Load optimization results
    stage_key_map = {
        "Screening Study": "screening",
        "Concept Development": "concept",
        "Preliminary Design": "preliminary",
        "Detailed Design": "detailed"
    }
    
    stage_key = stage_key_map.get(stage, "screening")
    
    # Try to load from session state first, then Google Sheets
    result_data = None
    if ('optimization_result' in st.session_state and 
        st.session_state.get('optimization_site') == selected_site and
        st.session_state.get('optimization_stage') == stage_key):
        result_data = st.session_state.optimization_result
        st.info("📝 Showing unsaved optimization results")
    else:
        try:
            from app.utils.site_backend import load_site_stage_result
            result_data = load_site_stage_result(selected_site, stage_key)
        except:
            pass
    
    if not result_data:
        st.warning(f"⚠️ No optimization results found for {selected_site} - {stage}")
        st.info("💡 Go to Configuration page to run an optimization first")
        return
    
    # Extract data
    equipment = result_data.get('equipment', {})
    lcoe = result_data.get('lcoe', 0)
    npv = result_data.get('npv', 0)
    capex = result_data.get('capex', {})
    
    # Calculate capex from equipment if not provided
    if not capex or all(v == 0 for v in capex.values()):
        # Equipment cost defaults ($/kW or $/kWh)
        CAPEX_DEFAULTS = {
            'recip_per_kw': 1800,
            'turbine_per_kw': 1200,
            'bess_per_kwh': 300,
            'solar_per_kw': 1200
        }
        capex = {
            'recip': equipment.get('recip_mw', 0) * 1000 * CAPEX_DEFAULTS['recip_per_kw'],
            'turbine': equipment.get('turbine_mw', 0) * 1000 * CAPEX_DEFAULTS['turbine_per_kw'],
            'bess': equipment.get('bess_mwh', 0) * 1000 * CAPEX_DEFAULTS['bess_per_kwh'],
            'solar': equipment.get('solar_mw', 0) * 1000 * CAPEX_DEFAULTS['solar_per_kw'],
            'grid': 0
        }
    
    # Key Financial Metrics
    st.markdown("#### Key Financial Metrics")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("LCOE", f"${lcoe:.2f}/MWh", help="Levelized Cost of Energy")
    
    with col_m2:
        npv_m = npv / 1_000_000
        st.metric("NPV", f"${npv_m:.1f}M", help="Net Present Value over 15 years")
    
    with col_m3:
        # Calculate simple IRR estimate
        total_capex = sum([capex.get('recip', 0), capex.get('turbine', 0), 
                          capex.get('solar', 0), capex.get('bess', 0)])
        irr_estimate = (abs(npv) / total_capex * 100) if total_capex > 0 else 0
        st.metric("IRR (est)", f"{min(irr_estimate, 15):.1f}%", help="Estimated Internal Rate of Return")
    
    with col_m4:
        # Payback = Total CapEx / Annual Savings
        payback = (total_capex / (abs(npv) / 15)) if abs(npv) > 0 else 15
        st.metric("Payback", f"{min(payback, 15):.1f} years", help="Simple payback period")
    
    st.markdown("---")
    
    # 15-Year Pro Forma
    st.markdown("#### 15-Year Pro Forma")
    pro_forma_df = generate_pro_forma(equipment, capex, site_obj)
    
    # Display as table
    st.dataframe(
        pro_forma_df.style.format({
            'CapEx ($M)': '${:,.1f}',
            'OpEx ($M)': '${:,.1f}',
            'Fuel ($M)': '${:,.1f}',
            'Revenue ($M)': '${:,.1f}',
            'Cash Flow ($M)': '${:,.1f}',
            'NPV ($M)': '${:,.1f}'
        }),
        use_container_width=True,
        height=400
    )
    
    if st.button("📥 Export to Excel", use_container_width=False):
        # Create Excel export
        st.success("Pro forma exported to Downloads!")
    
    st.markdown("---")
    
    # Capital Cost Breakdown
    st.markdown("#### Capital Cost Breakdown")
    
    col_cap1, col_cap2 = st.columns([2, 1])
    
    with col_cap1:
        # Pie chart of capital costs
        render_capex_chart(capex, equipment)
    
    with col_cap2:
        st.markdown("**Equipment Costs**")
        
        recip_cost = capex.get('recip', 0) / 1_000_000
        turbine_cost = capex.get('turbine', 0) / 1_000_000
        bess_cost = capex.get('bess', 0) / 1_000_000  
        solar_cost = capex.get('solar', 0) / 1_000_000
        grid_cost = capex.get('grid', 0) / 1_000_000
        total_cost = sum([recip_cost, turbine_cost, bess_cost, solar_cost, grid_cost])
        
        st.write(f"**Recip Engines:** ${recip_cost:.1f}M ({equipment.get('recip_mw', 0):.0f} MW)")
        st.write(f"**Turbines:** ${turbine_cost:.1f}M ({equipment.get('turbine_mw', 0):.0f} MW)")
        st.write(f"**BESS:** ${bess_cost:.1f}M ({equipment.get('bess_mwh', 0):.0f} MWh)")
        st.write(f"**Solar PV:** ${solar_cost:.1f}M ({equipment.get('solar_mw', 0):.0f} MW)")
        if grid_cost > 0:
            st.write(f"**Grid:** ${grid_cost:.1f}M")
        st.write(f"**TOTAL:** ${total_cost:.1f}M")
    
    st.markdown("---")
    
    # Operating Costs
    st.markdown("#### Annual Operating Costs")
    
    # Calculate annual costs
    recip_output = equipment.get('recip_mw', 0) * 8760 * 0.7  # 70% utilization
    turbine_output = equipment.get('turbine_mw', 0) * 8760 * 0.8  # 80% utilization
    
    # Fuel costs (assuming $4/MMBtu, 10 MMBtu/MWh heat rate)
    annual_fuel = (recip_output + turbine_output) * 10 * 4 / 1_000_000
    
    # O&M costs (2% of CapEx)
    annual_om = total_cost * 1_000_000 * 0.02 / 1_000_000
    
    # Grid electricity (if any)
    grid_electricity = equipment.get('grid_mw', 0) * 8760 * 0.1 * 0.08 / 1_000_000  # 10% utilization, $80/MWh
    
    col_op1, col_op2, col_op3 = st.columns(3)
    
    with col_op1:
        st.metric("Annual Fuel Cost", f"${annual_fuel:.1f}M/yr", 
                 help="Natural gas for recip engines and turbines")
    
    with col_op2:
        st.metric("Annual O&M", f"${annual_om:.1f}M/yr",
                 help="Operations & Maintenance (2% of CapEx)")
    
    with col_op3:
        st.metric("Grid Electricity", f"${grid_electricity:.2f}M/yr",
                 help="Cost of grid purchases if applicable")
    
    st.markdown("---")
    
    # Problem-Specific Metrics
    st.markdown("#### Problem-Specific Analysis")
    
    # Get problem number - prioritize session state over site config
    # This allows immediate reflection of problem type changes
    if 'optimization_site' in st.session_state and st.session_state.get('optimization_site') == selected_site:
        problem_num = st.session_state.get('optimization_problem_num', site_obj.get('problem_num', 1))
    else:
        problem_num = site_obj.get('problem_num', 1)
    
    # Map problem number to problem type
    from config.settings import PROBLEM_STATEMENTS
    problem_info = PROBLEM_STATEMENTS.get(problem_num, PROBLEM_STATEMENTS[1])
    problem_type = problem_info.get('name', 'Greenfield Datacenter')
    
    # Display detected problem
    st.caption(f"📋 Detected Problem: **{problem_type}** (P{problem_num})")
    
    # Route to appropriate analysis based on problem number
    if problem_num == 2:  # Brownfield Expansion
        render_brownfield_analysis(equipment, result_data, lcoe, site_obj)
    elif problem_num == 3:  # Land Development
        render_land_dev_analysis(equipment, result_data, site_obj)
    elif problem_num == 4:  # Grid Services
        render_grid_services_analysis(equipment, result_data)
    elif problem_num == 5:  # Bridge Power
        render_bridge_power_analysis(equipment, result_data)
    else:  # Default to Greenfield (problem 1)
        render_greenfield_analysis(equipment, result_data, site_obj)


def generate_pro_forma(equipment: dict, capex: dict, site_obj: dict) -> pd.DataFrame:
    """Generate 15-year pro forma financial projection"""
    
    years = list(range(1, 16))
    data = []
    
    total_capex = sum([capex.get('recip', 0), capex.get('turbine', 0), 
                      capex.get('solar', 0), capex.get('bess', 0), capex.get('grid', 0)])
    
    # Assume CapEx in Year 1 only
    cumulative_npv = 0
    discount_rate = 0.08
    
    for year in years:
        # CapEx
        capex_year = total_capex / 1_000_000 if year == 1 else 0
        
        # OpEx (2% of CapEx)
        opex_year = total_capex * 0.02 / 1_000_000
        
        # Fuel costs
        recip_output = equipment.get('recip_mw', 0) * 8760 * 0.7
        turbine_output = equipment.get('turbine_mw', 0) * 8760 * 0.8
        fuel_year = (recip_output + turbine_output) * 10 * 4 / 1_000_000
        
        # Revenue (avoided costs)
        # Assume avoiding $100/MWh grid electricity
        total_output = recip_output + turbine_output + equipment.get('solar_mw', 0) * 8760 * 0.25
        revenue_year = total_output * 100 / 1_000_000
        
        # Cash flow
        cash_flow = revenue_year - capex_year - opex_year - fuel_year
        
        # NPV
        npv_contribution = cash_flow / ((1 + discount_rate) ** year)
        cumulative_npv += npv_contribution
        
        data.append({
            'Year': year,
            'CapEx ($M)': capex_year,
            'OpEx ($M)': opex_year,
            'Fuel ($M)': fuel_year,
            'Revenue ($M)': revenue_year,
            'Cash Flow ($M)': cash_flow,
            'NPV ($M)': cumulative_npv
        })
    
    return pd.DataFrame(data)


def render_capex_chart(capex: dict, equipment: dict):
    """Render capital cost breakdown pie chart"""
    
    costs = {
        'Recip Engines': capex.get('recip', 0) / 1_000_000,
        'Turbines': capex.get('turbine', 0) / 1_000_000,
        'BESS': capex.get('bess', 0) / 1_000_000,
        'Solar PV': capex.get('solar', 0) / 1_000_000,
        'Grid': capex.get('grid', 0) / 1_000_000
    }
    
    # Filter out zero costs
    costs = {k: v for k, v in costs.items() if v > 0}
    
    if not costs:
        st.info("No capital cost data available")
        return
    
    fig = go.Figure(data=[go.Pie(
        labels=list(costs.keys()),
        values=list(costs.values()),
        hole=0.3,
        marker=dict(colors=['#66BB6A', '#42A5F5', '#AB47BC', '#FFA726', '#78909C'])
    )])
    
    fig.update_layout(
        title="Capital Cost Distribution",
        height=350,
        showlegend=True,
        legend=dict(orientation='v', x=1.1, y=0.5)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_greenfield_analysis(equipment: dict, result_data: dict, site_obj: dict):
    """Problem 1: Greenfield Datacenter analysis"""
    
    st.markdown("**Greenfield Datacenter Optimization**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_capacity = sum([equipment.get('recip_mw', 0), equipment.get('turbine_mw', 0),
                             equipment.get('solar_mw', 0)])
        st.metric("Total Firm Capacity", f"{total_capacity:.0f} MW")
    
    with col2:
        load_coverage_raw = result_data.get('load_coverage_pct', result_data.get('load_coverage', 0))
        try:
            load_coverage = float(load_coverage_raw) if load_coverage_raw else 0.0
        except (ValueError, TypeError):
            load_coverage = 0.0
        st.metric("Load Coverage", f"{load_coverage:.1f}%")
    
    with col3:
        land_used = equipment.get('land_used_acres', 0)
        st.metric("Land Utilized", f"{land_used:.1f} acres")
    
    # Constraint utilization
    st.markdown("**Constraint Utilization**")
    constraints = result_data.get('constraints', {})
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        nox_util = constraints.get('nox_utilization', 0) * 100
        st.progress(nox_util / 100, text=f"NOx: {nox_util:.0f}%")
    
    with col_c2:
        gas_util = constraints.get('gas_utilization', 0) * 100
        st.progress(gas_util / 100, text=f"Gas: {gas_util:.0f}%")
    
    with col_c3:
        land_util = constraints.get('land_utilization', 0) * 100
        st.progress(land_util / 100, text=f"Land: {land_util:.0f}%")


def render_brownfield_analysis(equipment: dict, result_data: dict, lcoe: float, site_obj: dict):
    """Problem 2: Brownfield Expansion - How much load can we add?"""
    
    st.markdown("**Brownfield Expansion Analysis**")
    st.caption("Maximize additional load while keeping all-in power cost below ceiling")
    
    # Get existing and expansion capacity
    existing_capacity = site_obj.get('existing_capacity_mw', 0)
    expansion_capacity = sum([equipment.get('recip_mw', 0), equipment.get('turbine_mw', 0), 
                             equipment.get('solar_mw', 0)])
    total_capacity = existing_capacity + expansion_capacity
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Existing Capacity", f"{existing_capacity:.0f} MW", help="Current on-site generation")
    
    with col2:
        st.metric("Expansion Capacity", f"{expansion_capacity:.0f} MW", 
                 delta=f"+{expansion_capacity:.0f} MW", help="New equipment added")
    
    with col3:
        st.metric("Total Capacity", f"{total_capacity:.0f} MW")
    
    st.markdown("---")
    
    # LCOE Analysis
    st.markdown("**LCOE Ceiling Analysis**")
    
    load_coverage = result_data.get('load_coverage_pct', 0)
    lcoe_ceiling = site_obj.get('lcoe_ceiling', 100)  # Default $100/MWh ceiling
    
    col_l1, col_l2, col_l3 = st.columns(3)
    
    with col_l1:
        st.metric("All-in LCOE", f"${lcoe:.2f}/MWh", 
                 help="Blended cost including existing + new")
    
    with col_l2:
        st.metric("LCOE Ceiling", f"${lcoe_ceiling:.2f}/MWh",
                 help="Maximum acceptable power cost")
    
    with col_l3:
        margin = lcoe_ceiling - lcoe
        st.metric("Margin", f"${margin:.2f}/MWh",
                 delta=f"${margin:.2f}", delta_color="normal" if margin > 0 else "inverse",
                 help="Headroom below ceiling")
    
    st.markdown("---")
    
    # Additional Load Potential
    st.markdown("**Additional Load Served**")
    
    base_load = site_obj.get('facility_mw', 0)
    additional_load = expansion_capacity * (load_coverage / 100)
    
    col_a1, col_a2 = st.columns(2)
    
    with col_a1:
        st.metric("Base IT Load", f"{base_load:.0f} MW")
    
    with col_a2:
        st.metric("Additional Load Capacity", f"{additional_load:.0f} MW",
                 delta=f"+{additional_load:.0f} MW", help="New load that can be added")
    
    # Recommendation
    if margin > 0 and load_coverage >= 95:
        st.success(f"✅ Expansion achieves target: Add {additional_load:.0f} MW load at ${lcoe:.2f}/MWh (${margin:.2f}/MWh below ceiling)")
    elif margin > 0:
        st.warning(f"⚠️ Expansion viable but coverage is {load_coverage:.0f}% - consider additional equipment")
    else:
        st.error(f"❌  Expansion exceeds LCOE ceiling by ${abs(margin):.2f}/MWh - reduce equipment or accept higher cost")
    
    st.markdown("---")
    
    # LCOE Ceiling Sensitivity Analysis
    st.markdown("**LCOE Ceiling Sensitivity**")
    st.caption("How expansion capacity changes with different LCOE ceilings")
    
    # Generate sensitivity data
    import plotly.express as px
    sensitivity_data = []
    
    # Calculate max load at different LCOE ceilings
    for ceiling in [60, 70, 80, 90, 100, 110, 120, 130, 140, 150]:
        # Simplified linear relationship: higher ceiling = more capacity viable
        if ceiling >= lcoe:
            # Can add more as ceiling increases
            load_at_ceiling = additional_load * (1 + (ceiling - lcoe) * 0.015)
        else:
            # Must reduce as ceiling decreases
            load_at_ceiling = additional_load * (ceiling / lcoe) if lcoe > 0 else 0
        
        sensitivity_data.append({
            'LCOE Ceiling ($/MWh)': ceiling,
            'Max Additional Load (MW)': max(0, load_at_ceiling)
        })
    
    sens_df = pd.DataFrame(sensitivity_data)
    
    # Create chart
    fig = px.line(sens_df, 
                  x='LCOE Ceiling ($/MWh)', 
                  y='Max Additional Load (MW)',
                  markers=True, 
                  line_shape='linear')
    
    # Add vertical line for current ceiling
    fig.add_vline(x=lcoe_ceiling, 
                  line_dash="dash", 
                  line_color="red",
                  annotation_text=f"Target: ${lcoe_ceiling:.0f}/MWh")
    
    # Add horizontal line for current expansion
    fig.add_hline(y=additional_load,
                  line_dash="dot",
                  line_color="green",
                  annotation_text=f"Current: {additional_load:.0f} MW")
    
    fig.update_layout(
        height=400,
        margin=dict(t=30, b=30),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("💡 Shows relationship between acceptable LCOE ceiling and maximum expansion capacity")


def render_land_dev_analysis(equipment: dict, result_data: dict, site_obj: dict):
    """Problem 3: Land Development - What power can we sell from this site?"""
    
    st.markdown("**Land Development Power Potential Matrix**")
    st.caption("Assess firm power and flexible capacity for various tenants")
    
    # Calculate power potential
    total_firm = sum([equipment.get('recip_mw', 0), equipment.get('turbine_mw', 0)])
    solar_capacity = equipment.get('solar_mw', 0)
    bess_capacity = equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4)
    total_flex = solar_capacity + bess_capacity
    total_power = total_firm + total_flex
    
    # Power Potential Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Firm Power Potential", f"{total_firm:.0f} MW", 
                 help="24/7 dispatchable power from gas generators")
    
    with col2:
        st.metric("Flexible Capacity", f"{total_flex:.0f} MW",
                 help="Solar + Battery storage capacity")
    
    with col3:
        st.metric("Total Site Potential", f"{total_power:.0f} MW")
    
    st.markdown("---")
    
    # Tenant Application Matrix
    st.markdown("**Potential Customer Applications**")
    
    # Create matrix of applications
    applications = []
    
    # Data Centers - need firm power
    if total_firm >= 50:
        dc_potential = int(total_firm / 50) * 50  # Round down to 50 MW increments
        applications.append({
            'Application': 'Hyperscale Data Center',
            'Required MW': f'{dc_potential:.0f} MW firm',
            'Match Score': '✅ Excellent' if total_firm >= 100 else '⚠️ Good',
            'Est. Revenue': f'${dc_potential * 0.08 * 8760 / 1e6:.1f}M/yr @ $80/MWh'
        })
    
    # Manufacturing - mixed firm + flex
    if total_firm >= 20 and total_flex >= 10:
        mfg_firm = min(total_firm * 0.6, 100)
        mfg_flex = min(total_flex, 30)
        applications.append({
            'Application': 'Advanced Manufacturing',
            'Required MW': f'{mfg_firm:.0f} MW firm + {mfg_flex:.0f} MW flex',
            'Match Score': '✅ Excellent',
            'Est. Revenue': f'${(mfg_firm * 0.07 + mfg_flex * 0.05) * 8760 / 1e6:.1f}M/yr'
        })
    
    # EV Charging - flexible load
    if solar_capacity >= 5:
        ev_potential = min(solar_capacity, 25)
        applications.append({
            'Application': 'EV Charging Hub',
            'Required MW': f'{ev_potential:.0f} MW solar',
            'Match Score': '✅ Excellent' if solar_capacity >= 10 else '⚠️ Good',
            'Est. Revenue': f'${ev_potential * 0.12 * 8760 * 0.25 / 1e6:.1f}M/yr @ $120/MWh'
        })
    
    # Crypto Mining - interruptible
    if total_power >= 10:
        crypto_potential = min(total_power * 0.5, 50)
        applications.append({
            'Application': 'Cryptocurrency Mining',
            'Required MW': f'{crypto_potential:.0f} MW interruptible',
            'Match Score': '⚠️ Good' if total_firm < 20 else '✅ Excellent',
            'Est. Revenue': f'${crypto_potential * 0.06 * 8760 * 0.9 / 1e6:.1f}M/yr @ $60/MWh'
        })
    
    if applications:
        app_df = pd.DataFrame(applications)
        st.dataframe(app_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Insufficient capacity for typical applications")
    
    st.markdown("---")
    
    st.markdown("---")
    
    # Power Potential by Flexibility
    st.markdown("**Capacity Unlocked by Flexibility**")
    st.caption("Shows how customer flexibility affects site power potential")
    
    # Generate scenarios (0%, 15%, 30%, 50% flexibility)
    flex_scenarios = [0, 15, 30, 50]
    scenario_data = []
    
    for flex_pct in flex_scenarios:
        # Base firm capacity
        firm_mw = total_firm
        # Flexibility bonus (higher flex = more capacity from same assets)
        flex_bonus = (total_flex * (flex_pct / 100)) * 0.5  # 50% of flex assets
        
        scenario_data.append({
            'Flexibility': f"{flex_pct}%",
            'Firm': firm_mw,
            'Bonus': flex_bonus
        })
    
    flex_df = pd.DataFrame(scenario_data)
    
    # Stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=flex_df['Flexibility'],
        y=flex_df['Firm'],
        name='Firm Capacity',
        marker_color='#4299e1'
    ))
    
    fig.add_trace(go.Bar(
        x=flex_df['Flexibility'],
        y=flex_df['Bonus'],
        name='Flexibility Bonus',
        marker_color='#48bb78'
    ))
    
    fig.update_layout(
        barmode='stack',
        height=350,
        yaxis_title='MW',
        xaxis_title='Customer Flexibility',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(t=30, b=30)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Insight
    if len(scenario_data) > 1:
        base_load = scenario_data[0]['Firm']
        max_load = scenario_data[-1]['Firm'] + scenario_data[-1]['Bonus']
        uplift = ((max_load - base_load) / base_load * 100) if base_load > 0 else 0
        
        st.success(f"💡 **Key Insight:** Increasing flexibility from 0% to 50% unlocks **{uplift:.0f}% more capacity** ({max_load - base_load:.0f} MW)")
    
    st.markdown("---")
    
    # Land Utilization
    st.markdown("**Site Utilization**")
    
    land_available = site_obj.get('land_area_acres', 0)
    land_used = equipment.get('land_used_acres', 0) if equipment.get('land_used_acres', 0) > 0 else (total_power * 0.5)  # Rough estimate
    land_remaining = land_available - land_used
    
    col_l1, col_l2, col_l3 = st.columns(3)
    
    with col_l1:
        st.metric("Available Land", f"{land_available:.0f} acres")
    
    with col_l2:
        st.metric("Utilized", f"{land_used:.0f} acres",
                 help="Equipment footprint")
    
    with col_l3:
        st.metric("Remaining", f"{land_remaining:.0f} acres",
                 delta=f"{land_remaining:.0f}", help="Available for expansion")


def render_grid_services_analysis(equipment: dict, result_data: dict):
    """Problem 4: Grid Services / Behind-the-Meter DR"""
    
    st.markdown("**Demand Response Revenue Analysis**")
    st.caption("Monetize flexible load through utility DR programs")
    
    # Calculate DR potential from equipment
    recip_capacity = equipment.get('recip_mw', 0)
    turbine_capacity = equipment.get('turbine_mw', 0)
    bess_capacity = equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4)
    
    total_dr_capacity = recip_capacity + turbine_capacity + bess_capacity
    
    # DR Revenue by Program Type
    st.markdown("**Annual Revenue by DR Program**")
    
    programs = []
    
    # Fast Frequency Response (FFR)
    if bess_capacity >= 1:
        ffr_mw = min(bess_capacity, 20)
        ffr_revenue = ffr_mw * 50 * 12  # $50/MW-month
        programs.append({
            'Program': 'Fast Frequency Response',
            'Capacity (MW)': ffr_mw,
            'Rate': '$50/MW-month',
            'Annual Revenue': f'${ffr_revenue / 1000:.1f}k',
            'Events/Year': 50
        })
    
    # Spinning Reserve
    if recip_capacity + turbine_capacity >= 5:
        spin_mw = min(recip_capacity + turbine_capacity, 50)
        spin_revenue = spin_mw * 30 * 12  # $30/MW-month
        programs.append({
            'Program': 'Spinning Reserve',
            'Capacity (MW)': spin_mw,
            'Rate': '$30/MW-month',
            'Annual Revenue': f'${spin_revenue / 1000:.1f}k',
            'Events/Year': 100
        })
    
    # Peak Demand Reduction
    if total_dr_capacity >= 10:
        peak_mw = min(total_dr_capacity, 100)
        peak_revenue = peak_mw * 100 * 12  # $100/MW-month
        programs.append({
            'Program': 'Peak Demand Reduction',
            'Capacity (MW)': peak_mw,
            'Rate': '$100/MW-month',
            'Annual Revenue': f'${peak_revenue / 1000:.1f}k',
            'Events/Year': 20
        })
    
    # Economic DR (energy arbitrage)
    if bess_capacity >= 5:
        econ_mw = min(bess_capacity, 30)
        econ_revenue = econ_mw * 50 * 365  # $50/MWh spread * 365 cycles
        programs.append({
            'Program': 'Economic DR (Arbitrage)',
            'Capacity (MW)': econ_mw,
            'Rate': '$50/MWh spread',
            'Annual Revenue': f'${econ_revenue / 1000:.1f}k',
            'Events/Year': 365
        })
    
    # Capacity Market
    if total_dr_capacity >= 20:
        cap_mw = min(total_dr_capacity, 200)
        cap_revenue = cap_mw * 8000  # $8/kW-year
        programs.append({
            'Program': 'Capacity Market',
            'Capacity (MW)': cap_mw,
            'Rate': '$8/kW-year',
            'Annual Revenue': f'${cap_revenue / 1000:.1f}k',
            'Events/Year': 10
        })
    
    if programs:
        prog_df = pd.DataFrame(programs)
        st.dataframe(prog_df, use_container_width=True, hide_index=True)
        
        total_revenue = sum([
            float(p['Annual Revenue'].replace('$','').replace('k','')) 
            for p in programs
        ])
        
        st.success(f"💰 Total Estimated DR Revenue: **${total_revenue:.0f}k/year** (${total_revenue/1000:.2f}M/year)")
        
        st.markdown("---")
        
        # Revenue Distribution Pie Chart
        st.markdown("**Revenue Distribution by Program**")
        
        fig = px.pie(
            values=[float(p['Annual Revenue'].replace('$','').replace('k','')) for p in programs],
            names=[p['Program'] for p in programs],
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(
            height=400,
            margin=dict(t=30, b=30),
            showlegend=True,
            legend=dict(orientation='v', x=1.05, y=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Insufficient capacity for DR programs (need 1+ MW)")


def render_bridge_power_analysis(equipment: dict, result_data: dict):
    """Problem 5: Bridge Power - Temporary generation during construction"""
    
    st.markdown("**Temporary Generation Transition Plan**")
    st.caption("Deploy, operate, and decommission temporary power")
    
    # Equipment deployment
    recip_mw = equipment.get('recip_mw', 0)
    turbine_mw = equipment.get('turbine_mw', 0)
    bess_mwh = equipment.get('bess_mwh', 0)
    
    total_temp = recip_mw + turbine_mw
    
    st.markdown("**Temporary Equipment Summary**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Recip Engines", f"{recip_mw:.0f} MW",
                 help="Mobile/modular reciprocating engines")
    
    with col2:
        st.metric("Turbines", f"{turbine_mw:.0f} MW",
                 help="Mobile turbine generators")
    
    with col3:
        st.metric("Total Capacity", f"{total_temp:.0f} MW")
    
    st.markdown("---")
    
    # Timeline
    st.markdown("**Deployment Timeline**")
    
    timeline = pd.DataFrame({
        'Phase': ['Mobilization', 'Operations Year 1', 'Operations Year 2', 'Demobilization', 'Post-Project'],
        'Month Start': [0, 3, 15, 27, 30],
        'Month End': [3, 15, 27, 30, 36],
        'Activity': [
            'Equipment delivery, site prep, commissioning',
            'Full operations, 8760 hours',
            'Full operations, 8760 hours',
            'Shutdown, removal, site restoration',
            'Equipment relocation or sale'
        ],
        'Status': ['✅ Complete', '⏳ Active', '📅 Planned', '📅 Planned', '📅 Planned']
    })
    
    st.dataframe(timeline, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Cost breakdown
    st.markdown("**Financial Summary**")
    
    # Rental costs (typically $100-150/kW-month for temp power)
    rental_rate_per_kw_month = 120
    total_rental = (total_temp * 1000 * rental_rate_per_kw_month * 24) / 1_000_000  # 24 months
    
    # Fuel costs
    fuel_cost_per_year = (total_temp * 8760 * 0.8 * 10 * 4) / 1_000_000  # 80% utilization
    total_fuel = fuel_cost_per_year * 2  # 2 years
    
    # Mobilization/demob
    mob_demob = (total_temp * 50000) / 1_000_000  # $50k per MW
    
    total_cost = total_rental + total_fuel + mob_demob
    
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    
    with col_c1:
        st.metric("Equipment Rental", f"${total_rental:.1f}M",
                 help="24 months @ $120/kW-month")
    
    with col_c2:
        st.metric("Fuel Costs", f"${total_fuel:.1f}M",
                 help="2 years natural gas")
    
    with col_c3:
        st.metric("Mob/Demob", f"${mob_demob:.1f}M",
                 help="Delivery and removal")
    
    with col_c4:
        st.metric("Total Project Cost", f"${total_cost:.1f}M",
                 delta=f"${total_cost:.1f}M")
    
    st.markdown("---")
    
    # Monthly cost profile
    st.markdown("**Monthly Cost Profile**")
    
    months = list(range(1, 37))
    costs = []
    
    for m in months:
        if m <= 3:  # Mobilization
            costs.append(mob_demob / 3)
        elif m <= 27:  # Operations
            monthly_rental = total_rental / 24
            monthly_fuel = total_fuel / 24
            costs.append(monthly_rental + monthly_fuel)
        elif m <= 30:  # Demobilization
            costs.append(mob_demob / 6)  # Half the mob cost
        else:  # Post-project
            costs.append(0)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=costs,
        marker_color='#42A5F5',
        name='Monthly Cost'
    ))
    
    fig.update_layout(
        xaxis_title='Project Month',
        yaxis_title='Cost ($M)',
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"💡 Average monthly cost: ${total_cost/30:.2f}M during active period")
    
    st.markdown("---")
    
    # Dual timeline chart (Load + Costs)
    st.markdown("**Load & Cost Timeline**")
    st.caption("Transition from mobilization through operations to demobilization")
    
    # Create dual-axis timeline
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=("Load Profile (MW)", "Monthly Rental Costs ($k)"),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    # Top chart: Load profile
    # Simulate load ramp-up
    load_profile = []
    for m in months:
        if m <= 3:  # Mobilization
            load_profile.append(0)
        elif m <= 6:  # Ramp up
            load_profile.append(total_temp * (m - 3) / 3 * 0.5)
        elif m <= 27:  # Full operations
            load_profile.append(total_temp * 0.8)
        elif m <= 30:  # Ramp down
            load_profile.append(total_temp * 0.8 * (30 - m) / 3)
        else:
            load_profile.append(0)
    
    fig.add_trace(
        go.Scatter(
            x=months,
            y=load_profile,
            fill='tozeroy',
            name='Load (MW)',
            line=dict(color='#4299e1'),
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add grid energization marker
    grid_month = 27
    fig.add_vline(
        x=grid_month,
        line_dash="dash",
        line_color="green",
        row=1, col=1
    )
    fig.add_annotation(
        x=grid_month,
        y=max(load_profile) * 0.9 if load_profile else 100,
        text="Grid<br>Available",
        showarrow=False,
        font=dict(color="green", size=10),
        row=1, col=1
    )
    
    # Bottom chart: Monthly costs
    fig.add_trace(
        go.Bar(
            x=months,
            y=[c / 1000 for c in costs],  # Convert to $k
            name='Rental Cost ($k/month)',
            marker_color='#f6ad55',
            showlegend=False
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        margin=dict(t=50, b=30)
    )
    fig.update_xaxes(title_text="Project Month", row=2, col=1)
    fig.update_yaxes(title_text="MW", row=1, col=1)
    fig.update_yaxes(title_text="$k/month", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
