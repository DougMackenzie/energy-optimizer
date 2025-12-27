"""
Equipment Library Page
Browse and configure available equipment types
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import EQUIPMENT_DEFAULTS, COLORS


def render():
    """Render Equipment Library page"""
    
    st.markdown("### ⚙️ Equipment Library")
    st.markdown("*Browse and configure available generation and storage equipment*")
    st.markdown("---")
    
    # Equipment type tabs
    tab_recip, tab_turbine, tab_bess, tab_solar, tab_grid = st.tabs([
        "🔧 Reciprocating Engines",
        "💨 Gas Turbines", 
        "🔋 Battery Storage",
        "☀️ Solar PV",
        "🔌 Grid Connection"
    ])
    
    with tab_recip:
        render_recip_section()
    
    with tab_turbine:
        render_turbine_section()
    
    with tab_bess:
        render_bess_section()
    
    with tab_solar:
        render_solar_section()
    
    with tab_grid:
        render_grid_section()
    
    # Summary section
    st.markdown("---")
    st.markdown("#### 📊 Equipment Comparison")
    
    render_comparison_table()


def render_recip_section():
    """Reciprocating engine configuration"""
    
    st.markdown("#### Reciprocating Engines")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Default Specifications")
        
        defaults = EQUIPMENT_DEFAULTS['recip']
        
        specs = {
            'Parameter': [
                'Unit Capacity',
                'Heat Rate',
                'NOx Emissions',
                'CO Emissions',
                'CAPEX',
                'Variable O&M',
                'Fixed O&M',
                'Availability',
                'Lead Time',
                'Land Requirement',
                'Ramp Rate',
            ],
            'Value': [
                f"{defaults['capacity_mw']:.1f} MW",
                f"{defaults['heat_rate_btu_kwh']:,} Btu/kWh",
                f"{defaults['nox_lb_mwh']:.2f} lb/MWh",
                f"{defaults['co_lb_mwh']:.2f} lb/MWh",
                f"${defaults['capex_per_kw']:,}/kW",
                f"${defaults['vom_per_mwh']:.2f}/MWh",
                f"${defaults['fom_per_kw_yr']:.2f}/kW-yr",
                f"{defaults['availability']*100:.1f}%",
                f"{defaults['lead_time_months']} months",
                f"{defaults['land_acres_per_mw']:.1f} acres/MW",
                f"{defaults['ramp_rate_mw_min']:.1f} MW/min",
            ]
        }
        
        st.dataframe(pd.DataFrame(specs), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Available Models")
        
        models = [
            {'Model': 'Wärtsilä 50SG', 'Capacity (MW)': 18.3, 'Heat Rate': 7700, 'Lead Time': 18},
            {'Model': 'Jenbacher J920', 'Capacity (MW)': 10.4, 'Heat Rate': 7500, 'Lead Time': 15},
            {'Model': 'MAN 51/60G', 'Capacity (MW)': 18.4, 'Heat Rate': 7650, 'Lead Time': 18},
            {'Model': 'Caterpillar CG260', 'Capacity (MW)': 4.5, 'Heat Rate': 7900, 'Lead Time': 12},
        ]
        
        st.dataframe(pd.DataFrame(models), use_container_width=True, hide_index=True)
        
        st.markdown("##### Key Advantages")
        st.markdown("""
        - ✓ Fast deployment (12-18 months)
        - ✓ Excellent part-load efficiency
        - ✓ Fast ramp rates (3-5 MW/min)
        - ✓ Modular sizing
        - ✓ Black start capable
        """)
        
        st.markdown("##### Considerations")
        st.markdown("""
        - ⚠️ Higher NOx emissions than turbines
        - ⚠️ More maintenance-intensive
        - ⚠️ Sound attenuation required
        """)


def render_turbine_section():
    """Gas turbine configuration"""
    
    st.markdown("#### Gas Turbines")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Default Specifications")
        
        defaults = EQUIPMENT_DEFAULTS['turbine']
        
        specs = {
            'Parameter': [
                'Unit Capacity',
                'Heat Rate',
                'NOx Emissions',
                'CO Emissions',
                'CAPEX',
                'Variable O&M',
                'Fixed O&M',
                'Availability',
                'Lead Time',
                'Land Requirement',
                'Ramp Rate',
            ],
            'Value': [
                f"{defaults['capacity_mw']:.1f} MW",
                f"{defaults['heat_rate_btu_kwh']:,} Btu/kWh",
                f"{defaults['nox_lb_mwh']:.2f} lb/MWh",
                f"{defaults['co_lb_mwh']:.2f} lb/MWh",
                f"${defaults['capex_per_kw']:,}/kW",
                f"${defaults['vom_per_mwh']:.2f}/MWh",
                f"${defaults['fom_per_kw_yr']:.2f}/kW-yr",
                f"{defaults['availability']*100:.1f}%",
                f"{defaults['lead_time_months']} months",
                f"{defaults['land_acres_per_mw']:.1f} acres/MW",
                f"{defaults['ramp_rate_mw_min']:.1f} MW/min",
            ]
        }
        
        st.dataframe(pd.DataFrame(specs), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Available Models")
        
        models = [
            {'Model': 'GE LM6000', 'Capacity (MW)': 50.0, 'Heat Rate': 8500, 'Lead Time': 24},
            {'Model': 'Siemens SGT-800', 'Capacity (MW)': 57.0, 'Heat Rate': 8200, 'Lead Time': 26},
            {'Model': 'GE LM2500', 'Capacity (MW)': 33.0, 'Heat Rate': 9000, 'Lead Time': 20},
            {'Model': 'Solar Titan 130', 'Capacity (MW)': 15.0, 'Heat Rate': 9500, 'Lead Time': 18},
        ]
        
        st.dataframe(pd.DataFrame(models), use_container_width=True, hide_index=True)
        
        st.markdown("##### Key Advantages")
        st.markdown("""
        - ✓ Lower emissions (with SCR)
        - ✓ Higher single-unit capacity
        - ✓ Lower footprint per MW
        - ✓ Less maintenance per MWh
        """)
        
        st.markdown("##### Considerations")
        st.markdown("""
        - ⚠️ Longer lead times (24+ months)
        - ⚠️ Poor part-load efficiency
        - ⚠️ Higher minimum load
        - ⚠️ Slower startup
        """)


def render_bess_section():
    """Battery storage configuration"""
    
    st.markdown("#### Battery Energy Storage (BESS)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Default Specifications")
        
        defaults = EQUIPMENT_DEFAULTS['bess']
        
        specs = {
            'Parameter': [
                'Power Rating',
                'Duration',
                'Round-trip Efficiency',
                'CAPEX',
                'Degradation Cost',
                'Availability',
                'Lead Time',
                'Land Requirement',
                'Response Time',
            ],
            'Value': [
                f"{defaults['power_mw']:.1f} MW",
                f"{defaults['duration_hours']:.1f} hours",
                f"{defaults['roundtrip_efficiency']*100:.0f}%",
                f"${defaults['capex_per_kwh']}/kWh",
                f"${defaults['degradation_per_kwh']:.3f}/kWh",
                f"{defaults['availability']*100:.1f}%",
                f"{defaults['lead_time_months']} months",
                f"{defaults['land_acres_per_mwh']:.3f} acres/MWh",
                f"< 1 second",
            ]
        }
        
        st.dataframe(pd.DataFrame(specs), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Configuration Options")
        
        duration_options = [
            {'Duration': '2 hours', 'Use Case': 'Frequency regulation, ramp support', 'Cost ($/kWh)': 280},
            {'Duration': '4 hours', 'Use Case': 'Peak shaving, load shifting', 'Cost ($/kWh)': 236},
            {'Duration': '6 hours', 'Use Case': 'Solar firming, capacity', 'Cost ($/kWh)': 210},
            {'Duration': '8 hours', 'Use Case': 'Long duration arbitrage', 'Cost ($/kWh)': 195},
        ]
        
        st.dataframe(pd.DataFrame(duration_options), use_container_width=True, hide_index=True)
        
        st.markdown("##### Key Advantages")
        st.markdown("""
        - ✓ Zero direct emissions
        - ✓ 30% ITC eligible
        - ✓ Fastest response time
        - ✓ Grid services revenue
        - ✓ Modular and scalable
        """)
        
        st.markdown("##### Considerations")
        st.markdown("""
        - ⚠️ Limited duration (not baseload)
        - ⚠️ Degradation over time
        - ⚠️ Fire safety requirements
        """)


def render_solar_section():
    """Solar PV configuration"""
    
    st.markdown("#### Solar PV")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Default Specifications")
        
        defaults = EQUIPMENT_DEFAULTS['solar']
        
        specs = {
            'Parameter': [
                'CAPEX (DC)',
                'Capacity Factor',
                'Availability',
                'Lead Time',
                'Land Requirement',
                'Project Life',
                'Degradation',
                'O&M Cost',
            ],
            'Value': [
                f"${defaults['capex_per_w_dc']:.2f}/W-DC",
                f"{defaults['capacity_factor']*100:.0f}%",
                f"{defaults['availability']*100:.1f}%",
                f"{defaults['lead_time_months']} months",
                f"{defaults['land_acres_per_mw']:.1f} acres/MW-DC",
                "25-30 years",
                "0.5%/year",
                "$15-20/kW-yr",
            ]
        }
        
        st.dataframe(pd.DataFrame(specs), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Configuration Options")
        
        configs = [
            {'Type': 'Fixed Tilt', 'CF Premium': '—', 'Cost': 'Base', 'Land': '5 acres/MW'},
            {'Type': 'Single-Axis Tracking', 'CF Premium': '+15-20%', 'Cost': '+$0.10/W', 'Land': '6 acres/MW'},
            {'Type': 'Bifacial + Tracking', 'CF Premium': '+25-30%', 'Cost': '+$0.15/W', 'Land': '7 acres/MW'},
        ]
        
        st.dataframe(pd.DataFrame(configs), use_container_width=True, hide_index=True)
        
        st.markdown("##### Key Advantages")
        st.markdown("""
        - ✓ Zero emissions
        - ✓ 30% ITC eligible
        - ✓ Low O&M costs
        - ✓ 25+ year asset life
        - ✓ Hedge against fuel prices
        """)
        
        st.markdown("##### Considerations")
        st.markdown("""
        - ⚠️ Intermittent (not firm)
        - ⚠️ Large land requirement
        - ⚠️ Requires storage for 24/7 load
        """)


def render_grid_section():
    """Grid connection section"""
    
    st.markdown("#### Grid Connection")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Typical Parameters")
        
        defaults = EQUIPMENT_DEFAULTS['grid']
        
        specs = {
            'Parameter': [
                'Availability',
                'Lead Time',
                'Typical Cost',
                'Capacity',
            ],
            'Value': [
                f"{defaults['availability']*100:.2f}%",
                f"{defaults['lead_time_months']} months (typical)",
                "$25-100M (varies widely)",
                "Up to transmission limit",
            ]
        }
        
        st.dataframe(pd.DataFrame(specs), use_container_width=True, hide_index=True)
        
        st.markdown("##### Queue Times by ISO")
        
        queue_times = [
            {'ISO': 'ERCOT', 'Avg Queue': '24-36 months', 'Trend': '↑'},
            {'ISO': 'PJM', 'Avg Queue': '48-60 months', 'Trend': '↑↑'},
            {'ISO': 'MISO', 'Avg Queue': '36-48 months', 'Trend': '↑'},
            {'ISO': 'SPP', 'Avg Queue': '36-48 months', 'Trend': '→'},
            {'ISO': 'CAISO', 'Avg Queue': '60-84 months', 'Trend': '↑↑'},
        ]
        
        st.dataframe(pd.DataFrame(queue_times), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Key Advantages")
        st.markdown("""
        - ✓ Highest reliability (99.97%+)
        - ✓ Lowest marginal cost
        - ✓ No emissions at site
        - ✓ No fuel supply concerns
        - ✓ Unlimited duration
        """)
        
        st.markdown("##### Considerations")
        st.markdown("""
        - ⚠️ Long interconnection queues (5+ years)
        - ⚠️ High upfront interconnection costs
        - ⚠️ Transmission constraints
        - ⚠️ Exposure to market prices
        - ⚠️ Curtailment risk
        """)
        
        st.info("""
        **Bridge Power Problem:** Grid delays drive the need for BTM generation.
        Use Problem 5 to optimize the transition strategy.
        """)


def render_comparison_table():
    """Equipment comparison summary table"""
    
    comparison = [
        {
            'Equipment': '🔧 Recip Engine',
            'Capacity': '4-20 MW/unit',
            'Lead Time': '12-18 mo',
            'CAPEX': '$1,500-1,800/kW',
            'Fuel': 'Natural Gas',
            'Emissions': 'Moderate',
            'Best For': 'Baseload, fast deploy',
        },
        {
            'Equipment': '💨 Gas Turbine',
            'Capacity': '15-60 MW/unit',
            'Lead Time': '18-30 mo',
            'CAPEX': '$1,100-1,500/kW',
            'Fuel': 'Natural Gas',
            'Emissions': 'Low (w/SCR)',
            'Best For': 'Large scale, low emissions',
        },
        {
            'Equipment': '🔋 BESS',
            'Capacity': '1-100+ MW',
            'Lead Time': '9-15 mo',
            'CAPEX': '$200-300/kWh',
            'Fuel': 'None',
            'Emissions': 'Zero',
            'Best For': 'Peak shaving, grid services',
        },
        {
            'Equipment': '☀️ Solar PV',
            'Capacity': '1-500+ MW',
            'Lead Time': '9-15 mo',
            'CAPEX': '$0.90-1.20/W-DC',
            'Fuel': 'None',
            'Emissions': 'Zero',
            'Best For': 'Energy cost reduction',
        },
        {
            'Equipment': '🔌 Grid',
            'Capacity': 'Up to TX limit',
            'Lead Time': '36-84 mo',
            'CAPEX': '$25-100M',
            'Fuel': 'N/A',
            'Emissions': 'Grid mix',
            'Best For': 'Long-term, lowest cost',
        },
    ]
    
    st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render()
