"""
Table Components
Data tables and grids
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional


def equipment_table(
    equipment_list: List[Dict[str, Any]],
    show_columns: Optional[List[str]] = None,
):
    """
    Display equipment comparison table
    
    Args:
        equipment_list: List of equipment dicts
        show_columns: Columns to display (None for default)
    """
    if not equipment_list:
        st.info("No equipment to display")
        return
    
    default_columns = [
        'name', 'capacity_mw', 'efficiency_pct', 'heat_rate_btu_kwh',
        'start_time_cold_min', 'ramp_rate_mw_min', 'nox_lb_mwh',
        'lead_time_months_min', 'capex_per_kw'
    ]
    
    columns = show_columns or default_columns
    
    # Filter to available columns
    df = pd.DataFrame(equipment_list)
    available_cols = [c for c in columns if c in df.columns]
    
    if available_cols:
        display_df = df[available_cols].copy()
        
        # Rename columns for display
        column_names = {
            'name': 'Name',
            'capacity_mw': 'Capacity (MW)',
            'efficiency_pct': 'Efficiency (%)',
            'heat_rate_btu_kwh': 'Heat Rate',
            'start_time_cold_min': 'Start (min)',
            'ramp_rate_mw_min': 'Ramp (MW/min)',
            'nox_lb_mwh': 'NOx (lb/MWh)',
            'lead_time_months_min': 'Lead Time (mo)',
            'capex_per_kw': 'CAPEX ($/kW)',
        }
        display_df = display_df.rename(columns=column_names)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def scenario_table(
    scenarios: List[Dict[str, Any]],
    selected_id: Optional[str] = None,
):
    """
    Display scenario comparison table
    
    Args:
        scenarios: List of scenario dicts
        selected_id: ID of selected scenario to highlight
    """
    if not scenarios:
        st.info("No scenarios to display")
        return
    
    data = []
    for s in scenarios:
        row = {
            'Name': s.get('name', ''),
            'Time (mo)': s.get('time_to_power_months', 0),
            'LCOE ($/MWh)': f"${s.get('lcoe_per_mwh', 0):.0f}",
            'CAPEX ($M)': f"${s.get('capex_million', 0):.0f}",
            'Availability': f"{s.get('availability_pct', 0):.2f}%",
            'NOx (tpy)': s.get('nox_tpy', 0),
            'Feasible': '✓' if s.get('is_feasible', False) else '✗',
            'Pareto': '⭐' if s.get('is_pareto_optimal', False) else '',
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def dispatch_stats_table(stats: List[Dict[str, Any]]):
    """
    Display dispatch operating statistics table
    
    Args:
        stats: List of equipment operating stats
    """
    if not stats:
        st.info("No dispatch statistics to display")
        return
    
    df = pd.DataFrame(stats)
    
    # Expected columns
    expected = ['Equipment', 'Capacity', 'Hours', 'CF', 'Starts/yr', 'Avg Output', 'Fuel/Energy']
    available = [c for c in expected if c in df.columns]
    
    if available:
        st.dataframe(df[available], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def ram_failure_table(equipment_data: List[Dict[str, Any]]):
    """
    Display RAM failure data table
    
    Args:
        equipment_data: List of equipment with failure data
    """
    data = []
    for eq in equipment_data:
        row = {
            'Equipment': eq.get('name', ''),
            'FOR (%)': f"{eq.get('for_pct', 0):.2f}%",
            'MTBF (hrs)': f"{eq.get('mtbf_hrs', 0):,.0f}",
            'MTTR (hrs)': eq.get('mttr_hrs', 0),
            'Source': eq.get('source', 'N/A'),
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def violation_bars(violations: List[Dict[str, Any]]):
    """
    Display constraint violation bars
    
    Args:
        violations: List of {name, count, pct, color} dicts
    """
    for v in violations:
        cols = st.columns([2, 8, 1])
        
        with cols[0]:
            st.markdown(f"**{v['name']}**")
        
        with cols[1]:
            pct = v.get('pct', 0)
            color = v.get('color', '#DC3545')
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
            st.markdown(f"**{v.get('count', 0)}**")
