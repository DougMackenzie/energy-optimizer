"""
Dispatch Simulation Page - ENHANCED WITH DR OVERLAYS
8760 hourly operation simulation with Demand Response visualization
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from app.utils.dispatch_simulation import generate_8760_load_profile, dispatch_equipment, create_dispatch_summary_df


def render():
    st.markdown("### 📈 8760 Hourly Dispatch & Demand Response")
    
    # Check if optimization results exist
    if 'optimization_result' not in st.session_state:
        st.warning("⚠️ No optimization results available. Please run optimization first.")
        
        if st.button("🎯 Go to Optimizer", type="primary"):
            st.session_state.current_page = 'optimizer'
            st.rerun()
        
        return
    
    result = st.session_state.optimization_result
    
    # Check if MILP optimization with DR
    is_milp_dr = result.get('milp_optimized', False) and 'dr_metrics' in result
    
    # Header
    st.markdown(f"#### Dispatch Simulation: {result['scenario_name']}")
    if is_milp_dr:
        st.caption("✨ MILP optimization with integrated **Demand Response** capability")
    else:
        st.caption("Hour-by-hour equipment operation for 1 year (8,760 hours)")
    
    # Get load profile
    if 'load_profile_dr' in st.session_state and is_milp_dr:
        load_profile_dr = st.session_state.load_profile_dr
        load_data = load_profile_dr.get('load_data', {})
        base_load = load_profile_dr.get('peak_it_mw', 160) * load_profile_dr.get('pue', 1.25)
        load_factor = load_profile_dr.get('load_factor', 0.75)
    elif 'load_profile' in st.session_state:
        load_config = st.session_state.load_profile
        base_load = load_config.get('it_capacity_mw', 100) * load_config.get('pue', 1.25)
        load_factor = load_config.get('load_factor', 75) / 100
        load_data = None
    else:
        # Use site default  
        site = st.session_state.current_config['site']
        base_load = site.get('Total_Facility_MW', 200)
        load_factor = 0.75
        load_data = None
    
    # Create tabs for different views
    tab_overview, tab_dr, tab_export = st.tabs([
        "📊 Overview & Equipment", "⚡ Demand Response", "💾 Export Data"
    ])
    
    # Define time periods for all tabs
    time_periods = {
        "First Week (168 hours)": (0, 168),
        "First Month (720 hours)": (0, 720),
        "Summer Week (3000-3168)": (3000, 3168),
        "Winter Week (6000-6168)": (6000, 6168),
        "Full Year (8760 hours)": (0, 8760)
    }
    
    # ============================================
    # TAB 1: OVERVIEW & EQUIPMENT
    # ============================================
    with tab_overview:
        # Run simulation button
        col_sim1, col_sim2 = st.columns([3, 1])
        
        with col_sim1:
            st.info(f"""
            **Simulation Parameters:**
            - Base Load: {base_load:.1f} MW
            - Load Factor: {load_factor*100:.0f}%
            - Equipment: {result['scenario_name']}
            {"- **DR Enabled**: Yes ✓" if is_milp_dr else ""}
            """)
        
        with col_sim2:
            if st.button("⚡ Run 8760 Simulation", type="primary", use_container_width=True):
                with st.spinner("Running 8760-hour dispatch simulation..."):
                    # Generate load profile
                    if load_data and 'hourly' in load_data:
                        # Use MILP load profile
                        load_profile = load_data['hourly']['facility_load_mw']
                    else:
                        load_profile = generate_8760_load_profile(base_load, load_factor)
                    
                    # Run dispatch
                    dispatch_results = dispatch_equipment(
                        load_profile=load_profile,
                        equipment_config=result['equipment_config'],
                        bess_available=True
                    )
                    
                    # Add DR data if MILP
                    if is_milp_dr and load_data:
                        dispatch_results['dr_enabled'] = True
                        dispatch_results['flexibility_mw'] = load_data['hourly']['total_flexibility_mw']
                        dispatch_results['firm_load_mw'] = load_data['hourly']['firm_load_mw']
                        dispatch_results['workload_curt_mw'] = load_data['hourly'].get('workload_flexibility_mw', np.zeros(8760))
                        dispatch_results['cooling_curt_mw'] = load_data['hourly'].get('cooling_flexibility_mw', np.zeros(8760))
                        dispatch_results['dr_metrics'] = result['dr_metrics']
                    else:
                        dispatch_results['dr_enabled'] = False
                    
                    # Store results
                    st.session_state.dispatch_results = dispatch_results
                    
                    st.success("✅ Simulation complete!")
                    st.rerun()
        
        # Display results if available
        if 'dispatch_results' in st.session_state:
            dispatch = st.session_state.dispatch_results
            
            st.markdown("---")
            st.markdown("#### 📊 Annual Summary Metrics")
            
            # Summary metrics
            summary = dispatch['summary']
            
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            
            with col_m1:
                st.metric("Energy Served", f"{summary['total_energy_served_gwh']:.1f} GWh")
            
            with col_m2:
                st.metric("Reliability", f"{summary['reliability_pct']:.2f}%")
            
            with col_m3:
                st.metric("Fuel Cost", f"${summary['total_fuel_cost_m']:.2f}M")
            
            with col_m4:
                st.metric("NOx Emissions", f"{summary['total_nox_tons']:.1f} tons")
            
            with col_m5:
                st.metric("CO₂ Emissions", f"{summary['total_co2_tons']:,.0f} tons")
            
            # Interactive dispatch chart
            st.markdown("---")
            st.markdown("#### 📈 Interactive Hourly Dispatch Chart")
            
            col_period, col_chart = st.columns([2, 1])
            
            with col_period:
                selected_period = st.selectbox("Time period:", list(time_periods.keys()), index=0)
            
            with col_chart:
                chart_type = st.radio("Chart type:", ["Stacked", "Lines"], horizontal=True)
            
            start_hour, end_hour = time_periods[selected_period]
            
            # Create dispatch chart
            fig = create_dispatch_chart(dispatch, start_hour, end_hour, chart_type.lower())
            st.plotly_chart(fig, use_container_width=True)
    
    # ============================================
    # TAB 2: DEMAND RESPONSE
    # ============================================
    with tab_dr:
        if 'dispatch_results' in st.session_state and dispatch.get('dr_enabled', False):
            st.markdown("### ⚡ Demand Response Analysis")
            
            # DR metrics
            dr_metrics = dispatch.get('dr_metrics', {})
            
            col_dr1, col_dr2, col_dr3, col_dr4 = st.columns(4)
            
            with col_dr1:
                st.metric("Avg Flexibility", 
                         f"{np.mean(dispatch['flexibility_mw']):.1f} MW",
                         delta=f"{(np.mean(dispatch['flexibility_mw'])/np.mean(dispatch['load_mw'])*100):.1f}%")
            
            with col_dr2:
                total_curt = np.sum(dispatch['workload_curt_mw']) + np.sum(dispatch['cooling_curt_mw'])
                st.metric("Annual Curtailment",
                         f"{total_curt:.0f} MWh")
            
            with col_dr3:
                st.metric("DR Revenue",
                         f"${dr_metrics.get('dr_revenue_annual', 0):,.0f}/yr")
            
            with col_dr4:
                lcoe_benefit = dr_metrics.get('dr_revenue_annual', 0) / (summary['total_energy_served_gwh'] * 1000)
                st.metric("LCOE Benefit",
                         f"${lcoe_benefit:.2f}/MWh")
            
            # Time period selector
            st.markdown("---")
            selected_period_dr = st.selectbox("Time period:", list(time_periods.keys()), index=0, key="dr_period")
            start_dr, end_dr = time_periods[selected_period_dr]
            
            # DR flexibility chart
            st.markdown("#### 💡 Facility Load Breakdown: Firm vs Flexible")
            fig_flex = create_dr_flexibility_chart(dispatch, start_dr, end_dr)
            st.plotly_chart(fig_flex, use_container_width=True)
            
            # Curtailment detail
            st.markdown("#### 🔻 Curtailment Events by Type")
            fig_curt = create_curtailment_chart(dispatch, start_dr, end_dr)
            st.plotly_chart(fig_curt, use_container_width=True)
            
            # Flexibility heatmap
            st.markdown("#### 🔥 Annual Flexibility Utilization Heatmap")
            fig_heat = create_flexibility_heatmap(dispatch)
            st.plotly_chart(fig_heat, use_container_width=True)
        
        else:
            st.info("💡 **Demand Response not enabled**. Use Load Composer + MILP to enable DR.")
    
    # ============================================
    # TAB 3: EXPORT
    # ============================================
    with tab_export:
        if 'dispatch_results' in st.session_state:
            st.markdown("### 💾 Export 8760 Hourly Data")
            
            import io
            from datetime import datetime
            
            # Build export dataframe
            export_df = build_export_dataframe(dispatch)
            
            # Download buttons
            col1, col2, col3 = st.columns(3)
            
            site_name = result.get('site_name', 'Site').replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            with col1:
                csv_buffer = io.StringIO()
                export_df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    "📥 CSV", csv_buffer.getvalue(),
                    f"{site_name}_8760_{timestamp}.csv",
                    "text/csv", use_container_width=True, type="primary"
                )
            
            with col2:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    export_df.to_excel(writer, sheet_name='Dispatch', index=False)
                
                st.download_button(
                    "📥 Excel", excel_buffer.getvalue(),
                    f"{site_name}_8760_{timestamp}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, type="primary"
                )
            
            with col3:
                import json
                json_str = json.dumps(export_df.to_dict(orient='records'), indent=2)
                
                st.download_button(
                    "📥 JSON", json_str,
                    f"{site_name}_8760_{timestamp}.json",
                    "application/json", use_container_width=True
                )
            
            # Preview
            st.markdown("---")
            st.markdown("#### Data Preview (first 24 hours)")
            st.dataframe(export_df.head(24), use_container_width=True)


def create_dispatch_chart(dispatch, start, end, chart_type="stacked"):
    """Enhanced dispatch chart"""
    hours = np.arange(start, min(end, len(dispatch['load_mw'])))
    
    fig = go.Figure()
    
    if chart_type == "stacked":
        fig.add_trace(go.Scatter(x=hours, y=dispatch['grid_import_mw'][start:end], mode='lines', name='Grid', stackgroup='one', fillcolor='rgba(150,150,150,0.7)', line=dict(width=0)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['bess_discharge_mw'][start:end], mode='lines', name='BESS', stackgroup='one', fillcolor='rgba(255,165,0,0.7)', line=dict(width=0)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['turbine_dispatch_mw'][start:end], mode='lines', name='Turbine', stackgroup='one', fillcolor='rgba(255,99,71,0.7)', line=dict(width=0)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['recip_dispatch_mw'][start:end], mode='lines', name='Recip', stackgroup='one', fillcolor='rgba(50,150,250,0.7)', line=dict(width=0)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['solar_generation_mw'][start:end], mode='lines', name='Solar', stackgroup='one', fillcolor='rgba(255,215,0,0.7)', line=dict(width=0)))
    else:
        fig.add_trace(go.Scatter(x=hours, y=dispatch['grid_import_mw'][start:end], mode='lines', name='Grid', line=dict(color='gray', width=2)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['bess_discharge_mw'][start:end], mode='lines', name='BESS', line=dict(color='orange', width=2)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['turbine_dispatch_mw'][start:end], mode='lines', name='Turbine', line=dict(color='tomato', width=2)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['recip_dispatch_mw'][start:end], mode='lines', name='Recip', line=dict(color='royalblue', width=2)))
        fig.add_trace(go.Scatter(x=hours, y=dispatch['solar_generation_mw'][start:end], mode='lines', name='Solar', line=dict(color='gold', width=2)))
    
    fig.add_trace(go.Scatter(x=hours, y=dispatch['load_mw'][start:end], mode='lines', name='Load', line=dict(color='black', width=2, dash='dash')))
    
    fig.update_layout(title="Equipment Dispatch", xaxis_title="Hour", yaxis_title="MW", hovermode='x unified', height=500)
    return fig


def create_dr_flexibility_chart(dispatch, start, end):
    """DR flexibility waterfall"""
    hours = np.arange(start, min(end, len(dispatch['load_mw'])))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=dispatch['firm_load_mw'][start:end], mode='lines', name='Firm Load', stackgroup='one', fillcolor='rgba(100,100,100,0.8)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=hours, y=dispatch['flexibility_mw'][start:end], mode='lines', name='Flexibility', stackgroup='one', fillcolor='rgba(135,206,250,0.6)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=hours, y=dispatch['load_mw'][start:end], mode='lines', name='Total Load', line=dict(color='black', width=2, dash='dot')))
    
    fig.update_layout(title="Firm Load + Flexibility", xaxis_title="Hour", yaxis_title="MW", height=400, hovermode='x unified')
    return fig


def create_curtailment_chart(dispatch, start, end):
    """Curtailment detail chart"""
    hours = np.arange(start, min(end, len(dispatch['workload_curt_mw'])))
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x=hours, y=dispatch['workload_curt_mw'][start:end], mode='lines', name='Workload Curtail', line=dict(color='red', width=2), fill='tozeroy', fillcolor='rgba(255,0,0,0.3)'), secondary_y=False)
    fig.add_trace(go.Scatter(x=hours, y=dispatch['cooling_curt_mw'][start:end], mode='lines', name='Cooling Curtail', line=dict(color='blue', width=2), fill='tozeroy', fillcolor='rgba(0,0,255,0.3)'), secondary_y=False)
    fig.add_trace(go.Scatter(x=hours, y=dispatch['flexibility_mw'][start:end], mode='lines', name='Total Flexibility', line=dict(color='green', width=1, dash='dash')), secondary_y=True)
    
    fig.update_xaxes(title_text="Hour")
    fig.update_yaxes(title_text="Curtailment (MW)", secondary_y=False)
    fig.update_yaxes(title_text="Available (MW)", secondary_y=True)
    fig.update_layout(title="Curtailment Events", height=400, hovermode='x unified')
    return fig


def create_flexibility_heatmap(dispatch):
    """Annual flexibility heatmap"""
    flex_pct = (dispatch['flexibility_mw'] / dispatch['load_mw']) * 100
    flex_pct = np.nan_to_num(flex_pct, nan=0.0)
    
    weeks_data = flex_pct[:52*168].reshape(52, 168)
    
    fig = go.Figure(data=go.Heatmap(
        z=weeks_data,
        x=list(range(168)),
        y=[f"W{i+1}" for i in range(52)],
        colorscale='RdYlGn',
        colorbar=dict(title="Flex %")
    ))
    
    fig.update_layout(title="52 Weeks × 168 Hours Flexibility Heatmap", xaxis_title="Hour of Week", yaxis_title="Week", height=600)
    return fig


def build_export_dataframe(dispatch):
    """Build comprehensive export dataframe"""
    df = pd.DataFrame({
        'Hour': range(8760),
        'Load_MW': dispatch['load_profile_mw'],
        'Grid_MW': dispatch.get('grid_import_mw', np.zeros(8760)),
        'Solar_MW': dispatch.get('solar_output_mw', np.zeros(8760)),
        'Recip_MW': dispatch.get('recip_dispatch_mw', np.zeros(8760)),
        'Turbine_MW': dispatch.get('turbine_dispatch_mw', np.zeros(8760)),
        'BESS_Discharge_MW': dispatch.get('bess_discharge_mw', np.zeros(8760)),
        'BESS_Charge_MW': dispatch.get('bess_charge_mw', np.zeros(8760)),
        'BESS_SOC_MWh': dispatch.get('bess_soc_mwh', np.zeros(8760)),
        'NOx_lb': dispatch.get('nox_emissions_lb_hourly', np.zeros(8760)),
        'CO2_tons': dispatch.get('emissions_co2_tons', np.zeros(8760))
    })
    
    if dispatch.get('dr_enabled'):
        df['Firm_Load_MW'] = dispatch.get('firm_load_mw', np.zeros(8760))
        df['Flexibility_MW'] = dispatch.get('flexibility_mw', np.zeros(8760))
        df['Workload_Curtail_MW'] = dispatch.get('workload_curt_mw', np.zeros(8760))
        df['Cooling_Curtail_MW'] = dispatch.get('cooling_curt_mw', np.zeros(8760))
    
    return df


if __name__ == "__main__":
    render()
