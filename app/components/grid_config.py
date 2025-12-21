"""
Grid Interconnection Configuration Widget
Provides UI for configuring grid voltage levels, lead times, and capacity
"""

import streamlit as st
from typing import Dict


def render_grid_configuration(constraints: Dict, grid_enabled: bool = True) -> Dict:
    """
    Render grid interconnection configuration UI
    
    Args:
        constraints: Site constraints dictionary
        grid_enabled: Whether grid is enabled in the scenario
    
    Returns:
        grid_config: Dictionary with grid configuration
    """
    
    if not grid_enabled:
        # Return default configuration if grid not enabled
        return {
            'voltage_level': '345kV',
            'transformer_lead_months': 24,
            'breaker_lead_months': 18,
            'total_timeline_months': constraints.get('Estimated_Interconnection_Months', 96),
            'grid_capacity_override': None,
            'timeline_override': None,
            'grid_available_mw': constraints.get('Grid_Available_MW', 200)
        }
    
    st.markdown("#### 🔌 Grid Interconnection Configuration")
    st.caption("Configure grid voltage level and lead times for interconnection equipment")
    
    grid_col1, grid_col2, grid_col3 = st.columns(3)
    
    with grid_col1:
        voltage_level = st.selectbox(
            "Voltage Level",
            options=["138kV", "345kV", "500kV"],
            index=1,  # Default to 345kV
            key="grid_voltage_level",
            help="Higher voltage = more capacity but longer lead times"
        )
        
        # Calculate lead times based on voltage
        voltage_lead_times = {
            "138kV": {"transformer": 18, "breaker": 12, "total": 30},
            "345kV": {"transformer": 24, "breaker": 18, "total": 42},
            "500kV": {"transformer": 36, "breaker": 24, "total": 60}
        }
        
        lead_times = voltage_lead_times[voltage_level]
        
        st.metric("Transformer Lead Time", f"{lead_times['transformer']} mo")
        st.metric("Breaker Lead Time", f"{lead_times['breaker']} mo")
    
    with grid_col2:
        # Manual override for grid capacity
        use_manual_capacity = st.checkbox(
            "Override Grid Capacity",
            value=False,
            key="use_manual_grid_capacity",
            help="Manually specify available grid import capacity"
        )
        
        if use_manual_capacity:
            manual_grid_mw = st.number_input(
                "Manual Grid Capacity (MW)",
                min_value=0.0,
                max_value=1000.0,
                value=float(constraints.get('Grid_Available_MW', 200)),
                step=10.0,
                key="manual_grid_capacity_mw"
            )
            displayed_grid_capacity = manual_grid_mw
        else:
            displayed_grid_capacity = constraints.get('Grid_Available_MW', 200)
        
        st.metric("Available Grid Capacity", f"{displayed_grid_capacity} MW")
        
        # Show queue info
        queue_pos = constraints.get('Queue_Position', 'N/A')
        st.caption(f"📋 Queue Position: {queue_pos}")
    
    with grid_col3:
        # Manual override for timeline
        use_manual_timeline = st.checkbox(
            "Override Timeline",
            value=False,
            key="use_manual_timeline",
            help="Manually specify total interconnection timeline"
        )
        
        if use_manual_timeline:
            manual_timeline = st.number_input(
                "Manual Timeline (months)",
                min_value=0,
                max_value=240,
                value=constraints.get('Estimated_Interconnection_Months', 96),
                step=6,
                key="manual_interconnection_months"
            )
            displayed_timeline = manual_timeline
        else:
            displayed_timeline = lead_times['total']
        
        st.metric("Total Timeline", f"{displayed_timeline} mo ({displayed_timeline/12:.1f} yrs)")
        
        # Timeline color coding
        if displayed_timeline < 24:
            st.success("🚀 Fast")
        elif displayed_timeline < 48:
            st.info("⚡ Medium")
        else:
            st.warning("🐢 Slow")
    
    # Show comparison
    with st.expander("📊 Voltage Level Comparison", expanded=False):
        import pandas as pd
        
        comparison_data = []
        for voltage, times in voltage_lead_times.items():
            comparison_data.append({
                'Voltage': voltage,
                'Transformer (mo)': times['transformer'],
                'Breaker (mo)': times['breaker'],
                'Total (mo)': times['total'],
                'Total (yrs)': f"{times['total']/12:.1f}"
            })
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.info("""
        **Lead Time Factors:**
        - Transformer lead times are critical path for grid projects
        - 2025 supply chain: +80% price increase, 12-24mo delays common
        - Higher voltage = more capacity but exponentially longer lead times
        """)
    
    # Return configuration
    grid_config = {
        'voltage_level': voltage_level,
        'transformer_lead_months': lead_times['transformer'],
        'breaker_lead_months': lead_times['breaker'],
        'total_timeline_months': displayed_timeline,
        'grid_capacity_override': manual_grid_mw if use_manual_capacity else None,
        'timeline_override': manual_timeline if use_manual_timeline else None,
        'grid_available_mw': displayed_grid_capacity
    }
    
    return grid_config
