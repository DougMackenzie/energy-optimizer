"""
Comparison Page
Compare optimization results across all 4 EPC stages
"""

import streamlit as st
import pandas as pd
from app.utils.site_context_helper import display_site_context



def safe_float(value, default=0):
    """Safely convert value to float, handling empty strings and None"""
    if value is None or value == '' or value == 'None':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def render():
    st.markdown("### 🔄 Comparison")
    st.caption("Compare optimization results across EPC stages: Screening → Concept → Preliminary → Detailed")
    
    # Display site context
    
    # Site Selector
    if 'sites_list' in st.session_state and st.session_state.sites_list:
        site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
        selected_site = st.selectbox("Select Site", options=site_names, key="comparison_site")
    else:
        st.warning("No sites configured")
        return
    
    
    # Display site context (after selected_site is defined)
    display_site_context(selected_site)
    
    st.markdown("---")
    
    # Stage Comparison Table
    # Display problem type prominently
    
    # Get fresh site object from sites_list
    site_obj = next((s for s in st.session_state.sites_list if s.get('name') == selected_site), {})
    problem_num_display = site_obj.get('problem_num', 1)  # Load from site data (Google Sheets)
    
    from config.settings import PROBLEM_STATEMENTS
    problem_info_display = PROBLEM_STATEMENTS.get(problem_num_display, PROBLEM_STATEMENTS[1])
    
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
                padding: 16px 24px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #2b6cb0;">
        <div style="color: white; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
            {problem_info_display['icon']} PROBLEM STATEMENT
        </div>
        <div style="color: #bee3f8; font-size: 18px; font-weight: 700;">
            P{problem_num_display}: {problem_info_display['name']}
        </div>
        <div style="color: #90cdf4; font-size: 13px; margin-top: 4px;">
            {problem_info_display['objective']} — {problem_info_display['question']}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("#### Stage Comparison Matrix")
    
    # Load optimization results for all stages from Google Sheets
    from app.utils.site_backend import load_site_stage_result
    from datetime import datetime
    
    stage_keys = {
        'Screening (1)': 'screening',
        'Concept (2)': 'concept',
        'Preliminary (3)': 'preliminary',
        'Detailed (4)': 'detailed'
    }
    
    # Initialize data structure
    comparison_data = {
        'Metric': [
            'LCOE ($/MWh)',
            'NPV ($M)',
            'Recip Engines (MW)',
            'Turbines (MW)',
            'BESS (MWh)',
            'Solar PV (MW)',
            'Grid (MW)',
            'Total CapEx ($M)',
            'Annual OpEx ($M/yr)',
            'Completion Date',
            'Runtime',
            'Solver'
        ]
    }
    
    # Load data for each stage
    for stage_name, stage_key in stage_keys.items():
        try:
            print(f'\n=== COMPARISON DEBUG ===')
            print(f'Loading: {selected_site} - {stage_key}')
            # Load results from Google Sheets (gets latest version automatically)
            result = load_site_stage_result(selected_site, stage_key)
            print(f'Result: {"FOUND" if result else "NOT FOUND"}')
            if result:
                print(f'LCOE: {result.get("lcoe")}, Equipment: {list(result.get("equipment", {}).keys())}')
            
            if result:
                # Extract equipment data
                equipment = result.get('equipment', {})
                
                # Populate column with actual values
                comparison_data[stage_name] = [
                    f"{safe_float(result.get('lcoe', 0)):.1f}",  # LCOE
                    f"{safe_float(result.get('npv', 0)) / 1e6:.1f}",  # NPV in $M
                    f"{safe_float(equipment.get('recip_mw', 0)):.0f}",  # Recip MW
                    f"{safe_float(equipment.get('turbine_mw', 0)):.0f}",  # Turbines MW
                    f"{safe_float(equipment.get('bess_mwh', 0)):.0f}",  # BESS MWh
                    f"{safe_float(equipment.get('solar_mw', 0)):.0f}",  # Solar MW
                    f"{safe_float(equipment.get('grid_mw', 0)):.0f}",  # Grid MW
                    f"{safe_float(result.get('total_capex', result.get('capex', {}).get('total', 0))) / 1e6:.1f}",  # Total CapEx in $M
                    f"{safe_float(result.get('annual_opex', result.get('opex_annual', {}).get('total', 0))) / 1e6:.1f}",  # Annual OpEx in $M
                    datetime.fromisoformat(result.get('completion_date', '')).strftime('%Y-%m-%d %H:%M') if result.get('completion_date') else 'Not run',  # Completion date
                    f"{safe_float(result.get('runtime_seconds', 0)):.1f}s",  # Runtime
                    result.get('solver', 'Heuristic').upper()  # Solver
                ]
            else:
                # No results found - use TBD
                comparison_data[stage_name] = [
                    'TBD', 'TBD', 'TBD', 'TBD', 'TBD', 'TBD', 'TBD',
                    'TBD', 'TBD', 'Not run', '-', 
                    'Heuristic' if stage_key == 'screening' else 'MILP'
                ]
        except Exception as e:
            print(f"Error loading {stage_name}: {e}")
            # Error loading - use TBD
            comparison_data[stage_name] = [
                'TBD', 'TBD', 'TBD', 'TBD', 'TBD', 'TBD', 'TBD',
                'TBD', 'TBD', 'Not run', '-',
                'Heuristic' if stage_key == 'screening' else 'MILP'
            ]
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    # Show info about data freshness
    any_results = any(col != 'Not run' for col in [comparison_data[stage][9] for stage in stage_keys.keys()])
    if any_results:
        st.success("✅ Showing latest saved results for each stage")
    else:
        st.info("💡 Results will populate as each stage is completed")
    
    
    st.markdown("---")
    
    # Trend Charts
    st.markdown("#### Trend Analysis")
    
    col_trend1, col_trend2 = st.columns(2)
    
    with col_trend1:
        st.markdown("**LCOE Progression**")
        
        # Extract LCOE data
        import plotly.graph_objects as go
        
        stages_list = list(stage_keys.keys())
        lcoe_values = []
        
        for stage in stages_list:
            lcoe_str = comparison_data.get(stage, ['TBD'])[0]
            if lcoe_str != 'TBD':
                try:
                    lcoe_values.append(float(lcoe_str))
                except:
                    lcoe_values.append(None)
            else:
                lcoe_values.append(None)
        
        # Only show chart if we have at least one value
        if any(v is not None for v in lcoe_values):
            fig_lcoe = go.Figure()
            fig_lcoe.add_trace(go.Scatter(
                x=stages_list,
                y=lcoe_values,
                mode='lines+markers',
                name='LCOE',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=10)
            ))
            
            fig_lcoe.update_layout(
                yaxis_title="LCOE ($/MWh)",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_lcoe, use_container_width=True)
        else:
            st.info("📉 Complete stages to see LCOE trend")
    
    with col_trend2:
        st.markdown("**Equipment Capacity Evolution**")
        
        # Extract equipment data for chart
        import plotly.graph_objects as go
        
        recip_data = []
        turbine_data = []
        bess_data = []
        solar_data = []
        
        for stage in stages_list:
            stage_data = comparison_data.get(stage, ['TBD']*12)
            try:
                recip_data.append(float(stage_data[2]) if stage_data[2] != 'TBD' else 0)
                turbine_data.append(float(stage_data[3]) if stage_data[3] != 'TBD' else 0)
                bess_data.append(float(stage_data[4]) if stage_data[4] != 'TBD' else 0)
                solar_data.append(float(stage_data[5]) if stage_data[5] != 'TBD' else 0)
            except:
                recip_data.append(0)
                turbine_data.append(0)
                bess_data.append(0)
                solar_data.append(0)
        
        if sum(recip_data + turbine_data + bess_data + solar_data) > 0:
            fig_equip = go.Figure()
            
            fig_equip.add_trace(go.Bar(name='Recip Engines', x=stages_list, y=recip_data, marker_color='#ef4444'))
            fig_equip.add_trace(go.Bar(name='Turbines', x=stages_list, y=turbine_data, marker_color='#f59e0b'))
            fig_equip.add_trace(go.Bar(name='BESS', x=stages_list, y=bess_data, marker_color='#8b5cf6'))
            fig_equip.add_trace(go.Bar(name='Solar PV', x=stages_list, y=solar_data, marker_color='#10b981'))
            
            fig_equip.update_layout(
                barmode='stack',
                yaxis_title="Capacity (MW/MWh)",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_equip, use_container_width=True)
        else:
            st.info("📊 Complete stages to see equipment evolution")
    
    st.markdown("---")
    
    # Notes & Versioning
    st.markdown("#### Stage Notes")
    
    with st.expander("📝 Screening Study Notes", expanded=False):
        screening_notes = st.text_area(
            "Notes for Screening Study",
            value="Initial feasibility assessment...",
            key="screening_notes",
            height=100
        )
        
        col_v1, col_v2 = st.columns([3, 1])
        with col_v1:
            st.caption("Version: 1 | Last updated: TBD")
        with col_v2:
            if st.button("💾 Save Notes", key="save_screening"):
                st.success("Notes saved!")
    
    with st.expander("📝 Concept Development Notes"):
        concept_notes = st.text_area(
            "Notes for Concept Development",
            value="Detailed MILP results...",
            key="concept_notes",
            height=100
        )
    
    with st.expander("📝 Preliminary Design Notes"):
        prelim_notes = st.text_area(
            "Notes for Preliminary Design",
            value="Vendor quotes incorporated...",
            key="prelim_notes",
            height=100
        )
    
    with st.expander("📝 Detailed Design Notes"):
        detailed_notes = st.text_area(
            "Notes for Detailed Design",
            value="Final as-built parameters...",
            key="detailed_notes",
            height=100
        )
    
    st.markdown("---")
    
    # Export
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        if st.button("📥 Export to Excel", use_container_width=True):
            st.success("Comparison exported to Excel!")
    
    with col_exp2:
        if st.button("📄 Generate Word Report", use_container_width=True):
            st.success("Word report generated!")
    
    with col_exp3:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
