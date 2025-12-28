"""Interactive Plotly RAM/RBD Diagram"""
import plotly.graph_objects as go
from typing import Dict

def create_interactive_rbd_diagram(config: Dict):
    """Generate interactive Plotly Reliability Block Diagram with all equipment."""
    
    # Extract equipment
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    bess_mw = config.get('bess_mw', 0)
    solar_mw = config.get('solar_mw', 0)
    peak_load = config.get('peak_load_mw', 200)
    
    n_thermal = n_recip + n_turbine
    
    fig = go.Figure()
    
    # Input arrow
    fig.add_annotation(x=10, y=50, text="<b>IN</b>", showarrow=False, font=dict(size=14))
    fig.add_trace(go.Scatter(
        x=[30, 80], y=[50, 50],
        mode='lines',
        line=dict(color='black', width=3),
        hoverinfo='skip', showlegend=False
    ))
    
    # === THERMAL GENERATION BLOCK (Parallel K-of-N) ===
    # Background box
    fig.add_shape(
        type="rect", x0=100, y0=5, x1=400, y1=95,
        line=dict(color='#388E3C', width=3),
        fillcolor='#e8f5e9'
    )
    fig.add_annotation(
        x=250, y=88, text="<b>Thermal Generation</b>",
        showarrow=False, font=dict(size=12, color='#388E3C')
    )
    fig.add_annotation(
        x=250, y=78, text=f"(K of N: {n_thermal-1} of {n_thermal} required)",
        showarrow=False, font=dict(size=10, color='#666')
    )
    
    # Individual generators
    y_pos = 70
    for i in range(min(n_recip, 6)):
        fig.add_shape(
            type="rect", x0=120, y0=y_pos-10, x1=240, y1=y_pos+10,
            line=dict(color='#1976D2', width=2),
            fillcolor='#e3f2fd'
        )
        fig.add_annotation(
            x=180, y=y_pos, text=f"Recip {i+1} (18.3 MW)",
            showarrow=False, font=dict(size=11)
        )
        y_pos -= 18
    
    for i in range(min(n_turbine, 3)):
        fig.add_shape(
            type="rect", x0=120, y0=y_pos-10, x1=240, y1=y_pos+10,
            line=dict(color='#1976D2', width=2),
            fillcolor='#e3f2fd'
        )
        fig.add_annotation(
            x=180, y=y_pos, text=f"GT {i+1} (50 MW)",
            showarrow=False, font=dict(size=11)
        )
        y_pos -= 18
    
    # Arrow from thermal
    fig.add_trace(go.Scatter(
        x=[400, 450], y=[50, 50],
        mode='lines',
        line=dict(color='black', width=3),
        hoverinfo='skip', showlegend=False
    ))
    
    # === RENEWABLE/STORAGE BLOCK (If present) ===
    if solar_mw > 0 or bess_mw > 0:
        fig.add_shape(
            type="rect", x0=100, y0=-75, x1=400, y1=-5,
            line=dict(color='#F57C00', width=3),
            fillcolor='#fff3e0'
        )
        fig.add_annotation(
            x=250, y=-12, text="<b>Renewable & Storage</b>",
            showarrow=False, font=dict(size=12, color='#F57C00')
        )
        fig.add_annotation(
            x=250, y=-22, text="(Supplemental)",
            showarrow=False, font=dict(size=10, color='#666')
        )
        
        y_pos = -30
        if solar_mw > 0:
            fig.add_shape(
                type="rect", x0=120, y0=y_pos-10, x1=240, y1=y_pos+10,
                line=dict(color='#FFA726', width=2),
                fillcolor='#fff3e0'
            )
            fig.add_annotation(
                x=180, y=y_pos, text=f"Solar PV ({solar_mw:.0f} MW)",
                showarrow=False, font=dict(size=11)
            )
            y_pos -= 20
        
        if bess_mw > 0:
            fig.add_shape(
                type="rect", x0=120, y0=y_pos-10, x1=240, y1=y_pos+10,
                line=dict(color='#2196F3', width=2),
                fillcolor='#e3f2fd'
            )
            fig.add_annotation(
                x=180, y=y_pos, text=f"BESS ({bess_mw:.0f} MW)",
                showarrow=False, font=dict(size=11)
            )
        
        # Arrow from renewable
        fig.add_trace(go.Scatter(
            x=[400, 450], y=[-40, -40],
            mode='lines',
            line=dict(color='black', width=2, dash='dot'),
            hoverinfo='skip', showlegend=False
        ))
    
    # === ELECTRICAL DISTRIBUTION (Series - All Required) ===
    fig.add_shape(
        type="rect", x0=470, y0=10, x1=670, y1=90,
        line=dict(color='#F57C00', width=3),
        fillcolor='#fff3e0'
    )
    fig.add_annotation(
        x=570, y=78, text="<b>Electrical Distribution</b>",
        showarrow=False, font=dict(size=12, color='#F57C00')
    )
    fig.add_annotation(
        x=570, y=68, text="(Series: All Required)",
        showarrow=False, font=dict(size=10, color='#666')
    )
    
    # Transformer
    fig.add_shape(
        type="rect", x0=490, y0=55, x1=650, y1=70,
        line=dict(color='#1976D2', width=2),
        fillcolor='#e3f2fd'
    )
    fig.add_annotation(
        x=570, y=62.5, text="Main Transformer",
        showarrow=False, font=dict(size=11)
    )
    
    # Switchgear
    fig.add_shape(
        type="rect", x0=490, y0=30, x1=650, y1=45,
        line=dict(color='#1976D2', width=2),
        fillcolor='#e3f2fd'
    )
    fig.add_annotation(
        x=570, y=37.5, text="Main Switchgear",
        showarrow=False, font=dict(size=11)
    )
    
    # Arrow to output
    fig.add_trace(go.Scatter(
        x=[670, 720], y=[50, 50],
        mode='lines',
        line=dict(color='black', width=3),
        hoverinfo='skip', showlegend=False
    ))
    
    # === OUTPUT (Datacenter) ===
    fig.add_shape(
        type="rect", x0=730, y0=30, x1=830, y1=70,
        line=dict(color='#1976D2', width=3),
        fillcolor='#e3f2fd'
    )
    fig.add_annotation(
        x=780, y=55, text=f"<b>DATACENTER</b><br>{peak_load:.0f} MW",
        showarrow=False, font=dict(size=12)
    )
    
    fig.add_trace(go.Scatter(
        x=[830, 860], y=[50, 50],
        mode='lines',
        line=dict(color='black', width=3),
        hoverinfo='skip', showlegend=False
    ))
    fig.add_annotation(x=875, y=50, text="<b>OUT</b>", showarrow=False, font=dict(size=14))
    
    # Layout
    fig.update_layout(
        title=dict(
            text=f"<b>Reliability Block Diagram - {config.get('project_name', 'System')}</b>",
            x=0.5, xanchor='center', font=dict(size=18)
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 900]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-80, 100]),
        plot_bgcolor='white', paper_bgcolor='white',
        height=400,
        hovermode=False,
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig
