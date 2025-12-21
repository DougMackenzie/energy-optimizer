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
        st.markdown("##### Detailed Metrics")
        df_summary = create_dispatch_summary_df(dispatch)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
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
