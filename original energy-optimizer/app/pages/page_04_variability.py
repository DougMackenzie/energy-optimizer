"""
Variability Analysis Page
Analyze load variability and mitigation stack
"""

import streamlit as st
import plotly.graph_objects as go

def render():
    st.markdown("### 📊 Variability Analysis")
    
    st.info(
        "💡 **Variability by Timescale:** Different timescales of load variation are handled "
        "by different parts of the power system. Understanding this helps size equipment correctly."
    )
    
    # Metrics row
    cols = st.columns(5)
    metrics = [
        ("Peak Facility Load", "216 MW", "Summer peak PUE"),
        ("Average Load", "156 MW", "72% avg utilization"),
        ("Minimum Load", "92 MW", "Winter night low"),
        ("Load Factor", "72%", None),
        ("Swing Range", "124 MW", "57% of peak"),
    ]
    
    for i, (label, value, delta) in enumerate(metrics):
        with cols[i]:
            st.metric(label=label, value=value, delta=delta)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Variability Mitigation Stack")
        
        layers = [
            ("⚡", "GPU/Chip Level", "VRMs, capacitors", "1 ns - 10 μs", False),
            ("🔌", "Rack PDU", "High-freq filtering", "10 μs - 1 ms", False),
            ("🔋", "Rack UPS (30s)", "KEY: Absorbs GPU startups", "1 ms - 30 s", True),
            ("🧠", "Algorithmic Mgmt", "Job scheduling, queuing", "1 s - 10 min", True),
            ("⚙️", "BTM BESS", "OPTIMIZER SIZES THIS", "100 ms - 15 min", True),
            ("🏭", "BTM Generation", "OPTIMIZER SIZES THIS", "2 min - 24 hr", True),
            ("🌡️", "Cooling/Seasonal", "PUE variation", "5 min - Months", False),
        ]
        
        for icon, name, detail, timescale, highlight in layers:
            bg_color = "#e6f4ff" if highlight else "#f8f9fa"
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; padding: 8px 12px; 
                            background: {bg_color}; border-radius: 6px; margin-bottom: 6px;
                            border: 1px solid #dee2e6;">
                    <div style="font-size: 18px; margin-right: 12px;">{icon}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 12px;">{name}</div>
                        <div style="font-size: 10px; color: #666;">{detail}</div>
                    </div>
                    <div style="font-family: monospace; font-size: 11px; color: #2E86AB;">{timescale}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown("#### What BTM Power System Sees")
        st.caption("After UPS & Algorithm Smoothing")
        
        # Create a simple comparison chart
        fig = go.Figure()
        
        import numpy as np
        x = np.linspace(0, 60, 200)
        raw = 160 + 40 * np.sin(x * 2) + 20 * np.sin(x * 10) + 10 * np.random.randn(200)
        smoothed = 160 + 15 * np.sin(x * 0.5)
        
        fig.add_trace(go.Scatter(x=x, y=raw, mode='lines', name='Raw IT Load',
                                  line=dict(color='#DC3545', width=1), opacity=0.4))
        fig.add_trace(go.Scatter(x=x, y=smoothed, mode='lines', name='After UPS Smoothing',
                                  line=dict(color='#28A745', width=2.5)))
        
        fig.update_layout(
            height=250,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis_title="Time (seconds)",
            yaxis_title="MW",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary stats
        st.markdown("##### Smoothing Effect")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Raw transient", "5.2x (83 MW)")
        with col_b:
            st.metric("After UPS", "1.8x (29 MW)")
        with col_c:
            st.metric("Reduction", "65%")
    
    st.markdown("---")
    
    # Residual variability table
    st.markdown("#### Residual Variability (What BTM Must Handle)")
    
    variability_data = {
        "Timescale": ["Sub-second", "1-30 sec", "30s - 5 min", "5 min - 1 hr", "Hourly", "Seasonal"],
        "Swing (MW)": ["±5 MW", "±15 MW", "±25 MW", "±40 MW", "±60 MW", "±30 MW"],
        "Ramp Rate": ["50 MW/s", "1 MW/s", "0.3 MW/s", "0.1 MW/s", "—", "—"],
        "Handled By": ["BESS", "BESS", "BESS + Engine", "Engine", "8760 Dispatch", "PUE/Cooling"],
    }
    
    st.dataframe(variability_data, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render()
