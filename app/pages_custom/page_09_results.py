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
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🎯 Go to Optimizer", type="primary"):
                st.session_state.current_page = 'optimizer'
                st.rerun()
        
        with col_btn2:
            if st.button("🎲 Load Demo Results", type="secondary"):
                # Load demo results instantly for testing
                from app.utils.multi_scenario import run_all_scenarios
                from app.utils.site_loader import load_sites, load_site_constraints, load_scenario_templates
                
                with st.spinner("Loading demo data..."):
                    try:
                            # Use 600MW Sample Problem for robust demo
                            from sample_problem_600mw import get_sample_problem
                            problem = get_sample_problem()
                            
                            site = problem['site']
                            constraints = {**problem['constraints'], 'N_Minus_1_Required': False}
                            load_profile_dr = problem['load_profile']
                            
                            # Run all scenarios with MILP
                            all_results = run_all_scenarios(
                                site=site, 
                                constraints=constraints, 
                                objectives=objectives, 
                                scenarios=scenarios, 
                                grid_config=None,
                                use_milp=True,
                                load_profile_dr=load_profile_dr
                            )
                            
                            if all_results:
                                # Find first feasible result
                                result = next((r for r in all_results if r.get('feasible')), None)
                                
                                if result:
                                    scenario = next((s for s in scenarios if s.get('Scenario_Name') == result.get('scenario_name')), scenarios[0])
                                    
                                    st.session_state.optimization_result = result
                                    st.session_state.multi_scenario_results = all_results
                                    st.session_state.current_config = {
                                        'site': site,
                                        'scenario': scenario,
                                        'constraints': constraints,
                                        'objectives': objectives,
                                        'equipment_enabled': {
                                            'recip': True,
                                            'turbine': True,
                                            'bess': True,
                                            'solar': True,
                                            'grid': True
                                        }
                                    }
                                    st.success("✅ Demo data loaded!")
                                    st.rerun()
                                else:
                                    st.error("No feasible scenarios found")
                    except Exception as e:
                        st.error(f"Error loading demo data: {str(e)}")
        
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
        
        # Use .get() with defaults to prevent KeyError
        annual_opex = economics.get('annual_opex_m', 0)
        annual_fuel = economics.get('annual_fuel_cost_m', 0)
        annual_gen = economics.get('annual_generation_gwh', 0)
        capacity_factor = economics.get('capacity_factor_pct', 0)
        
        st.metric("O&M", f"${annual_opex:.2f}M/yr")
        st.metric("Fuel/Energy", f"${annual_fuel:.2f}M/yr")
        
        total_annual = annual_opex + annual_fuel
        st.metric("Total Annual", f"${total_annual:.2f}M/yr")
        
        # Capacity factor
        st.caption(f"Capacity Factor: {capacity_factor:.1f}%")
    
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
    
    # DEMAND RESPONSE METRICS (New Section)
    if 'dr_metrics' in result and result['dr_metrics']:
        st.markdown("---")
        st.markdown("#### 💡 Demand Response Metrics")
        
        dr = result['dr_metrics']
        
        # Key DR metrics
        col_dr1, col_dr2, col_dr3, col_dr4 = st.columns(4)
        
        with col_dr1:
            st.metric("Annual Curtailment", 
                     f"{dr.get('total_curtailment_mwh', 0):.0f} MWh",
                     delta=f"{dr.get('curtailment_pct', 0):.2f}% of load")
        
        with col_dr2:
            st.metric("DR Revenue", 
                     f"${dr.get('dr_revenue_annual', 0):,.0f}/yr")
        
        with col_dr3:
            # Calculate LCOE benefit
            if economics.get('lcoe_mwh') and economics.get('annual_generation_gwh'):
                lcoe_benefit = (dr.get('dr_revenue_annual', 0) / 
                               (economics['annual_generation_gwh'] * 1000))
                st.metric("LCOE Benefit", 
                         f"${lcoe_benefit:.2f}/MWh",
                         delta="Lower is better",
                         delta_color="inverse")
            else:
                st.metric("LCOE Benefit", "N/A")
        
        with col_dr4:
            # Total flexibility percentage
            if 'load_data' in st.session_state.get('load_profile_dr', {}):
                load_data = st.session_state.load_profile_dr['load_data']
                flex_pct = load_data['summary'].get('avg_flexibility_pct', 0)
                st.metric("Avg Flexibility", f"{flex_pct:.1f}%")
            else:
                st.metric("Avg Flexibility", f"{dr.get('curtailment_pct', 0):.1f}%")
        
        # DR capacity breakdown by product
        if dr.get('dr_capacity_by_product'):
            st.markdown("##### DR Capacity Enrolled by Product")
            
            dr_products = dr['dr_capacity_by_product']
            product_data = []
            
            for product, capacity_mw in dr_products.items():
                if capacity_mw > 0:
                    product_data.append({
                        'Product': product.replace('_', ' ').title(),
                        'Enrolled Capacity (MW)': f"{capacity_mw:.1f}",
                        'Status': '✅ Active' if capacity_mw > 0 else '❌ Inactive'
                    })
            
            if product_data:
                df_dr = pd.DataFrame(product_data)
                st.dataframe(df_dr, use_container_width=True, hide_index=True)
            else:
                st.info("No DR products enrolled in this optimization")
        
        # Flexibility composition (if available)
        if 'load_data' in st.session_state.get('load_profile_dr', {}):
            with st.expander("📊 View Flexibility Breakdown"):
                load_data = st.session_state.load_profile_dr['load_data']
                
                col_flex1, col_flex2 = st.columns(2)
                
                with col_flex1:
                    st.markdown("**IT Workload Flexibility**")
                    workload_flex = {
                        'Pre-Training': load_data['summary'].get('pre_training_flex_avg', 0),
                        'Fine-Tuning': load_data['summary'].get('fine_tuning_flex_avg', 0),
                        'Batch Inference': load_data['summary'].get('batch_flex_avg', 0),
                        'Real-Time': load_data['summary'].get('realtime_flex_avg', 0),
                    }
                    
                    for wl, flex in workload_flex.items():
                        if flex > 0:
                            st.caption(f"• {wl}: {flex:.1f} MW")
                
                with col_flex2:
                    st.markdown("**Cooling Flexibility**")
                    cooling_flex = load_data['summary'].get('cooling_flex_avg', 0)
                    st.caption(f"• Cooling systems: {cooling_flex:.1f} MW")
                    st.caption(f"• Thermal time constant: 30 min (typical)")

    
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
            with st.spinner("Generating comprehensive Word document..."):
                from app.utils.word_report import generate_comprehensive_word_report
                
                # Get all necessary data
                site = st.session_state.current_config.get('site', {})
                constraints = st.session_state.current_config.get('constraints', {})
                scenario = st.session_state.current_config.get('scenario', {})
                equipment_config = result.get('equipment_config', {})
                load_profile = st.session_state.get('load_profile', None)
                
                try:
                    # Generate Word document
                    word_bytes = generate_comprehensive_word_report(
                        site=site,
                        constraints=constraints,
                        scenario=scenario,
                        equipment_config=equipment_config,
                        optimization_result=result,
                        load_profile=load_profile
                    )
                    
                    # Store for download
                    st.session_state.generated_report = word_bytes
                    st.session_state.report_type = 'docx'
                    
                    st.success("✅ Comprehensive Word report generated! Download below.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
    
    with col_next3:
        if 'generated_report' in st.session_state:
            # Create a safe filename
            safe_scenario_name = result['scenario_name'].replace(' ', '_').replace('+', 'plus').replace('(', '').replace(')', '')
            
            # Check report type
            report_type = st.session_state.get('report_type', 'txt')
            
            if report_type == 'docx':
                filename = f"Optimization_Report_{safe_scenario_name}.docx"
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                data = st.session_state.generated_report  # Already bytes
            else:
                filename = f"optimization_report_{safe_scenario_name}.txt"
                mime_type = "text/plain"
                data = st.session_state.generated_report.encode('utf-8') if isinstance(st.session_state.generated_report, str) else st.session_state.generated_report
            
            st.download_button(
                label="📥 Download Report",
                data=data,
                file_name=filename,
                mime=mime_type,
                use_container_width=True,
                key="download_report_btn"
            )
        else:
            st.caption("⚠️ Click 'Generate Report' first")
    
    with col_next4:
        if st.button("🔧 Modify Config", use_container_width=True):
            st.session_state.current_page = 'optimizer'
            st.rerun()


if __name__ == "__main__":
    render()
