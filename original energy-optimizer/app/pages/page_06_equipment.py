"""
Equipment Library Page
Browse and select equipment for scenarios
"""

import streamlit as st
import yaml
from pathlib import Path


def render():
    st.markdown("### 🔧 Equipment Library")
    
    col_header, col_actions = st.columns([3, 1])
    with col_actions:
        st.button("+ Add Equipment", type="primary", use_container_width=True)
    
    # Tabs for equipment types
    tabs = st.tabs(["Recip Engines", "Gas Turbines", "BESS", "Solar PV", "Grid"])
    
    # Load equipment data
    config_path = Path(__file__).parent.parent.parent / "config" / "equipment_defaults.yaml"
    
    try:
        with open(config_path) as f:
            equipment_data = yaml.safe_load(f)
    except:
        equipment_data = {"recip_engines": [], "gas_turbines": [], "bess": [], "solar_pv": [], "grid": []}
    
    # Recip Engines tab
    with tabs[0]:
        for equip in equipment_data.get("recip_engines", [])[:3]:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{equip.get('name', 'Unknown')}**")
                    st.caption(f"{equip.get('manufacturer', '')} • {equip.get('model', '')}")
                    
                    cols = st.columns(4)
                    specs = [
                        ("Capacity", f"{equip.get('capacity_mw', 0)} MW"),
                        ("Efficiency", f"{equip.get('efficiency_pct', 0)}%"),
                        ("Start Time", f"{equip.get('start_time_cold_min', 0)} min"),
                        ("Lead Time", f"{equip.get('lead_time_months_min', 0)}-{equip.get('lead_time_months_max', 0)} mo"),
                    ]
                    for i, (label, value) in enumerate(specs):
                        with cols[i]:
                            st.markdown(f"<small style='color: #666;'>{label}</small><br>**{value}**", 
                                       unsafe_allow_html=True)
                
                with col2:
                    qty = st.number_input("Qty", min_value=0, max_value=20, value=0, 
                                          key=f"qty_{equip.get('id', '')}", label_visibility="collapsed")
                
                st.markdown("---")
    
    # Gas Turbines tab
    with tabs[1]:
        for equip in equipment_data.get("gas_turbines", [])[:3]:
            with st.container():
                st.markdown(f"**{equip.get('name', 'Unknown')}**")
                st.caption(f"{equip.get('capacity_mw', 0)} MW | {equip.get('efficiency_pct', 0)}% eff | {equip.get('lead_time_months_min', 0)}-{equip.get('lead_time_months_max', 0)} mo lead")
                st.markdown("---")
    
    # BESS tab
    with tabs[2]:
        for equip in equipment_data.get("bess", []):
            with st.container():
                st.markdown(f"**{equip.get('name', 'Unknown')}**")
                st.caption(f"{equip.get('power_mw', 0)} MW / {equip.get('energy_mwh', 0)} MWh | {equip.get('duration_hrs', 0)}-hour duration")
                
                mwh = st.number_input("MWh", min_value=0, max_value=1000, value=100, 
                                      key=f"bess_{equip.get('id', '')}")
                st.markdown("---")
    
    # Solar PV tab
    with tabs[3]:
        for equip in equipment_data.get("solar_pv", []):
            st.markdown(f"**{equip.get('name', 'Unknown')}**")
            st.caption(f"{equip.get('capacity_factor_pct', 0)}% CF | {equip.get('lead_time_months_min', 0)}-{equip.get('lead_time_months_max', 0)} mo")
            st.number_input("MW", min_value=0, max_value=500, value=50, key=f"solar_{equip.get('id', '')}")
            st.markdown("---")
    
    # Grid tab
    with tabs[4]:
        st.markdown("**Grid Import**")
        st.caption("Subject to interconnection queue and utility timeline")
        grid_mw = st.number_input("Available MW", min_value=0, max_value=500, value=150)
        st.info("Grid availability: 99.97% | Subject to queue position and study timeline")
    
    # Summary
    st.markdown("---")
    st.markdown("#### Selection Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Nameplate", "312.8 MW")
    with col2:
        st.metric("Firm (N-1)", "294.0 MW")
    with col3:
        st.metric("Equipment Types", "4 selected")


if __name__ == "__main__":
    render()
