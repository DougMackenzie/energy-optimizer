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
        if st.button("🔄 Reload from Sheets", use_container_width=True):
            # Clear cache and reload
            if 'equipment_library' in st.session_state:
                del st.session_state.equipment_library
            st.rerun()
        st.button("+ Add Equipment", type="primary", use_container_width=True)
    
    # Tabs for equipment types
    tabs = st.tabs(["Recip Engines", "Gas Turbines", "BESS", "Solar PV", "Grid"])
    
    # Load equipment data from Google Sheets - SINGLE SOURCE OF TRUTH
    from app.utils.data_io import load_equipment_from_sheets
    
    with st.spinner("Loading equipment library from Google Sheets..."):
        equipment_data = load_equipment_from_sheets()
    
    # Show data source info
    st.info("📊 Equipment data loaded from [Google Sheets Database](https://docs.google.com/spreadsheets/d/1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so) - Single source of truth")
    
    # Recip Engines tab
    with tabs[0]:
        recip_engines = equipment_data.get("Reciprocating_Engines", [])
        if not recip_engines:
            st.info("💡 No reciprocating engines in library. Click 'Reload from Sheets' or add equipment to Google Sheets.")
        else:
            for equip in recip_engines[:10]:  # Show up to 10 units
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # Use Google Sheets column names
                        name = equip.get('Model', equip.get('name', 'Unknown'))
                        mfr = equip.get('Manufacturer', '')
                        model = equip.get('Model', '')
                        
                        st.markdown(f"**{name}**")
                        st.caption(f"{mfr} • {model}")
                        
                        cols = st.columns(4)
                        specs = [
                            ("Capacity", f"{equip.get('Capacity_MW', equip.get('capacity_mw', 0))} MW"),
                            ("Efficiency", f"{equip.get('Efficiency_Pct', equip.get('efficiency_pct', 0))}%"),
                            ("Start Time", f"{equip.get('Start_Time_Cold_Min', equip.get('start_time_cold_min', 0))} min"),
                            ("Lead Time", f"{equip.get('Lead_Time_Months_Min', equip.get('lead_time_months_min', 0))}-{equip.get('Lead_Time_Months_Max', equip.get('lead_time_months_max', 0))} mo"),
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
        gas_turbines = equipment_data.get("Gas_Turbines", [])
        if not gas_turbines:
            st.info("💡 No gas turbines in library. Click 'Reload from Sheets' or add to Google Sheets.")
        else:
            for equip in gas_turbines[:10]:
                if equip is None:
                    continue
                    
                with st.container():
                    name = equip.get('Model', equip.get('name', 'Unknown'))
                    cap = equip.get('Capacity_MW', equip.get('capacity_mw', 0))
                    eff = equip.get('Efficiency_Pct', equip.get('efficiency_pct', 0))
                    lead_min = equip.get('Lead_Time_Months_Min', equip.get('lead_time_months_min', 0))
                    lead_max = equip.get('Lead_Time_Months_Max', equip.get('lead_time_months_max', 0))
                    
                    st.markdown(f"**{name}**")
                    st.caption(f"{cap} MW | {eff}% eff | {lead_min}-{lead_max} mo lead")
                    st.markdown("---")
    
    # BESS tab
    with tabs[2]:
        bess_systems = equipment_data.get("BESS", [])
        if not bess_systems:
            st.info("💡 No BESS systems in library. Click 'Reload from Sheets' or add to Google Sheets.")
        else:
            for equip in bess_systems:
                if equip is None:
                    continue
                    
                with st.container():
                    name = equip.get('Model', equip.get('name', 'Unknown'))
                    power = equip.get('Power_MW', equip.get('power_mw', 0))
                    energy = equip.get('Energy_MWh', equip.get('energy_mwh', 0))
                    duration = equip.get('Duration_hrs', equip.get('duration_hrs', 0))
                    
                    st.markdown(f"**{name}**")
                    st.caption(f"{power} MW / {energy} MWh | {duration}-hour duration")
                    
                    mwh = st.number_input("MWh", min_value=0, max_value=1000, value=100, 
                                          key=f"bess_{equip.get('ID', equip.get('id', name))}")
                    st.markdown("---")
    
    # Solar PV tab
    with tabs[3]:
        solar_systems = equipment_data.get("Solar_PV", [])
        if not solar_systems:
            st.info("💡 No solar PV systems in library. Click 'Reload from Sheets' or add to Google Sheets.")
        else:
            for equip in solar_systems:
                if equip is None:
                    continue
                    
                # Solar PV has different field structure
                system_type = equip.get('System_Type', equip.get('name', 'Unknown'))
                region = equip.get('Region', '')
                cf = equip.get('Capacity_Factor_Pct', equip.get('capacity_factor_pct', 0))
                capex = equip.get('CAPEX_per_W_DC', equip.get('capex_per_w_dc', 0))
                
                name = f"{system_type} - {region}" if region else system_type
                
                st.markdown(f"**{name}**")
                st.caption(f"{cf}% CF | ${capex}/W DC | {equip.get('Lead_Time_Months', equip.get('lead_time_months', 12))} mo lead")
                st.number_input("MW", min_value=0, max_value=500, value=50, key=f"solar_{equip.get('ID', equip.get('id', name))}")
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
