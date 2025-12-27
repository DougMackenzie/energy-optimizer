"""
Load Variability Analysis Page
Analyze workload volatility and seasonal patterns
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def render_variability_content():
    """Render variability analysis content (for embedding in Load Composer)"""
    # Get load profile from session state (try both possible keys)
    if 'load_profile_dr' in st.session_state:
        load_config = st.session_state.load_profile_dr
    elif 'load_profile' in st.session_state:
        load_config = st.session_state.load_profile
    else:
        st.warning("⚠️ No load profile defined. Please configure load in the Basic Load tab first.")
        return
    
    workload_mix = load_config.get('workload_mix', {})
    
    col_wl1, col_wl2 = st.columns(2)
    
    with col_wl1:
        st.markdown("##### Current Workload Mix")
        
        if workload_mix and sum(workload_mix.values()) > 0:
            # Pie chart of workload mix
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(workload_mix.keys()),
                values=list(workload_mix.values()),
                hole=0.3
            )])
            fig_pie.update_layout(title="Workload Distribution", height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Configure workload mix in the Workload Mix tab to see distribution.")
    
    with col_wl2:
        st.markdown("##### Variability Characteristics")
        
        # Calculate weighted variability
        variability_by_type = {
            'pre_training': 0.05,
            'fine_tuning': 0.08,
            'batch_inference': 0.15,
            'realtime_inference': 0.20,
            'rl_training': 0.10,
            'cloud_hpc': 0.12,
        }
        
        total_weight = sum(workload_mix.values()) if workload_mix else 0
        if total_weight > 0:
            weighted_variability = sum(
                workload_mix.get(wl, 0) / total_weight * variability_by_type.get(wl, 0.1)
                for wl in workload_mix.keys()
            )
        else:
            weighted_variability = 0.1
        
        st.metric("Weighted Variability", f"{weighted_variability:.1%}")
        st.caption("Lower is more stable")
        
        predictability_by_type = {
            'pre_training': 0.95,
            'fine_tuning': 0.90,
            'batch_inference': 0.75,
            'realtime_inference': 0.70,
            'rl_training': 0.85,
            'cloud_hpc': 0.80,
        }
        
        if total_weight > 0:
            weighted_predictability = sum(
                workload_mix.get(wl, 0) / total_weight * predictability_by_type.get(wl, 0.75)
                for wl in workload_mix.keys()
            )
        else:
            weighted_predictability = 0.75
        
        st.metric("Predictability Score", f"{weighted_predictability:.1%}")
        st.caption("Higher is more predictable")
    
    # Variability impact
    st.markdown("---")
    st.markdown("#### Variability Impact")
    
    if weighted_variability < 0.10:
        st.success("✅ **Low Variability** - Excellent for baseload generation")
        st.caption("Stable load enables efficient operation")
    elif weighted_variability < 0.20:
        st.info("ℹ️ **Moderate Variability** - Well-suited for combined cycle")
        st.caption("Some load-following capability needed")
    else:
        st.warning("⚠️ **High Variability** - Requires flexible generation")
        st.caption("BESS and fast-ramping units recommended")


def render():
    """Full page render with title"""
    st.markdown("### 📊 Load Variability Analysis")
    st.caption("Analyze workload volatility, seasonal patterns, and demand variability")
    
    # Call the content function
    render_variability_content()


if __name__ == "__main__":
    render()
