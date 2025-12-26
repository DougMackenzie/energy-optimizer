"""
Timeline Charts Module
Power availability timelines and portfolio growth visualization
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict
from datetime import datetime, timedelta
import pandas as pd

def create_annual_capacity_timeline(sites_list: List[Dict], comparison_data: List[Dict]) -> go.Figure:
    """
    Create annual stacked area chart showing portfolio capacity growth from 2026-2035
    
    Args:
        sites_list: List of site dicts
        comparison_data: Comparison data with stage info
    
    Returns:
        Plotly figure
    """
    # Create annual data structure
    years = list(range(2026, 2036))  # 2026-2035
    
    # Build site data with power-on years
    site_timeline_data = []
    
    for site in sites_list:
        site_name = site.get('name', 'Unknown')
        capacity_mw = site.get('it_capacity_mw', 0)
        
        # Find this site in comparison_data to get stage
        site_comp = next((c for c in comparison_data if c['Site'] == site_name), None)
        
        if site_comp:
            power_on_date_str = site_comp.get('Power-On Date', 'Q4 2028')
            # Parse "Q2 2026" format
            parts = power_on_date_str.split()
            if len(parts) == 2:
                quarter = int(parts[0][1])  # Extract number from "Q2" 
                year = int(parts[1])
                # Convert quarter to approximate month
                month = (quarter - 1) * 3 + 2  # Q1=Feb, Q2=May, Q3=Aug, Q4=Nov
            else:
                year = 2028
                month = 10
        else:
            # Default to 2028 if no data
            year = 2028
            month = 10
        
        site_timeline_data.append({
            'site': site_name,
            'capacity_mw': capacity_mw,
            'power_on_year': year,
            'power_on_month': month
        })
    
    # Create annual capacity matrix
    # For each year, sum up capacity from sites that are online
    annual_capacity_by_site = {}
    
    for site_data in site_timeline_data:
        site_name = site_data['site']
        capacity = site_data['capacity_mw']
        power_on_year = site_data['power_on_year']
        
        annual_capacity_by_site[site_name] = []
        for year in years:
            if year >= power_on_year:
                annual_capacity_by_site[site_name].append(capacity)
            else:
                annual_capacity_by_site[site_name].append(0)
    
    # Create stacked area chart
    fig = go.Figure()
    
    # Color palette
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    
    # Add trace for each site (stacked)
    for i, (site_name, capacities) in enumerate(annual_capacity_by_site.items()):
        fig.add_trace(go.Scatter(
            x=years,
            y=capacities,
            name=site_name,
            mode='lines',
            stackgroup='one',  # This creates the stacked area
            fillcolor=colors[i % len(colors)],
            line=dict(width=0.5, color=colors[i % len(colors)]),
            hovertemplate=f"<b>{site_name}</b><br>" +
                          "Year: %{x}<br>" +
                          "Capacity: %{y:.0f} MW<extra></extra>"
        ))
    
    # Add cumulative line on top
    cumulative_capacity = [sum(annual_capacity_by_site[site][i] 
                               for site in annual_capacity_by_site) 
                           for i in range(len(years))]
    
    fig.add_trace(go.Scatter(
        x=years,
        y=cumulative_capacity,
        name='Total Portfolio',
        mode='lines+markers',
        line=dict(color='#1f2937', width=3, dash='dot'),
        marker=dict(size=8, color='#1f2937'),
        hovertemplate="<b>Total Portfolio</b><br>" +
                      "Year: %{x}<br>" +
                      "Total Capacity: %{y:.0f} MW<extra></extra>",
        showlegend=True
    ))
    
    # Update layout
    fig.update_layout(
        title="Portfolio Capacity Growth (2026-2035)",
        xaxis=dict(
            title="Year",
            showgrid=True,
            gridcolor='#e5e7eb',
            tickmode='linear',
            tick0=2026,
            dtick=1
        ),
        yaxis=dict(
            title="Cumulative Capacity (MW)",
            showgrid=True,
            gridcolor='#e5e7eb'
        ),
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig


def create_power_availability_gantt(sites_list: List[Dict]) -> go.Figure:
    """
    Create Gantt chart showing construction timeline
    (DEPRECATED - use create_annual_capacity_timeline instead)
    """
    # This function is retained for backward compatibility but is deprecated
    # Redirect to annual timeline
    return create_annual_capacity_timeline(sites_list, [])
