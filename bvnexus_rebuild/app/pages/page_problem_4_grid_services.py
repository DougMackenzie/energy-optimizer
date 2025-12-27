"""
Problem 4: Grid Services
Objective: Maximize DR revenue stack
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

from config.settings import PROBLEM_STATEMENTS, COLORS, WORKLOAD_FLEXIBILITY, DR_SERVICES


def render():
    """Render Problem 4: Grid Services page"""
    
    prob = PROBLEM_STATEMENTS[4]
    
    st.markdown(f"### {prob['icon']} Problem 4: {prob['name']}")
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
        
        with st.expander("🏭 Facility Profile", expanded=True):
            peak_load = st.number_input("Peak Load (MW)", 50, 2000, 600)
            pue = st.slider("PUE", 1.1, 1.5, 1.25, 0.05)
        
        with st.expander("🤖 AI Workload Mix", expanded=True):
            st.markdown("**Workload Allocation (%)**")
            
            pre_training = st.slider("Pre-training", 0, 100, 30)
            fine_tuning = st.slider("Fine-tuning", 0, 100, 20)
            batch_inference = st.slider("Batch Inference", 0, 100, 30)
            realtime_inference = st.slider("Real-time Inference", 0, 100, 20)
            
            total = pre_training + fine_tuning + batch_inference + realtime_inference
            if total != 100:
                st.warning(f"Total = {total}%. Should equal 100%")
            
            workload_mix = {
                'pre_training': pre_training / 100,
                'fine_tuning': fine_tuning / 100,
                'batch_inference': batch_inference / 100,
                'real_time_inference': realtime_inference / 100,
            }
        
        with st.expander("🔌 DR Service Options", expanded=True):
            st.markdown("**Available Services**")
            
            use_econ_dr = st.checkbox("Economic DR (60+ min response)", value=True)
            use_ers_10 = st.checkbox("ERS-10 (10 min response)", value=True)
            use_ers_30 = st.checkbox("ERS-30 (30 min response)", value=True)
            use_capacity = st.checkbox("Capacity Market", value=True)
        
        st.markdown("---")
        
        run_phase1 = st.button("▶️ Optimize DR Enrollment", type="primary", use_container_width=True)
        run_phase2 = st.button("🔒 Run Phase 2 (MILP)", disabled=True, use_container_width=True)
    
    with col_results:
        st.markdown("#### 📊 DR Revenue Analysis")
        
        if run_phase1:
            with st.spinner("Optimizing DR service enrollment..."):
                try:
                    from app.optimization.heuristic_optimizer import GridServicesHeuristic
                    
                    load_trajectory = {2025: peak_load * pue}
                    
                    optimizer = GridServicesHeuristic(
                        site={},
                        load_trajectory=load_trajectory,
                        constraints={},
                        workload_mix=workload_mix,
                    )
                    
                    result = optimizer.optimize()
                    
                    # Store results
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    
                    st.session_state.optimization_results[4] = {
                        'result': result,
                        'total_revenue': result.objective_value,
                        'flex_mw': result.dispatch_summary.get('total_flex_mw', 0),
                        'revenue_per_mw': result.dispatch_summary.get('dr_revenue_per_mw', 0),
                        'services': result.dispatch_summary.get('services', {}),
                        'workload_mix': workload_mix,
                    }
                    st.session_state.phase_1_complete[4] = True
                    
                    st.success(f"✅ Phase 1 complete in {result.solve_time_seconds:.1f} seconds")
                    
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")
        
        result_data = st.session_state.get('optimization_results', {}).get(4)
        
        if result_data:
            # Key metric - revenue
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                        padding: 24px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 14px; color: #92400e; margin-bottom: 8px;">
                    Annual DR Revenue Potential
                </div>
                <div style="font-size: 48px; font-weight: 700; color: #78350f;">
                    ${result_data['total_revenue']/1e6:.1f}M
                </div>
                <div style="font-size: 14px; color: #a16207; margin-top: 8px;">
                    {result_data['flex_mw']:.0f} MW flexible @ ${result_data['revenue_per_mw']/1000:.0f}k/MW-year
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics row
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Load", f"{peak_load} MW")
            with col2:
                st.metric("Flexible Capacity", f"{result_data['flex_mw']:.0f} MW")
            with col3:
                flex_pct = result_data['flex_mw'] / (peak_load * pue) * 100 if peak_load > 0 else 0
                st.metric("Flexibility %", f"{flex_pct:.0f}%")
            
            st.markdown("---")
            
            # Revenue by service
            st.markdown("##### Revenue by DR Service")
            
            services = result_data.get('services', {})
            if services:
                service_data = []
                for svc_id, revenue in services.items():
                    svc_info = DR_SERVICES.get(svc_id, {})
                    service_data.append({
                        'Service': svc_info.get('name', svc_id),
                        'Response Time': f"{svc_info.get('response_time_min', 0)} min",
                        'Annual Revenue': f"${revenue/1000:.0f}k",
                    })
                
                svc_df = pd.DataFrame(service_data)
                st.dataframe(svc_df, use_container_width=True, hide_index=True)
                
                # Pie chart
                fig = px.pie(
                    values=list(services.values()),
                    names=[DR_SERVICES.get(k, {}).get('name', k) for k in services.keys()],
                    title="Revenue Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(height=300, margin=dict(t=50, b=20))
                st.plotly_chart(fig, use_container_width=True)
            
            # Workload compatibility matrix
            st.markdown("##### Workload × Service Compatibility")
            
            compat_data = []
            for wl_id, wl_info in WORKLOAD_FLEXIBILITY.items():
                row = {'Workload': wl_id.replace('_', ' ').title()}
                row['Flexibility'] = f"{wl_info['flexibility_pct']*100:.0f}%"
                
                for svc_id, svc_info in DR_SERVICES.items():
                    if wl_id in svc_info.get('compatible_workloads', []):
                        row[svc_info['name']] = "✓"
                    else:
                        row[svc_info['name']] = "—"
                
                compat_data.append(row)
            
            compat_df = pd.DataFrame(compat_data)
            st.dataframe(compat_df, use_container_width=True, hide_index=True)
            
            # Recommendations
            st.markdown("##### 💡 Recommendations")
            
            if result_data['flex_mw'] < peak_load * 0.20:
                st.warning("""
                **Low Flexibility**: Only {:.0f}% of load is flexible. 
                Consider increasing batch inference workloads to unlock more DR revenue.
                """.format(flex_pct))
            else:
                st.success("""
                **Good Flexibility**: {:.0f}% of load available for DR services.
                Projected revenue of ${:.0f}k/MW-year is in line with market benchmarks.
                """.format(flex_pct, result_data['revenue_per_mw']/1000))
        
        else:
            st.info("👈 Configure workload mix and click **Optimize DR Enrollment**")
            
            # Service descriptions
            st.markdown("##### Available DR Services")
            
            for svc_id, svc_info in DR_SERVICES.items():
                with st.expander(f"📌 {svc_info['name']}"):
                    st.markdown(f"""
                    - **Response Time**: {svc_info['response_time_min']} minutes
                    - **Min Duration**: {svc_info.get('min_duration_hours', 'N/A')} hours
                    - **Compatible Workloads**: {', '.join(svc_info.get('compatible_workloads', []))}
                    """)


if __name__ == "__main__":
    render()
