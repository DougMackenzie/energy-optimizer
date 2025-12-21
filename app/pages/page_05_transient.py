"""
Transient Analysis Page
Power quality, transients, and ramp rate analysis
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def render():
    st.markdown("### ⚡ Transient & Power Quality Analysis")
    st.caption("Analyze transient events, ramp rates, and power quality requirements")
    
    # Check if configuration exists
    if 'current_config' not in st.session_state:
        st.warning("⚠️ No configuration loaded. Please configure equipment first.")
        
        if st.button("📋 Go to Equipment Library", type="primary"):
            st.session_state.current_page = 'equipment_library'
            st.rerun()
        
        return
    
    config = st.session_state.current_config
    site = config['site']
    constraints = config.get('constraints', {})
    
    total_load = site.get('Total_Facility_MW', 200)
    
    st.markdown("#### ⚡ Transient Event Scenarios")
    
    # Define transient scenarios
    st.info("""
    **Common Transient Events for Datacenters:**
    - Server startup/shutdown (gradual)
    - Workload migration (step change)
    - Cooling system cycling (periodic)
    - Grid disturbances (sudden)
    """)
    
    # Transient parameters
    col_trans1, col_trans2 = st.columns(2)
    
    with col_trans1:
        st.markdown("##### Transient Event Configuration")
        
        event_type = st.selectbox("Event Type", [
            "Workload Step Change",
            "Server Startup Ramp",
            "Cooling System Cycle",
            "Grid Disturbance"
        ])
        
        if event_type == "Workload Step Change":
            step_size = st.slider("Step Size (% of load)", 5, 50, 20)
            duration_sec = st.slider("Duration (seconds)", 1, 60, 10)
        elif event_type == "Server Startup Ramp":
            ramp_size = st.slider("Ramp Size (% of load)", 10, 100, 50)
            ramp_time_min = st.slider("Ramp Time (minutes)", 1, 30, 10)
        else:
            step_size = 15
            duration_sec = 5
    
    with col_trans2:
        st.markdown("##### Site Requirements")
        
        max_transient = constraints.get('Max_Transient_pct', 30)
        st.metric("Max Allowed Transient", f"{max_transient}%")
        st.caption("From site constraints")
        
        max_ramp = constraints.get('Max_Ramp_MW_min', 50)
        st.metric("Max Ramp Rate", f"{max_ramp} MW/min")
        st.caption("Equipment capability")
    
    # Simulate transient event
    st.markdown("---")
    st.markdown("#### 📊 Transient Simulation")
    
    if st.button("🔬 Run Transient Analysis", type="primary"):
        with st.spinner("Simulating transient event..."):
            
            # Generate transient profile
            time_points = 200  # 200 points for smooth curve
            time = np.linspace(0, 60, time_points)  # 60 seconds
            
            # Base load
            base_load = total_load * 0.75  # 75% nominal load
            load_profile = np.ones(time_points) * base_load
            
            # Add transient event at t=10s
            event_start = int(time_points * 10/60)
            
            if event_type == "Workload Step Change":
                step_mw = total_load * (step_size / 100)
                # Step up
                load_profile[event_start:event_start+int(duration_sec*time_points/60)] += step_mw
                # Step down
                end_point = event_start + int((duration_sec + 10) * time_points/60)
                if end_point < time_points:
                    load_profile[end_point:] -= step_mw
            else:
                # Gradual ramp
                ramp_points = int(ramp_time_min * 60 * time_points / 60)
                ramp = np.linspace(0, total_load * (ramp_size/100), min(ramp_points, time_points - event_start))
                load_profile[event_start:event_start+len(ramp)] += ramp
            
            # Calculate required BESS response
            load_delta = np.diff(load_profile, prepend=load_profile[0])
            max_delta = np.max(np.abs(load_delta))
            max_delta_mw = max_delta * (time_points / 60)  # Convert to MW
            
            # Store results
            st.session_state.transient_results = {
                'time': time,
                'load': load_profile,
                'delta': load_delta,
                'max_delta_mw': max_delta_mw,
                'event_type': event_type
            }
            
            st.success("✅ Transient simulation complete!")
            st.rerun()
    
    # Display results
    if 'transient_results' in st.session_state:
        results = st.session_state.transient_results
        
        st.markdown("---")
        st.markdown("#### 📈 Transient Response")
        
        # Metrics
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        
        with col_res1:
            max_load = np.max(results['load'])
            st.metric("Peak Load", f"{max_load:.1f} MW")
        
        with col_res2:
            min_load = np.min(results['load'])
            st.metric("Min Load", f"{min_load:.1f} MW")
        
        with col_res3:
            max_swing = max_load - min_load
            swing_pct = (max_swing / total_load) * 100
            st.metric("Max Swing", f"{max_swing:.1f} MW")
            st.caption(f"{swing_pct:.1f}% of capacity")
        
        with col_res4:
            max_delta = results['max_delta_mw']
            st.metric("Max Ramp Rate", f"{max_delta:.1f} MW/s")
            st.caption(f"{max_delta * 60:.0f} MW/min")
        
        # Load profile chart
        fig_load = go.Figure()
        fig_load.add_trace(go.Scatter(
            x=results['time'],
            y=results['load'],
            mode='lines',
            name='Load Demand',
            line=dict(color='blue', width=3)
        ))
        
        fig_load.add_hline(y=total_load, line_dash="dash", line_color="red",
                          annotation_text="Peak Capacity")
        
        fig_load.update_layout(
            title=f"Transient Event: {results['event_type']}",
            xaxis_title="Time (seconds)",
            yaxis_title="Load (MW)",
            height=400
        )
        
        st.plotly_chart(fig_load, use_container_width=True)
        
        # Rate of change chart
        fig_roc = go.Figure()
        fig_roc.add_trace(go.Scatter(
            x=results['time'],
            y=results['delta'] * (len(results['time']) / 60),  # Convert to MW/s
            mode='lines',
            name='Rate of Change',
            line=dict(color='orange', width=2),
            fill='tozeroy'
        ))
        
        fig_roc.update_layout(
            title="Load Rate of Change",
            xaxis_title="Time (seconds)",
            yaxis_title="dP/dt (MW/s)",
            height=300
        )
        
        st.plotly_chart(fig_roc, use_container_width=True)
        
        # BESS requirement analysis
        st.markdown("---")
        st.markdown("#### 🔋 BESS Sizing for Transient Response")
        
        # Check if BESS exists in config
        if 'optimization_result' in st.session_state:
            result = st.session_state.optimization_result
            bess_power = sum(e.get('power_mw', 0) for e in result['equipment_config'].get('bess', []))
            bess_energy = sum(e.get('energy_mwh', 0) for e in result['equipment_config'].get('bess', []))
        else:
            bess_power = 0
            bess_energy = 0
        
        col_bess1, col_bess2, col_bess3 = st.columns(3)
        
        with col_bess1:
            required_power = max_swing
            st.metric("Required BESS Power", f"{required_power:.1f} MW")
            st.caption("To handle max swing")
            
            if bess_power >= required_power:
                st.success(f"✅ Configured: {bess_power:.1f} MW")
            else:
                st.error(f"❌ Configured: {bess_power:.1f} MW (insufficient)")
        
        with col_bess2:
            # Energy for 5-minute bridging
            required_energy = max_swing * (5/60)  # 5 minutes
            st.metric("Required BESS Energy", f"{required_energy:.1f} MWh")
            st.caption("5-min bridging")
            
            if bess_energy >= required_energy:
                st.success(f"✅ Configured: {bess_energy:.1f} MWh")
            else:
                st.warning(f"⚠️ Configured: {bess_energy:.1f} MWh")
        
        with col_bess3:
            # Response time
            response_ms = 16  # Typical BESS response (1 cycle = 16.67ms)
            st.metric("BESS Response Time", f"{response_ms} ms")
            st.caption("< 1 AC cycle")
        
        # Recommendations
        st.markdown("---")
        st.markdown("#### 💡 Transient Mitigation Recommendations")
        
        if max_swing > total_load * 0.3:
            st.warning(f"""
            **High Transient Risk ({swing_pct:.0f}% swing):**
            - Increase BESS capacity to {required_power * 1.2:.0f} MW
            - Consider multiple smaller BESS units for redundancy
            - Implement load shedding for extreme events
            - Configure workload scheduler to limit ramp rates
            """)
        elif max_swing > total_load * 0.15:
            st.info(f"""
            **Moderate Transient Risk ({swing_pct:.0f}% swing):**
            - Current BESS sizing appears adequate
            - Monitor actual transient events
            - Consider 10-20% reserve margin
            """)
        else:
            st.success(f"""
            **Low Transient Risk ({swing_pct:.0f}% swing):**
            - Equipment well-sized for anticipated transients
            - BESS provides good margin
            - Standard operating procedures sufficient
            """)


if __name__ == "__main__":
    render()
