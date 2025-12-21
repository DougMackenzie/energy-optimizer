"""
Results Page
Display optimization results, economics, and scenario comparisons
"""

import streamlit as st
import pandas as pd


def render():
    st.markdown("### 📊 Optimization Results")
    
    # Check if results exist
    if 'optimization_result' not in st.session_state:
        st.warning("⚠️ No optimization results available. Please run optimization from the Optimizer page first.")
        
        if st.button("🎯 Go to Optimizer", type="primary"):
            st.session_state.current_page = 'optimizer'
            st.rerun()
        
        return
    
    # Load results
    result = st.session_state.optimization_result
    
    # Header with feasibility status
    col_status, col_actions = st.columns([3, 1])
    
    with col_status:
        if result['feasible']:
            st.success(f"✅ **FEASIBLE SOLUTION** - Scenario: {result['scenario_name']}")
        else:
            st.error(f"❌ **INFEASIBLE** - Scenario: {result['scenario_name']}")
    
    with col_actions:
        if st.button("🔄 Run Another", use_container_width=True):
            st.session_state.current_page = 'optimizer'
            st.rerun()
    
    # Key Metrics Dashboard
    st.markdown("---")
    st.markdown("#### 🎯 Key Metrics")
    
    economics = result['economics']
    timeline = result['timeline']
    metrics = result['metrics']
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        lcoe_color = "normal"
        if economics['lcoe_mwh'] < 80:
            lcoe_color = "inverse"
        st.metric("LCOE", f"${economics['lcoe_mwh']:.2f}/MWh")
    
    with col2:
        st.metric("CAPEX", f"${economics['total_capex_m']:.1f}M")
    
    with col3:
        deployment_months = timeline['timeline_months']
        delta_color = "inverse" if deployment_months < 24 else "normal"
        st.metric("Deployment", f"{deployment_months} mo", delta=f"{timeline['deployment_speed']}")
    
    with col4:
        st.metric("Capacity", f"{metrics['total_capacity_mw']:.1f} MW")
    
    with col5:
        st.metric("Annual Gen", f"{economics['annual_generation_gwh']:.1f} GWh")
    
    # Constraint Status
    st.markdown("---")
    st.markdown("#### ✅ Constraint Status")
    
    if result['violations']:
        st.error(f"**{len(result['violations'])} Violation(s):**")
        for v in result['violations']:
            st.error(f"• {v}")
    else:
        st.success("✅ All constraints satisfied!")
    
    if result['warnings']:
        st.warning(f"**{len(result['warnings'])} Warning(s):**")
        for w in result['warnings']:
            st.warning(f"• {w}")
    
    # Economics Breakdown
    st.markdown("---")
    st.markdown("#### 💰 Economics Breakdown")
    
    col_econ1, col_econ2 = st.columns(2)
    
    with col_econ1:
        st.markdown("##### Capital Costs")
        st.metric("Total CAPEX", f"${economics['total_capex_m']:.2f}M")
        st.caption(f"Per MW: ${economics['total_capex_m'] / metrics['total_capacity_mw']:.2f}M/MW" if metrics['total_capacity_mw'] > 0 else "N/A")
        
        # Equipment breakdown (if available)
        if result.get('equipment_config'):
            config = result['equipment_config']
            
            if config.get('recip_engines'):
                num_recip = len(config['recip_engines'])
                st.caption(f"• Recip Engines: {num_recip} units")
            
            if config.get('gas_turbines'):
                num_turb = len(config['gas_turbines'])
                st.caption(f"• Gas Turbines: {num_turb} units")
            
            if config.get('bess'):
                num_bess = len(config['bess'])
                st.caption(f"• BESS: {num_bess} units")
            
            if config.get('solar_mw_dc'):
                st.caption(f"• Solar: {config['solar_mw_dc']} MW DC")
    
    with col_econ2:
        st.markdown("##### Operating Costs (Annual)")
        st.metric("O&M", f"${economics['annual_opex_m']:.2f}M/yr")
        st.metric("Fuel/Energy", f"${economics['annual_fuel_cost_m']:.2f}M/yr")
        
        total_annual = economics['annual_opex_m'] + economics['annual_fuel_cost_m']
        st.metric("Total Annual", f"${total_annual:.2f}M/yr")
        
        # Capacity factor
        st.caption(f"Capacity Factor: {economics['capacity_factor_pct']:.1f}%")
    
    # Timeline & Critical Path
    st.markdown("---")
    st.markdown("#### ⏱️ Deployment Timeline")
    
    col_time1, col_time2 = st.columns([2, 1])
    
    with col_time1:
        st.metric("Total Timeline", f"{timeline['timeline_months']} months ({timeline['timeline_years']:.1f} years)")
        st.info(f"**Critical Path:** {timeline['critical_path']}")
        
        # Show stages
        if timeline.get('stages'):
            st.markdown("**Equipment Lead Times:**")
            for stage_name, stage_months in timeline['stages']:
                st.caption(f"• {stage_name}: {stage_months} months")
    
    with col_time2:
        # Deployment speed indicator
        speed = timeline['deployment_speed']
        if speed == 'Fast':
            st.success(f"🚀 **{speed}** Deployment")
            st.caption("< 24 months")
        elif speed == 'Medium':
            st.info(f"⚡ **{speed}** Deployment")
            st.caption("24-48 months")
        else:
            st.warning(f"🐢 **{speed}** Deployment")
            st.caption("> 48 months")
    
    # Equipment Configuration
    st.markdown("---")
    st.markdown("#### ⚙️ Equipment Configuration")
    
    if result.get('equipment_config'):
        config = result['equipment_config']
        
        # Create equipment summary table
        equip_data = []
        
        if config.get('recip_engines'):
            for engine in config['recip_engines']:
                equip_data.append({
                    'Type': 'Reciprocating Engine',
                    'Capacity (MW)': engine.get('capacity_mw', 0),
                    'Capacity Factor': f"{engine.get('capacity_factor', 0):.1%}",
                    'Heat Rate (Btu/kWh)': engine.get('heat_rate_btu_kwh', 0),
                    'CAPEX ($/kW)': f"${engine.get('capex_per_kw', 0):,.0f}"
                })
        
        if config.get('gas_turbines'):
            for turbine in config['gas_turbines']:
                equip_data.append({
                    'Type': 'Gas Turbine',
                    'Capacity (MW)': turbine.get('capacity_mw', 0),
                    'Capacity Factor': f"{turbine.get('capacity_factor', 0):.1%}",
                    'Heat Rate (Btu/kWh)': turbine.get('heat_rate_btu_kwh', 0),
                    'CAPEX ($/kW)': f"${turbine.get('capex_per_kw', 0):,.0f}"
                })
        
        if config.get('bess'):
            for bess in config['bess']:
                equip_data.append({
                    'Type': 'BESS',
                    'Capacity (MW)': bess.get('power_mw', 0),
                    'Energy (MWh)': bess.get('energy_mwh', 0),
                    'Duration (hrs)': bess.get('energy_mwh', 0) / bess.get('power_mw', 1) if bess.get('power_mw') else 0,
                    'CAPEX ($/kWh)': f"${bess.get('capex_per_kwh', 0):,.0f}"
                })
        
        if config.get('solar_mw_dc'):
            equip_data.append({
                'Type': 'Solar PV',
                'Capacity (MW DC)': config.get('solar_mw_dc', 0),
                'CAPEX ($/W)': f"${config.get('solar_capex_per_w', 0):.2f}",
                'Note': 'Single-axis tracker'
            })
        
        if equip_data:
            df = pd.DataFrame(equip_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Next Steps / Actions
    st.markdown("---")
    st.markdown("####🚀 Next Steps")
    
    col_next1, col_next2, col_next3, col_next4 = st.columns(4)
    
    with col_next1:
        if st.button("📈 View Dispatch", use_container_width=True):
            st.session_state.current_page = 'dispatch'
            st.rerun()
    
    with col_next2:
        if st.button("📄 Generate Report", use_container_width=True, type="primary"):
            # Generate portfolio report
            from app.utils.report_export import generate_portfolio_report_data, export_to_text_summary
            
            # Compile data
            sites = [st.session_state.current_config['site']] if 'current_config' in st.session_state else []
            scenarios = [st.session_state.current_config['scenario']] if 'current_config' in st.session_state else []
            results = [result]
            
            report_data = generate_portfolio_report_data(
                sites=sites,
                scenarios=scenarios,
                optimization_results=results
            )
            
            # Generate text export
            report_text = export_to_text_summary(report_data)
            
            # Store for download
            st.session_state.generated_report = report_text
            
            st.success("✅ Report generated! Download below.")
            st.rerun()
    
    with col_next3:
        if 'generated_report' in st.session_state:
            st.download_button(
                label="📥 Download Report",
                data=st.session_state.generated_report,
                file_name=f"optimization_report_{result['scenario_name'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with col_next4:
        if st.button("🔧 Modify Config", use_container_width=True):
            st.session_state.current_page = 'optimizer'
            st.rerun()


if __name__ == "__main__":
    render()
