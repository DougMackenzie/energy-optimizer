"""
Dispatch Analysis Page
8760 annual dispatch and sub-second transient view
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd


def render():
    st.markdown("### ⚙️ Dispatch Analysis")
    
    col_header, col_actions = st.columns([3, 1])
    with col_actions:
        scenario = st.selectbox(
            "Scenario",
            ["Scenario A: Recip-Heavy", "Scenario B: Hybrid", "Scenario C: Grid-Primary"],
            label_visibility="collapsed"
        )
    
    # Summary metrics
    cols = st.columns(5)
    metrics = [
        ("Annual Generation", "1,401 GWh"),
        ("Engines", "892 GWh (63.7%)"),
        ("BESS", "124 GWh (8.9%)"),
        ("Solar", "110 GWh (7.9%)"),
        ("Grid", "275 GWh (19.6%)"),
    ]
    
    for i, (label, value) in enumerate(metrics):
        with cols[i]:
            st.metric(label, value)
    
    st.markdown("---")
    
    # Zoom Path
    st.markdown("##### 🔍 Zoom Level")
    zoom_cols = st.columns(8)
    zoom_levels = ["Year", "→", "Jul", "→", "Week 28", "→", "Jul 15", "→ 14:32"]
    
    selected_zoom = st.radio(
        "Zoom",
        ["Year", "Month", "Week", "Day", "Hour", "Seconds"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Dual chart view
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 8760 Annual Dispatch")
        
        # Generate synthetic 8760 data
        hours = np.arange(8760)
        
        # Seasonal pattern (cooling load higher in summer)
        seasonal = 20 * np.sin(2 * np.pi * hours / 8760 - np.pi/2)
        
        # Daily pattern
        daily = 15 * np.sin(2 * np.pi * hours / 24 - np.pi/3)
        
        # Base load
        base_load = 160
        
        # Total load
        load = base_load + seasonal + daily + np.random.randn(8760) * 5
        
        # Dispatch (simplified)
        solar = np.maximum(0, 30 * np.sin(2 * np.pi * (hours % 24) / 24 - np.pi/2)) * (1 + 0.2 * np.sin(2 * np.pi * hours / 8760))
        grid = np.ones(8760) * 30
        bess = np.abs(np.sin(2 * np.pi * hours / 24)) * 15
        engines = load - solar - grid - bess
        engines = np.maximum(0, engines)
        
        # Aggregate to monthly for cleaner viz
        monthly_data = pd.DataFrame({
            'hour': hours,
            'load': load,
            'solar': solar,
            'bess': bess,
            'engines': engines,
            'grid': grid,
        })
        monthly_data['month'] = (monthly_data['hour'] // 730).astype(int)
        monthly_avg = monthly_data.groupby('month').mean()
        
        fig1 = go.Figure()
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        fig1.add_trace(go.Scatter(
            x=months, y=monthly_avg['grid'], 
            fill='tozeroy', name='Grid', 
            line=dict(color='#6c757d'), fillcolor='rgba(108,117,125,0.7)'
        ))
        fig1.add_trace(go.Scatter(
            x=months, y=monthly_avg['grid'] + monthly_avg['engines'], 
            fill='tonexty', name='Engines', 
            line=dict(color='#2E86AB'), fillcolor='rgba(46,134,171,0.8)'
        ))
        fig1.add_trace(go.Scatter(
            x=months, y=monthly_avg['grid'] + monthly_avg['engines'] + monthly_avg['bess'], 
            fill='tonexty', name='BESS', 
            line=dict(color='#F18F01'), fillcolor='rgba(241,143,1,0.8)'
        ))
        fig1.add_trace(go.Scatter(
            x=months, y=monthly_avg['grid'] + monthly_avg['engines'] + monthly_avg['bess'] + monthly_avg['solar'], 
            fill='tonexty', name='Solar', 
            line=dict(color='#28A745'), fillcolor='rgba(40,167,69,0.8)'
        ))
        
        # Load line
        fig1.add_trace(go.Scatter(
            x=months, y=monthly_avg['load'],
            mode='lines', name='Load',
            line=dict(color='#DC3545', width=2, dash='dash')
        ))
        
        fig1.update_layout(
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            yaxis_title="MW",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        st.caption("Click on July to zoom in → See peak summer operation")
    
    with col2:
        st.markdown("#### Sub-Second Detail")
        
        # Generate sub-second data
        seconds = np.linspace(0, 60, 600)
        
        # Simulate a step load event at t=15s
        step_time = 15
        step_size = 20  # MW
        
        # Load demand (step at t=15)
        load_ss = 160 * np.ones(600)
        load_ss[seconds >= step_time] = 160 + step_size
        
        # BESS response (instant, then decay as engines ramp)
        bess_ss = 15 * np.ones(600)
        bess_response = np.zeros(600)
        for i, t in enumerate(seconds):
            if t >= step_time:
                # BESS jumps instantly, then decays as engines take over
                time_since_step = t - step_time
                bess_response[i] = step_size * np.exp(-time_since_step / 20)
        bess_ss = bess_ss + bess_response
        
        # Engine response (slow ramp)
        engine_ss = 115 * np.ones(600)
        engine_ramp = np.zeros(600)
        for i, t in enumerate(seconds):
            if t >= step_time:
                time_since_step = t - step_time
                # Engines ramp up over ~45 seconds
                engine_ramp[i] = step_size * (1 - np.exp(-time_since_step / 15))
        engine_ss = engine_ss + engine_ramp
        
        # Combined output
        combined = bess_ss + engine_ss + 30  # +30 for grid baseline
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=seconds, y=load_ss,
            mode='lines', name='Load',
            line=dict(color='#DC3545', width=2, dash='dash')
        ))
        
        fig2.add_trace(go.Scatter(
            x=seconds, y=bess_ss,
            mode='lines', name='BESS',
            line=dict(color='#F18F01', width=2.5)
        ))
        
        fig2.add_trace(go.Scatter(
            x=seconds, y=engine_ss,
            mode='lines', name='Engines',
            line=dict(color='#2E86AB', width=2.5)
        ))
        
        fig2.add_trace(go.Scatter(
            x=seconds, y=combined,
            mode='lines', name='Combined',
            line=dict(color='#28A745', width=3)
        ))
        
        # Add event marker
        fig2.add_vline(x=step_time, line_dash="dash", line_color="#DC3545", 
                       annotation_text="GPU batch start (+20 MW)", annotation_position="top right")
        
        fig2.update_layout(
            height=300,
            margin=dict(l=40, r=20, t=30, b=40),
            xaxis_title="Seconds",
            yaxis_title="MW",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            title=dict(text="Jul 15, 2026 • 14:32:00 - 14:33:00", font=dict(size=11)),
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("20 MW step load at :15 • BESS responds in <100ms • Engines ramp over 45s")
    
    st.markdown("---")
    
    # Operating Statistics
    st.markdown("#### Equipment Operating Statistics")
    
    stats_data = {
        "Equipment": ["Wärtsilä #1-4 (Base)", "Wärtsilä #5-6 (Peak)", "BESS 100 MWh", "Solar PV", "Grid Import"],
        "Capacity": ["75.2 MW", "37.6 MW", "25 MW", "50 MW", "150 MW"],
        "Hours": ["7,800", "2,400", "4,960", "2,628", "8,760"],
        "CF": ["89%", "27%", "57%", "25%", "21%"],
        "Starts/yr": ["52", "365", "730", "365", "—"],
        "Avg Output": ["67 MW", "32 MW", "17 MW", "42 MW", "31 MW"],
        "Fuel/Energy": ["4.2M MMBtu", "0.9M MMBtu", "124 GWh cycled", "—", "275 GWh"],
    }
    
    st.dataframe(stats_data, use_container_width=True, hide_index=True)
    
    # Export buttons
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.button("📥 Export 8760 CSV", use_container_width=True)
    with col_b:
        st.button("📄 Export Report", use_container_width=True)
    with col_c:
        st.button("📊 Export Charts", use_container_width=True)


if __name__ == "__main__":
    render()
