"""Interactive Plotly Single Line Diagram"""
import plotly.graph_objects as go
from typing import Dict

def create_interactive_single_line_diagram(config: Dict):
    """Generate interactive Plotly single line diagram with zoom capability."""
    
    # Extract equipment counts
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    bess_mw = config.get('bess_mw', 0)
    solar_mw = config.get('solar_mw', 0)
    peak_load = config.get('peak_load_mw', 200)
    
    fig = go.Figure()
    
    # Main bus (horizontal line)
    fig.add_trace(go.Scatter(
        x=[50, 850], y=[250, 250],
        mode='lines',
        line=dict(color='black', width=5),
        hoverinfo='skip', showlegend=False
    ))
    
    fig.add_annotation(x=450, y=280, text="<b>MAIN BUS (13.8 kV)</b>", showarrow=False, font=dict(size=16))
    
    # Recip engines
    for i in range(min(n_recip, 8)):
        x = 100 + i * 80
        fig.add_trace(go.Scatter(x=[x, x], y=[250, 120], mode='lines', line=dict(color='gray', width=3), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[100], mode='markers+text',
            marker=dict(size=50, color='#4CAF50', line=dict(color='black', width=3)),
            text='G', textposition='middle center', textfont=dict(size=18, color='white'),
            hovertemplate=f'<b>Recip {i+1}</b><br>18.3 MW<extra></extra>', showlegend=False
        ))
        fig.add_annotation(x=x, y=70, text=f"<b>R{i+1}</b>", showarrow=False, font=dict(size=14))
        fig.add_annotation(x=x, y=55, text="<b>18.3 MW</b>", showarrow=False, font=dict(size=12, color='#666'))  # NEW: MW label
    
    # Solar
    if solar_mw > 0:
        x = 350
        fig.add_trace(go.Scatter(x=[x, x], y=[250, 120], mode='lines', line=dict(color='gray', width=3), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[100], mode='markers+text',
            marker=dict(size=60, color='#FFA726', symbol='square', line=dict(color='black', width=3)),
            text='☀', textposition='middle center', textfont=dict(size=28, color='white'),
            hovertemplate=f'<b>Solar PV</b><br>{solar_mw:.0f} MW<extra></extra>', showlegend=False
        ))
        fig.add_annotation(x=x, y=65, text=f"<b>SOLAR<br>{solar_mw:.0f} MW</b>", showarrow=False, font=dict(size=14))
    
    # Turbines
    for i in range(min(n_turbine, 4)):
        x = 550 + i * 90
        fig.add_trace(go.Scatter(x=[x, x], y=[250, 120], mode='lines', line=dict(color='gray', width=3), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[100], mode='markers+text',
            marker=dict(size=55, color='#4CAF50', line=dict(color='black', width=3)),
            text='G', textposition='middle center', textfont=dict(size=20, color='white'),
            hovertemplate=f'<b>Turbine {i+1}</b><br>50 MW<extra></extra>', showlegend=False
        ))
        fig.add_annotation(x=x, y=70, text=f"<b>GT{i+1}</b>", showarrow=False, font=dict(size=14))
        fig.add_annotation(x=x, y=55, text="<b>50 MW</b>", showarrow=False, font=dict(size=12, color='#666'))  # NEW: MW label
    
    # BESS
    if bess_mw > 0:
        x = 200
        fig.add_trace(go.Scatter(x=[x, x], y=[250, 380], mode='lines', line=dict(color='gray', width=3), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[400], mode='markers+text',
            marker=dict(size=70, color='#2196F3', symbol='square', line=dict(color='black', width=3)),
            text='BESS', textposition='middle center', textfont=dict(size=16, color='white'),
            hovertemplate=f'<b>BESS</b><br>{bess_mw:.0f} MW<extra></extra>', showlegend=False
        ))
        fig.add_annotation(x=x, y=440, text=f"<b>{bess_mw:.0f} MW</b>", showarrow=False, font=dict(size=14))
    
    # Load
    x = 650
    fig.add_trace(go.Scatter(x=[x, x], y=[250, 380], mode='lines', line=dict(color='gray', width=3), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(
        x=[x], y=[400], mode='markers',
        marker=dict(size=60, color='#f44336', symbol='triangle-down', line=dict(color='black', width=3)),
        hovertemplate=f'<b>Datacenter</b><br>{peak_load:.0f} MW<extra></extra>', showlegend=False
    ))
    fig.add_annotation(x=x, y=445, text=f"<b>DATACENTER<br>{peak_load:.0f} MW</b>", showarrow=False, font=dict(size=14))
    
    fig.update_layout(
        title=dict(text=f"<b>{config.get('project_name', 'Datacenter')}</b><br>{peak_load:.0f} MW Peak Load | 13.8 kV", x=0.5, xanchor='center', font=dict(size=22)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-20, 900]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[40, 480]),
        plot_bgcolor='white', paper_bgcolor='white',
        height=450, hovermode='closest', showlegend=False,  # Reduced from 650
        margin=dict(l=20, r=20, t=100, b=20)
    )
    
    return fig
