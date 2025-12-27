"""
RAM (Reliability, Availability, Maintainability) Analysis Page
K-of-N redundancy and availability calculations
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from math import comb

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import EQUIPMENT_DEFAULTS, COLORS


def render():
    """Render RAM Analysis page"""
    
    st.markdown("### 🔧 RAM Analysis")
    st.markdown("*Reliability, Availability, and Maintainability Assessment*")
    st.markdown("---")
    
    # Get results
    results = st.session_state.get('optimization_results', {})
    result = results.get(1)
    
    # Tabs
    tab_overview, tab_kofn, tab_availability, tab_mtbf = st.tabs([
        "📊 Overview", "🔢 K-of-N Analysis", "📈 Availability", "⏱️ MTBF/MTTR"
    ])
    
    with tab_overview:
        render_overview_tab(result)
    
    with tab_kofn:
        render_kofn_tab(result)
    
    with tab_availability:
        render_availability_tab(result)
    
    with tab_mtbf:
        render_mtbf_tab()


def render_overview_tab(result):
    """Overview of RAM concepts and current configuration"""
    
    st.markdown("#### RAM Overview")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        ##### What is RAM?
        
        **Reliability** - Probability that a system will perform its intended function 
        for a specified period under stated conditions.
        
        **Availability** - Proportion of time a system is in a functioning condition.
        
        **Maintainability** - Ease with which a system can be maintained to keep it 
        in or restore it to a functioning condition.
        
        ---
        
        ##### Key Metrics
        
        | Metric | Definition |
        |--------|------------|
        | **MTBF** | Mean Time Between Failures |
        | **MTTR** | Mean Time To Repair |
        | **MTTF** | Mean Time To Failure |
        | **Availability** | MTBF / (MTBF + MTTR) |
        """)
    
    with col2:
        st.markdown("##### Equipment Availability Assumptions")
        
        avail_data = [
            {'Equipment': 'Reciprocating Engine', 'Availability': f"{EQUIPMENT_DEFAULTS['recip']['availability']*100:.1f}%", 
             'Typical MTBF': '2,000 hours', 'Typical MTTR': '50 hours'},
            {'Equipment': 'Gas Turbine', 'Availability': f"{EQUIPMENT_DEFAULTS['turbine']['availability']*100:.1f}%",
             'Typical MTBF': '1,500 hours', 'Typical MTTR': '75 hours'},
            {'Equipment': 'BESS', 'Availability': f"{EQUIPMENT_DEFAULTS['bess']['availability']*100:.1f}%",
             'Typical MTBF': '20,000 hours', 'Typical MTTR': '24 hours'},
            {'Equipment': 'Solar PV', 'Availability': f"{EQUIPMENT_DEFAULTS['solar']['availability']*100:.1f}%",
             'Typical MTBF': '50,000 hours', 'Typical MTTR': '8 hours'},
            {'Equipment': 'Grid Connection', 'Availability': f"{EQUIPMENT_DEFAULTS['grid']['availability']*100:.2f}%",
             'Typical MTBF': '2,000 hours', 'Typical MTTR': '4 hours'},
        ]
        
        st.dataframe(pd.DataFrame(avail_data), use_container_width=True, hide_index=True)
    
    # Current configuration
    if result:
        st.markdown("---")
        st.markdown("##### Current Configuration RAM")
        
        equipment = result.get('equipment', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate overall availability
        overall_avail = calculate_system_availability(equipment)
        
        with col1:
            st.metric("System Availability", f"{overall_avail*100:.2f}%")
        
        with col2:
            hours_down = (1 - overall_avail) * 8760
            st.metric("Expected Downtime", f"{hours_down:.0f} hrs/yr")
        
        with col3:
            n_recips = equipment.get('n_recips', 0)
            n_turbines = equipment.get('n_turbines', 0)
            st.metric("Thermal Units", f"{n_recips + n_turbines}")
        
        with col4:
            # Check N-1
            n1_met = check_n1_redundancy(equipment, result.get('dispatch_summary', {}).get('total_load_gwh', 0) / 8.76)
            st.metric("N-1 Status", "✓ Met" if n1_met else "✗ Not Met")


def render_kofn_tab(result):
    """K-of-N redundancy analysis"""
    
    st.markdown("#### K-of-N Redundancy Analysis")
    
    st.info("""
    **K-of-N Configuration:** System is available if at least K units out of N total units are operational.
    
    Example: A 6-of-8 configuration means 8 units installed, and the system is available if 6+ are working.
    """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("##### Configuration")
        
        n_units = st.number_input("Total Units (N)", 2, 20, 8)
        k_required = st.number_input("Required Units (K)", 1, n_units, min(6, n_units))
        unit_availability = st.slider("Unit Availability", 0.90, 0.999, 0.975, 0.001, format="%.3f")
        
        st.markdown("---")
        
        # Calculate
        system_avail = calculate_kofn_availability(k_required, n_units, unit_availability)
        
        st.metric("System Availability", f"{system_avail*100:.4f}%")
        st.metric("Nines", f"{-np.log10(1-system_avail):.2f}")
        st.metric("Expected Downtime", f"{(1-system_avail)*8760:.1f} hrs/yr")
    
    with col2:
        st.markdown("##### K-of-N Availability Matrix")
        
        # Create matrix
        matrix_data = []
        
        for n in range(2, 13):
            row = {'N (Total)': n}
            for k in range(1, n + 1):
                avail = calculate_kofn_availability(k, n, unit_availability)
                row[f'K={k}'] = f"{avail*100:.2f}%"
            matrix_data.append(row)
        
        matrix_df = pd.DataFrame(matrix_data)
        st.dataframe(matrix_df, use_container_width=True, hide_index=True, height=400)
    
    # Visualization
    st.markdown("##### Availability vs. Required Units")
    
    k_values = list(range(1, n_units + 1))
    avail_values = [calculate_kofn_availability(k, n_units, unit_availability) * 100 for k in k_values]
    
    fig = px.bar(x=k_values, y=avail_values, 
                labels={'x': 'K (Required Units)', 'y': 'System Availability (%)'},
                color=avail_values, color_continuous_scale='Greens')
    
    fig.add_hline(y=99.5, line_dash="dash", line_color="red", 
                 annotation_text="99.5% Target")
    
    fig.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    st.markdown("##### Recommendations")
    
    # Find minimum K for 99.5%
    for k in range(1, n_units + 1):
        if calculate_kofn_availability(k, n_units, unit_availability) >= 0.995:
            st.success(f"✓ **{k}-of-{n_units}** configuration achieves 99.5% availability target")
            st.info(f"This means you can tolerate **{n_units - k} simultaneous failures** while maintaining service.")
            break
    else:
        st.warning(f"⚠️ Cannot achieve 99.5% with {n_units} units. Consider adding more units or improving unit reliability.")


def render_availability_tab(result):
    """Detailed availability analysis"""
    
    st.markdown("#### System Availability Analysis")
    
    # Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Series vs Parallel Configuration")
        
        config_type = st.radio("Configuration Type", ["Parallel (Redundant)", "Series (All Required)", "Mixed"])
        
        if config_type == "Parallel (Redundant)":
            st.markdown("""
            **Parallel Configuration:**
            - System available if ANY unit is available
            - A_system = 1 - Π(1 - A_i)
            - Higher availability
            """)
            
            a1 = st.slider("Unit 1 Availability", 0.9, 0.999, 0.975, 0.001, key="a1")
            a2 = st.slider("Unit 2 Availability", 0.9, 0.999, 0.975, 0.001, key="a2")
            a3 = st.slider("Unit 3 Availability", 0.9, 0.999, 0.975, 0.001, key="a3")
            
            # Calculate parallel availability
            parallel_avail = 1 - (1 - a1) * (1 - a2) * (1 - a3)
            
            st.metric("System Availability", f"{parallel_avail*100:.4f}%")
        
        elif config_type == "Series (All Required)":
            st.markdown("""
            **Series Configuration:**
            - System available only if ALL units available
            - A_system = Π(A_i)
            - Lower availability
            """)
            
            a1 = st.slider("Unit 1 Availability", 0.9, 0.999, 0.975, 0.001, key="s1")
            a2 = st.slider("Unit 2 Availability", 0.9, 0.999, 0.975, 0.001, key="s2")
            a3 = st.slider("Unit 3 Availability", 0.9, 0.999, 0.975, 0.001, key="s3")
            
            series_avail = a1 * a2 * a3
            
            st.metric("System Availability", f"{series_avail*100:.4f}%")
        
        else:  # Mixed
            st.markdown("""
            **Mixed Configuration:**
            - Parallel groups in series
            - Common for critical systems
            """)
            
            st.info("Mixed configuration calculator coming soon")
    
    with col2:
        st.markdown("##### Availability Targets by Application")
        
        targets = [
            {'Application': 'Tier 1 Datacenter', 'Target': '99.671%', 'Downtime': '28.8 hrs/yr'},
            {'Application': 'Tier 2 Datacenter', 'Target': '99.741%', 'Downtime': '22.7 hrs/yr'},
            {'Application': 'Tier 3 Datacenter', 'Target': '99.982%', 'Downtime': '1.6 hrs/yr'},
            {'Application': 'Tier 4 Datacenter', 'Target': '99.995%', 'Downtime': '0.4 hrs/yr'},
            {'Application': 'AI Training (typical)', 'Target': '99.5%', 'Downtime': '43.8 hrs/yr'},
            {'Application': 'AI Inference (critical)', 'Target': '99.9%', 'Downtime': '8.8 hrs/yr'},
        ]
        
        st.dataframe(pd.DataFrame(targets), use_container_width=True, hide_index=True)
        
        st.markdown("##### Number of 'Nines'")
        
        nines_data = [
            {'Nines': '2 (99%)', 'Downtime': '87.6 hrs/yr', 'Level': 'Low'},
            {'Nines': '3 (99.9%)', 'Downtime': '8.76 hrs/yr', 'Level': 'Standard'},
            {'Nines': '4 (99.99%)', 'Downtime': '52.6 min/yr', 'Level': 'High'},
            {'Nines': '5 (99.999%)', 'Downtime': '5.26 min/yr', 'Level': 'Very High'},
        ]
        
        st.dataframe(pd.DataFrame(nines_data), use_container_width=True, hide_index=True)


def render_mtbf_tab():
    """MTBF and MTTR analysis"""
    
    st.markdown("#### MTBF/MTTR Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Equipment MTBF/MTTR")
        
        mtbf_data = [
            {'Equipment': 'Recip Engine (18 MW)', 'MTBF (hrs)': 2000, 'MTTR (hrs)': 48, 
             'Availability': f"{2000/(2000+48)*100:.2f}%"},
            {'Equipment': 'Gas Turbine (50 MW)', 'MTBF (hrs)': 1500, 'MTTR (hrs)': 72,
             'Availability': f"{1500/(1500+72)*100:.2f}%"},
            {'Equipment': 'BESS (4-hr)', 'MTBF (hrs)': 20000, 'MTTR (hrs)': 24,
             'Availability': f"{20000/(20000+24)*100:.2f}%"},
            {'Equipment': 'Solar Inverter', 'MTBF (hrs)': 50000, 'MTTR (hrs)': 8,
             'Availability': f"{50000/(50000+8)*100:.2f}%"},
            {'Equipment': 'Transformer', 'MTBF (hrs)': 100000, 'MTTR (hrs)': 168,
             'Availability': f"{100000/(100000+168)*100:.2f}%"},
        ]
        
        st.dataframe(pd.DataFrame(mtbf_data), use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("##### Availability Calculator")
        
        mtbf = st.number_input("MTBF (hours)", 100, 100000, 2000)
        mttr = st.number_input("MTTR (hours)", 1, 500, 48)
        
        availability = mtbf / (mtbf + mttr)
        unavailability = mttr / (mtbf + mttr)
        
        st.metric("Availability", f"{availability*100:.3f}%")
        st.metric("Unavailability", f"{unavailability*100:.3f}%")
        st.metric("Expected Failures/Year", f"{8760/mtbf:.1f}")
        st.metric("Expected Downtime/Year", f"{8760/mtbf * mttr:.0f} hours")
    
    # Maintenance strategy impact
    st.markdown("---")
    st.markdown("##### Maintenance Strategy Impact")
    
    strategies = [
        {'Strategy': 'Reactive (Fail-Fix)', 'MTTR Multiplier': 1.5, 'Cost': 'Low upfront, high reactive'},
        {'Strategy': 'Preventive (Scheduled)', 'MTTR Multiplier': 1.0, 'Cost': 'Moderate, predictable'},
        {'Strategy': 'Predictive (Condition-Based)', 'MTTR Multiplier': 0.7, 'Cost': 'Higher upfront, lower reactive'},
        {'Strategy': 'Reliability-Centered', 'MTTR Multiplier': 0.5, 'Cost': 'Optimized total cost'},
    ]
    
    st.dataframe(pd.DataFrame(strategies), use_container_width=True, hide_index=True)
    
    st.info("""
    **Recommendation:** For AI datacenter applications, implement predictive maintenance 
    with real-time monitoring to minimize MTTR and maximize availability. Budget for 
    strategic spares to reduce repair time for critical components.
    """)


# Helper functions

def calculate_kofn_availability(k: int, n: int, unit_avail: float) -> float:
    """Calculate K-of-N system availability using binomial distribution"""
    
    availability = 0
    
    for i in range(k, n + 1):
        # Probability of exactly i units available
        prob = comb(n, i) * (unit_avail ** i) * ((1 - unit_avail) ** (n - i))
        availability += prob
    
    return availability


def calculate_system_availability(equipment: dict) -> float:
    """Calculate overall system availability based on equipment configuration"""
    
    # Get unit counts
    n_recips = equipment.get('n_recips', 0)
    n_turbines = equipment.get('n_turbines', 0)
    
    total_units = n_recips + n_turbines
    
    if total_units == 0:
        return 0.0
    
    # Assume we need N-1 for full capacity
    k_required = max(1, total_units - 1)
    
    # Weighted average availability
    if n_recips + n_turbines > 0:
        avg_avail = (
            n_recips * EQUIPMENT_DEFAULTS['recip']['availability'] +
            n_turbines * EQUIPMENT_DEFAULTS['turbine']['availability']
        ) / (n_recips + n_turbines)
    else:
        avg_avail = 0.95
    
    return calculate_kofn_availability(k_required, total_units, avg_avail)


def check_n1_redundancy(equipment: dict, peak_load: float) -> bool:
    """Check if N-1 redundancy requirement is met"""
    
    total_capacity = equipment.get('total_firm_mw', 0)
    
    # Largest single unit
    recip_mw = EQUIPMENT_DEFAULTS['recip']['capacity_mw'] if equipment.get('n_recips', 0) > 0 else 0
    turbine_mw = EQUIPMENT_DEFAULTS['turbine']['capacity_mw'] if equipment.get('n_turbines', 0) > 0 else 0
    
    largest_unit = max(recip_mw, turbine_mw)
    
    n1_capacity = total_capacity - largest_unit
    
    return n1_capacity >= peak_load


if __name__ == "__main__":
    render()
