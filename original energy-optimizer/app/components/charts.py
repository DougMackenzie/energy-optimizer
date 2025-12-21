"""
Chart Components
Plotly charts for visualization
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any


def pareto_chart(
    scenarios: List[Dict],
    x_metric: str = "time_to_power_months",
    y_metric: str = "lcoe_per_mwh",
    color_metric: str = "capex_million",
    selected_id: Optional[str] = None,
    height: int = 350,
) -> go.Figure:
    """
    Create Pareto frontier chart
    
    Args:
        scenarios: List of scenario dicts with metrics
        x_metric: Metric for x-axis
        y_metric: Metric for y-axis
        color_metric: Metric for color scale
        selected_id: ID of selected scenario to highlight
        height: Chart height in pixels
    """
    fig = go.Figure()
    
    # Separate Pareto and non-Pareto
    pareto = [s for s in scenarios if s.get("is_pareto_optimal", False)]
    non_pareto = [s for s in scenarios if not s.get("is_pareto_optimal", False)]
    
    # Non-Pareto points (gray)
    if non_pareto:
        fig.add_trace(go.Scatter(
            x=[s.get(x_metric, 0) for s in non_pareto],
            y=[s.get(y_metric, 0) for s in non_pareto],
            mode='markers',
            marker=dict(size=8, color='#cccccc', line=dict(color='#999', width=1)),
            name='Non-Pareto',
            hovertemplate='%{text}<extra></extra>',
            text=[s.get("name", "") for s in non_pareto],
        ))
    
    # Pareto points
    if pareto:
        # Sort by x for line
        pareto_sorted = sorted(pareto, key=lambda s: s.get(x_metric, 0))
        
        fig.add_trace(go.Scatter(
            x=[s.get(x_metric, 0) for s in pareto_sorted],
            y=[s.get(y_metric, 0) for s in pareto_sorted],
            mode='markers+lines',
            marker=dict(
                size=12,
                color=[s.get(color_metric, 0) for s in pareto_sorted],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=color_metric.replace("_", " ").title(), thickness=15),
                line=dict(color='white', width=2),
            ),
            line=dict(color='#2E86AB', width=2, dash='dot'),
            name='Pareto Optimal',
            hovertemplate='%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>',
            text=[s.get("name", "") for s in pareto_sorted],
        ))
    
    # Highlight selected
    if selected_id:
        selected = next((s for s in scenarios if s.get("id") == selected_id), None)
        if selected:
            fig.add_trace(go.Scatter(
                x=[selected.get(x_metric, 0)],
                y=[selected.get(y_metric, 0)],
                mode='markers',
                marker=dict(size=16, color='#F18F01', symbol='circle',
                           line=dict(color='white', width=3)),
                name='Selected',
                hovertemplate=f'⭐ {selected.get("name", "")}<extra></extra>',
            ))
    
    # Labels
    x_label = x_metric.replace("_", " ").title()
    y_label = y_metric.replace("_", " ").title()
    
    fig.update_layout(
        height=height,
        margin=dict(l=50, r=20, t=20, b=50),
        xaxis_title=x_label,
        yaxis_title=y_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode='closest',
    )
    
    return fig


def dispatch_chart(
    data: pd.DataFrame,
    height: int = 300,
    show_load_line: bool = True,
) -> go.Figure:
    """
    Create stacked area dispatch chart
    
    Args:
        data: DataFrame with columns for each source and 'load'
        height: Chart height
        show_load_line: Whether to show load demand line
    """
    fig = go.Figure()
    
    colors = {
        'grid': '#6c757d',
        'engines': '#2E86AB',
        'bess': '#F18F01',
        'solar': '#28A745',
    }
    
    # Add traces in order (bottom to top)
    sources = ['grid', 'engines', 'bess', 'solar']
    cumulative = np.zeros(len(data))
    
    for source in sources:
        if source in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=cumulative + data[source],
                fill='tonexty' if source != 'grid' else 'tozeroy',
                name=source.title(),
                line=dict(color=colors.get(source, '#999')),
                fillcolor=colors.get(source, '#999'),
            ))
            cumulative = cumulative + data[source]
    
    # Load line
    if show_load_line and 'load' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['load'],
            mode='lines',
            name='Load',
            line=dict(color='#DC3545', width=2, dash='dash'),
        ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode='x unified',
    )
    
    return fig


def stacked_area_chart(
    x: List,
    series: Dict[str, List],
    colors: Optional[Dict[str, str]] = None,
    height: int = 250,
) -> go.Figure:
    """Simple stacked area chart"""
    fig = go.Figure()
    
    default_colors = ['#6c757d', '#2E86AB', '#F18F01', '#28A745', '#DC3545']
    
    for i, (name, values) in enumerate(series.items()):
        color = colors.get(name) if colors else default_colors[i % len(default_colors)]
        fig.add_trace(go.Scatter(
            x=x,
            y=values,
            fill='tonexty' if i > 0 else 'tozeroy',
            name=name,
            line=dict(color=color),
        ))
    
    fig.update_layout(height=height, margin=dict(l=40, r=20, t=20, b=40))
    return fig


def transient_chart(
    seconds: np.ndarray,
    load: np.ndarray,
    bess: np.ndarray,
    engines: np.ndarray,
    event_time: float = 15.0,
    event_label: str = "Step load event",
    height: int = 300,
) -> go.Figure:
    """
    Create sub-second transient response chart
    """
    fig = go.Figure()
    
    # Combined output
    combined = bess + engines
    
    # Load
    fig.add_trace(go.Scatter(
        x=seconds, y=load,
        mode='lines', name='Load',
        line=dict(color='#DC3545', width=2, dash='dash'),
    ))
    
    # BESS
    fig.add_trace(go.Scatter(
        x=seconds, y=bess,
        mode='lines', name='BESS',
        line=dict(color='#F18F01', width=2.5),
    ))
    
    # Engines
    fig.add_trace(go.Scatter(
        x=seconds, y=engines,
        mode='lines', name='Engines',
        line=dict(color='#2E86AB', width=2.5),
    ))
    
    # Combined
    fig.add_trace(go.Scatter(
        x=seconds, y=combined,
        mode='lines', name='Combined',
        line=dict(color='#28A745', width=3),
    ))
    
    # Event marker
    fig.add_vline(
        x=event_time, 
        line_dash="dash", 
        line_color="#DC3545",
        annotation_text=event_label,
        annotation_position="top right",
    )
    
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis_title="Seconds",
        yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    return fig
