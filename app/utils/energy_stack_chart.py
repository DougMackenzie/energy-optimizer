"""
15-Year Energy Stack Forecast Chart
Displays stacked bar chart with equipment capacity over 15 years
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np


def render_energy_stack_forecast(equipment: dict, selected_site: str):
    """Render the 15-year energy stack forecast chart"""
    
    import plotly.graph_objects as go
    import numpy as np
    
    # Create 15-year projection
    years = list(range(2025, 2040))
    
    # Get site load (assume it grows 2% per year from current facility_mw)
    if 'sites_list' in st.session_state:
        site_obj = next((s for s in st.session_state.sites_list if s.get('name') == selected_site), None)
        base_load = site_obj.get('facility_mw', 900) if site_obj else 900
    else:
        base_load = 900
    
    target_load = [base_load * (1.02 ** i) for i in range(15)]
    
    # Equipment capacity (constant for Screening, phased in later stages)
    recip_capacity = [equipment.get('recip_mw', 0)] * 15
    turbine_capacity = [equipment.get('turbine_mw', 0)] * 15
    solar_capacity = [equipment.get('solar_mw', 0)] * 15
    bess_capacity = [equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4)] * 15  # Convert MWh to MW
    grid_capacity = [equipment.get('grid_mw', 0)] * 15
    
    # Calculate total capacity and unserved load
    total_capacity = np.array(recip_capacity) + np.array(turbine_capacity) + np.array(solar_capacity) + np.array(bess_capacity) + np.array(grid_capacity)
    unserved = [max(0, target_load[i] - total_capacity[i]) for i in range(15)]
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Add equipment stacks
    fig.add_trace(go.Bar(name='Recip Engines', x=years, y=recip_capacity, 
                        marker_color='#2E7D32', hovertemplate='Recip: %{y:.0f} MW<extra></extra>'))
    fig.add_trace(go.Bar(name='Turbines', x=years, y=turbine_capacity,
                        marker_color='#1565C0', hovertemplate='Turbines: %{y:.0f} MW<extra></extra>'))
    fig.add_trace(go.Bar(name='Solar PV', x=years, y=solar_capacity,
                        marker_color='#F57C00', hovertemplate='Solar: %{y:.0f} MW<extra></extra>'))
    fig.add_trace(go.Bar(name='BESS', x=years, y=bess_capacity,
                        marker_color='#7B1FA2', hovertemplate='BESS: %{y:.0f} MW<extra></extra>'))
    
    if any(g > 0 for g in grid_capacity):
        fig.add_trace(go.Bar(name='Grid', x=years, y=grid_capacity,
                            marker_color='#424242', hovertemplate='Grid: %{y:.0f} MW<extra></extra>'))
    
    # Add unserved load if any
    if any(u > 0 for u in unserved):
        fig.add_trace(go.Bar(name='Unserved Load', x=years, y=unserved,
                            marker_color='#C62828', hovertemplate='Unserved: %{y:.0f} MW<extra></extra>'))
    
    # Add target load line
    fig.add_trace(go.Scatter(name='Target Load', x=years, y=target_load,
                            mode='lines+markers', line=dict(color='black', width=2, dash='dash'),
                            marker=dict(size=6), hovertemplate='Target: %{y:.0f} MW<extra></extra>'))
    
    fig.update_layout(
        barmode='stack',
        xaxis_title='Year',
        yaxis_title='Capacity (MW)',
        hovermode='x unified',
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary stats
    total_cap = sum([equipment.get('recip_mw', 0), equipment.get('turbine_mw', 0), 
                    equipment.get('solar_mw', 0), bess_capacity[0], equipment.get('grid_mw', 0)])
    coverage_year1 = min(100, total_cap / target_load[0] * 100) if target_load[0] > 0 else 0
    coverage_year15 = min(100, total_cap / target_load[-1] * 100) if target_load[-1] > 0 else 0
    
    st.caption(f"📊 Coverage: {coverage_year1:.0f}% (Year 1) → {coverage_year15:.0f}% (Year 15) | Total Installed: {total_cap:.0f} MW")
