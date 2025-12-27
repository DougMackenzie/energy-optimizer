"""
Sites & Load Configuration Page
Configure site parameters and load trajectory
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import COLORS, WORKLOAD_FLEXIBILITY


def render():
    """Render the Sites & Load page"""
    
    st.markdown("### 📍 Sites & Load Configuration")
    st.markdown("*Define your datacenter site and load characteristics*")
    st.markdown("---")
    
    # Tabs for different configuration sections
    tab_site, tab_load, tab_workload, tab_summary = st.tabs([
        "🏭 Site Parameters", "📈 Load Trajectory", "🤖 Workload Mix", "📋 Summary"
    ])
    
    with tab_site:
        render_site_config()
    
    with tab_load:
        render_load_trajectory()
    
    with tab_workload:
        render_workload_mix()
    
    with tab_summary:
        render_configuration_summary()


def render_site_config():
    """Site parameters configuration"""
    
    st.markdown("#### Site Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        site_name = st.text_input("Site Name", value=st.session_state.get('site_name', 'New Datacenter Site'))
        
        location = st.text_input("Location", value=st.session_state.get('site_location', 'Tulsa, OK'))
        
        iso_rto = st.selectbox(
            "ISO/RTO",
            ["SPP", "ERCOT", "PJM", "MISO", "CAISO", "NYISO", "ISO-NE"],
            index=["SPP", "ERCOT", "PJM", "MISO", "CAISO", "NYISO", "ISO-NE"].index(
                st.session_state.get('iso_rto', 'SPP')
            )
        )
        
        voltage_level = st.selectbox(
            "Interconnection Voltage",
            ["69 kV", "138 kV", "230 kV", "345 kV", "500 kV"],
            index=2
        )
    
    with col2:
        land_acres = st.number_input(
            "Available Land (acres)", 
            10, 5000, 
            st.session_state.get('land_acres', 500)
        )
        
        gas_supply = st.number_input(
            "Gas Pipeline Capacity (MCF/day)",
            1000, 500000,
            st.session_state.get('gas_supply', 50000)
        )
        
        nox_limit = st.number_input(
            "Air Permit NOx Limit (tpy)",
            25, 500,
            st.session_state.get('nox_limit', 100),
            help="100 tpy = minor source threshold"
        )
        
        grid_queue_months = st.number_input(
            "Grid Queue Position (months)",
            12, 120,
            st.session_state.get('grid_queue_months', 60),
            help="Expected months until grid interconnection"
        )
    
    st.markdown("---")
    st.markdown("#### Environmental Constraints")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        water_available = st.checkbox("Water Available for Cooling", value=True)
        water_limit = st.number_input("Water Limit (gal/day)", 0, 10000000, 1000000) if water_available else 0
    
    with col2:
        noise_restricted = st.checkbox("Noise Restrictions", value=False)
        noise_limit_dba = st.number_input("Noise Limit (dBA at fence)", 50, 90, 65) if noise_restricted else 90
    
    with col3:
        elevation_ft = st.number_input("Elevation (ft)", 0, 10000, 900)
        ambient_temp_f = st.number_input("Design Ambient (°F)", 80, 120, 95)
    
    # Save to session state
    if st.button("💾 Save Site Configuration", type="primary"):
        st.session_state.current_site = {
            'Site_Name': site_name,
            'Location': location,
            'ISO_RTO': iso_rto,
            'Voltage': voltage_level,
            'Land_Acres': land_acres,
            'Gas_MCF_Day': gas_supply,
            'NOx_TPY_Limit': nox_limit,
            'Grid_Queue_Months': grid_queue_months,
            'Water_Available': water_available,
            'Water_Limit_GPD': water_limit,
            'Noise_Restricted': noise_restricted,
            'Noise_Limit_DBA': noise_limit_dba,
            'Elevation_FT': elevation_ft,
            'Ambient_F': ambient_temp_f,
        }
        st.session_state.site_name = site_name
        st.session_state.site_location = location
        st.session_state.iso_rto = iso_rto
        st.session_state.land_acres = land_acres
        st.session_state.gas_supply = gas_supply
        st.session_state.nox_limit = nox_limit
        st.session_state.grid_queue_months = grid_queue_months
        
        st.success("✅ Site configuration saved!")


def render_load_trajectory():
    """Load trajectory configuration"""
    
    st.markdown("#### Load Trajectory")
    st.markdown("Define how load grows over time")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Phased Deployment**")
        
        first_year = st.number_input("First Load Year", 2024, 2035, 
                                      st.session_state.get('first_year', 2028))
        first_load_mw = st.number_input("Initial IT Load (MW)", 10, 500,
                                         st.session_state.get('first_load_mw', 150))
        target_load_mw = st.number_input("Target IT Load (MW)", 50, 2000,
                                          st.session_state.get('target_load_mw', 600))
        ramp_years = st.number_input("Years to Full Load", 1, 10,
                                      st.session_state.get('ramp_years', 4))
    
    with col2:
        st.markdown("**Facility Parameters**")
        
        pue = st.slider("Power Usage Effectiveness (PUE)", 1.10, 1.60, 
                        st.session_state.get('pue', 1.25), 0.01)
        
        load_factor = st.slider("Annual Load Factor (%)", 50, 100,
                                st.session_state.get('load_factor', 85)) / 100
        
        n1_required = st.checkbox("N-1 Redundancy Required", 
                                  value=st.session_state.get('n1_required', True))
        
        min_availability = st.slider("Minimum Availability (%)", 99.0, 99.99,
                                     st.session_state.get('min_availability', 99.5), 0.01)
    
    # Generate trajectory
    load_trajectory = {}
    facility_trajectory = {}
    
    for i in range(ramp_years + 1):
        year = first_year + i
        if i == 0:
            it_load = first_load_mw
        else:
            progress = min(i / ramp_years, 1.0)
            it_load = first_load_mw + (target_load_mw - first_load_mw) * progress
        
        load_trajectory[year] = round(it_load, 1)
        facility_trajectory[year] = round(it_load * pue, 1)
    
    # Extend to 2040
    for year in range(first_year + ramp_years + 1, 2041):
        load_trajectory[year] = target_load_mw
        facility_trajectory[year] = round(target_load_mw * pue, 1)
    
    # Display trajectory
    st.markdown("---")
    st.markdown("#### Load Trajectory Preview")
    
    traj_df = pd.DataFrame({
        'Year': list(load_trajectory.keys())[:10],
        'IT Load (MW)': list(load_trajectory.values())[:10],
        'Facility Load (MW)': list(facility_trajectory.values())[:10],
    })
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.dataframe(traj_df, use_container_width=True, hide_index=True, height=350)
    
    with col2:
        fig = go.Figure()
        
        years = list(load_trajectory.keys())[:10]
        
        fig.add_trace(go.Scatter(
            x=years, y=[load_trajectory[y] for y in years],
            name='IT Load', mode='lines+markers',
            line=dict(color='#4299e1', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=years, y=[facility_trajectory[y] for y in years],
            name='Facility Load', mode='lines+markers',
            line=dict(color='#48bb78', width=2)
        ))
        
        fig.update_layout(
            height=350,
            margin=dict(t=30, b=30, l=50, r=20),
            xaxis_title='Year',
            yaxis_title='MW',
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Save
    if st.button("💾 Save Load Trajectory", type="primary"):
        st.session_state.load_trajectory = load_trajectory
        st.session_state.facility_trajectory = facility_trajectory
        st.session_state.first_year = first_year
        st.session_state.first_load_mw = first_load_mw
        st.session_state.target_load_mw = target_load_mw
        st.session_state.ramp_years = ramp_years
        st.session_state.pue = pue
        st.session_state.load_factor = load_factor
        st.session_state.n1_required = n1_required
        st.session_state.min_availability = min_availability
        
        st.success("✅ Load trajectory saved!")


def render_workload_mix():
    """AI workload mix configuration"""
    
    st.markdown("#### AI Workload Mix")
    st.markdown("Define the mix of AI workloads to determine flexibility profile")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Workload Allocation**")
        
        pre_training = st.slider(
            "Pre-training (%)", 0, 100, 
            st.session_state.get('wl_pre_training', 30),
            help="Large-scale model training, checkpoint-capable"
        )
        
        fine_tuning = st.slider(
            "Fine-tuning (%)", 0, 100,
            st.session_state.get('wl_fine_tuning', 20),
            help="Shorter training runs, more interruptible"
        )
        
        batch_inference = st.slider(
            "Batch Inference (%)", 0, 100,
            st.session_state.get('wl_batch_inference', 30),
            help="Queue-based, highly deferrable"
        )
        
        realtime_inference = st.slider(
            "Real-time Inference (%)", 0, 100,
            st.session_state.get('wl_realtime_inference', 20),
            help="Latency-critical, minimal flexibility"
        )
        
        total = pre_training + fine_tuning + batch_inference + realtime_inference
        
        if total != 100:
            st.warning(f"⚠️ Total = {total}%. Adjust to equal 100%")
        else:
            st.success(f"✓ Total = 100%")
    
    with col2:
        st.markdown("**Workload Characteristics**")
        
        # Calculate weighted flexibility
        workload_mix = {
            'pre_training': pre_training / 100,
            'fine_tuning': fine_tuning / 100,
            'batch_inference': batch_inference / 100,
            'real_time_inference': realtime_inference / 100,
        }
        
        total_flex = 0
        char_data = []
        
        for wl_id, fraction in workload_mix.items():
            wl_info = WORKLOAD_FLEXIBILITY.get(wl_id, {})
            flex = wl_info.get('flexibility_pct', 0)
            response = wl_info.get('response_time_min', 0)
            
            total_flex += fraction * flex
            
            char_data.append({
                'Workload': wl_id.replace('_', ' ').title(),
                'Mix': f"{fraction*100:.0f}%",
                'Flexibility': f"{flex*100:.0f}%",
                'Response Time': f"{response} min",
            })
        
        char_df = pd.DataFrame(char_data)
        st.dataframe(char_df, use_container_width=True, hide_index=True)
        
        # Summary metric
        st.markdown(f"""
        <div style="background: #ebf8ff; padding: 16px; border-radius: 8px; margin-top: 16px;">
            <div style="font-size: 14px; color: #2c5282;">Weighted Facility Flexibility</div>
            <div style="font-size: 32px; font-weight: 700; color: #2b6cb0;">{total_flex*100:.1f}%</div>
            <div style="font-size: 12px; color: #4a5568;">Available for demand response</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Pie chart
    st.markdown("---")
    
    if total == 100:
        fig = px.pie(
            values=[pre_training, fine_tuning, batch_inference, realtime_inference],
            names=['Pre-training', 'Fine-tuning', 'Batch Inference', 'Real-time Inference'],
            title="Workload Distribution",
            color_discrete_sequence=['#4299e1', '#48bb78', '#f6ad55', '#fc8181']
        )
        fig.update_layout(height=300, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Save
    if st.button("💾 Save Workload Mix", type="primary"):
        st.session_state.workload_mix = workload_mix
        st.session_state.wl_pre_training = pre_training
        st.session_state.wl_fine_tuning = fine_tuning
        st.session_state.wl_batch_inference = batch_inference
        st.session_state.wl_realtime_inference = realtime_inference
        st.session_state.total_flexibility = total_flex
        
        st.success("✅ Workload mix saved!")


def render_configuration_summary():
    """Summary of all configuration"""
    
    st.markdown("#### Configuration Summary")
    
    # Site
    site = st.session_state.get('current_site', {})
    
    if site:
        st.markdown("##### 🏭 Site")
        
        site_df = pd.DataFrame({
            'Parameter': ['Name', 'Location', 'ISO/RTO', 'Land', 'Gas Supply', 'NOx Limit', 'Grid Queue'],
            'Value': [
                site.get('Site_Name', 'Not set'),
                site.get('Location', 'Not set'),
                site.get('ISO_RTO', 'Not set'),
                f"{site.get('Land_Acres', 0)} acres",
                f"{site.get('Gas_MCF_Day', 0):,} MCF/day",
                f"{site.get('NOx_TPY_Limit', 0)} tpy",
                f"{site.get('Grid_Queue_Months', 0)} months",
            ]
        })
        st.dataframe(site_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Site not configured. Go to Site Parameters tab.")
    
    st.markdown("---")
    
    # Load
    load_traj = st.session_state.get('load_trajectory', {})
    
    if load_traj:
        st.markdown("##### 📈 Load Trajectory")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("First Year", st.session_state.get('first_year', 'N/A'))
        with col2:
            st.metric("Initial Load", f"{st.session_state.get('first_load_mw', 0)} MW")
        with col3:
            st.metric("Target Load", f"{st.session_state.get('target_load_mw', 0)} MW")
        with col4:
            st.metric("PUE", st.session_state.get('pue', 'N/A'))
    else:
        st.warning("⚠️ Load trajectory not configured. Go to Load Trajectory tab.")
    
    st.markdown("---")
    
    # Workload
    wl_mix = st.session_state.get('workload_mix', {})
    
    if wl_mix:
        st.markdown("##### 🤖 Workload Mix")
        
        col1, col2 = st.columns(2)
        with col1:
            for wl, frac in wl_mix.items():
                st.write(f"**{wl.replace('_', ' ').title()}:** {frac*100:.0f}%")
        with col2:
            st.metric("Total Flexibility", f"{st.session_state.get('total_flexibility', 0)*100:.1f}%")
    else:
        st.warning("⚠️ Workload mix not configured. Go to Workload Mix tab.")
    
    st.markdown("---")
    
    # Ready check
    all_configured = bool(site and load_traj and wl_mix)
    
    if all_configured:
        st.success("✅ All configurations complete! Ready to run optimization.")
        
        if st.button("🎯 Go to Problem Selection", type="primary", use_container_width=True):
            st.session_state.current_page = 'problem_selection'
            st.rerun()
    else:
        st.info("Complete all configuration sections above, then proceed to Problem Selection.")


if __name__ == "__main__":
    render()
