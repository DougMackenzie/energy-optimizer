"""
Load Composer Page
Define facility load profiles and workload characteristics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render():
    st.markdown("### 📈 Load Composer")
    
    st.info("""
    **Define your facility's energy demand profile**
    
    Configure IT workload mix, PUE, and load growth trajectory to model realistic power requirements.
    """)
    
    # Initialize session state for load profile
    if 'load_profile' not in st.session_state:
        st.session_state.load_profile = {
            'it_capacity_mw': 100,
            'pue': 1.25,
            'workload_mix': {
                'Training': 40,
                'Inference': 30,
                'HPC': 20,
                'Enterprise': 10
            },
            'load_factor': 75,
            'growth_trajectory': []
        }
    
    # Workload Configuration
    st.markdown("#### 🖥️ IT Workload Configuration")
    
    col_wl1, col_wl2 = st.columns([3, 2])
    
    with col_wl1:
        st.markdown("##### Workload Mix (%)")
        st.caption("Define the percentage split of your AI/HPC workload types")
        
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        
        with col_w1:
            training_pct = st.slider("🎯 Training", 0, 100, 
                                     st.session_state.load_profile['workload_mix']['Training'],
                                     help="AI model training workloads")
        
        with col_w2:
            inference_pct = st.slider("⚡ Inference", 0, 100,
                                     st.session_state.load_profile['workload_mix']['Inference'],
                                     help="AI inference/serving workloads")
        
        with col_w3:
            hpc_pct = st.slider("🔬 HPC", 0, 100,
                               st.session_state.load_profile['workload_mix']['HPC'],
                               help="High-performance computing")
        
        with col_w4:
            enterprise_pct = st.slider("💼 Enterprise", 0, 100,
                                      st.session_state.load_profile['workload_mix']['Enterprise'],
                                      help="Traditional enterprise workloads")
        
        # Validate mix adds to 100%
        total_pct = training_pct + inference_pct + hpc_pct + enterprise_pct
        if total_pct != 100:
            st.warning(f"⚠️ Workload mix totals {total_pct}% (should be 100%)")
        else:
            st.success(f"✅ Workload mix totals 100%")
        
        # Update session state
        st.session_state.load_profile['workload_mix'] = {
            'Training': training_pct,
            'Inference': inference_pct,
            'HPC': hpc_pct,
            'Enterprise': enterprise_pct
        }
    
    with col_wl2:
        st.markdown("##### Workload Characteristics")
        
        # Show typical load factors by workload type
        workload_chars = {
            'Training': {'Load Factor': '85-95%', 'Volatility': 'Low', 'Predictability': 'High'},
            'Inference': {'Load Factor': '70-90%', 'Volatility': 'Medium', 'Predictability': 'Medium'},
            'HPC': {'Load Factor': '75-95%', 'Volatility': 'Low', 'Predictability': 'High'},
            'Enterprise': {'Load Factor': '40-70%', 'Volatility': 'High', 'Predictability': 'Medium'}
        }
        
        df_chars = pd.DataFrame(workload_chars).T
        st.dataframe(df_chars, use_container_width=True)
    
    # Facility Parameters
    st.markdown("---")
    st.markdown("#### ⚙️ Facility Parameters")
    
    col_fac1, col_fac2, col_fac3, col_fac4 = st.columns(4)
    
    with col_fac1:
        it_capacity = st.number_input("IT Capacity (MW)", 
                                     min_value=1.0, max_value=1000.0, 
                                     value=float(st.session_state.load_profile['it_capacity_mw']),
                                     step=10.0,
                                     help="Nameplate IT capacity")
        st.session_state.load_profile['it_capacity_mw'] = it_capacity
    
    with col_fac2:
        pue = st.number_input("Design PUE",
                             min_value=1.0, max_value=3.0,
                             value=float(st.session_state.load_profile['pue']),
                             step=0.01,
                             help="Power Usage Effectiveness")
        st.session_state.load_profile['pue'] = pue
    
    with col_fac3:
        total_facility = it_capacity * pue
        st.metric("Total Facility Load", f"{total_facility:.1f} MW")
        st.caption("IT Capacity × PUE")
    
    with col_fac4:
        load_factor = st.slider("Avg Load Factor (%)",
                               min_value=0, max_value=100,
                               value=int(st.session_state.load_profile['load_factor']),
                               help="Average % of capacity utilized")
        st.session_state.load_profile['load_factor'] = load_factor
    
    # Load Growth Trajectory
    st.markdown("---")
    st.markdown("#### 📊 Load Growth Trajectory")
    
    col_growth1, col_growth2 = st.columns([2, 1])
    
    with col_growth1:
        st.caption("Define how capacity ramps up over time")
        
        # Simple 5-year trajectory
        years = list(range(2026, 2031))
        
        col_y1, col_y2, col_y3, col_y4, col_y5 = st.columns(5)
        
        with col_y1:
            y2026_mw = st.number_input("2026 (MW)", min_value=0.0, max_value=1000.0, value=50.0)
        with col_y2:
            y2027_mw = st.number_input("2027 (MW)", min_value=0.0, max_value=1000.0, value=100.0)
        with col_y3:
            y2028_mw = st.number_input("2028 (MW)", min_value=0.0, max_value=1000.0, value=150.0)
        with col_y4:
            y2029_mw = st.number_input("2029 (MW)", min_value=0.0, max_value=1000.0, value=180.0)
        with col_y5:
            y2030_mw = st.number_input("2030 (MW)", min_value=0.0, max_value=1000.0, value=200.0)
        
        trajectory = [y2026_mw, y2027_mw, y2028_mw, y2029_mw, y2030_mw]
        st.session_state.load_profile['growth_trajectory'] = list(zip(years, trajectory))
    
    with col_growth2:
        # Plot trajectory
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=trajectory, mode='lines+markers',
                                name='Load Growth', line=dict(color='#1f77b4', width=3)))
        fig.update_layout(
            title="Capacity Ramp",
            xaxis_title="Year",
            yaxis_title="MW",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Summary and Save
    st.markdown("---")
    st.markdown("#### 💾 Load Profile Summary")
    
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    
    with col_sum1:
        st.metric("Peak IT Load", f"{it_capacity} MW")
        st.metric("Peak Facility Load", f"{total_facility:.1f} MW")
    
    with col_sum2:
        avg_load = total_facility * (load_factor / 100)
        st.metric("Avg Facility Load", f"{avg_load:.1f} MW")
        st.caption(f"{load_factor}% load factor")
    
    with col_sum3:
        annual_energy = avg_load * 8760 / 1000
        st.metric("Annual Energy", f"{annual_energy:.0f} GWh")
        st.caption("At avg load")
    
    # Save button
    col_save1, col_save2 = st.columns([3, 1])
    
    with col_save1:
        st.info("Load profile will be used for dispatch simulation and energy analysis")
    
    with col_save2:
        if st.button("💾 Save Profile", type="primary", use_container_width=True):
            st.success("✅ Load profile saved to session state!")
            
            # If configuration exists, update it
            if 'current_config' in st.session_state:
                st.session_state.current_config['load_profile'] = st.session_state.load_profile


if __name__ == "__main__":
    render()
