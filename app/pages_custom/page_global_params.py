"""
Global Parameters Page
Central location for equipment library and global model parameters
"""

import streamlit as st
import pandas as pd
from config.settings import ECONOMIC_DEFAULTS, CONSTRAINT_DEFAULTS

def render():
    st.markdown("### ⚙️ Global Parameters")
    st.markdown("*Equipment library and model-wide parameters referenced across all optimizations*")
    st.markdown("---")
    
    # Create tabs for different parameter categories
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔧 Equipment Library",
        "💰 Economic Parameters", 
        "📊 Default Constraints",
        "🌍 Emissions & Environmental"
    ])
    
    # =============================================================================
    # TAB 1: EQUIPMENT LIBRARY
    # =============================================================================
    with tab1:
        st.markdown("## 🔧 Equipment Library")
        st.caption("Standard equipment specifications used across all optimizations")
        
        # Equipment selector
        equipment_type = st.selectbox(
            "Select Equipment Type",
            ["Reciprocating Engines", "Combustion Turbines", "Battery Storage (BESS)", 
             "Solar PV", "Grid Interconnection"],
            key="global_equip_select"
        )
        
        if equipment_type == "Reciprocating Engines":
            st.markdown("### Reciprocating Engine Generators")
            st.markdown("""
            Natural gas reciprocating engines are the backbone of flexible datacenter power generation.
            High efficiency, fast start/stop, excellent load following.
            """)
            
            # Equipment specs table
            recip_data = {
                "Model": ["CAT 3516E", "CAT 3520C", "Waukesha 7044GSI", "Jenbacher J624", "MAN 20V35/44G"],
                "Capacity (MW)": [1.25, 2.0, 3.0, 4.4, 10.0],
                "Efficiency (HHV)": ["38.5%", "40.2%", "41.5%", "43.8%", "44.5%"],
                "Heat Rate (Btu/kWh)": [8860, 8490, 8220, 7790, 7670],
                "Capex ($/kW)": [1400, 1350, 1300, 1250, 1150],
                "Opex ($/kW-yr)": [45, 42, 40, 38, 35],
                "NOx (g/bhp-hr)": [0.15, 0.15, 0.15, 0.10, 0.10],
                "Start Time": ["<2 min", "<2 min", "<2 min", "<3 min", "<3 min"],
            }
            
            df_recip = pd.DataFrame(recip_data)
            st.dataframe(df_recip, use_container_width=True, hide_index=True)
            
            st.info("""
            **Key Characteristics:**
            - ✅ Excellent load following (10-100% capacity)
            - ✅ Fast start/stop for intermittent loads
            - ✅ High efficiency even at part load
            - ⚠️ Higher emissions than turbines (per MWh)
            - ⚠️ More frequent maintenance
            
            **Typical Use:** Baseload and peak shaving for <100 MW sites
            """)
        
        elif equipment_type == "Combustion Turbines":
            st.markdown("### Combustion Turbine Generators")
            st.markdown("""
            Gas turbines provide efficient power at scale with lower emissions.
            Best for larger sites with steady baseload requirements.
            """)
            
            turbine_data = {
                "Model": ["GE LM2500+", "Solar Titan 130", "Siemens SGT-400", "GE LM6000"],
                "Capacity (MW)": [30, 15, 13, 47],
                "Efficiency (HHV)": ["37.5%", "32.8%", "35.2%", "41.5%"],
                "Heat Rate (Btu/kWh)": [9100, 10400, 9690, 8220],
                "Capex ($/kW)": [950, 1100, 1050, 850],
                "Opex ($/kW-yr)": [28, 32, 30, 25],
                "NOx (g/bhp-hr)": [0.07, 0.09, 0.08, 0.05],
                "Start Time": ["10 min", "7 min", "8 min", "10 min"],
            }
            
            df_turbine = pd.DataFrame(turbine_data)
            st.dataframe(df_turbine, use_container_width=True, hide_index=True)
            
            st.info("""
            **Key Characteristics:**
            - ✅ Lower capex per MW at scale
            - ✅ Lower NOx emissions
            - ✅ Longer maintenance intervals
            - ⚠️ Less efficient at part load
            - ⚠️ Slower start/stop
            
            **Typical Use:** Baseload for >100 MW sites
            """)
        
        elif equipment_type == "Battery Storage (BESS)":
            st.markdown("### Battery Energy Storage Systems")
            st.markdown("""
            Lithium-ion batteries provide fast response, load shifting, and zero-emission backup.
            Critical for demand response and renewable integration.
            """)
            
            bess_data = {
                "Technology": ["Li-ion NMC", "Li-ion LFP", "Flow Battery"],
                "Duration": ["2 hours", "4 hours", "4-8 hours"],
                "Round-Trip Eff": ["88%", "90%", "70%"],
                "Capex ($/kWh)": [350, 320, 450],
                "Capex ($/kW)": [180, 200, 220],
                "Opex ($/kWh-yr)": [8, 7, 12],
                "Cycle Life": ["5,000", "8,000", "15,000"],
                "Degradation": ["2%/yr", "1.5%/yr", "0.5%/yr"],
            }
            
            df_bess = pd.DataFrame(bess_data)
            st.dataframe(df_bess, use_container_width=True, hide_index=True)
            
            st.info("""
            **Key Characteristics:**
            - ✅ Instant response (<100ms)
            - ✅ Zero emissions
            - ✅ Energy arbitrage (charge/discharge)
            - ⚠️ High upfront cost
            - ⚠️ Degradation over time
            
            **Typical Use:** Peak shaving, demand response, solar firming
            """)
        
        elif equipment_type == "Solar PV":
            st.markdown("### Solar Photovoltaic Systems")
            st.markdown("""
            Solar PV provides zero-marginal-cost clean energy with minimal O&M.
            Best paired with BESS for round-the-clock operation.
            """)
            
            solar_data = {
                "Technology": ["Mono-Si Module", "Bi-facial Module", "Thin Film"],
                "Efficiency": ["21.5%", "23.0%", "18.0%"],
                "Capex ($/W DC)": [0.85, 0.95, 0.75],
                "Capex ($/W AC)": [1.10, 1.20, 0.95],
                "Opex ($/kW-yr)": [15, 16, 14],
                "Degradation": ["0.5%/yr", "0.4%/yr", "0.7%/yr"],
                "Land (acres/MW)": [5, 5.5, 6],
                "Capacity Factor": ["25%", "27%", "23%"],
            }
            
            df_solar = pd.DataFrame(solar_data)
            st.dataframe(df_solar, use_container_width=True, hide_index=True)
            
            st.info("""
            **Key Characteristics:**
            - ✅ Zero fuel cost
            - ✅ Low maintenance
            - ✅ 25+ year lifespan
            - ⚠️ Intermittent (daylight only)
            - ⚠️ Land intensive
            
            **Typical Use:** Daytime baseload, sustainability goals
            """)
        
        else:  # Grid Interconnection
            st.markdown("### Grid Interconnection")
            st.markdown("""
            Utility grid connection provides unlimited capacity but with long lead times
            and variable costs depending on tariff structure.
            """)
            
            grid_data = {
                "Voltage Level": ["138 kV", "230 kV", "345 kV", "500 kV"],
                "Typical Capacity": ["50-150 MW", "100-300 MW", "200-600 MW", "500+ MW"],
                "Interconnection ($/kW)": [450, 350, 280, 220],
                "Timeline (months)": ["36-48", "48-60", "60-72", "72-96"],
                "Demand Charge ($/kW-mo)": [10, 12, 15, 18],
                "Energy Charge ($/MWh)": [45, 42, 40, 38],
                "Study Costs": ["$100k", "$200k", "$500k", "$1M+"],
            }
            
            df_grid = pd.DataFrame(grid_data)
            st.dataframe(df_grid, use_container_width=True, hide_index=True)
            
            st.warning("""
            **Key Considerations:**
            - ✅ Unlimited capacity (within ISO limits)
            - ✅ High reliability
            - ⚠️ Long lead times (3-8 years)
            - ⚠️ Complex tariff structures
            - ⚠️ Demand charges can be significant
            
            **Typical Use:** Backup power, future capacity hedge
            """)
    
    # =============================================================================
    # TAB 2: ECONOMIC PARAMETERS
    # =============================================================================
    with tab2:
        st.markdown("## 💰 Economic Parameters")
        st.caption("Default financial assumptions used in LCOE and NPV calculations")
        
        col_econ1, col_econ2 = st.columns(2)
        
        with col_econ1:
            st.markdown("### Financing Parameters")
            
            econ_params = {
                "Parameter": [
                    "Discount Rate",
                "Project Lifetime",
                    "Natural Gas Price ($/MMBtu)",
                    "Gas Price Escalation",
                    "Grid Electricity ($/MWh)",
                    "Grid Escalation",
                    "Carbon Price ($/ton CO2)",
                ],
                "Value": [
                    f"{ECONOMIC_DEFAULTS.get('discount_rate', 0.08) * 100:.1f}%",
                    f"{ECONOMIC_DEFAULTS.get('project_lifetime_years', 15)} years",
                    f"${ECONOMIC_DEFAULTS.get('gas_price_mmbtu', 4.50):.2f}",
                    f"{ECONOMIC_DEFAULTS.get('gas_escalation', 0.02) * 100:.1f}%/yr",
                    f"${ECONOMIC_DEFAULTS.get('grid_electricity_mwh', 45):.0f}",
                    f"{ECONOMIC_DEFAULTS.get('electricity_escalation', 0.025) * 100:.1f}%/yr",
                    f"${ECONOMIC_DEFAULTS.get('carbon_price', 0):.0f}",
                ]
            }
            
            df_econ = pd.DataFrame(econ_params)
            st.dataframe(df_econ, use_container_width=True, hide_index=True)
        
        with col_econ2:
            st.markdown("### Tax & Incentives")
            
            tax_params = {
                "Parameter": [
                    "Federal ITC (Solar)",
                    "State ITC",
                    "MACRS Depreciation",
                    "Property Tax Rate",
                    "Income Tax Rate",
                ],
                "Value": [
                    "30%",
                    "Varies by state",
                    "5-year",
                    "1.0-2.5%/yr",
                    "21% (Federal) + State",
                ]
            }
            
            df_tax = pd.DataFrame(tax_params)
            st.dataframe(df_tax, use_container_width=True, hide_index=True)
        
        st.info("""
        **Note:** These are default values. Problem-specific optimizations may override these 
        parameters based on site location, utility tariffs, and project financing structure.
        """)
    
    # =============================================================================
    # TAB 3: DEFAULT CONSTRAINTS
    # =============================================================================
    with tab3:
        st.markdown("## 📊 Default Constraints")
        st.caption("Typical constraint values applied if not specified at the site level")
        
        col_const1, col_const2 = st.columns(2)
        
        with col_const1:
            st.markdown("### Operational Constraints")
            
            op_constraints = {
                "Constraint": [
                    "N-1 Redundancy",
                    "Min Load Factor",
                    "Max Load Factor",
                    "BESS Min SOC",
                    "BESS Max Cycles/Day",
                    "Grid Availability",
                ],
                "Default Value": [
                    "Disabled (BTM only)",
                    "20% (engines/turbines)",
                    "100%",
                    "10%",
                    "2 cycles",
                    "99.5%",
                ]
            }
            
            df_op = pd.DataFrame(op_constraints)
            st.dataframe(df_op, use_container_width=True, hide_index=True)
        
        with col_const2:
            st.markdown("### Environmental Constraints")
            
            env_constraints = {
                "Constraint": [
                    "NOx Limit (tons/yr)",
                    "Gas Curtailment Risk",
                    "Water Availability",
                    "Noise Limit (dBA)",
                    "Setback Requirements",
                ],
                "Default Value": [
                    "Site-specific",
                    "0% (no curtailment)",
                    "Unlimited",
                    "Site-specific",
                    "Site-specific",
                ]
            }
            
            df_env = pd.DataFrame(env_constraints)
            st.dataframe(df_env, use_container_width=True, hide_index=True)
        
        st.warning("""
        **Important:** Many constraints are site-specific and should be configured in the 
        Dashboard → Sites & Infrastructure tab for each location.
        """)
    
    # =============================================================================
    # TAB 4: EMISSIONS
    # =============================================================================
    with tab4:
        st.markdown("## 🌍 Emissions & Environmental Factors")
        st.caption("Carbon intensity and environmental impact parameters")
        
        st.markdown("### Emissions Factors")
        
        emissions_data = {
            "Source": [
                "Natural Gas (Recip Engine)",
                "Natural Gas (Turbine)",
                "Grid Electricity (US Avg)",
                "Grid Electricity (ERCOT)",
                "Grid Electricity (CAISO)",
                "Solar PV",
                "Battery Storage",
            ],
            "CO2 (lb/MWh)": [
                1175,
                1250,
                857,
                775,
                465,
                0,
                0,
            ],
            "NOx (lb/MWh)": [
                0.65,
                0.35,
                0.85,
                0.70,
                0.25,
                0,
                0,
            ],
            "Water (gal/MWh)": [
                15,
                12,
                550,
                420,
                180,
                5,
                0,
            ]
        }
        
        df_emissions = pd.DataFrame(emissions_data)
        st.dataframe(df_emissions, use_container_width=True, hide_index=True)
        
        st.markdown("### Natural Gas Composition")
        
        gas_composition = {
            "Component": ["Methane (CH4)", "Ethane (C2H6)", "Propane (C3H8)", "CO2", "N2", "HHV"],
            "Typical %": ["94%", "3%", "1%", "1%", "1%", "1,030 Btu/scf"],
        }
        
        df_gas = pd.DataFrame(gas_composition)
        st.dataframe(df_gas, use_container_width=True, hide_index=True)
        
        st.success("""
        **Carbon Neutrality Strategies:**
        - Maximize solar + BESS deployment
        - Use carbon offsets for grid electricity
        - Consider RNG (renewable natural gas) for engines
        - Participate in utility green tariff programs
        - Target low-carbon ISOs (CAISO, NYISO)
        """)
