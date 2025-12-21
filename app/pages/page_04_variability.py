"""
Load Variability Analysis Page
Analyze workload volatility and seasonal patterns
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def render():
    st.markdown("### 📊 Load Variability Analysis")
    st.caption("Analyze workload volatility, seasonal patterns, and demand variability")
    
    # Get load profile from session state
    if 'load_profile' not in st.session_state:
        st.warning("⚠️ No load profile defined. Please configure in Load Composer first.")
        
        if st.button("📈 Go to Load Composer", type="primary"):
            st.session_state.current_page = 'load_composer'
            st.rerun()
        
        return
    
    load_config = st.session_state.load_profile
    
    st.markdown("#### Workload Variability Characteristics")
    
    # Display current workload mix
    workload_mix = load_config.get('workload_mix', {})
    
    col_wl1, col_wl2 = st.columns(2)
    
    with col_wl1:
        st.markdown("##### Current Workload Mix")
        
        # Pie chart of workload mix
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(workload_mix.keys()),
            values=list(workload_mix.values()),
            hole=0.3
        )])
        fig_pie.update_layout(title="Workload Distribution", height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_wl2:
        st.markdown("##### Variability Characteristics")
        
        # Calculate weighted variability
        variability_by_type = {
            'Training': 0.05,      # 5% variability (very stable)
            'Inference': 0.15,     # 15% variability (moderate)
            'HPC': 0.08,          # 8% variability (stable)
            'Enterprise': 0.25    # 25% variability (volatile)
        }
        
        weighted_variability = sum(
            workload_mix.get(wl, 0) / 100 * variability_by_type.get(wl, 0.1)
            for wl in workload_mix.keys()
        )
        
        st.metric("Weighted Variability", f"{weighted_variability:.1%}")
        st.caption("Lower is more stable")
        
        predictability_by_type = {
            'Training': 0.95,
            'Inference': 0.75,
            'HPC': 0.90,
            'Enterprise': 0.60
        }
        
        weighted_predictability = sum(
            workload_mix.get(wl, 0) / 100 * predictability_by_type.get(wl, 0.75)
            for wl in workload_mix.keys()
        )
        
        st.metric("Predictability Score", f"{weighted_predictability:.1%}")
        st.caption("Higher is more predictable")
    
    # Seasonal analysis
    st.markdown("---")
    st.markdown("#### 📅 Seasonal Patterns")
    
    col_sea1, col_sea2 = st.columns([2, 1])
    
    with col_sea1:
        # Generate sample seasonal load curve
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        base_load = load_config.get('it_capacity_mw', 100) * load_config.get('pue', 1.25)
        load_factor = load_config.get('load_factor', 75) / 100
        
        # Seasonal factors (cooling load higher in summer)
        seasonal_factors = [1.02, 1.01, 1.00, 0.98, 0.97, 1.03,
                           1.05, 1.06, 1.04, 1.00, 0.99, 1.01]
        
        monthly_loads = [base_load * load_factor * factor for factor in seasonal_factors]
        
        fig_seasonal = go.Figure()
        fig_seasonal.add_trace(go.Scatter(
            x=months,
            y=monthly_loads,
            mode='lines+markers',
            name='Monthly Avg Load',
            line=dict(color='blue', width=3),
            marker=dict(size=8)
        ))
        
        fig_seasonal.update_layout(
            title="Seasonal Load Variation",
            xaxis_title="Month",
            yaxis_title="Average Load (MW)",
            height=350
        )
        
        st.plotly_chart(fig_seasonal, use_container_width=True)
    
    with col_sea2:
        st.markdown("**Seasonal Drivers:**")
        st.markdown("""
        **Summer (Jun-Aug):**
        - Higher cooling loads
        - PUE increases 3-5%
        - Peak demand periods
        
        **Winter (Dec-Feb):**
        - Lower cooling loads
        - Best PUE performance
        - Variable heating needs
        
        **Spring/Fall:**
        - Moderate conditions
        - Optimal efficiency
        - Planned maintenance windows
        """)
    
    # Peak demand analysis
    st.markdown("---")
    st.markdown("#### ⚡ Peak Demand Analysis")
    
    col_peak1, col_peak2, col_peak3 = st.columns(3)
    
    with col_peak1:
        peak_load = base_load
        st.metric("Peak Load", f"{peak_load:.1f} MW")
        st.caption("Design capacity")
    
    with col_peak2:
        avg_load = base_load * load_factor
        st.metric("Average Load", f"{avg_load:.1f} MW")
        st.caption(f"{load_factor:.0%} load factor")
    
    with col_peak3:
        peak_to_avg_ratio = peak_load / avg_load if avg_load > 0 else 1
        st.metric("Peak/Avg Ratio", f"{peak_to_avg_ratio:.2f}x")
        st.caption("Load variation")
    
    # Daily load profile
    st.markdown("---")
    st.markdown("#### 🕐 Daily Load Profile")
    
    hours = list(range(24))
    
    # Typical datacenter has relatively flat profile, slight peak during business hours
    daily_factors = [
        0.95, 0.93, 0.92, 0.91, 0.92, 0.94,  # Midnight-6am
        0.97, 1.00, 1.02, 1.03, 1.04, 1.05,  # 6am-noon
        1.05, 1.04, 1.03, 1.04, 1.05, 1.04,  # Noon-6pm
        1.02, 1.00, 0.99, 0.98, 0.97, 0.96   # 6pm-midnight
    ]
    
    hourly_loads = [avg_load * factor for factor in daily_factors]
    
    fig_daily = go.Figure()
    fig_daily.add_trace(go.Scatter(
        x=hours,
        y=hourly_loads,
        mode='lines',
        name='Hourly Load',
        line=dict(color='green', width=2),
        fill='tozeroy'
    ))
    
    fig_daily.update_layout(
        title="Typical Daily Load Profile",
        xaxis_title="Hour of Day",
        yaxis_title="Load (MW)",
        height=350
    )
    
    st.plotly_chart(fig_daily, use_container_width=True)
    
    # Volatility metrics
    st.markdown("---")
    st.markdown("#### 📈 Volatility Metrics")
    
    col_vol1, col_vol2 = st.columns(2)
    
    with col_vol1:
        st.markdown("**Load Statistics:**")
        
        stats = pd.DataFrame({
            'Metric': ['Peak Load', 'Average Load', 'Minimum Load', 'Standard Deviation', 'Coefficient of Variation'],
            'Value': [
                f"{peak_load:.1f} MW",
                f"{avg_load:.1f} MW",
                f"{avg_load * 0.85:.1f} MW",
                f"{avg_load * 0.08:.1f} MW",
                f"{0.08:.1%}"
            ]
        })
        
        st.dataframe(stats, use_container_width=True, hide_index=True)
    
    with col_vol2:
        st.markdown("**Variability Impact:**")
        
        if weighted_variability < 0.10:
            st.success("✅ **Low Variability** - Excellent for baseload generation")
            st.caption("Stable load enables efficient operation")
        elif weighted_variability < 0.20:
            st.info("ℹ️ **Moderate Variability** - Well-suited for combined cycle")
            st.caption("Some load-following capability needed")
        else:
            st.warning("⚠️ **High Variability** - Requires flexible generation")
            st.caption("BESS and fast-ramping units recommended")
    
    # Recommendations
    st.markdown("---")
    st.markdown("#### 💡 Design Recommendations")
    
    if weighted_variability < 0.15:
        st.success("""
        **Stable Load Profile:**
        - Baseload generation (recip engines, turbines) well-suited
        - High capacity factors achievable (70-85%)
        - Predictive maintenance feasible
        - Lower reserve requirements
        """)
    else:
        st.warning("""
        **Variable Load Profile:**
        - Include BESS for load smoothing
        - Fast-ramping gas turbines recommended
        - Higher reserve margins (15-20%)
        - Real-time dispatch optimization critical
        """)


if __name__ == "__main__":
    render()
