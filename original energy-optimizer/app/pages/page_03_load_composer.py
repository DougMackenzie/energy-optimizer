"""
Load Composer Page
Define facility parameters and workload mix
"""

import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    DEFAULT_IT_CAPACITY_MW, DEFAULT_PUE, DEFAULT_RACK_UPS_SECONDS,
    DEFAULT_WORKLOAD_MIX, WORKLOAD_CHARACTERISTICS, PUE_SEASONAL, COLORS
)


def render():
    """Render the Load Composer page"""
    
    # Header
    col_header, col_actions = st.columns([3, 1])
    with col_header:
        st.markdown("### 📈 Load Composer")
    with col_actions:
        col_a, col_b = st.columns(2)
        with col_a:
            st.button("💾 Save", use_container_width=True)
        with col_b:
            if st.button("Next →", type="primary", use_container_width=True):
                st.session_state.current_page = 'variability'
                st.rerun()
    
    st.info(
        "💡 **Workload Composition:** Different AI workloads have dramatically different "
        "power characteristics. Pre-training is steady; inference is bursty. Mix workloads "
        "to model your actual facility load shape."
    )
    
    # ==========================================================================
    # Facility Parameters
    # ==========================================================================
    st.markdown("#### Facility Parameters")
    
    cols = st.columns(6)
    
    with cols[0]:
        it_capacity = st.number_input(
            "IT Capacity (MW)",
            min_value=10,
            max_value=2000,
            value=DEFAULT_IT_CAPACITY_MW,
            step=10,
            help="Total IT load capacity (before PUE)"
        )
    
    with cols[1]:
        design_pue = st.number_input(
            "Design PUE",
            min_value=1.05,
            max_value=2.0,
            value=DEFAULT_PUE,
            step=0.05,
            format="%.2f",
            help="Power Usage Effectiveness at design conditions"
        )
    
    with cols[2]:
        cooling_type = st.selectbox(
            "Cooling Type",
            options=["Air Cooled", "Direct Liquid (DLC)", "Immersion"],
            index=1
        )
    
    with cols[3]:
        rack_ups = st.selectbox(
            "Rack UPS",
            options=["None", "30 sec", "60 sec", "5 min"],
            index=1,
            help="Ride-through time for rack-level UPS"
        )
    
    with cols[4]:
        design_ambient = st.number_input(
            "Design Ambient (°F)",
            min_value=70,
            max_value=120,
            value=95,
            step=5
        )
    
    with cols[5]:
        total_facility = it_capacity * design_pue
        st.metric(
            label="Total Facility Load",
            value=f"{total_facility:.0f} MW",
            help="IT Capacity × PUE"
        )
    
    st.markdown("---")
    
    # ==========================================================================
    # Quick Presets
    # ==========================================================================
    st.markdown("#### Quick Presets")
    
    preset_cols = st.columns(4)
    
    presets = {
        "training": {
            "name": "🧠 Training Focused",
            "desc": "70% pre-train, 15% fine-tune, 15% other",
            "mix": {"pre_training": 0.70, "fine_tuning": 0.15, "batch_inference": 0.05, 
                    "realtime_inference": 0.05, "rl_training": 0.03, "cloud_hpc": 0.02}
        },
        "balanced": {
            "name": "⚖️ Balanced Mix",
            "desc": "40% train, 35% inference, 25% other",
            "mix": {"pre_training": 0.40, "fine_tuning": 0.15, "batch_inference": 0.20, 
                    "realtime_inference": 0.10, "rl_training": 0.05, "cloud_hpc": 0.10}
        },
        "inference": {
            "name": "🚀 Inference Heavy",
            "desc": "20% train, 60% inference, 20% cloud",
            "mix": {"pre_training": 0.15, "fine_tuning": 0.05, "batch_inference": 0.35, 
                    "realtime_inference": 0.25, "rl_training": 0.05, "cloud_hpc": 0.15}
        },
        "cloud": {
            "name": "☁️ Traditional Cloud",
            "desc": "80% traditional HPC/cloud workloads",
            "mix": {"pre_training": 0.05, "fine_tuning": 0.05, "batch_inference": 0.05, 
                    "realtime_inference": 0.05, "rl_training": 0.0, "cloud_hpc": 0.80}
        },
    }
    
    # Initialize workload mix in session state
    if 'workload_mix' not in st.session_state:
        st.session_state.workload_mix = DEFAULT_WORKLOAD_MIX.copy()
    
    for i, (key, preset) in enumerate(presets.items()):
        with preset_cols[i]:
            if st.button(preset['name'], use_container_width=True, key=f"preset_{key}"):
                st.session_state.workload_mix = preset['mix'].copy()
                st.rerun()
            st.caption(preset['desc'])
    
    st.markdown("---")
    
    # ==========================================================================
    # Workload Mix Sliders
    # ==========================================================================
    st.markdown("#### Workload Mix (% of IT Capacity)")
    
    col_sliders, col_summary = st.columns([3, 1])
    
    with col_sliders:
        workload_mix = {}
        total_pct = 0
        
        for wl_key, wl_info in WORKLOAD_CHARACTERISTICS.items():
            col_color, col_slider, col_value, col_mw = st.columns([0.5, 6, 1, 1])
            
            with col_color:
                st.markdown(
                    f"<div style='width: 16px; height: 16px; background: {wl_info['color']}; "
                    f"border-radius: 4px; margin-top: 8px;'></div>",
                    unsafe_allow_html=True
                )
            
            with col_slider:
                current_val = int(st.session_state.workload_mix.get(wl_key, 0) * 100)
                new_val = st.slider(
                    wl_info['name'],
                    min_value=0,
                    max_value=100,
                    value=current_val,
                    key=f"slider_{wl_key}",
                    help=wl_info['description']
                )
                workload_mix[wl_key] = new_val / 100
                total_pct += new_val
            
            with col_value:
                st.markdown(f"**{new_val}%**")
            
            with col_mw:
                mw_val = it_capacity * (new_val / 100)
                st.markdown(f"*{mw_val:.0f} MW*")
        
        # Update session state
        st.session_state.workload_mix = workload_mix
        
        # Validation
        if abs(total_pct - 100) > 1:
            st.warning(f"⚠️ Workload mix totals {total_pct}% (should be 100%)")
        else:
            st.success(f"✅ Workload mix: {total_pct}%")
        
        # Visualization bar
        st.markdown("**Workload Mix Visualization**")
        bar_html = '<div style="display: flex; height: 24px; border-radius: 4px; overflow: hidden;">'
        for wl_key, wl_info in WORKLOAD_CHARACTERISTICS.items():
            pct = workload_mix.get(wl_key, 0) * 100
            if pct > 0:
                bar_html += f'<div style="width: {pct}%; background: {wl_info["color"]}; display: flex; align-items: center; justify-content: center; color: white; font-size: 9px; font-weight: 600;">'
                if pct > 8:
                    bar_html += wl_info['name'].split()[0]
                bar_html += '</div>'
        bar_html += '</div>'
        st.markdown(bar_html, unsafe_allow_html=True)
    
    with col_summary:
        st.markdown("**Workload Characteristics**")
        
        # Calculate composite metrics
        weighted_util = sum(
            workload_mix.get(k, 0) * sum(v['utilization_range']) / 2
            for k, v in WORKLOAD_CHARACTERISTICS.items()
        )
        
        weighted_transient = sum(
            workload_mix.get(k, 0) * sum(v['transient_magnitude']) / 2
            for k, v in WORKLOAD_CHARACTERISTICS.items()
        )
        
        st.metric("Avg Utilization", f"{weighted_util*100:.0f}%")
        st.metric("Eff. Transient Mag", f"{weighted_transient:.1f}x")
        
        # Variability index
        var_scores = {"low": 1, "medium": 2, "high": 3, "very_high": 4}
        weighted_var = sum(
            workload_mix.get(k, 0) * var_scores.get(v['variability'], 2)
            for k, v in WORKLOAD_CHARACTERISTICS.items()
        )
        var_label = "Low" if weighted_var < 1.5 else "Medium" if weighted_var < 2.5 else "High" if weighted_var < 3.5 else "Very High"
        st.metric("Variability Index", var_label)
    
    st.markdown("---")
    
    # ==========================================================================
    # PUE Seasonal Variation
    # ==========================================================================
    st.markdown("#### PUE & Seasonal Variation")
    
    pue_cols = st.columns(4)
    
    seasonal_labels = [
        ("Winter Low", "winter_low", "#28A745"),
        ("Spring/Fall", "spring_fall", "#6c757d"),
        ("Summer Avg", "summer_avg", "#FFC107"),
        ("Summer Peak", "summer_peak", "#DC3545"),
    ]
    
    for i, (label, key, color) in enumerate(seasonal_labels):
        with pue_cols[i]:
            pue_val = PUE_SEASONAL[key]
            total_load = it_capacity * pue_val
            
            st.markdown(
                f"""
                <div style="text-align: center; padding: 12px; background: {color}20; 
                            border-radius: 6px; border: 1px solid {color}40;">
                    <div style="font-size: 11px; color: #666;">{label}</div>
                    <div style="font-size: 24px; font-weight: 700; color: {color};">{pue_val:.2f}</div>
                    <div style="font-size: 11px; color: #999;">{total_load:.0f} MW total</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Store load profile in session state
    st.session_state.project['load_profile'] = {
        'it_capacity_mw': it_capacity,
        'design_pue': design_pue,
        'cooling_type': cooling_type,
        'rack_ups': rack_ups,
        'design_ambient_f': design_ambient,
        'workload_mix': workload_mix,
        'total_facility_mw': total_facility,
    }


if __name__ == "__main__":
    render()
