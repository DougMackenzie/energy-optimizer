"""
Problem 3: Land Development
Objective: Maximize firm power by flexibility scenario
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

from config.settings import PROBLEM_STATEMENTS, COLORS, CONSTRAINT_DEFAULTS


def render():
    """Render Problem 3: Land Development page"""
    
    prob = PROBLEM_STATEMENTS[3]
    
    st.markdown(f"### {prob['icon']} Problem 3: {prob['name']}")
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
    
    col_input, col_results = st.columns([1, 2])
    
    with col_input:
        st.markdown("#### 📋 Site Characteristics")
        
        with st.expander("🗺️ Site Parameters", expanded=True):
            land_acres = st.number_input("Available Land (acres)", 50, 5000, 500)
            gas_mcf = st.number_input("Gas Pipeline (MCF/day)", 5000, 500000, 100000)
            grid_proximity = st.selectbox("345kV Proximity", ["<1 mile", "1-5 miles", "5-10 miles", ">10 miles"])
            nox_limit = st.number_input("NOx Limit (tpy)", 25, 500, 100)
        
        with st.expander("🔄 Flexibility Scenarios", expanded=True):
            st.markdown("**Customer Flexibility Assumptions**")
            flex_scenarios = st.multiselect(
                "Scenarios to Analyze",
                options=[0, 15, 30, 50],
                default=[0, 15, 30, 50],
                format_func=lambda x: f"{x}% Flexibility"
            )
            
            st.info("""
            **Flexibility** = % of load that can be curtailed for grid services.
            Higher flexibility unlocks more capacity from same equipment.
            """)
        
        with st.expander("📊 Analysis Scope", expanded=False):
            target_load = st.number_input("Reference Load Target (MW)", 100, 2000, 600)
            pue = st.slider("PUE", 1.1, 1.5, 1.25, 0.05)
        
        st.markdown("---")
        
        run_phase1 = st.button("▶️ Analyze All Scenarios", type="primary", use_container_width=True)
        run_phase2 = st.button("🔒 Run Phase 2 (MILP)", disabled=True, use_container_width=True)
    
    with col_results:
        st.markdown("#### 📊 Power Potential Matrix")
        
        if run_phase1:
            with st.spinner("Analyzing flexibility scenarios..."):
                try:
                    from app.optimization.heuristic_optimizer import LandDevHeuristic
                    
                    load_trajectory = {2025: target_load * pue}
                    
                    optimizer = LandDevHeuristic(
                        site={},
                        load_trajectory=load_trajectory,
                        constraints={
                            'nox_tpy_annual': nox_limit,
                            'gas_supply_mcf_day': gas_mcf,
                            'land_area_acres': land_acres,
                        },
                        flexibility_scenarios=[f/100 for f in flex_scenarios],
                    )
                    
                    results = optimizer.optimize()
                    
                    # Store results
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    
                    st.session_state.optimization_results[3] = {
                        'scenarios': results,
                        'flex_scenarios': flex_scenarios,
                    }
                    st.session_state.phase_1_complete[3] = True
                    
                    st.success("✅ All scenarios analyzed")
                    
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
        
        result_data = st.session_state.get('optimization_results', {}).get(3)
        
        if result_data:
            scenarios = result_data['scenarios']
            
            # Build matrix
            matrix_data = []
            for flex_pct, result in scenarios.items():
                flex_display = int(flex_pct * 100)
                matrix_data.append({
                    'Flexibility': f"{flex_display}%",
                    'Max Load (MW)': result.objective_value,
                    'Firm Capacity (MW)': result.equipment_config.get('total_firm_mw', 0),
                    'LCOE ($/MWh)': result.lcoe,
                    'Binding Constraint': next(
                        (k for k, v in result.constraint_status.items() if v.get('binding')),
                        'None'
                    ).replace('_', ' ').title(),
                })
            
            matrix_df = pd.DataFrame(matrix_data)
            
            # Highlight table
            st.dataframe(matrix_df, use_container_width=True, hide_index=True)
            
            # Visual comparison
            st.markdown("##### Capacity Unlocked by Flexibility")
            
            fig = go.Figure()
            
            loads = [m['Max Load (MW)'] for m in matrix_data]
            firms = [m['Firm Capacity (MW)'] for m in matrix_data]
            flex_labels = [m['Flexibility'] for m in matrix_data]
            
            fig.add_trace(go.Bar(
                x=flex_labels, y=firms,
                name='Firm Capacity', marker_color='#4299e1'
            ))
            
            fig.add_trace(go.Bar(
                x=flex_labels, y=[l - f for l, f in zip(loads, firms)],
                name='Flexibility Bonus', marker_color='#48bb78'
            ))
            
            fig.update_layout(
                barmode='stack',
                height=350,
                yaxis_title='MW',
                xaxis_title='Customer Flexibility',
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Key insight
            if len(loads) > 1:
                base_load = loads[0]
                max_load = max(loads)
                uplift = (max_load - base_load) / base_load * 100 if base_load > 0 else 0
                
                st.markdown(f"""
                <div style="background: #e6fffa; padding: 16px; border-radius: 8px; margin-top: 16px;">
                    <strong>Key Insight:</strong> Increasing customer flexibility from 0% to {max(result_data['flex_scenarios'])}% 
                    unlocks <strong>{uplift:.0f}% more load capacity</strong> ({max_load - base_load:.0f} MW) 
                    from the same site constraints.
                </div>
                """, unsafe_allow_html=True)
            
            # Constraint analysis
            st.markdown("##### Binding Constraints by Scenario")
            
            constraint_summary = []
            for flex_pct, result in scenarios.items():
                for name, status in result.constraint_status.items():
                    if status.get('binding'):
                        constraint_summary.append({
                            'Flexibility': f"{int(flex_pct*100)}%",
                            'Constraint': name.replace('_', ' ').title(),
                            'Utilization': f"{status.get('value', 0) / status.get('limit', 1) * 100:.0f}%",
                        })
            
            if constraint_summary:
                const_df = pd.DataFrame(constraint_summary)
                st.dataframe(const_df, use_container_width=True, hide_index=True)
        
        else:
            st.info("👈 Configure site parameters and click **Analyze All Scenarios**")
            
            st.markdown("""
            ##### What This Analysis Shows
            
            For land developers and site evaluators, this problem answers:
            - Maximum power capacity available on a given site
            - How customer flexibility assumptions affect capacity
            - Which constraints are binding (NOx, gas, land)
            - Shadow prices for constraint relaxation
            """)


if __name__ == "__main__":
    render()
