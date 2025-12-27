"""
Problem 2: Brownfield Expansion
Objective: Maximize load within LCOE ceiling
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
    """Render Problem 2: Brownfield Expansion page"""
    
    prob = PROBLEM_STATEMENTS[2]
    
    st.markdown(f"### {prob['icon']} Problem 2: {prob['name']}")
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
        st.markdown("#### 📋 Configuration")
        
        with st.expander("🏭 Existing Facility", expanded=True):
            existing_load = st.number_input("Existing Load (MW)", 0, 1000, 200)
            existing_capacity = st.number_input("Existing Capacity (MW)", 0, 1500, 250)
            current_lcoe = st.number_input("Current Blended LCOE ($/MWh)", 30, 200, 75)
        
        with st.expander("📈 Expansion Target", expanded=True):
            lcoe_ceiling = st.number_input("LCOE Ceiling ($/MWh)", 40, 150, 85)
            max_expansion = st.number_input("Max Expansion Target (MW)", 50, 1000, 400)
            pue = st.slider("PUE", 1.1, 1.5, 1.25, 0.05)
        
        with st.expander("⚠️ Constraints", expanded=False):
            nox_limit = st.number_input("NOx Limit (tpy)", 10, 500, 100)
            gas_limit = st.number_input("Gas Supply (MCF/day)", 1000, 200000, 50000)
            land_limit = st.number_input("Land Available (acres)", 10, 2000, 300)
        
        st.markdown("---")
        
        run_phase1 = st.button("▶️ Run Phase 1 (Heuristic)", type="primary", use_container_width=True)
        run_phase2 = st.button("🔒 Run Phase 2 (MILP)", disabled=True, use_container_width=True)
    
    with col_results:
        st.markdown("#### 📊 Results")
        
        if run_phase1:
            with st.spinner("Finding maximum expansion capacity..."):
                try:
                    from app.optimization.heuristic_optimizer import BrownfieldHeuristic
                    
                    # Create load trajectory for expansion
                    total_target = existing_load + max_expansion
                    load_trajectory = {2025: total_target * pue}
                    
                    optimizer = BrownfieldHeuristic(
                        site={},
                        load_trajectory=load_trajectory,
                        constraints={
                            'nox_tpy_annual': nox_limit,
                            'gas_supply_mcf_day': gas_limit,
                            'land_area_acres': land_limit,
                        },
                        lcoe_ceiling=lcoe_ceiling,
                        existing_load_mw=existing_load * pue,
                    )
                    
                    result = optimizer.optimize()
                    
                    # Store results
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    
                    st.session_state.optimization_results[2] = {
                        'result': result,
                        'max_additional_load': result.dispatch_summary.get('max_additional_load_mw', 0),
                        'total_load': result.dispatch_summary.get('total_load_mw', 0),
                        'lcoe': result.lcoe,
                        'capex': result.capex_total,
                        'equipment': result.equipment_config,
                        'feasible': result.feasible,
                    }
                    st.session_state.phase_1_complete[2] = True
                    
                    st.success(f"✅ Phase 1 complete in {result.solve_time_seconds:.1f} seconds")
                    
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")
        
        result_data = st.session_state.get('optimization_results', {}).get(2)
        
        if result_data:
            # Key finding
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ebf8ff 0%, #e6fffa 100%); 
                        padding: 24px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 14px; color: #4a5568; margin-bottom: 8px;">
                    Maximum Additional Load Within ${lcoe_ceiling}/MWh Ceiling
                </div>
                <div style="font-size: 48px; font-weight: 700; color: #2c5282;">
                    {result_data['max_additional_load']:.0f} MW
                </div>
                <div style="font-size: 14px; color: #718096; margin-top: 8px;">
                    Total: {result_data['total_load']:.0f} MW at ${result_data['lcoe']:.1f}/MWh
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Existing Load", f"{existing_load} MW")
            with col2:
                st.metric("Max Addition", f"+{result_data['max_additional_load']:.0f} MW")
            with col3:
                st.metric("Blended LCOE", f"${result_data['lcoe']:.1f}/MWh")
            with col4:
                st.metric("Expansion CAPEX", f"${result_data['capex']/1e6:.0f}M")
            
            # Sensitivity chart
            st.markdown("##### LCOE Ceiling Sensitivity")
            
            # Run sensitivity analysis
            sensitivity_data = []
            for ceiling in [60, 70, 80, 90, 100, 110, 120]:
                # Simplified: linear relationship approximation
                if ceiling >= lcoe_ceiling:
                    max_load = result_data['max_additional_load'] * (1 + (ceiling - lcoe_ceiling) * 0.01)
                else:
                    max_load = result_data['max_additional_load'] * (ceiling / lcoe_ceiling)
                sensitivity_data.append({'LCOE Ceiling ($/MWh)': ceiling, 'Max Additional Load (MW)': max_load})
            
            sens_df = pd.DataFrame(sensitivity_data)
            
            fig = px.line(sens_df, x='LCOE Ceiling ($/MWh)', y='Max Additional Load (MW)',
                         markers=True, line_shape='linear')
            fig.add_vline(x=lcoe_ceiling, line_dash="dash", line_color="red",
                         annotation_text=f"Current: ${lcoe_ceiling}")
            fig.update_layout(height=300, margin=dict(t=30, b=30))
            st.plotly_chart(fig, use_container_width=True)
            
            # Equipment summary
            st.markdown("##### Required New Equipment")
            equip = result_data['equipment']
            equip_df = pd.DataFrame({
                'Equipment': ['Recip Engines', 'Gas Turbines', 'Solar PV', 'BESS'],
                'Capacity': [
                    f"{equip.get('recip_mw', 0):.1f} MW",
                    f"{equip.get('turbine_mw', 0):.1f} MW", 
                    f"{equip.get('solar_mw', 0):.1f} MW",
                    f"{equip.get('bess_mwh', 0):.1f} MWh"
                ]
            })
            st.dataframe(equip_df, use_container_width=True, hide_index=True)
        
        else:
            st.info("👈 Configure parameters and click **Run Phase 1** to find maximum expansion capacity")


if __name__ == "__main__":
    render()
