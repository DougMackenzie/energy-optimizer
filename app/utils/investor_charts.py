"""
Investor Charts Module
Plotly visualizations for financial metrics and portfolio analysis
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict

def create_npv_chart(portfolio_data: List[Dict]) -> go.Figure:
    """Create bar chart showing NPV by site"""
    
    sites = [d['site'] for d in portfolio_data]
    npv_values = [d.get('npv_m', 0) for d in portfolio_data]
    
    fig = go.Figure(data=[
        go.Bar(
            x=sites,
            y=npv_values,
            marker_color='#10b981',
            text=[f"${v:.1f}M" for v in npv_values],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Net Present Value by Site",
        xaxis_title="Site",
        yaxis_title="NPV ($M)",
        height=400,
        showlegend=False
    )
    
    return fig


def create_irr_chart(portfolio_data: List[Dict]) -> go.Figure:
    """Create horizontal bar chart showing IRR comparison"""
    
    sites = [d['site'] for d in portfolio_data]
    irr_values = [d.get('irr_pct', 0) for d in portfolio_data]
    
    fig = go.Figure(data=[
        go.Bar(
            x=irr_values,
            y=sites,
            orientation='h',
            marker_color='#3b82f6',
            text=[f"{v:.1f}%" for v in irr_values],
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Internal Rate of Return by Site",
        xaxis_title="IRR (%)",
        yaxis_title="Site",
        height=400,
        showlegend=False
    )
    
    return fig


def create_lcoe_capacity_bubble(portfolio_data: List[Dict]) -> go.Figure:
    """Create bubble chart showing LCOE vs Capacity (size = CapEx)"""
    
    sites = [d['site'] for d in portfolio_data]
    lcoe_values = [d.get('lcoe', 0) for d in portfolio_data]
    capacity_values = [d.get('capacity_mw', 0) for d in portfolio_data]
    capex_values = [d.get('capex_m', 0) for d in portfolio_data]
    
    fig = go.Figure(data=[
        go.Scatter(
            x=capacity_values,
            y=lcoe_values,
            mode='markers+text',
            marker=dict(
                size=[c * 0.5 for c in capex_values],  # Scale bubble size
                color=capex_values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="CapEx ($M)")
            ),
            text=sites,
            textposition='top center'
        )
    ])
    
    fig.update_layout(
        title="LCOE vs Capacity (Bubble Size = CapEx)",
        xaxis_title="IT Capacity (MW)",
        yaxis_title="LCOE ($/MWh)",
        height=400,
        showlegend=False
    )
    
    return fig


def create_cash_flow_waterfall(site_data: Dict) -> go.Figure:
    """Create waterfall chart showing cash flow breakdown"""
    
    capex = -site_data.get('capex_m', 0)
    opex_annual = -site_data.get('opex_annual_m', 0) * 20  # 20-year total
    revenue_estimate = abs(capex) + abs(opex_annual) + site_data.get('npv_m', 0)
    
    fig = go.Figure(data=[
        go.Waterfall(
            x=["Initial\nCapEx", "20-Year\nOpEx", "Revenue\n(Est.)", "Net\nNPV"],
            y=[capex, opex_annual, revenue_estimate, site_data.get('npv_m', 0)],
            measure=["relative", "relative", "relative", "total"],
            text=[f"${abs(capex):.1f}M", f"${abs(opex_annual):.1f}M", 
                  f"${revenue_estimate:.1f}M", f"${site_data.get('npv_m', 0):.1f}M"],
            textposition="outside",
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#3b82f6"}}
        )
    ])
    
    fig.update_layout(
        title=f"Cash Flow Analysis - {site_data.get('site', 'Site')}",
        yaxis_title="Cash Flow ($M)",
        height=400,
        showlegend=False
    )
    
    return fig
