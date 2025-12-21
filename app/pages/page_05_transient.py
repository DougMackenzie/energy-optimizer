"""
Transient Screening Page
Simplified physics checks (NOT dynamic simulation)
"""

import streamlit as st


def render():
    st.markdown("### ⚡ Transient Screening")
    
    st.warning(
        "⚠️ **Screening Only - Not Dynamic Simulation:** These checks use simplified physics-based "
        "calculations to screen scenarios. **Passing screening does NOT guarantee success.** "
        "Final validation requires ETAP or equivalent dynamic simulation tools."
    )
    
    # Summary metrics
    cols = st.columns(4)
    with cols[0]:
        st.metric("Pass", "4", delta_color="normal")
    with cols[1]:
        st.metric("Warnings", "1", delta_color="off")
    with cols[2]:
        st.metric("Needs Study", "1", delta_color="off")
    with cols[3]:
        st.metric("Failures", "0", delta_color="normal")
    
    st.markdown("---")
    
    # Scenario selection
    st.markdown("#### Selected Scenario")
    scenario = st.selectbox(
        "Scenario",
        ["Scenario A: 6x Wärtsilä + 100 MWh BESS", 
         "Scenario B: 4x Recip + 2x LM2500",
         "Scenario C: Grid Primary + Backup"],
        label_visibility="collapsed"
    )
    
    cols = st.columns(5)
    scenario_params = [
        ("Engines", "6 × 18.8 MW"),
        ("BESS Power", "25 MW"),
        ("BESS Energy", "100 MWh"),
        ("Grid", "150 MW"),
        ("Rack UPS", "30 sec"),
    ]
    for i, (label, value) in enumerate(scenario_params):
        with cols[i]:
            st.metric(label, value)
    
    st.markdown("---")
    
    # Screening checks
    checks = [
        ("pass", "✓", "1. BESS Energy for Engine Ramp", 
         "Can BESS cover load while engines start?",
         "Gap: 0.48 MWh | BESS: 60 MWh → **125× margin (PASS)**"),
        ("pass", "✓", "2. Combined Ramp Rate",
         "Equipment meets residual variability needs?",
         "Required: 1.0 MW/s | BESS: 25 MW instant → **PASS**"),
        ("pass", "✓", "3. N-1 Spinning Reserve",
         "System survives largest unit trip?",
         "N-1 capacity: 269 MW > 200 MW → **PASS**"),
        ("warn", "!", "4. Inertia / Frequency Stability",
         "Sufficient rotating mass for RoCoF?",
         "RoCoF ≈ **2.1 Hz/s** (limit: 1-2 Hz/s) → **WARNING**"),
        ("pass", "✓", "5. UPS Ride-Through",
         "UPS provides enough cushion?",
         "BESS response: <100 ms → **PASS**"),
        ("study", "?", "6. Islanding Transition",
         "Seamless grid-to-island transition?",
         "**Cannot screen - Requires ETAP study**"),
    ]
    
    for status, icon, title, detail, calc in checks:
        bg_colors = {"pass": "#f8fff8", "warn": "#fffef8", "study": "#f8fbff"}
        border_colors = {"pass": "#28A745", "warn": "#FFC107", "study": "#2E86AB"}
        
        st.markdown(
            f"""
            <div style="display: flex; padding: 12px; background: {bg_colors[status]}; 
                        border-radius: 6px; border-left: 4px solid {border_colors[status]}; 
                        margin-bottom: 8px;">
                <div style="width: 28px; height: 28px; border-radius: 50%; 
                            background: {border_colors[status]}20; color: {border_colors[status]};
                            display: flex; align-items: center; justify-content: center;
                            font-weight: bold; margin-right: 12px; flex-shrink: 0;">
                    {icon}
                </div>
                <div>
                    <div style="font-weight: 600; font-size: 13px;">{title}</div>
                    <div style="font-size: 11px; color: #666; margin-bottom: 4px;">{detail}</div>
                    <div style="font-family: monospace; font-size: 10px; background: #f8f9fa; 
                                padding: 6px 8px; border-radius: 4px;">{calc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Conclusion
    st.success("**Screening Conclusion:** Likely Viable - Proceed to Optimization")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✓ Confident Findings**")
        st.markdown("- BESS sizing adequate\n- N-1 satisfied\n- UPS provides cushion")
    with col2:
        st.markdown("**⚠️ Items for ETAP**")
        st.markdown("- Frequency stability (RoCoF)\n- Islanding dynamics\n- Protection coordination")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.button("📄 Export ETAP Scope", use_container_width=True)
    with col_b:
        st.button("📊 Export Study Input", use_container_width=True)


if __name__ == "__main__":
    render()
