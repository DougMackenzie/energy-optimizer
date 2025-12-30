"""
Problem 1: Greenfield Datacenter
Objective: Minimize LCOE for known load trajectory

This page provides:
- Phase 1: Heuristic optimization (30-60 seconds) - AVAILABLE NOW
- Phase 2: MILP optimization with HiGHS - PLACEHOLDER
- Results: 8760 dispatch, pro forma, 15-year forecast
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS, CONSTRAINT_DEFAULTS, ECONOMIC_DEFAULTS


def render():
    """Render Problem 1: Greenfield Datacenter page"""
    
    prob = PROBLEM_STATEMENTS[1]
    
    # Header
    st.markdown(f"### {prob['icon']} Problem 1: {prob['name']}")
    st.markdown(f"*{prob['objective']} — {prob['question']}*")
    st.markdown("---")
    
    # Tier indicator
    st.markdown("""
    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <div style="background: #e6fffa; color: #234e52; padding: 8px 16px; border-radius: 8px; font-size: 13px;">
            <strong>Phase 1:</strong> Heuristic Screening ✓ Available
        </div>
        <div style="background: #f7fafc; color: #718096; padding: 8px 16px; border-radius: 8px; font-size: 13px;">
            <strong>Phase 2:</strong> MILP Optimization 🔜 Coming Soon
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Main layout - inputs on left, results on right
    col_input, col_results = st.columns([1, 2])
    
    with col_input:
        st.markdown("#### 📋 Configuration")
        
        # Load Trajectory
        with st.expander("📈 Load Trajectory", expanded=True):
            st.markdown("**Annual Load (MW IT)**")
            
            col1, col2 = st.columns(2)
            with col1:
                first_year = st.number_input("First Load Year", 2025, 2035, 2028)
                first_load = st.number_input("First Load (MW)", 10, 1000, 150)
            with col2:
                target_load = st.number_input("Target Load (MW)", 50, 2000, 600)
                ramp_years = st.number_input("Years to Ramp", 1, 10, 4)
            
            pue = st.slider("PUE", 1.1, 1.5, 1.25, 0.05)
            
            # Generate load trajectory
            load_trajectory = {}
            for i in range(ramp_years + 1):
                year = first_year + i
                if i == 0:
                    load_trajectory[year] = first_load
                else:
                    load_trajectory[year] = min(first_load + (target_load - first_load) * i / ramp_years, target_load)
            
            # Extend to 2035
            for year in range(first_year + ramp_years + 1, 2036):
                load_trajectory[year] = target_load
            
            # Apply PUE for facility load
            facility_trajectory = {y: l * pue for y, l in load_trajectory.items()}
            
            # Show trajectory table
            traj_df = pd.DataFrame({
                'Year': list(load_trajectory.keys()),
                'IT Load (MW)': list(load_trajectory.values()),
                'Facility Load (MW)': [round(l * pue, 1) for l in load_trajectory.values()]
            })
            st.dataframe(traj_df, use_container_width=True, hide_index=True, height=150)
        
        # Constraints
        with st.expander("⚠️ Constraints", expanded=True):
            nox_limit = st.number_input("NOx Limit (tpy)", 10, 500, CONSTRAINT_DEFAULTS['nox_tpy_annual'])
            gas_limit = st.number_input("Gas Supply (MCF/day)", 1000, 200000, CONSTRAINT_DEFAULTS['gas_supply_mcf_day'])
            land_limit = st.number_input("Land Available (acres)", 10, 2000, CONSTRAINT_DEFAULTS['land_area_acres'])
            n1_required = st.checkbox("N-1 Redundancy Required", value=True)
        
        # Equipment options
        with st.expander("⚙️ Equipment Options", expanded=False):
            use_recips = st.checkbox("Reciprocating Engines", value=True)
            use_turbines = st.checkbox("Gas Turbines", value=True)
            use_solar = st.checkbox("Solar PV", value=True)
            use_bess = st.checkbox("Battery Storage", value=True)
        
        # Economic parameters
        with st.expander("💰 Economic Parameters", expanded=False):
            discount_rate = st.slider("Discount Rate", 0.05, 0.12, ECONOMIC_DEFAULTS['discount_rate'], 0.01)
            fuel_price = st.slider("Natural Gas ($/MMBtu)", 2.0, 6.0, ECONOMIC_DEFAULTS['fuel_price_mmbtu'], 0.25)
            project_life = st.number_input("Project Life (years)", 10, 30, ECONOMIC_DEFAULTS['project_life_years'])
        
        st.markdown("---")
        
        # Run buttons
        st.markdown("#### 🚀 Run Optimization")
        
        run_phase1 = st.button("▶️ Run Phase 1 (Heuristic)", type="primary", use_container_width=True)
        
        st.markdown("""
        <div style="font-size: 11px; color: #718096; margin-top: 4px;">
            ~30-60 seconds • Indicative results (±50%)
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("")
        
        run_phase2 = st.button("🔒 Run Phase 2 (MILP)", disabled=True, use_container_width=True)
        st.markdown("""
        <div style="font-size: 11px; color: #a0aec0; margin-top: 4px;">
            Coming soon: HiGHS optimization for Class 3 accuracy
        </div>
        """, unsafe_allow_html=True)
    
    with col_results:
        st.markdown("#### 📊 Results")
        
        # Check if we have results
        result = st.session_state.get('optimization_results', {}).get(1)
        
        if run_phase1:
            # Run the optimization
            with st.spinner("Running Phase 1 Heuristic Optimization..."):
                try:
                    # Use v2.1.1 Greenfield optimizer with backend integration
                    from app.optimization import GreenfieldHeuristicV2
                    
                    constraints = {
                        'nox_tpy_annual': nox_limit,
                        'gas_supply_mcf_day': gas_limit,
                        'land_area_acres': land_limit,
                        'n_minus_1_required': n1_required,
                    }
                    
                    economic_params = {
                        'discount_rate': discount_rate,
                        'fuel_price_mmbtu': fuel_price,
                        'project_life_years': project_life,
                    }
                    
                    # Use facility (not IT) load for sizing with v2.1.1
                    optimizer = GreenfieldHeuristicV2(
                        site={'name': 'Configured Site'},
                        load_trajectory=facility_trajectory,
                        constraints=constraints,
                        economic_params=economic_params,
                    )
                    
                    result = optimizer.optimize()
                    
                    # Store in session state
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    st.session_state.optimization_results[1] = {
                        'result': result,
                        'lcoe': result.lcoe,
                        'capex': result.capex_total,
                        'opex': result.opex_annual,
                        'equipment': result.equipment_config,
                        'dispatch_summary': result.dispatch_summary,
                        'feasible': result.feasible,
                        'timeline': result.timeline_months,
                        'constraints': result.constraint_status,
                        'violations': result.violations,
                        'solve_time': result.solve_time_seconds,
                    }
                    st.session_state.phase_1_complete[1] = True
                    
                    st.success(f"✅ Phase 1 complete in {result.solve_time_seconds:.1f} seconds")
                    
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display results if available
        result_data = st.session_state.get('optimization_results', {}).get(1)
        
        if result_data:
            # Status indicator
            if result_data['feasible']:
                st.markdown("""
                <div style="background: #c6f6d5; color: #22543d; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong>✓ FEASIBLE SOLUTION</strong> — All constraints satisfied
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: #fed7d7; color: #742a2a; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong>⚠️ CONSTRAINT VIOLATIONS</strong><br/>
                    {', '.join(result_data['violations'][:3])}
                </div>
                """, unsafe_allow_html=True)
            
            # Key metrics
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            with metrics_col1:
                st.metric("LCOE", f"${result_data['lcoe']:.1f}/MWh")
            with metrics_col2:
                st.metric("CAPEX", f"${result_data['capex']/1e6:.0f}M")
            with metrics_col3:
                st.metric("Timeline", f"{result_data['timeline']} months")
            with metrics_col4:
                st.metric("Solve Time", f"{result_data['solve_time']:.1f}s")
            
            st.markdown("---")
            
            # Tabs for different result views
            tab_summary, tab_equipment, tab_dispatch, tab_proforma, tab_constraints = st.tabs([
                "📊 Summary", "⚙️ Equipment", "📈 8760 Dispatch", "💰 Pro Forma", "⚠️ Constraints"
            ])
            
            with tab_summary:
                render_summary_tab(result_data)
            
            with tab_equipment:
                render_equipment_tab(result_data)
            
            with tab_dispatch:
                render_dispatch_tab(result_data, facility_trajectory)
            
            with tab_proforma:
                render_proforma_tab(result_data, project_life, discount_rate)
            
            with tab_constraints:
                render_constraints_tab(result_data)
        
        else:
            # No results yet
            st.info("👈 Configure parameters and click **Run Phase 1** to start optimization")
            
            # Show example results placeholder
            st.markdown("#### Expected Outputs")
            st.markdown("""
            - **Equipment Sizing**: Optimal mix of recips, turbines, solar, BESS
            - **8760 Dispatch**: Hourly generation schedule for full year
            - **Pro Forma**: 15-year cash flow projection
            - **Constraint Analysis**: Shadow prices on binding constraints
            - **Timeline**: Deployment Gantt chart
            """)


def render_summary_tab(result_data):
    """Render summary results tab"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Key Results")
        
        summary_df = pd.DataFrame({
            'Metric': ['LCOE', 'Total CAPEX', 'Annual OPEX', 'Deployment Timeline', 'Total Capacity'],
            'Value': [
                f"${result_data['lcoe']:.2f}/MWh",
                f"${result_data['capex']/1e6:.1f}M",
                f"${result_data['opex']/1e6:.1f}M/year",
                f"{result_data['timeline']} months",
                f"{result_data['equipment'].get('total_firm_mw', 0):.1f} MW",
            ]
        })
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Dispatch Summary")
        
        dispatch = result_data.get('dispatch_summary', {})
        dispatch_df = pd.DataFrame({
            'Metric': ['Total Generation', 'Total Load', 'Unserved Energy', 'Solar Penetration', 'Recip CF'],
            'Value': [
                f"{dispatch.get('total_generation_gwh', 0):.1f} GWh",
                f"{dispatch.get('total_load_gwh', 0):.1f} GWh",
                f"{dispatch.get('unserved_mwh', 0):.1f} MWh",
                f"{dispatch.get('solar_penetration_pct', 0):.1f}%",
                f"{dispatch.get('recip_cf', 0):.1%}",
            ]
        })
        st.dataframe(dispatch_df, use_container_width=True, hide_index=True)


