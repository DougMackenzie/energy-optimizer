"""
Dispatch Simulation Page
8760 hourly operation simulation and analysis
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render():
    st.markdown("### 📈 8760 Hourly Dispatch")
    
    # Check if optimization results exist
    if 'optimization_result' not in st.session_state:
        st.warning("⚠️ No optimization results available. Please run optimization first.")
        
        if st.button("🎯 Go to Optimizer", type="primary"):
            st.session_state.current_page = 'optimizer'
            st.rerun()
        
        return
    
    result = st.session_state.optimization_result
    
    # Header
    st.markdown(f"#### Dispatch Simulation: {result['scenario_name']}")
    st.caption("Hour-by-hour equipment operation for 1 year (8,760 hours)")
    
    # Get load profile
    if 'load_profile' in st.session_state:
        load_config = st.session_state.load_profile
        base_load = load_config.get('it_capacity_mw', 100) * load_config.get('pue', 1.25)
        load_factor = load_config.get('load_factor', 75) / 100
    else:
        # Use site default
        site = st.session_state.current_config['site']
        base_load = site.get('Total_Facility_MW', 200)
        load_factor = 0.75
    
    # Run simulation button
    col_sim1, col_sim2 = st.columns([3, 1])
    
    with col_sim1:
        st.info(f"""
        **Simulation Parameters:**
        - Base Load: {base_load:.1f} MW
        - Load Factor: {load_factor*100:.0f}%
        - Equipment: {result['scenario_name']}
        """)
    
    with col_sim2:
        if st.button("⚡ Run 8760 Simulation", type="primary", use_container_width=True):
            with st.spinner("Running 8760-hour dispatch simulation..."):
                from app.utils.dispatch_simulation import generate_8760_load_profile, dispatch_equipment, create_dispatch_summary_df
                
                # Generate load profile
                load_profile = generate_8760_load_profile(base_load, load_factor)
                
                # Run dispatch
                dispatch_results = dispatch_equipment(
                    load_profile=load_profile,
                    equipment_config=result['equipment_config'],
                    bess_available=True
                )
                
                # Store results
                st.session_state.dispatch_results = dispatch_results
                
                st.success("✅ Simulation complete!")
                st.rerun()
    
    # Display results if available
    if 'dispatch_results' in st.session_state:
        dispatch = st.session_state.dispatch_results
        
        st.markdown("---")
        st.markdown("#### 📊 Simulation Results")
        
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
        
        # Detailed summary table
        st.markdown("##### 📋 Annual Summary Metrics")
        df_summary = create_dispatch_summary_df(dispatch)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Equipment Utilization Table
        st.markdown("---")
        st.markdown("#### ⚙️ Equipment Utilization Breakdown")
        
        # Calculate utilization metrics
        total_hours = 8760
        
        recip_capacity = sum(e.get('capacity_mw', 0) for e in result['equipment_config'].get('recip_engines', []))
        turbine_capacity = sum(e.get('capacity_mw', 0) for e in result['equipment_config'].get('gas_turbines', []))
        bess_capacity = sum(e.get('power_mw', 0) for e in result['equipment_config'].get('bess', []))
        solar_capacity = result['equipment_config'].get('solar_mw_dc', 0)
        
        utilization_data = []
        
        if recip_capacity > 0:
            recip_gen = np.sum(dispatch['recip_dispatch_mw'])
            recip_cf = (recip_gen / (recip_capacity * total_hours)) if recip_capacity > 0 else 0
            recip_hours = summary['recip_hours']
            utilization_data.append({
                'Equipment': 'Reciprocating Engines',
                'Capacity (MW)': f"{recip_capacity:.1f}",
                'Energy (GWh)': f"{recip_gen/1000:.1f}",
                'Capacity Factor': f"{recip_cf:.1%}",
                'Operating Hours': f"{recip_hours:,.0f}",
                'Utilization': f"{(recip_hours/total_hours):.1%}"
            })
        
        if turbine_capacity > 0:
            turbine_gen = np.sum(dispatch['turbine_dispatch_mw'])
            turbine_cf = (turbine_gen / (turbine_capacity * total_hours)) if turbine_capacity > 0 else 0
            turbine_hours = summary['turbine_hours']
            utilization_data.append({
                'Equipment': 'Gas Turbines',
                'Capacity (MW)': f"{turbine_capacity:.1f}",
                'Energy (GWh)': f"{turbine_gen/1000:.1f}",
                'Capacity Factor': f"{turbine_cf:.1%}",
                'Operating Hours': f"{turbine_hours:,.0f}",
                'Utilization': f"{(turbine_hours/total_hours):.1%}"
            })
        
        if bess_capacity > 0:
            bess_discharge = np.sum(dispatch['bess_discharge_mw'])
            bess_charge = np.sum(dispatch['bess_charge_mw'])
            utilization_data.append({
                'Equipment': 'BESS',
                'Capacity (MW)': f"{bess_capacity:.1f}",
                'Energy (GWh)': f"{bess_discharge/1000:.1f} ↓ / {bess_charge/1000:.1f} ↑",
                'Capacity Factor': f"{summary['avg_bess_cycles_per_day']:.2f} cycles/day",
                'Operating Hours': 'Continuous',
                'Utilization': '100%'
            })
        
        if solar_capacity > 0:
            solar_gen = np.sum(dispatch['solar_generation_mw'])
            solar_cf = summary['avg_solar_cf']
            utilization_data.append({
                'Equipment': 'Solar PV',
                'Capacity (MW)': f"{solar_capacity:.1f}",
                'Energy (GWh)': f"{solar_gen/1000:.1f}",
                'Capacity Factor': f"{solar_cf:.1%}",
                'Operating Hours': '~12/day',
                'Utilization': 'Daylight Hours'
            })
        
        grid_import = np.sum(dispatch['grid_import_mw'])
        if grid_import > 0:
            grid_hours = summary['grid_hours']
            utilization_data.append({
                'Equipment': 'Grid Import',
                'Capacity (MW)': f"{result['equipment_config'].get('grid_import_mw', 0):.1f}",
                'Energy (GWh)': f"{grid_import/1000:.1f}",
                'Capacity Factor': 'Variable',
                'Operating Hours': f"{grid_hours:,.0f}",
                'Utilization': f"{(grid_hours/total_hours):.1%}"
            })
        
        df_utilization = pd.DataFrame(utilization_data)
        st.dataframe(df_utilization, use_container_width=True, hide_index=True)
        
        # Time series visualizations
        st.markdown("---")
        st.markdown("#### 📈 Hourly Dispatch Visualization")
        
        # Select time period to display
        time_periods = {
            "First Week (168 hours)": (0, 168),
            "First Month (720 hours)": (0, 720),
            "Summer Week (3000-3168)": (3000, 3168),
            "Winter Week (6000-6168)": (6000, 6168),
            "Full Year (8760 hours)": (0, 8760)
        }
        
        selected_period = st.selectbox("Select time period to view:", list(time_periods.keys()), index=0)
        start_hour, end_hour = time_periods[selected_period]
        
        # Create stacked area chart
        hours = np.arange(start_hour, min(end_hour, len(dispatch['load_mw'])))
        
        fig = go.Figure()
        
        # Add traces in stack order
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['grid_import_mw'][start_hour:end_hour],
            mode='lines',
            name='Grid Import',
            stackgroup='one',
            fillcolor='rgba(150, 150, 150, 0.7)',
            line=dict(width=0)
        ))
        
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['bess_discharge_mw'][start_hour:end_hour],
            mode='lines',
            name='BESS Discharge',
            stackgroup='one',
            fillcolor='rgba(255, 165, 0, 0.7)',
            line=dict(width=0)
        ))
        
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['turbine_dispatch_mw'][start_hour:end_hour],
            mode='lines',
            name='Gas Turbines',
            stackgroup='one',
            fillcolor='rgba(255, 99, 71, 0.7)',
            line=dict(width=0)
        ))
        
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['recip_dispatch_mw'][start_hour:end_hour],
            mode='lines',
            name='Recip Engines',
            stackgroup='one',
            fillcolor='rgba(50, 150, 250, 0.7)',
            line=dict(width=0)
        ))
        
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['solar_generation_mw'][start_hour:end_hour],
            mode='lines',
            name='Solar PV',
            stackgroup='one',
            fillcolor='rgba(255, 215, 0, 0.7)',
            line=dict(width=0)
        ))
        
        # Add load line
        fig.add_trace(go.Scatter(
            x=hours,
            y=dispatch['load_mw'][start_hour:end_hour],
            mode='lines',
            name='Load Demand',
            line=dict(color='black', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title=f"Hourly Dispatch - {selected_period}",
            xaxis_title="Hour",
            yaxis_title="Power (MW)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # BESS State of Charge
        if np.sum(dispatch['bess_soc_mwh']) > 0:
            st.markdown("##### Battery State of Charge")
            
            fig_bess = go.Figure()
            fig_bess.add_trace(go.Scatter(
                x=hours,
                y=dispatch['bess_soc_mwh'][start_hour:end_hour],
                mode='lines',
                name='SOC',
                line=dict(color='orange', width=2),
                fill='tozeroy'
            ))
            
            fig_bess.update_layout(
                title="BESS State of Charge",
                xaxis_title="Hour",
                yaxis_title="Energy (MWh)",
                height=300
            )
            
            st.plotly_chart(fig_bess, use_container_width=True)
        
        # Emissions over time
        st.markdown("##### Hourly Emissions")
        
        col_em1, col_em2 = st.columns(2)
        
        with col_em1:
            fig_nox = go.Figure()
            fig_nox.add_trace(go.Scatter(
                x=hours,
                y=dispatch['emissions_nox_lb'][start_hour:end_hour],
                mode='lines',
                name='NOx',
                line=dict(color='red', width=1),
                fill='tozeroy'
            ))
            fig_nox.update_layout(
                title="NOx Emissions",
                xaxis_title="Hour",
                yaxis_title="NOx (lb/hr)",
                height=250
            )
            st.plotly_chart(fig_nox, use_container_width=True)
        
        with col_em2:
            fig_co2 = go.Figure()
            fig_co2.add_trace(go.Scatter(
                x=hours,
                y=dispatch['emissions_co2_tons'][start_hour:end_hour],
                mode='lines',
                name='CO2',
                line=dict(color='brown', width=1),
                fill='tozeroy'
            ))
            fig_co2.update_layout(
                title="CO₂ Emissions",
                xaxis_title="Hour",
                yaxis_title="CO₂ (tons/hr)",
                height=250
            )
            st.plotly_chart(fig_co2, use_container_width=True)
        
        # High-Resolution Transient Analysis
        st.markdown("---")
        with st.expander("🔬 High-Resolution Transient Analysis (Second-Level)", expanded=False):
            st.markdown("#### Detailed Power Quality Analysis")
            st.caption("Simulate transient events with 1-second resolution")
            
            col_trans1, col_trans2, col_trans3 = st.columns(3)
            
            with col_trans1:
                event_type = st.selectbox("Event Type", [
                    "step_change",
                    "ramp_up", 
                    "ramp_down",
                    "oscillation"
                ], format_func=lambda x: x.replace('_', ' ').title())
            
            with col_trans2:
                duration = st.slider("Duration (seconds)", 60, 600, 300)
            
            with col_trans3:
                magnitude = st.slider("Event Magnitude (%)", 5, 50, 20)
            
            if st.button("⚡ Run High-Res Simulation", type="primary"):
                with st.spinner("Running second-level transient simulation..."):
                    from app.utils.highres_transient import generate_high_res_transient, calculate_power_quality_metrics
                    
                    transient_data = generate_high_res_transient(
                        base_load_mw=base_load,
                        event_type=event_type,
                        duration_seconds=duration,
                        event_magnitude_pct=magnitude
                    )
                    
                    pq_metrics = calculate_power_quality_metrics(transient_data)
                    
                    st.session_state.transient_highres = transient_data
                    st.session_state.pq_metrics = pq_metrics
                    
                    st.success("✅ High-resolution simulation complete!")
                    st.rerun()
            
            if 'transient_highres' in st.session_state:
                trans_data = st.session_state.transient_highres
                pq = st.session_state.pq_metrics
                
                st.markdown("---")
                col_pq1, col_pq2, col_pq3, col_pq4 = st.columns(4)
                
                with col_pq1:
                    st.metric("Max Freq Dev", f"{pq['max_frequency_deviation_hz']:.3f} Hz")
                with col_pq2:
                    st.metric("Max Ramp", f"{pq['max_ramp_rate_mw_s']:.1f} MW/s")
                with col_pq3:
                    st.metric("BESS Response", f"{pq['bess_max_response_mw']:.1f} MW")
                with col_pq4:
                    st.metric("Stabilize Time", f"{pq['time_to_stabilize_s']:.0f} s")
                
                fig_highres = go.Figure()
                fig_highres.add_trace(go.Scatter(x=trans_data['time'], y=trans_data['load_mw'], mode='lines', name='Load', line=dict(color='blue', width=2)))
                fig_highres.add_trace(go.Scatter(x=trans_data['time'], y=trans_data['generator_response_mw'], mode='lines', name='Generator', line=dict(color='green', width=2)))
                fig_highres.add_trace(go.Scatter(x=trans_data['time'], y=trans_data['bess_response_mw'], mode='lines', name='BESS', line=dict(color='orange', width=2)))
                fig_highres.update_layout(title="Transient Response (1-second resolution)", xaxis_title="Time (s)", yaxis_title="Power (MW)", height=400)
                st.plotly_chart(fig_highres, use_container_width=True)
        
        # Export options
        st.markdown("---")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            if st.button("📊 Export to Excel", use_container_width=True):
                st.info("Excel export coming soon!")
        
        with col_exp2:
            if st.button("📄 Generate Report", use_container_width=True):
                st.info("PDF report coming soon!")
        
        with col_exp3:
            if st.button("🔄 Run New Simulation", use_container_width=True):
                if 'dispatch_results' in st.session_state:
                    del st.session_state.dispatch_results
                st.rerun()


if __name__ == "__main__":
    render()
