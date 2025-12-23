"""
Form Components
Input forms and controls
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable


def equipment_card(
    equipment: Dict[str, Any],
    selected: bool = False,
    quantity: int = 0,
    on_quantity_change: Optional[Callable] = None,
    key_prefix: str = "",
):
    """
    Display an equipment card with selection and quantity
    
    Args:
        equipment: Equipment data dict
        selected: Whether equipment is selected
        quantity: Current quantity
        on_quantity_change: Callback for quantity changes
        key_prefix: Prefix for widget keys
    """
    border_color = "#F18F01" if selected else "#dee2e6"
    bg_color = "#fffaf5" if selected else "#ffffff"
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(
                f"""
                <div style="border: 2px solid {border_color}; border-radius: 8px; 
                            padding: 12px; background: {bg_color};">
                    <div style="font-weight: 600; font-size: 13px;">{equipment.get('name', 'Unknown')}</div>
                    <div style="font-size: 10px; color: #666; margin-bottom: 8px;">
                        {equipment.get('manufacturer', '')} • {equipment.get('model', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Specs grid
            specs = [
                ("Capacity", f"{equipment.get('capacity_mw', 0)} MW"),
                ("Efficiency", f"{equipment.get('efficiency_pct', 0)}%"),
                ("Start Time", f"{equipment.get('start_time_cold_min', 0)} min"),
                ("Lead Time", f"{equipment.get('lead_time_months_min', 0)}-{equipment.get('lead_time_months_max', 0)} mo"),
            ]
            
            cols = st.columns(4)
            for i, (label, value) in enumerate(specs):
                with cols[i]:
                    st.markdown(
                        f"<small style='color: #666;'>{label}</small><br><b>{value}</b>",
                        unsafe_allow_html=True
                    )
        
        with col2:
            new_qty = st.number_input(
                "Qty",
                min_value=0,
                max_value=20,
                value=quantity,
                key=f"{key_prefix}_{equipment.get('id', 'unknown')}_qty",
                label_visibility="collapsed"
            )
            
            if on_quantity_change and new_qty != quantity:
                on_quantity_change(equipment.get('id'), new_qty)
        
        st.markdown("---")


def constraint_form(
    constraints: Dict[str, Any],
    key_prefix: str = "constraints",
) -> Dict[str, Any]:
    """
    Display constraint input form
    
    Args:
        constraints: Current constraint values
        key_prefix: Prefix for widget keys
    
    Returns:
        Updated constraint dict
    """
    updated = constraints.copy()
    
    st.markdown("##### Capacity & Reliability")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        updated['min_capacity_mw'] = st.number_input(
            "Min Capacity (MW)",
            value=constraints.get('min_capacity_mw', 200),
            min_value=10,
            max_value=2000,
            key=f"{key_prefix}_min_cap"
        )
    
    with col2:
        updated['reserve_margin_pct'] = st.number_input(
            "Reserve Margin (%)",
            value=constraints.get('reserve_margin_pct', 10),
            min_value=0,
            max_value=50,
            key=f"{key_prefix}_reserve"
        )
    
    with col3:
        updated['n_minus_1'] = st.selectbox(
            "N-1 Contingency",
            ["Required", "N-2", "Not Required"],
            index=0 if constraints.get('n_minus_1', True) else 2,
            key=f"{key_prefix}_n1"
        ) == "Required"
    
    with col4:
        updated['min_availability_pct'] = st.number_input(
            "Min Availability (%)",
            value=float(constraints.get('min_availability_pct', 99.9)),
            min_value=95.0,
            max_value=99.999,
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_avail"
        )
    
    st.markdown("##### Performance & Timeline")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        updated['min_ramp_rate_mw_s'] = st.number_input(
            "Min Ramp Rate (MW/s)",
            value=float(constraints.get('min_ramp_rate_mw_s', 1.0)),
            min_value=0.1,
            max_value=10.0,
            step=0.1,
            key=f"{key_prefix}_ramp"
        )
    
    with col2:
        updated['max_time_to_power_months'] = st.number_input(
            "Max Time-to-Power (mo)",
            value=constraints.get('max_time_to_power_months', 24),
            min_value=6,
            max_value=60,
            key=f"{key_prefix}_time"
        )
    
    with col3:
        updated['max_nox_tpy'] = st.number_input(
            "Max NOx (tpy)",
            value=constraints.get('max_nox_tpy', 99),
            min_value=0,
            max_value=500,
            help="99 tpy = minor source threshold",
            key=f"{key_prefix}_nox"
        )
    
    with col4:
        updated['max_lcoe_per_mwh'] = st.number_input(
            "Max LCOE ($/MWh)",
            value=constraints.get('max_lcoe_per_mwh', 85),
            min_value=30,
            max_value=200,
            key=f"{key_prefix}_lcoe"
        )
    
    return updated


def workload_slider(
    workload_key: str,
    workload_info: Dict[str, Any],
    current_value: float,
    it_capacity_mw: float,
    key_prefix: str = "workload",
) -> float:
    """
    Display a workload slider with info
    
    Args:
        workload_key: Workload identifier
        workload_info: Workload characteristics dict
        current_value: Current percentage (0-1)
        it_capacity_mw: IT capacity for MW calculation
        key_prefix: Widget key prefix
    
    Returns:
        New percentage value (0-1)
    """
    col_color, col_slider, col_value, col_mw = st.columns([0.5, 6, 1, 1])
    
    with col_color:
        st.markdown(
            f"""
            <div style="width: 16px; height: 16px; 
                        background: {workload_info.get('color', '#999')}; 
                        border-radius: 4px; margin-top: 8px;"></div>
            """,
            unsafe_allow_html=True
        )
    
    with col_slider:
        new_value = st.slider(
            workload_info.get('name', workload_key),
            min_value=0,
            max_value=100,
            value=int(current_value * 100),
            key=f"{key_prefix}_{workload_key}",
            help=workload_info.get('description', ''),
        )
    
    with col_value:
        st.markdown(f"**{new_value}%**")
    
    with col_mw:
        mw = it_capacity_mw * (new_value / 100)
        st.markdown(f"*{mw:.0f} MW*")
    
    return new_value / 100