def render_equipment_tab(result_data):
    """Render equipment configuration tab"""
    
    equipment = result_data.get('equipment', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Thermal Generation")
        
        # Recips
        if equipment.get('recip_mw', 0) > 0:
            st.markdown(f"""
            **Reciprocating Engines**
            - Count: {equipment.get('n_recips', 0)} units
            - Total Capacity: {equipment.get('recip_mw', 0):.1f} MW
            - Unit Size: 18.3 MW each
            """)
        
        # Turbines
        if equipment.get('turbine_mw', 0) > 0:
            st.markdown(f"""
            **Gas Turbines**
            - Count: {equipment.get('n_turbines', 0)} units
            - Total Capacity: {equipment.get('turbine_mw', 0):.1f} MW
            - Unit Size: 50.0 MW each
            """)
    
    with col2:
        st.markdown("##### Renewables & Storage")
        
        if equipment.get('solar_mw', 0) > 0:
            st.markdown(f"""
            **Solar PV**
            - Capacity: {equipment.get('solar_mw', 0):.1f} MW DC
            - Land: {equipment.get('solar_mw', 0) * 5:.1f} acres
            """)
        
        if equipment.get('bess_mwh', 0) > 0:
            st.markdown(f"""
            **Battery Storage**
            - Energy: {equipment.get('bess_mwh', 0):.1f} MWh
            - Power: {equipment.get('bess_mw', 0):.1f} MW
            - Duration: {equipment.get('bess_mwh', 0) / equipment.get('bess_mw', 1):.1f} hours
            """)
    
    # Capacity pie chart
    st.markdown("##### Capacity Mix")
    
    cap_data = []
    if equipment.get('recip_mw', 0) > 0:
        cap_data.append({'Source': 'Recip Engines', 'MW': equipment['recip_mw']})
    if equipment.get('turbine_mw', 0) > 0:
        cap_data.append({'Source': 'Gas Turbines', 'MW': equipment['turbine_mw']})
    if equipment.get('solar_mw', 0) > 0:
        cap_data.append({'Source': 'Solar PV', 'MW': equipment['solar_mw']})
    if equipment.get('bess_mw', 0) > 0:
        cap_data.append({'Source': 'BESS', 'MW': equipment['bess_mw']})
    
    if cap_data:
        fig = px.pie(cap_data, values='MW', names='Source', 
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)


def render_dispatch_tab(result_data, load_trajectory):
    """Render 8760 dispatch visualization"""
    
    st.markdown("##### Hourly Dispatch (Representative Week)")
    
    # Generate dispatch data
    try:
        # Use v2.1.1 for dispatch generation
        from app.optimization import GreenfieldHeuristicV2
        
        optimizer = GreenfieldHeuristicV2(
            site={},
            load_trajectory=load_trajectory,
            constraints={},
        )
        
        dispatch_df = optimizer.generate_8760_dispatch(result_data['equipment'])
        
        # Show first week
        week_df = dispatch_df.head(168).copy()
        
        # Stacked area chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=week_df['hour'], y=week_df['recip_mw'],
            fill='tozeroy', name='Recip Engines',
            line=dict(width=0.5, color='#48bb78')
        ))
        
        fig.add_trace(go.Scatter(
            x=week_df['hour'], y=week_df['recip_mw'] + week_df['turbine_mw'],
            fill='tonexty', name='Gas Turbines',
            line=dict(width=0.5, color='#4299e1')
        ))
        
        fig.add_trace(go.Scatter(
            x=week_df['hour'], y=week_df['recip_mw'] + week_df['turbine_mw'] + week_df['solar_mw'],
            fill='tonexty', name='Solar PV',
            line=dict(width=0.5, color='#f6ad55')
        ))
        
        fig.add_trace(go.Scatter(
            x=week_df['hour'], y=week_df['load_mw'],
            name='Load', line=dict(width=2, color='#e53e3e', dash='dash')
        ))
        
        fig.update_layout(
            height=350,
            margin=dict(t=30, b=30, l=50, r=20),
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            xaxis_title='Hour of Week',
            yaxis_title='Power (MW)',
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Download button for full 8760
        st.markdown("##### Download Full 8760 Data")
        
        csv = dispatch_df.to_csv(index=False)
        st.download_button(
            "📥 Download 8760 CSV",
            csv,
            "bvnexus_8760_dispatch.csv",
            "text/csv",
        )
        
    except Exception as e:
        st.warning(f"Could not generate dispatch visualization: {e}")


def render_proforma_tab(result_data, project_life, discount_rate):
    """Render 15-year pro forma cash flow"""
    
    st.markdown("##### 15-Year Pro Forma Cash Flow")
    
    capex = result_data['capex']
    opex = result_data['opex']
    
    # Generate yearly cash flows
    years = list(range(0, min(project_life, 15) + 1))
    
    cash_flows = []
    cumulative = 0
    
    for year in years:
        if year == 0:
            cf = -capex
        else:
            # OPEX with 2.5% escalation
            escalated_opex = opex * (1.025 ** (year - 1))
            cf = -escalated_opex
        
        cumulative += cf
        npv_factor = 1 / (1 + discount_rate) ** year
        
        cash_flows.append({
            'Year': year,
            'CAPEX': -capex if year == 0 else 0,
            'OPEX': -opex * (1.025 ** (year - 1)) if year > 0 else 0,
            'Cash Flow': cf,
            'Cumulative': cumulative,
            'NPV Factor': npv_factor,
            'Discounted CF': cf * npv_factor,
        })
    
    cf_df = pd.DataFrame(cash_flows)
    
    # Format for display
    display_df = cf_df.copy()
    for col in ['CAPEX', 'OPEX', 'Cash Flow', 'Cumulative', 'Discounted CF']:
        display_df[col] = display_df[col].apply(lambda x: f"${x/1e6:.1f}M")
    display_df['NPV Factor'] = display_df['NPV Factor'].apply(lambda x: f"{x:.3f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # Summary metrics
    npv = cf_df['Discounted CF'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total CAPEX", f"${capex/1e6:.1f}M")
    with col2:
        st.metric("NPV (Costs)", f"${npv/1e6:.1f}M")
    with col3:
        st.metric("Simple Payback", "N/A (cost center)")
    
    # Cash flow chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=cf_df['Year'], y=cf_df['Cash Flow']/1e6,
        name='Annual Cash Flow', marker_color='#4299e1'
    ))
    
    fig.add_trace(go.Scatter(
        x=cf_df['Year'], y=cf_df['Cumulative']/1e6,
        name='Cumulative', line=dict(color='#e53e3e', width=2)
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(t=30, b=30),
        yaxis_title='$ Millions',
        xaxis_title='Year',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_constraints_tab(result_data):
    """Render constraint analysis"""
    
    st.markdown("##### Constraint Status")
    
    constraints = result_data.get('constraints', {})
    
    # Build constraint table
    constraint_data = []
    
    for name, status in constraints.items():
        if isinstance(status, dict):
            value = status.get('value', 0)
            limit = status.get('limit', 0)
            binding = status.get('binding', False)
            
            utilization = (value / limit * 100) if limit > 0 else 0
            
            constraint_data.append({
                'Constraint': name.replace('_', ' ').title(),
                'Value': f"{value:.1f}",
                'Limit': f"{limit:.1f}",
                'Utilization': f"{utilization:.1f}%",
                'Status': '🔴 Binding' if binding else '🟢 OK',
            })
    
    if constraint_data:
        df = pd.DataFrame(constraint_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Violations
    violations = result_data.get('violations', [])
    if violations:
        st.markdown("##### ⚠️ Violations")
        for v in violations:
            st.error(v)
    else:
        st.success("All constraints satisfied")
    
    # Shadow prices (indicative)
    st.markdown("##### Shadow Prices (Indicative)")
    st.info("""
    **Note:** Shadow prices from Phase 1 heuristic are rough approximations only.
    Run Phase 2 (MILP) for accurate dual variables.
    
    Shadow prices indicate the marginal value of relaxing each constraint by one unit:
    - **NOx**: $/ton of additional emission allowance
    - **Gas Supply**: $/MCF of additional daily gas capacity  
    - **Land**: $/acre of additional land
    """)


if __name__ == "__main__":
    render()
