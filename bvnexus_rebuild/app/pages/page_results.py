"""
Results Dashboard Page
Consolidated view of optimization results across all problem statements
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
    """Render Results Dashboard page"""
    
    st.markdown("### 📈 Results Dashboard")
    st.markdown("*Consolidated optimization results across all problem statements*")
    st.markdown("---")
    
    # Check for results
    results = st.session_state.get('optimization_results', {})
    
    if not results:
        st.warning("No optimization results available yet.")
        st.info("Run Phase 1 optimization on any problem statement to see results here.")
        
        if st.button("🎯 Go to Problem Selection", type="primary"):
            st.session_state.current_page = 'problem_selection'
            st.rerun()
        return
    
    # Summary metrics
    st.markdown("#### 📊 Summary Metrics")
    
    cols = st.columns(5)
    
    for i, (prob_num, prob_info) in enumerate(PROBLEM_STATEMENTS.items()):
        result = results.get(prob_num)
        
        with cols[i]:
            if result:
                # Get primary metric based on problem type
                if prob_num == 1:
                    value = f"${result.get('lcoe', 0):.0f}/MWh"
                    label = "LCOE"
                elif prob_num == 2:
                    value = f"+{result.get('max_additional_load', 0):.0f} MW"
                    label = "Max Expansion"
                elif prob_num == 3:
                    scenarios = result.get('scenarios', {})
                    if scenarios:
                        max_load = max(r.objective_value for r in scenarios.values())
                        value = f"{max_load:.0f} MW"
                    else:
                        value = "—"
                    label = "Max Capacity"
                elif prob_num == 4:
                    value = f"${result.get('total_revenue', 0)/1e6:.1f}M"
                    label = "DR Revenue"
                elif prob_num == 5:
                    value = f"${result.get('npv_total', 0)/1e6:.1f}M"
                    label = "NPV"
                
                st.metric(
                    f"P{prob_num}: {prob_info['short_name']}",
                    value,
                    help=prob_info['objective']
                )
            else:
                st.metric(
                    f"P{prob_num}: {prob_info['short_name']}",
                    "—",
                    help="Not yet run"
                )
    
    st.markdown("---")
    
    # Detailed results tabs
    tab_compare, tab_equipment, tab_economics, tab_constraints, tab_export = st.tabs([
        "📊 Comparison", "⚙️ Equipment", "💰 Economics", "⚠️ Constraints", "📤 Export"
    ])
    
    with tab_compare:
        render_comparison_tab(results)
    
    with tab_equipment:
        render_equipment_summary(results)
    
    with tab_economics:
        render_economics_summary(results)
    
    with tab_constraints:
        render_constraints_summary(results)
    
    with tab_export:
        render_export_tab(results)


def render_comparison_tab(results):
    """Render cross-problem comparison"""
    
    st.markdown("##### Problem Statement Comparison")
    
    # Build comparison table
    comparison_data = []
    
    for prob_num, prob_info in PROBLEM_STATEMENTS.items():
        result = results.get(prob_num)
        
        if result:
            row = {
                'Problem': f"P{prob_num}: {prob_info['short_name']}",
                'Objective': prob_info['objective'],
                'Status': '✓ Feasible' if result.get('feasible', True) else '⚠️ Issues',
            }
            
            # Add problem-specific results
            if prob_num == 1:
                row['Primary Result'] = f"${result.get('lcoe', 0):.1f}/MWh"
                row['CAPEX'] = f"${result.get('capex', 0)/1e6:.1f}M"
                row['Timeline'] = f"{result.get('timeline', 0)} mo"
            elif prob_num == 2:
                row['Primary Result'] = f"+{result.get('max_additional_load', 0):.0f} MW"
                row['CAPEX'] = f"${result.get('capex', 0)/1e6:.1f}M"
                row['Timeline'] = "—"
            elif prob_num == 3:
                scenarios = result.get('scenarios', {})
                if scenarios:
                    max_load = max(r.objective_value for r in scenarios.values())
                    row['Primary Result'] = f"{max_load:.0f} MW"
                else:
                    row['Primary Result'] = "—"
                row['CAPEX'] = "Multiple"
                row['Timeline'] = "—"
            elif prob_num == 4:
                row['Primary Result'] = f"${result.get('total_revenue', 0)/1e6:.1f}M/yr"
                row['CAPEX'] = "—"
                row['Timeline'] = "—"
            elif prob_num == 5:
                row['Primary Result'] = f"${result.get('npv_total', 0)/1e6:.1f}M NPV"
                row['CAPEX'] = f"${result.get('perm_capex', 0)/1e6:.1f}M"
                row['Timeline'] = f"{result.get('grid_month', 0)} mo"
            
            comparison_data.append(row)
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No results to compare yet.")
    
    # Visual comparison chart
    if len([r for r in results.values() if r]) >= 2:
        st.markdown("##### LCOE Comparison (where applicable)")
        
        lcoe_data = []
        for prob_num in [1, 2]:  # Problems with LCOE
            result = results.get(prob_num)
            if result and result.get('lcoe'):
                lcoe_data.append({
                    'Problem': f"P{prob_num}: {PROBLEM_STATEMENTS[prob_num]['short_name']}",
                    'LCOE ($/MWh)': result['lcoe']
                })
        
        if lcoe_data:
            fig = px.bar(lcoe_data, x='Problem', y='LCOE ($/MWh)', 
                        color='Problem', color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_equipment_summary(results):
    """Summarize equipment across all problems"""
    
    st.markdown("##### Equipment Summary by Problem")
    
    equip_data = []
    
    for prob_num, result in results.items():
        if not result:
            continue
        
        equipment = result.get('equipment', {})
        if not equipment:
            continue
        
        prob_info = PROBLEM_STATEMENTS.get(prob_num, {})
        
        equip_data.append({
            'Problem': f"P{prob_num}: {prob_info.get('short_name', '')}",
            'Recip (MW)': f"{equipment.get('recip_mw', 0):.0f}",
            'Turbine (MW)': f"{equipment.get('turbine_mw', 0):.0f}",
            'Solar (MW)': f"{equipment.get('solar_mw', 0):.0f}",
            'BESS (MWh)': f"{equipment.get('bess_mwh', 0):.0f}",
            'Total Firm (MW)': f"{equipment.get('total_firm_mw', 0):.0f}",
        })
    
    if equip_data:
        df = pd.DataFrame(equip_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Stacked bar chart
        st.markdown("##### Capacity Mix Visualization")
        
        fig = go.Figure()
        
        problems = [d['Problem'] for d in equip_data]
        
        fig.add_trace(go.Bar(name='Recip', x=problems, 
                            y=[float(d['Recip (MW)']) for d in equip_data],
                            marker_color='#48bb78'))
        fig.add_trace(go.Bar(name='Turbine', x=problems,
                            y=[float(d['Turbine (MW)']) for d in equip_data],
                            marker_color='#4299e1'))
        fig.add_trace(go.Bar(name='Solar', x=problems,
                            y=[float(d['Solar (MW)']) for d in equip_data],
                            marker_color='#f6ad55'))
        
        fig.update_layout(barmode='stack', height=350, 
                         yaxis_title='Capacity (MW)',
                         legend=dict(orientation='h', yanchor='bottom', y=1.02))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equipment data available.")


def render_economics_summary(results):
    """Economic summary across problems"""
    
    st.markdown("##### Economic Summary")
    
    econ_data = []
    
    for prob_num, result in results.items():
        if not result:
            continue
        
        prob_info = PROBLEM_STATEMENTS.get(prob_num, {})
        
        econ_data.append({
            'Problem': f"P{prob_num}: {prob_info.get('short_name', '')}",
            'CAPEX ($M)': result.get('capex', 0) / 1e6,
            'OPEX ($M/yr)': result.get('opex', 0) / 1e6 if result.get('opex') else 0,
            'LCOE ($/MWh)': result.get('lcoe', 0) if result.get('lcoe') else 0,
        })
    
    if econ_data:
        df = pd.DataFrame(econ_data)
        
        # Format for display
        display_df = df.copy()
        display_df['CAPEX ($M)'] = display_df['CAPEX ($M)'].apply(lambda x: f"${x:.1f}M")
        display_df['OPEX ($M/yr)'] = display_df['OPEX ($M/yr)'].apply(lambda x: f"${x:.1f}M" if x > 0 else "—")
        display_df['LCOE ($/MWh)'] = display_df['LCOE ($/MWh)'].apply(lambda x: f"${x:.1f}" if x > 0 else "—")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # CAPEX comparison
        st.markdown("##### CAPEX Comparison")
        
        fig = px.bar(df, x='Problem', y='CAPEX ($M)',
                    color='Problem', color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=300, showlegend=False, yaxis_title='CAPEX ($M)')
        st.plotly_chart(fig, use_container_width=True)


def render_constraints_summary(results):
    """Constraint analysis across problems"""
    
    st.markdown("##### Constraint Status Summary")
    
    constraint_data = []
    
    for prob_num, result in results.items():
        if not result:
            continue
        
        constraints = result.get('constraints', {})
        if not constraints:
            continue
        
        prob_info = PROBLEM_STATEMENTS.get(prob_num, {})
        
        for name, status in constraints.items():
            if isinstance(status, dict):
                constraint_data.append({
                    'Problem': f"P{prob_num}",
                    'Constraint': name.replace('_', ' ').title(),
                    'Value': f"{status.get('value', 0):.1f}",
                    'Limit': f"{status.get('limit', 0):.1f}",
                    'Utilization': f"{status.get('value', 0) / status.get('limit', 1) * 100:.0f}%" if status.get('limit', 0) > 0 else "—",
                    'Binding': '🔴 Yes' if status.get('binding') else '🟢 No',
                })
    
    if constraint_data:
        df = pd.DataFrame(constraint_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Binding constraints summary
        binding = [c for c in constraint_data if '🔴' in c['Binding']]
        
        if binding:
            st.warning(f"**{len(binding)} binding constraints** across all problems:")
            for c in binding:
                st.markdown(f"- **{c['Problem']}**: {c['Constraint']} ({c['Utilization']})")
        else:
            st.success("No binding constraints detected.")
    else:
        st.info("No constraint data available.")


def render_export_tab(results):
    """Export options"""
    
    st.markdown("##### Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Summary Report**")
        
        # Build summary text
        summary_lines = ["bvNexus Optimization Results Summary", "=" * 40, ""]
        
        for prob_num, result in results.items():
            if result:
                prob_info = PROBLEM_STATEMENTS.get(prob_num, {})
                summary_lines.append(f"Problem {prob_num}: {prob_info.get('name', '')}")
                summary_lines.append(f"  Objective: {prob_info.get('objective', '')}")
                summary_lines.append(f"  Feasible: {result.get('feasible', True)}")
                summary_lines.append(f"  LCOE: ${result.get('lcoe', 0):.1f}/MWh")
                summary_lines.append(f"  CAPEX: ${result.get('capex', 0)/1e6:.1f}M")
                summary_lines.append("")
        
        summary_text = "\n".join(summary_lines)
        
        st.download_button(
            "📄 Download Summary (TXT)",
            summary_text,
            "bvnexus_results_summary.txt",
            "text/plain"
        )
    
    with col2:
        st.markdown("**Detailed Data**")
        
        # Build Excel-like CSV
        if results:
            # Create multi-sheet equivalent as multiple CSVs
            
            # Equipment summary
            equip_rows = []
            for prob_num, result in results.items():
                if result and result.get('equipment'):
                    equip = result['equipment']
                    equip_rows.append({
                        'Problem': prob_num,
                        'Recip_MW': equip.get('recip_mw', 0),
                        'Turbine_MW': equip.get('turbine_mw', 0),
                        'Solar_MW': equip.get('solar_mw', 0),
                        'BESS_MWh': equip.get('bess_mwh', 0),
                        'CAPEX': result.get('capex', 0),
                        'OPEX': result.get('opex', 0),
                        'LCOE': result.get('lcoe', 0),
                    })
            
            if equip_rows:
                df = pd.DataFrame(equip_rows)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    "📊 Download Equipment Summary (CSV)",
                    csv,
                    "bvnexus_equipment_summary.csv",
                    "text/csv"
                )
    
    st.markdown("---")
    
    st.markdown("##### Report Generation")
    st.info("""
    **Coming Soon:** Full report generation with:
    - Executive summary
    - Equipment specifications
    - 8760 dispatch data
    - Pro forma cash flows
    - Constraint analysis
    - Deployment timeline
    """)
    
    st.button("📑 Generate Full Report (Coming Soon)", disabled=True)


if __name__ == "__main__":
    render()
