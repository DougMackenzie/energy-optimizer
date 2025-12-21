"""
Optimizer Page
Configure constraints and objectives, run optimization
"""

import streamlit as st
from config.settings import DEFAULT_CONSTRAINTS


def render():
    st.markdown("### 🎯 Optimizer")
    
    col_header, col_actions = st.columns([3, 1])
    with col_actions:
        if st.button("⚡ Run Optimization", type="primary", use_container_width=True):
            with st.spinner("Running optimization..."):
                import time
                time.sleep(2)  # Simulate optimization
                st.session_state.current_page = 'results'
                st.rerun()
    
    # Hard Constraints Section
    with st.expander("🔒 HARD CONSTRAINTS (Must Satisfy - Pass/Fail)", expanded=True):
        st.caption("Scenarios that violate these constraints are marked infeasible")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.number_input("Min Capacity (MW)", value=200, min_value=10, max_value=2000)
            st.number_input("Min Ramp Rate (MW/s)", value=1.0, min_value=0.1, max_value=10.0, step=0.1)
        
        with col2:
            st.number_input("Reserve Margin (%)", value=10, min_value=0, max_value=50)
            st.number_input("Freq Tolerance (Hz)", value=0.5, min_value=0.1, max_value=2.0, step=0.1)
        
        with col3:
            st.selectbox("N-1 Contingency", ["Required", "N-2", "Not Required"])
            st.number_input("Voltage Tolerance (%)", value=5, min_value=1, max_value=15)
        
        with col4:
            st.number_input("Min Availability (%)", value=99.9, min_value=95.0, max_value=99.999, step=0.1)
            st.number_input("Max Time-to-Power (mo)", value=24, min_value=6, max_value=60)
        
        st.markdown("---")
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.number_input("Max NOx (tpy)", value=99, min_value=0, max_value=500, 
                           help="99 tpy = minor source threshold")
        with col6:
            st.number_input("Max LCOE ($/MWh)", value=85, min_value=30, max_value=200)
        with col7:
            st.number_input("Max CAPEX ($M)", value=400, min_value=50, max_value=2000)
        with col8:
            st.number_input("Site Limit (MW)", value=300, min_value=50, max_value=2000)
    
    # Objectives Section
    with st.expander("🎯 OPTIMIZATION OBJECTIVES", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.selectbox(
                "Primary Objective (Minimize)",
                ["Time-to-Power (months)", "LCOE ($/MWh)", "Total CAPEX ($)", "Carbon Intensity (kg CO₂/MWh)"]
            )
        
        with col2:
            st.selectbox(
                "Method",
                ["ε-Constraint (Pareto frontier)", "Weighted Sum", "Lexicographic"]
            )
        
        st.info(
            "**ε-Constraint Method:** Optimize primary objective while treating secondary objectives "
            "as bounded constraints. Vary bounds to trace Pareto frontier showing optimal tradeoffs."
        )
    
    # Solver Settings
    with st.expander("⚙️ Solver Settings"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.selectbox("Solver", ["CBC (Free)", "Gurobi (Commercial)", "GLPK"])
        with col2:
            st.number_input("Scenarios", value=100, min_value=10, max_value=1000)
        with col3:
            st.number_input("Pareto Points", value=15, min_value=5, max_value=50)
        with col4:
            st.number_input("MIP Gap (%)", value=0.1, min_value=0.01, max_value=5.0, step=0.1)
    
    # Summary Panel
    st.markdown("---")
    st.markdown("#### Configuration Summary")
    
    cols = st.columns(6)
    summary = [
        ("Target Capacity", "200 MW"),
        ("With Reserve", "220 MW"),
        ("Equipment Types", "4 selected"),
        ("Min Availability", "99.9%"),
        ("Max Time", "24 mo"),
        ("Max LCOE", "$85/MWh"),
    ]
    
    for i, (label, value) in enumerate(summary):
        with cols[i]:
            st.metric(label, value)


if __name__ == "__main__":
    render()
