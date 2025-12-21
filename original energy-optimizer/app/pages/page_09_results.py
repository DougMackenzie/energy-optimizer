"""
Results Page
Optimization results, Pareto frontier, scenario comparison
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np


def render():
    st.markdown("### 📊 Optimization Results")
    
    # Summary metrics
    cols = st.columns(6)
    metrics = [
        ("Scenarios Analyzed", "100"),
        ("Feasible", "47"),
        ("Infeasible", "53"),
        ("Pareto Optimal", "12"),
        ("Best Time", "14 mo"),
        ("Best LCOE", "$62/MWh"),
    ]
    
    for i, (label, value) in enumerate(metrics):
        with cols[i]:
            color = "normal" if i not in [2] else "off"
            st.metric(label, value)
    
    st.markdown("---")
    
    # Constraint Violations
    st.markdown("#### Constraint Violations (Why 53 Scenarios Failed)")
    
    violations = [
        ("NOx Limit", 23, 43, "#DC3545"),
        ("Time-to-Power", 15, 28, "#FFC107"),
        ("Availability", 8, 15, "#FFC107"),
        ("Ramp Rate", 5, 9, "#2E86AB"),
        ("LCOE", 2, 4, "#2E86AB"),
    ]
    
    for label, count, pct, color in violations:
        cols = st.columns([2, 8, 1])
        with cols[0]:
            st.markdown(f"**{label}**")
        with cols[1]:
            st.markdown(
                f"""
                <div style="height: 20px; background: #f8f9fa; border-radius: 4px; overflow: hidden;">
                    <div style="width: {pct}%; height: 100%; background: {color}; 
                                display: flex; align-items: center; justify-content: flex-end; 
                                padding-right: 8px; color: white; font-size: 10px; font-weight: 600;">
                        {pct}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with cols[2]:
            st.markdown(f"**{count}**")
    
    st.markdown("---")
    
    # Pareto Frontier Chart
    st.markdown("#### Pareto Frontier: Time-to-Power vs LCOE")
    st.caption("Click points to select scenario • Color = CAPEX (dark = higher)")
    
    # Create Pareto chart
    fig = go.Figure()
    
    # Non-Pareto points (gray)
    fig.add_trace(go.Scatter(
        x=[18, 25, 32, 38],
        y=[70, 75, 72, 68],
        mode='markers',
        marker=dict(size=10, color='#cccccc', line=dict(color='#999999', width=1)),
        name='Non-Pareto',
        hovertemplate='Time: %{x} mo<br>LCOE: $%{y}/MWh'
    ))
    
    # Pareto points
    pareto_x = [10, 14, 18, 26, 34, 42, 50]
    pareto_y = [95, 68, 65, 62, 58, 56, 54]
    pareto_capex = [350, 295, 310, 280, 220, 180, 145]  # $M
    
    fig.add_trace(go.Scatter(
        x=pareto_x,
        y=pareto_y,
        mode='markers+lines',
        marker=dict(
            size=14,
            color=pareto_capex,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title='CAPEX ($M)', thickness=15, len=0.5),
            line=dict(color='white', width=2)
        ),
        line=dict(color='#2E86AB', width=2, dash='dot'),
        name='Pareto Optimal',
        hovertemplate='Time: %{x} mo<br>LCOE: $%{y}/MWh<br>CAPEX: $%{marker.color}M'
    ))
    
    # Highlight selected point
    fig.add_trace(go.Scatter(
        x=[14],
        y=[68],
        mode='markers',
        marker=dict(size=18, color='#F18F01', symbol='circle', 
                    line=dict(color='white', width=3)),
        name='Selected',
        hovertemplate='⭐ Scenario A<br>Time: 14 mo<br>LCOE: $68/MWh'
    ))
    
    fig.update_layout(
        height=350,
        margin=dict(l=50, r=20, t=20, b=50),
        xaxis_title="Time-to-Power (months)",
        yaxis_title="LCOE ($/MWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(range=[5, 55]),
        yaxis=dict(range=[50, 100]),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Scenario Cards
    st.markdown("#### Top Scenarios")
    
    cols = st.columns(3)
    
    scenarios = [
        {
            "name": "Scenario A: Recip-Heavy",
            "config": "6x Wärtsilä 50SG + 100 MWh BESS + 50 MW Solar",
            "optimal": True,
            "selected": True,
            "metrics": {"Time": ("14 mo", "success"), "LCOE": ("$68", None), 
                       "CAPEX": ("$295M", None), "Availability": ("99.92%", None),
                       "NOx": ("87 tpy", None), "Carbon": ("385 kg/MWh", None)}
        },
        {
            "name": "Scenario B: Hybrid",
            "config": "4x Recip + 2x LM2500 + 50 MWh BESS",
            "optimal": False,
            "selected": False,
            "metrics": {"Time": ("22 mo", "warning"), "LCOE": ("$62", "success"), 
                       "CAPEX": ("$310M", None), "Availability": ("99.95%", None),
                       "NOx": ("92 tpy", None), "Carbon": ("410 kg/MWh", None)}
        },
        {
            "name": "Scenario C: Grid-Primary",
            "config": "150 MW Grid + 2x Recip + 50 MWh BESS",
            "optimal": False,
            "selected": False,
            "metrics": {"Time": ("42 mo", "danger"), "LCOE": ("$55", "success"), 
                       "CAPEX": ("$145M", "success"), "Availability": ("99.97%", None),
                       "NOx": ("28 tpy", None), "Carbon": ("320 kg/MWh", None)}
        },
    ]
    
    for i, scenario in enumerate(scenarios):
        with cols[i]:
            border_color = "#F18F01" if scenario["selected"] else "#28A745" if scenario["optimal"] else "#dee2e6"
            bg_color = "#fffaf5" if scenario["selected"] else "#ffffff"
            
            st.markdown(
                f"""
                <div style="border: 2px solid {border_color}; border-radius: 8px; 
                            padding: 16px; background: {bg_color};">
                    {"<div style='font-size: 10px; color: #28A745; font-weight: 600; margin-bottom: 4px;'>⭐ Recommended</div>" if scenario["optimal"] else ""}
                    <div style="font-size: 13px; font-weight: 600; color: #1E3A5F;">{scenario["name"]}</div>
                    <div style="font-size: 10px; color: #666; margin-bottom: 12px;">{scenario["config"]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            for label, (value, status) in scenario["metrics"].items():
                color = "#28A745" if status == "success" else "#FFC107" if status == "warning" else "#DC3545" if status == "danger" else "#333"
                st.markdown(f"<small>{label}</small> <b style='color: {color};'>{value}</b>", 
                           unsafe_allow_html=True)


if __name__ == "__main__":
    render()
