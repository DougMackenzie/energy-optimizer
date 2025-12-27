"""
Problem 5: Bridge Power Transition
Objective: Minimize NPV of BTM-to-Grid transition
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS


def render():
    """Render Problem 5: Bridge Power Transition page"""
    
    prob = PROBLEM_STATEMENTS[5]
    
    st.markdown(f"### {prob['icon']} Problem 5: {prob['name']}")
    st.markdown(f"*{prob['objective']} — {prob['question']}*")
    st.markdown("---")
    
    # Context callout
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); 
                padding: 16px 20px; border-radius: 12px; margin-bottom: 20px; border-left: 4px solid #ef4444;">
        <strong style="color: #991b1b;">The #1 Pain Point:</strong>
        <span style="color: #7f1d1d;">Grid interconnection takes 5+ years, but customers need power in 18 months.</span>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        with st.expander("⚡ Grid Timeline", expanded=True):
            grid_queue_months = st.number_input(
                "Grid Interconnection (months from now)", 
                12, 120, 60,
                help="Typical: 48-84 months for major ISOs"
            )
            
            grid_capacity = st.number_input("Grid Connection Capacity (MW)", 50, 2000, 600)
            grid_connection_cost = st.number_input("Grid Connection Cost ($M)", 1, 100, 25)
        
        with st.expander("📈 Load Timeline", expanded=True):
            first_load_month = st.number_input("First Load (months from now)", 6, 48, 18)
            first_load_mw = st.number_input("Initial Load (MW)", 25, 500, 150)
            target_load_mw = st.number_input("Target Load (MW)", 100, 2000, 600)
            ramp_months = st.number_input("Ramp Duration (months)", 6, 60, 36)
            pue = st.slider("PUE", 1.1, 1.5, 1.25, 0.05)
        
        with st.expander("💰 Asset Options", expanded=True):
            st.markdown("**Rental Gensets**")
            rental_cost = st.number_input("Rental Cost ($/MW-month)", 5000, 30000, 15000)
            
            st.markdown("**Permanent BTM Assets**")
            use_permanent = st.checkbox("Allow permanent BTM investment", value=True)
            
            st.markdown("**Title V Avoidance**")
            title_v_limit = st.number_input("Rolling 12-month NOx limit (tpy)", 50, 200, 100)
        
        st.markdown("---")
        
        run_phase1 = st.button("▶️ Optimize Transition Strategy", type="primary", use_container_width=True)
        run_phase2 = st.button("🔒 Run Phase 2 (MILP)", disabled=True, use_container_width=True)
    
    with col_results:
        st.markdown("#### 📊 Transition Strategy")
        
        if run_phase1:
            with st.spinner("Optimizing bridge power strategy..."):
                try:
                    from app.optimization.heuristic_optimizer import BridgePowerHeuristic
                    
                    # Build load trajectory by year (simplified)
                    load_trajectory = {}
                    for year in range(2025, 2032):
                        months_from_now = (year - 2025) * 12
                        if months_from_now < first_load_month:
                            load_trajectory[year] = 0
                        elif months_from_now < first_load_month + ramp_months:
                            progress = (months_from_now - first_load_month) / ramp_months
                            load_trajectory[year] = (first_load_mw + (target_load_mw - first_load_mw) * progress) * pue
                        else:
                            load_trajectory[year] = target_load_mw * pue
                    
                    optimizer = BridgePowerHeuristic(
                        site={},
                        load_trajectory=load_trajectory,
                        constraints={'nox_tpy_annual': title_v_limit},
                        grid_available_month=grid_queue_months,
                        horizon_months=72,
                    )
                    
                    result = optimizer.optimize()
                    
                    # Store results
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    
                    st.session_state.optimization_results[5] = {
                        'result': result,
                        'npv_total': result.dispatch_summary.get('npv_total', 0),
                        'npv_rental': result.dispatch_summary.get('npv_rental', 0),
                        'perm_capex': result.dispatch_summary.get('perm_capex', 0),
                        'grid_month': grid_queue_months,
                        'monthly_loads': result.dispatch_summary.get('monthly_loads', []),
                        'rental_costs': result.dispatch_summary.get('rental_costs', []),
                    }
                    st.session_state.phase_1_complete[5] = True
                    
                    st.success(f"✅ Phase 1 complete in {result.solve_time_seconds:.1f} seconds")
                    
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        
        result_data = st.session_state.get('optimization_results', {}).get(5)
        
        if result_data:
            # Key metric - NPV
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fef2f2 0%, #fce7f3 100%); 
                        padding: 24px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 14px; color: #9f1239; margin-bottom: 8px;">
                    Total NPV of Bridge Power Strategy
                </div>
                <div style="font-size: 48px; font-weight: 700; color: #881337;">
                    ${result_data['npv_total']/1e6:.1f}M
                </div>
                <div style="font-size: 14px; color: #be185d; margin-top: 8px;">
                    Grid energization at month {result_data['grid_month']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Cost breakdown
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rental NPV", f"${result_data['npv_rental']/1e6:.1f}M")
            with col2:
                st.metric("Permanent CAPEX", f"${result_data['perm_capex']/1e6:.1f}M")
            with col3:
                st.metric("Grid Months", f"{result_data['grid_month']}")
            
            st.markdown("---")
            
            # Timeline visualization
            st.markdown("##### 📅 Transition Timeline")
            
            # Create timeline data
            months = list(range(72))
            loads = result_data.get('monthly_loads', [0] * 72)
            rentals = result_data.get('rental_costs', [0] * 72)
            
            # Pad if needed
            while len(loads) < 72:
                loads.append(loads[-1] if loads else 0)
            while len(rentals) < 72:
                rentals.append(0)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                               subplot_titles=("Load Profile", "Monthly Costs"),
                               vertical_spacing=0.15)
            
            # Load profile
            fig.add_trace(
                go.Scatter(x=months, y=loads, fill='tozeroy', name='Load (MW)',
                          line=dict(color='#4299e1')),
                row=1, col=1
            )
            
            # Add grid energization line
            fig.add_vline(x=result_data['grid_month'], line_dash="dash", 
                         line_color="green", row=1, col=1)
            fig.add_annotation(x=result_data['grid_month'], y=max(loads) * 0.9,
                              text="Grid<br>Available", showarrow=False,
                              font=dict(color="green", size=10), row=1, col=1)
            
            # Costs
            fig.add_trace(
                go.Bar(x=months, y=[r/1000 for r in rentals], name='Rental Cost ($k/month)',
                      marker_color='#f6ad55'),
                row=2, col=1
            )
            
            fig.update_layout(height=450, margin=dict(t=50, b=30))
            fig.update_xaxes(title_text="Month", row=2, col=1)
            fig.update_yaxes(title_text="MW", row=1, col=1)
            fig.update_yaxes(title_text="$k/month", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Strategy summary
            st.markdown("##### 📋 Recommended Strategy")
            
            rental_months = sum(1 for r in rentals if r > 0)
            
            st.markdown(f"""
            <div style="background: #f7fafc; padding: 16px; border-radius: 8px;">
                <ol style="margin: 0; padding-left: 20px;">
                    <li><strong>Months 0-{first_load_month}:</strong> Pre-construction phase, no load</li>
                    <li><strong>Month {first_load_month}:</strong> Initial load comes online ({first_load_mw} MW)</li>
                    <li><strong>Months {first_load_month}-{result_data['grid_month']}:</strong> Bridge power via 70% permanent / 30% rental</li>
                    <li><strong>Month {result_data['grid_month']}:</strong> Grid energization, phase out rentals</li>
                    <li><strong>Post-grid:</strong> Full grid supply, repurpose BTM assets for backup/peaking</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
            
            # Title V analysis
            st.markdown("##### ⚠️ Title V Permit Analysis")
            
            st.info(f"""
            **Rolling 12-month NOx limit:** {title_v_limit} tpy
            
            The optimization considers Title V avoidance by managing emission intensity 
            across rental and permanent assets. With grid available at month {result_data['grid_month']},
            the strategy phases out high-emitting rentals before triggering Title V thresholds.
            """)
            
        else:
            st.info("👈 Configure timeline and click **Optimize Transition Strategy**")
            
            # Explanation
            st.markdown("""
            ##### What This Analysis Solves
            
            **The Grid Queue Problem:**
            - Major ISOs (ERCOT, PJM, SPP) have 5-7+ year interconnection queues
            - AI datacenter customers need power in 12-24 months
            - BTM generation bridges the gap, but rental vs. buy decisions are complex
            
            **This problem optimizes:**
            - When to use rental gensets vs. permanent BTM assets
            - Optimal rental-to-permanent ratio
            - Title V permit avoidance strategy
            - Grid energization timing
            - Residual value of BTM assets post-grid
            """)


if __name__ == "__main__":
    render()
