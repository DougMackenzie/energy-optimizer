"""
Charts for phased deployment visualization
"""
import plotly.graph_objects as go
import pandas as pd
from typing import Dict


def create_annual_capacity_stack_chart(deployment: Dict, load_trajectory: Dict, years: list) -> go.Figure:
    """
    Create stacked bar chart showing annual capacity by technology with power deficit.
    
    Args:
        deployment: Deployment schedule from phased optimizer
        load_trajectory: Target load by year
        years: List of years to display
    
    Returns:
        Plotly figure object
    """
    # Extract data
    recip_mw = [deployment['cumulative_recip_mw'].get(year, 0) for year in years]
    turbine_mw = [deployment['cumulative_turbine_mw'].get(year, 0) for year in years]
    bess_mw = [deployment['cumulative_bess_mwh'].get(year, 0) / 4 for year in years]  # 4-hour BESS
    solar_mw = [deployment['cumulative_solar_mw'].get(year, 0) for year in years]
    grid_mw = [deployment['grid_mw'].get(year, 0) for year in years]
    
    # Calculate total capacity and deficit
    total_capacity = []
    deficit = []
    for i, year in enumerate(years):
        capacity = recip_mw[i] + turbine_mw[i] + bess_mw[i] + solar_mw[i] + grid_mw[i]
        target = load_trajectory.get(year, 0)
        total_capacity.append(capacity)
        deficit.append(max(0, target - capacity))
    
    # Create figure
    fig = go.Figure()
    
    # Add capacity bars (stacked)
    if any(recip_mw):
        fig.add_trace(go.Bar(
            name='Reciprocating Engines',
            x=years,
            y=recip_mw,
            marker_color='#2E86AB',
            hovertemplate='%{y:.1f} MW<extra></extra>'
        ))
    
    if any(turbine_mw):
        fig.add_trace(go.Bar(
            name='Gas Turbines',
            x=years,
            y=turbine_mw,
            marker_color='#A23B72',
            hovertemplate='%{y:.1f} MW<extra></extra>'
        ))
    
    if any(bess_mw):
        fig.add_trace(go.Bar(
            name='BESS',
            x=years,
            y=bess_mw,
            marker_color='#F18F01',
            hovertemplate='%{y:.1f} MW<extra></extra>'
        ))
    
    if any(solar_mw):
        fig.add_trace(go.Bar(
            name='Solar PV',
            x=years,
            y=solar_mw,
            marker_color='#C73E1D',
            hovertemplate='%{y:.1f} MW<extra></extra>'
        ))
    
    if any(grid_mw):
        fig.add_trace(go.Bar(
            name='Grid Import',
            x=years,
            y=grid_mw,
            marker_color='#6A994E',
            hovertemplate='%{y:.1f} MW<extra></extra>'
        ))
    
    # Add deficit bars (on top of stack)
    if any(deficit):
        fig.add_trace(go.Bar(
            name='❌ Unmet Load (Deficit)',
            x=years,
            y=deficit,
            marker_color='rgba(200, 0, 0, 0.3)',
            marker_pattern_shape='/',
            hovertemplate='%{y:.1f} MW deficit<extra></extra>'
        ))
    
    # Add target load line
    target_values = [load_trajectory.get(year, 0) for year in years]
    fig.add_trace(go.Scatter(
        name='Target Load',
        x=years,
        y=target_values,
        mode='lines+markers',
        line=dict(color='red', width=3, dash='dash'),
        marker=dict(size=10, symbol='diamond'),
        hovertemplate='Target: %{y:.1f} MW<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title='Annual Capacity Stack by Technology',
        xaxis_title='Year',
        yaxis_title='Capacity (MW)',
        barmode='stack',
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12)
    )
    
    # Grid styling
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    return fig
