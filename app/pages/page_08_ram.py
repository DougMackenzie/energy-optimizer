"""
RAM Analysis Page
Reliability, Availability, and Maintainability analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict


def calculate_ram_metrics(equipment_config: Dict) -> Dict:
    """
    Calculate RAM metrics for equipment configuration
    
    Based on IEEE 493 (Gold Book) and typical industry data
    """
    
    # Typical MTBF and MTTR values (hours)
    equipment_params = {
        'recip': {
            'mtbf': 8760,  # 1 year typical
            'mttr': 72,    # 3 days
            'availability': 0.992,
            'forced_outage_rate': 0.008
        },
        'turbine': {
            'mtbf': 17520,  # 2 years typical
            'mttr': 168,    # 1 week
            'availability': 0.990,
            'forced_outage_rate': 0.010
        },
        'bess': {
            'mtbf': 43800,  # 5 years
            'mttr': 24,     # 1 day
            'availability': 0.9995,
            'forced_outage_rate': 0.0005
        },
        'solar': {
            'mtbf': 87600,  # 10 years
            'mttr': 48,     # 2 days
            'availability': 0.9995,
            'forced_outage_rate': 0.0005
        },
        'grid': {
            'mtbf': 4380,   # 6 months (varies widely)
            'mttr': 4,      # 4 hours
            'availability': 0.999,
            'forced_outage_rate': 0.001
        }
    }
    
    results = {
        'equipment': [],
        'system_availability': 0,
        'n_minus_1_availability': 0,
        'expected_outages_per_year': 0,
        'expected_downtime_hours_per_year': 0
    }
    
    # Analyze each equipment type
    total_capacity = 0
    weighted_availability = 0
    
    # Reciprocating Engines
    recip_count = len(equipment_config.get('recip_engines', []))
    if recip_count > 0:
        recip_cap = sum(e.get('capacity_mw', 0) for e in equipment_config.get('recip_engines', []))
        params = equipment_params['recip']
        
        # Parallel redundancy increases availability
        unit_avail = params['availability']
        system_avail = 1 - (1 - unit_avail) ** recip_count
        
        results['equipment'].append({
            'Type': 'Reciprocating Engines',
            'Count': recip_count,
            'Capacity (MW)': recip_cap,
            'Unit Availability': f"{unit_avail:.4f}",
            'System Availability': f"{system_avail:.6f}",
            'MTBF (hrs)': params['mtbf'],
            'MTTR (hrs)': params['mttr']
        })
        
        total_capacity += recip_cap
        weighted_availability += system_avail * recip_cap
    
    # Gas Turbines
    turbine_count = len(equipment_config.get('gas_turbines', []))
    if turbine_count > 0:
        turbine_cap = sum(e.get('capacity_mw', 0) for e in equipment_config.get('gas_turbines', []))
        params = equipment_params['turbine']
        
        unit_avail = params['availability']
        system_avail = 1 - (1 - unit_avail) ** turbine_count
        
        results['equipment'].append({
            'Type': 'Gas Turbines',
            'Count': turbine_count,
            'Capacity (MW)': turbine_cap,
            'Unit Availability': f"{unit_avail:.4f}",
            'System Availability': f"{system_avail:.6f}",
            'MTBF (hrs)': params['mtbf'],
            'MTTR (hrs)': params['mttr']
        })
        
        total_capacity += turbine_cap
        weighted_availability += system_avail * turbine_cap
    
    # BESS
    bess_count = len(equipment_config.get('bess', []))
    if bess_count > 0:
        bess_cap = sum(e.get('power_mw', 0) for e in equipment_config.get('bess', []))
        params = equipment_params['bess']
        
        unit_avail = params['availability']
        system_avail = 1 - (1 - unit_avail) ** bess_count
        
        results['equipment'].append({
            'Type': 'BESS',
            'Count': bess_count,
            'Capacity (MW)': bess_cap,
            'Unit Availability': f"{unit_avail:.4f}",
            'System Availability': f"{system_avail:.6f}",
            'MTBF (hrs)': params['mtbf'],
            'MTTR (hrs)': params['mttr']
        })
    
    # Solar
    solar_cap = equipment_config.get('solar_mw_dc', 0)
    if solar_cap > 0:
        params = equipment_params['solar']
        
        results['equipment'].append({
            'Type': 'Solar PV',
            'Count': 1,
            'Capacity (MW)': solar_cap,
            'Unit Availability': f"{params['availability']:.4f}",
            'System Availability': f"{params['availability']:.6f}",
            'MTBF (hrs)': params['mtbf'],
            'MTTR (hrs)': params['mttr']
        })
    
    # Grid
    grid_cap = equipment_config.get('grid_import_mw', 0)
    if grid_cap > 0:
        params = equipment_params['grid']
        
        results['equipment'].append({
            'Type': 'Grid Connection',
            'Count': 1,
            'Capacity (MW)': grid_cap,
            'Unit Availability': f"{params['availability']:.4f}",
            'System Availability': f"{params['availability']:.6f}",
            'MTBF (hrs)': params['mtbf'],
            'MTTR (hrs)': params['mttr']
        })
        
        total_capacity += grid_cap
        weighted_availability += params['availability'] * grid_cap
    
    # Calculate system-level metrics
    if total_capacity > 0:
        results['system_availability'] = weighted_availability / total_capacity
    else:
        results['system_availability'] = 0
    
    # N-1 availability (largest unit out)
    # Simplified: assume 10% reduction for N-1 scenario
    results['n_minus_1_availability'] = results['system_availability'] * 0.90
    
    # Expected outages per year
    results['expected_outages_per_year'] = (1 - results['system_availability']) * 10  # Rough estimate
    
    # Expected downtime hours per year
    results['expected_downtime_hours_per_year'] = 8760 * (1 - results['system_availability'])
    
    return results


def render():
    st.markdown("### 🛡️ RAM Analysis")
    st.caption("Reliability, Availability, and Maintainability")
    
    # Check if optimization results exist
    if 'optimization_result' not in st.session_state:
        st.warning("⚠️ No optimization results available. Please run optimization first.")
        
        if st.button("🎯 Go to Optimizer", type="primary"):
            st.session_state.current_page = 'optimizer'
            st.rerun()
        
        return
    
    result = st.session_state.optimization_result
    
    st.markdown(f"#### RAM Analysis: {result['scenario_name']}")
    
    # Run RAM analysis button
    col_ram1, col_ram2 = st.columns([3, 1])
    
    with col_ram1:
        st.info("""
        **Reliability Analysis based on:**
        - IEEE 493 Gold Book standards
        - Industry-typical MTBF/MTTR values
        - Parallel redundancy calculations
        """)
    
    with col_ram2:
        if st.button("📊 Calculate RAM", type="primary", use_container_width=True):
            with st.spinner("Calculating reliability metrics..."):
                ram_results = calculate_ram_metrics(result['equipment_config'])
                st.session_state.ram_results = ram_results
                st.success("✅ RAM analysis complete!")
                st.rerun()
    
    # Display results if available
    if 'ram_results' in st.session_state:
        ram = st.session_state.ram_results
        
        st.markdown("---")
        st.markdown("#### 📊 System Reliability Metrics")
        
        # Key metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            st.metric("System Availability", f"{ram['system_availability']:.4%}")
            st.caption("Weighted by capacity")
        
        with col_m2:
            st.metric("N-1 Availability", f"{ram['n_minus_1_availability']:.4%}")
            st.caption("Largest unit out")
        
        with col_m3:
            downtime = ram['expected_downtime_hours_per_year']
            st.metric("Expected Downtime", f"{downtime:.1f} hrs/yr")
            st.caption(f"{downtime/24:.1f} days/year")
        
        with col_m4:
            uptime = 8760 - downtime
            st.metric("Expected Uptime", f"{uptime:.0f} hrs/yr")
            st.caption(f"{uptime/8760:.2%} of year")
        
        # Equipment details table
        st.markdown("---")
        st.markdown("#### ⚙️ Equipment Reliability Details")
        
        df_equip = pd.DataFrame(ram['equipment'])
        st.dataframe(df_equip, use_container_width=True, hide_index=True)
        
        # Availability comparison chart
        st.markdown("---")
        st.markdown("#### 📈 Availability Comparison")
        
        fig = go.Figure()
        
        equipment_types = [e['Type'] for e in ram['equipment']]
        system_avails = [float(e['System Availability']) for e in ram['equipment']]
        
        fig.add_trace(go.Bar(
            x=equipment_types,
            y=system_avails,
            text=[f"{a:.4%}" for a in system_avails],
            textposition='auto',
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][:len(equipment_types)]
        ))
        
        fig.update_layout(
            title="System Availability by Equipment Type",
            xaxis_title="Equipment",
            yaxis_title="Availability",
            yaxis=dict(tickformat='.2%'),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Reliability standards comparison
        st.markdown("---")
        st.markdown("#### 📋 Industry Standards Comparison")
        
        col_std1, col_std2 = st.columns(2)
        
        with col_std1:
            st.markdown("**Tier Standards (Uptime Institute):**")
            standards = pd.DataFrame({
                'Tier': ['Tier I', 'Tier II', 'Tier III', 'Tier IV'],
                'Availability': ['99.671%', '99.741%', '99.982%', '99.995%'],
                'Downtime/Year': ['28.8 hrs', '22.7 hrs', '1.6 hrs', '0.4 hrs'],
                'N+X': ['N', 'N+1', 'N+1 (concurrent)', 'N+2']
            })
            st.dataframe(standards, use_container_width=True, hide_index=True)
            
            # Compare to system
            sys_avail = ram['system_availability']
            if sys_avail >= 0.99995:
                st.success("✅ Meets or exceeds **Tier IV** standards")
            elif sys_avail >= 0.99982:
                st.success("✅ Meets **Tier III** standards")
            elif sys_avail >= 0.99741:
                st.info("ℹ️ Meets **Tier II** standards")
            else:
                st.warning("⚠️ Below Tier II standards")
        
        with col_std2:
            st.markdown("**SLA Comparison:**")
            slas = pd.DataFrame({
                'SLA Level': ['99.9% (3-nines)', '99.99% (4-nines)', '99.999% (5-nines)', '99.9999% (6-nines)'],
                'Downtime/Year': ['8.76 hrs', '52.6 min', '5.26 min', '31.5 sec'],
                'Typical Use': ['Enterprise', 'Mission-critical', 'Life-safety', 'Extreme']
            })
            st.dataframe(slas, use_container_width=True, hide_index=True)
            
            # SLA achievement
            if sys_avail >= 0.999999:
                st.success("✅ Achieves **6-nines** availability")
            elif sys_avail >= 0.99999:
                st.success("✅ Achieves **5-nines** availability")
            elif sys_avail >= 0.9999:
                st.info("ℹ️ Achieves **4-nines** availability")
            else:
                st.warning("ℹ️ Below 4-nines SLA")
        
        # Improvement recommendations
        st.markdown("---")
        st.markdown("#### 💡 Reliability Improvement Recommendations")
        
        if ram['system_availability'] < 0.9999:
            st.info("""
            **To improve system reliability:**
            - Add redundant units (increase N+1 to N+2)
            - Include BESS for transient backup
            - Implement preventive maintenance program
            - Add automated transfer switches
            - Consider dual-feed grid connections
            """)
        else:
            st.success("""
            **Excellent reliability! To maintain:**
            - Regular preventive maintenance
            - Spare parts inventory management
            - Operator training programs
            - Real-time monitoring systems
            """)


if __name__ == "__main__":
    render()
