"""
Enhanced Load Composer Page with Demand Response Configuration
Integrates workload mix, cooling flexibility, and DR economics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from app.utils.load_profile_generator import (
    generate_load_profile_with_flexibility,
    calculate_dr_economics
)


def render():
    st.markdown("### ⚡ Load Composer with Demand Response")
    
    st.info("""
    **Configure facility load profile with demand response capabilities**
    
    Define IT workload mix, cooling flexibility, and DR participation to optimize power costs.
    """)
    
    # Initialize session state
    if 'load_profile_dr' not in st.session_state:
        st.session_state.load_profile_dr = {
            'peak_it_mw': 160.0,
            'pue': 1.25,
            'load_factor': 0.75,
            'workload_mix': {
                'pre_training': 40,
                'fine_tuning': 20,
                'batch_inference': 15,
                'realtime_inference': 15,
                'rl_training': 5,
                'cloud_hpc': 5,
            },
            'cooling_flex': 0.25,
            'thermal_constant_min': 30,
            'enabled_dr_products': ['economic_dr'],
        }
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Basic Load", "🔄 Workload Mix", "❄️ Cooling Flexibility", "💰 DR Economics"
    ])
    
    # =========================================================================
    # TAB 1: BASIC FACILITY PARAMETERS
    # =========================================================================
    with tab1:
        st.markdown("#### Basic Facility Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            peak_it_mw = st.number_input(
                "Peak IT Load (MW)", 
                min_value=10.0, max_value=2000.0, 
                value=st.session_state.load_profile_dr['peak_it_mw'], 
                step=10.0,
                help="Peak IT equipment load excluding cooling"
            )
            st.session_state.load_profile_dr['peak_it_mw'] = peak_it_mw
        
        with col2:
            pue = st.number_input(
                "PUE", 
                min_value=1.0, max_value=2.0, 
                value=st.session_state.load_profile_dr['pue'], 
                step=0.05,
                help="Power Usage Effectiveness (1.2-1.4 typical for modern facilities)"
            )
            st.session_state.load_profile_dr['pue'] = pue
        
        with col3:
            load_factor = st.slider(
                "Load Factor (%)", 
                min_value=50, max_value=100, 
                value=int(st.session_state.load_profile_dr['load_factor'] * 100),
                help="Average utilization as % of peak"
            ) / 100
            st.session_state.load_profile_dr['load_factor'] = load_factor
        
        # Calculate derived values
        peak_facility_mw = peak_it_mw * pue
        avg_facility_mw = peak_facility_mw * load_factor
        
        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Peak Facility Load", f"{peak_facility_mw:.1f} MW")
        col_m2.metric("Average Load", f"{avg_facility_mw:.1f} MW")
        col_m3.metric("Annual Energy", f"{avg_facility_mw * 8760 / 1000:.1f} GWh")
        
        # Load trajectory (simplified)
        st.markdown("#### Load Growth Trajectory")
        
        enable_growth = st.checkbox("Enable load growth over planning horizon", value=True)
        
        if enable_growth:
            growth_rate = st.slider(
                "Annual Load Growth (%)", 
                min_value=0, max_value=30, value=10,
                help="Year-over-year load growth rate"
            ) / 100
            
            years = list(range(2026, 2036))
            trajectory = {y: min(1.0 + growth_rate * i, 2.0) for i, y in enumerate(years)}
            
            # Show trajectory chart
            fig_growth = go.Figure()
            fig_growth.add_trace(go.Scatter(
                x=years,
                y=[peak_facility_mw * trajectory[y] for y in years],
                mode='lines+markers',
                name='Peak Load',
                line=dict(color='#1f77b4', width=3)
            ))
            fig_growth.update_layout(
                title="Load Growth Trajectory",
                xaxis_title="Year",
                yaxis_title="Peak Facility Load (MW)",
                height=300
            )
            st.plotly_chart(fig_growth, use_container_width=True)
            
            st.session_state.load_profile_dr['load_trajectory'] = trajectory
        else:
            st.session_state.load_profile_dr['load_trajectory'] = {y: 1.0 for y in range(2026, 2036)}
    
    # =========================================================================
    # TAB 2: WORKLOAD MIX
    # =========================================================================
    with tab2:
        st.markdown("#### AI Workload Composition with DR Flexibility")
        
        st.info("""
        **Research Finding:** Different AI workloads have different flexibility characteristics.
        - **Pre-training:** 20-40% flexible, 15+ min response, checkpoint required
        - **Fine-tuning:** 40-60% flexible, 5+ min response
        - **Batch inference:** 80-100% flexible, <1 min response
        - **Real-time inference:** 0-10% flexible (SLA protected)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            pre_training_pct = st.slider(
                "Pre-Training (%)", 0, 100, 
                st.session_state.load_profile_dr['workload_mix']['pre_training'],
                help="Large model training - most interruptible but slow to stop"
            )
            fine_tuning_pct = st.slider(
                "Fine-Tuning (%)", 0, 100,
                st.session_state.load_profile_dr['workload_mix']['fine_tuning'],
                help="Model customization - medium flexibility"
            )
            batch_inference_pct = st.slider(
                "Batch Inference (%)", 0, 100,
                st.session_state.load_profile_dr['workload_mix']['batch_inference'],
                help="Offline predictions - highly flexible"
            )
        
        with col2:
            realtime_inference_pct = st.slider(
                "Real-Time Inference (%)", 0, 100,
                st.session_state.load_profile_dr['workload_mix']['realtime_inference'],
                help="Production API serving - lowest flexibility"
            )
            rl_training_pct = st.slider(
                "RL Training (%)", 0, 100,
                st.session_state.load_profile_dr['workload_mix']['rl_training'],
                help="Reinforcement learning - medium-high flexibility"
            )
            cloud_hpc_pct = st.slider(
                "Cloud HPC (%)", 0, 100,
                st.session_state.load_profile_dr['workload_mix']['cloud_hpc'],
                help="Traditional HPC workloads - low-medium flexibility"
            )
        
        # Validate sum = 100%
        total_pct = (pre_training_pct + fine_tuning_pct + batch_inference_pct + 
                     realtime_inference_pct + rl_training_pct + cloud_hpc_pct)
        
        if total_pct != 100:
            st.error(f"⚠️ Workload percentages must sum to 100%. Current: {total_pct}%")
        else:
            st.success(f"✅ Workload mix: {total_pct}%")
        
        # Update session state
        st.session_state.load_profile_dr['workload_mix'] = {
            'pre_training': pre_training_pct,
            'fine_tuning': fine_tuning_pct,
            'batch_inference': batch_inference_pct,
            'realtime_inference': realtime_inference_pct,
            'rl_training': rl_training_pct,
            'cloud_hpc': cloud_hpc_pct,
        }
        
        # Workload mix pie chart
        if total_pct == 100:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Pre-Training', 'Fine-Tuning', 'Batch Inference', 
                       'Real-Time Inference', 'RL Training', 'Cloud HPC'],
                values=[pre_training_pct, fine_tuning_pct, batch_inference_pct, 
                       realtime_inference_pct, rl_training_pct, cloud_hpc_pct],
                hole=0.4,
                marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            )])
            fig_pie.update_layout(title="Workload Composition", height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # =========================================================================
    # TAB 3: COOLING FLEXIBILITY
    # =========================================================================
    with tab3:
        st.markdown("#### Cooling System Flexibility")
        
        st.info("""
        **Research Finding:** Cooling can provide 20-30% flexibility:
        - Thermal time constant: 15-60 minutes
        - Setpoint increase: 2-5°C before equipment limits
        - Power reduction: 3-5% per degree Celsius
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_setpoint_increase = st.slider(
                "Max Setpoint Increase (°C)", 1, 5, 3,
                help="Maximum temperature rise allowed"
            )
            
            power_per_degree = st.slider(
                "Power Reduction per °C (%)", 1, 8, 4,
                help="% of cooling load saved per degree"
            )
        
        with col2:
            thermal_constant = st.slider(
                "Thermal Time Constant (min)", 10, 60, 30,
                help="Time to reach new equilibrium"
            )
            
            min_chiller_time = st.slider(
                "Min Chiller On Time (min)", 10, 30, 20,
                help="Minimum runtime before cycling"
            )
        
        # Calculate cooling flexibility
        cooling_fraction = (pue - 1) / pue
        max_cooling_flex = max_setpoint_increase * power_per_degree / 100
        cooling_flex_facility = cooling_fraction * max_cooling_flex
        
        st.session_state.load_profile_dr['cooling_flex'] = max_cooling_flex
        st.session_state.load_profile_dr['thermal_constant_min'] = thermal_constant
        
        st.markdown("---")
        col_c1, col_c2, col_c3 = st.columns(3)
        col_c1.metric("Cooling Load Fraction", f"{cooling_fraction*100:.1f}%")
        col_c2.metric("Cooling Flexibility", f"{max_cooling_flex*100:.1f}%")
        col_c3.metric("Facility Contribution", f"{cooling_flex_facility*100:.1f}%")
    
    # =========================================================================
    # TAB 4: DR ECONOMICS
    # =========================================================================
    with tab4:
        st.markdown("#### Demand Response Economics")
        
        # Generate load profile only if workload mix is valid
        if total_pct == 100:
            # Generate flexibility profile
            load_data = generate_load_profile_with_flexibility(
                peak_it_load_mw=peak_it_mw,
                pue=pue,
                load_factor=load_factor,
                workload_mix=st.session_state.load_profile_dr['workload_mix'],
                cooling_flex_pct=st.session_state.load_profile_dr['cooling_flex']
            )
            
            # Summary metrics
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            flex_summary = load_data['summary']
            col_s1.metric("Avg Facility Load", f"{flex_summary['avg_load_mw']:.1f} MW")
            col_s2.metric("Avg Flexible Load", f"{flex_summary['avg_flexibility_mw']:.1f} MW")
            col_s3.metric("Flexibility %", f"{flex_summary['avg_flexibility_pct']:.1f}%")
            col_s4.metric("Firm Load", 
                         f"{flex_summary['avg_load_mw'] - flex_summary['avg_flexibility_mw']:.1f} MW")
            
            st.markdown("---")
            st.markdown("#### DR Product Analysis")
            
            # Analyze each DR product
            dr_results = []
            for product in ['spinning_reserve', 'non_spinning_reserve', 'economic_dr', 'emergency_dr']:
                result = calculate_dr_economics(load_data, product)
                dr_results.append({
                    'Product': product.replace('_', ' ').title(),
                    'Response Time': f"{result['response_time_min']} min",
                    'Available MW': f"{result['guaranteed_capacity_mw']:.1f}",
                    'Capacity Payment': f"${result['capacity_payment_annual']:,.0f}",
                    'Total Revenue': f"${result['total_annual_revenue']:,.0f}",
                    '$/MW-year': f"${result['revenue_per_mw_year']:,.0f}",
                })
            
            df_dr = pd.DataFrame(dr_results)
            st.dataframe(df_dr, use_container_width=True, hide_index=True)
            
            # Revenue chart
            fig_revenue = go.Figure()
            fig_revenue.add_trace(go.Bar(
                x=[r['Product'] for r in dr_results],
                y=[float(r['Total Revenue'].replace('$', '').replace(',', '')) for r in dr_results],
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            ))
            fig_revenue.update_layout(
                title="Annual DR Revenue by Product",
                xaxis_title="DR Product",
                yaxis_title="Annual Revenue ($)",
                height=350
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### Flexibility Profile (First Week)")
            
            # Plot first 168 hours
            hours = np.arange(168)
            
            fig = go.Figure()
            
            # Stack: Firm load on bottom, flexibility on top
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['firm_load_mw'][:168],
                name='Firm Load', fill='tozeroy',
                line=dict(color='#1f77b4', width=0),
                fillcolor='rgba(31, 119, 180, 0.7)'
            ))
            
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['total_load_mw'][:168],
                name='Total Load', fill='tonexty',
                line=dict(color='#2ca02c', width=0),
                fillcolor='rgba(44, 160, 44, 0.5)'
            ))
            
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['total_flex_mw'][:168],
                name='Flexible Load', 
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ))
            
            fig.update_layout(
                title="Load Profile with Flexibility Breakdown",
                xaxis_title="Hour of Week",
                yaxis_title="Power (MW)",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Store load data in session state
            st.session_state.load_profile_dr['load_data'] = load_data
        
        else:
            st.warning("⚠️ Please fix workload mix to sum to 100% before viewing DR economics.")
    
    # =========================================================================
    # SAVE CONFIGURATION
    # =========================================================================
    st.markdown("---")
    
    col_save1, col_save2 = st.columns([3, 1])
    
    with col_save2:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            if total_pct != 100:
                st.error("Cannot save - workload mix must sum to 100%")
            else:
                # Save complete configuration for optimizer
                st.success("✅ Load profile with DR saved!")
                
                # Update main session state if needed
                if 'current_config' in st.session_state:
                    st.session_state.current_config['load_profile_dr'] = st.session_state.load_profile_dr
    
    with col_save1:
        if total_pct == 100 and 'load_data' in st.session_state.load_profile_dr:
            with st.expander("📋 View Configuration Summary"):
                summary = {
                    'Peak IT Load (MW)': peak_it_mw,
                    'PUE': pue,
                    'Peak Facility Load (MW)': peak_facility_mw,
                    'Total Flexibility (%)': f"{flex_summary['avg_flexibility_pct']:.1f}%",
                    'Flexible MW': f"{flex_summary['avg_flexibility_mw']:.1f}",
                }
                st.json(summary)


if __name__ == "__main__":
    render()
