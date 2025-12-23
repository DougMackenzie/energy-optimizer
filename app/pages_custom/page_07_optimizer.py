"""
Optimizer Page
Evaluates scenarios against constraints and runs optimization
"""

import streamlit as st
from app.utils.constraint_validator import validate_configuration
from datetime import datetime


def render():
    st.markdown("### 🎯 Optimizer")
    
    # Check if configuration exists
    if 'current_config' not in st.session_state:
        st.warning("⚠️ No configuration loaded. Please configure your energy stack in the Equipment Library page first.")
        
        if st.button("📋 Go to Equipment Library", type="primary"):
            st.session_state.current_page = 'equipment_library'
            st.rerun()
        
        return
    
    # Load configuration
    config = st.session_state.current_config
    site = config['site']
    scenario = config['scenario']
    equipment_enabled = config['equipment_enabled']
    constraints = config['constraints']
    objectives = config['objectives']
    
    # Display Configuration Summary
    st.markdown("#### 📋 Current Configuration")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Site", site.get('Site_Name', 'Unknown'))
        st.caption(f"ISO: {site.get('ISO', 'N/A')}")
    with col2:
        st.metric("Scenario", scenario.get('Scenario_Name', 'Unknown')[:20] + "...")
        st.caption(f"Target: ${scenario.get('Target_LCOE_MWh', 0)}/MWh")
    with col3:
        enabled_count = sum(1 for v in equipment_enabled.values() if v)
        st.metric("Technologies", f"{enabled_count} enabled")
        tech_list = [k.title() for k, v in equipment_enabled.items() if v]
        st.caption(", ".join(tech_list[:3]))
    with col4:
        if objectives:
            st.metric("Objective", objectives.get('Primary_Objective', 'N/A')[:15])
            st.caption(f"Max: {objectives.get('Deployment_Max_Months', 0)} mo")
        else:
            st.metric("Objective", "Not Set")
    
    # Multi-Scenario Comparison
    st.markdown("---")
    
    # Optimization Mode Selector
    st.markdown("#### ⚙️ Optimization Settings")
    col_mode1, col_mode2 = st.columns([2, 3])
    
    with col_mode1:
    with col_mode1:
        st.markdown("**Optimization Mode**")
        st.success("🎯 **Accurate Mode (Recommended)**")
        st.caption("1008 hours, 1% MIP gap - Best for final designs")
        
        # Force Accurate Mode (Fast mode disabled due to instability)
        st.session_state.use_fast_milp = False
    
    with col_mode2:
        st.info("ℹ️ **Note:** Fast Mode has been temporarily disabled to ensure result accuracy. Solves may take 2-4 minutes per scenario.")
    
    st.markdown("---")
    
    with st.expander("🔄 Batch Run All Scenarios", expanded=False):
        st.markdown("#### Compare All Deployment Strategies")
        st.info("""
        **Auto-run all 5 scenarios** for this site and compare:
        - Automatically sizes equipment for each scenario
        - Validates constraints
        - Calculates LCOE and deployment timeline
        - Ranks scenarios by weighted objectives
        """)
        
        col_batch1, col_batch2 = st.columns([3, 1])
        
        with col_batch1:
            st.caption("This will run: BTM Only, All Sources, Bridge to Backup")
        
        with col_batch2:
            # Check if Load Composer is configured
            if 'load_profile_dr' not in st.session_state:
                st.error("⚠️ **Load Composer Required**")
                st.markdown("""
                To use the optimizer, you must first configure the Load Composer:
                
                1. Navigate to **Load Composer** (in sidebar)
                2. Configure all 4 tabs (Load, Workload, Cooling, DR Economics)
                3. Click **Save Configuration**
                4. Return here to run scenarios
                
                The legacy scipy optimizer is deprecated and no longer supported.
                """)
                if st.button("📊 Go to Load Composer", use_container_width=True):
                    st.session_state.current_page = 'load_composer'
                    st.rerun()
            else:
                if st.button("⚡ Run All Scenarios", type="primary", use_container_width=True):
                    with st.spinner("Running all scenarios with MILP... This may take 2-4 minutes"):
                        from app.utils.multi_scenario import run_all_scenarios, create_comparison_table
                        from app.utils.site_loader import load_scenario_templates
                        
                        scenarios = load_scenario_templates()
                        
                        # Get data from session state
                        load_profile_dr = st.session_state.load_profile_dr
                        
                        st.info("🚀 Using bvNexus MILP optimizer (100% feasibility guaranteed)")
                        
                        # Run all scenarios with MILP
                        results = run_all_scenarios(
                            site=site,
                            constraints=constraints,
                            objectives=objectives,
                            scenarios=scenarios,
                            grid_config=None,
                            use_milp=True,
                            load_profile_dr=load_profile_dr
                        )
                        
                        # Store results
                        st.session_state.multi_scenario_results = results
                        
                        st.success(f"✅ Completed {len(results)} scenarios!")
                        st.rerun()
        
        # Display results if available
        if 'multi_scenario_results' in st.session_state:
            st.markdown("---")
            st.markdown("#### 📊 Scenario Comparison Results")
            
            from app.utils.multi_scenario import create_comparison_table
            
            results = st.session_state.multi_scenario_results
            df = create_comparison_table(results)
            
            # Display table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # DETAILED EQUIPMENT COMBINATION ANALYSIS
            st.markdown("---")
            st.markdown("### 🔍 Equipment Combination Analysis")
            st.markdown("All equipment combinations tested within each scenario, ranked by performance")
            
            import pandas as pd
            
            for result in results:
                scenario_name = result.get('scenario_name', 'Unknown')
                equipment_config = result.get('equipment_config', {})
                
                if '_combination_results' in equipment_config:
                    combination_results = equipment_config['_combination_results']
                    
                    with st.expander(f"📋 {scenario_name} - {len(combination_results)} Combinations Tested", expanded=True):
                        # Create comparison dataframe
                        combo_data = []
                        for idx, combo in enumerate(combination_results):
                            combo_data.append({
                                'Rank': idx + 1,
                                'Equipment Combination': combo['combination_name'],
                                'Feasible': '✅' if combo['feasible'] else '❌',
                                'Power (MW-years)': f"{combo['total_power_delivered']:.0f}",
                                'LCOE ($/MWh)': f"${combo['lcoe']:.2f}",
                                'Timeline (mo)': combo['critical_path_months'],
                                'Violations': len(combo['violations']) if combo['violations'] else 0
                            })
                        
                        combo_df = pd.DataFrame(combo_data)
                        st.dataframe(combo_df, use_container_width=True, hide_index=True)
                        
                        # Summary
                        feasible = [c for c in combination_results if c['feasible']]
                        st.markdown(f"**Summary:** {len(feasible)}/{len(combination_results)} combinations feasible")
                        
                        if feasible:
                            best = feasible[0]
                            st.success(f"🏆 Best: {best['combination_name']} - {best['total_power_delivered']:.0f} MW-years @ ${best['lcoe']:.2f}/MWh")
            
            # Add annual capacity stack charts for feasible scenarios
            feasible_results = [r for r in results if r.get('feasible')]
            if feasible_results:
                st.markdown("---")
                st.markdown("### 📊 Annual Capacity Deployment")
                st.markdown("Stacked capacity by technology showing phased deployment over time")
                
                from app.utils.phased_charts import create_annual_capacity_stack_chart
                
                for idx, result in enumerate(feasible_results):
                    equipment_config = result.get('equipment_config', {})
                    if '_phased_deployment' in equipment_config:
                        st.markdown(f"#### {result['scenario_name']}")
                        
                        deployment = equipment_config['_phased_deployment']
                        load_trajectory = site.get('load_trajectory', {
                            2026: 0, 2027: 0, 2028: 150, 2029: 300, 2030: 450, 2031: 600,
                            2032: 600, 2033: 600, 2034: 600, 2035: 600
                        })
                        
                        fig = create_annual_capacity_stack_chart(
                            deployment=deployment,
                            load_trajectory=load_trajectory,
                            years=list(range(2026, 2036))  # 2026-2035 (10 years)
                        )
                        
                        # Use unique key for each chart to avoid Streamlit duplicate ID error
                        st.plotly_chart(fig, use_container_width=True, key=f"capacity_chart_{idx}")
            
            # Show top recommendation
            if len(results) > 0 and results[0].get('feasible'):
                top_result = results[0]
                st.success(f"""
                **🏆 Recommended Scenario: {top_result['scenario_name']}**
                - LCOE: ${top_result['economics']['lcoe_mwh']:.2f}/MWh
                - Deployment: {top_result['timeline']['timeline_months']} months
                - Score: {top_result['score']:.1f}/100
                """)
            
            # Option to select a scenario
            scenario_names = [r['scenario_name'] for r in results if r.get('feasible')]
            
            if scenario_names:
                col_sel1, col_sel2 = st.columns([3, 1])
                
                with col_sel1:
                    selected_scenario = st.selectbox("Select scenario to view details:", scenario_names, key="scenario_selector")
                
                with col_sel2:
                    if st.button("📋 View Details", use_container_width=True, type="primary"):
                        # Find selected result
                        selected_result = next((r for r in results if r['scenario_name'] == selected_scenario), None)
                        if selected_result:
                            st.session_state.optimization_result = selected_result
                            st.success(f"✅ Loading {selected_scenario}...")
                            st.session_state.current_page = 'results'
                            st.rerun()
            else:
                st.warning("⚠️ No feasible scenarios to view. All scenarios have constraint violations.")
            
            # Export All Scenarios Button (always show if results exist)
            st.markdown("---")
            st.markdown("#### 📄 Export All Scenarios")
            
            col_export1, col_export2 = st.columns([3, 1])
            
            with col_export1:
                st.info("Generate a comprehensive Word document containing all scenarios (feasible + infeasible) with comparison table and detailed analysis.")
            
            with col_export2:
                if st.button("📥 Export All Scenarios", use_container_width=True, type="primary"):
                    with st.spinner("Generating multi-scenario report..."):
                        from app.utils.multi_scenario_report import generate_multi_scenario_report
                        
                        # Generate report
                        report_bytes = generate_multi_scenario_report(
                            site=site,
                            constraints=constraints,
                            all_results=results,
                            load_profile=None  # TODO: Add load profile if available
                        )
                        
                        # Create download
                        filename = f"{site.get('Site_Name', 'Site').replace(' ', '_')}_All_Scenarios_{datetime.now().strftime('%Y%m%d')}.docx"
                        st.download_button(
                            label="💾 Download Multi-Scenario Report",
                            data=report_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                        
                        st.success(f"✅ Report generated! Click above to download.")
    
    st.markdown("---")
    
    # Equipment Sizing Section (existing content continues below)
    st.markdown("#### ⚙️ Manual Equipment Sizing")
    st.info("Configure equipment capacities for this scenario. The optimizer will validate against site constraints.")
    
    from app.utils.data_io import load_equipment_from_sheets
    equipment_data = load_equipment_from_sheets()
    
    # Create sizing inputs based on enabled equipment
    sizing = {}
    
    if equipment_enabled.get('recip'):
        with st.expander("🔋 Reciprocating Engines", expanded=True):
            recip_engines = equipment_data.get("Reciprocating_Engines", [])
            if recip_engines:
                st.markdown("**Select model and quantity:**")
                
                model_options = [f"{e.get('Model', 'Unknown')} ({e.get('Capacity_MW', 0)} MW)" 
                                for e in recip_engines if e]
                selected_model = st.selectbox("Engine Model", model_options, key="recip_model")
                
                # Find selected engine
                model_name = selected_model.split(" (")[0]
                selected_engine = next((e for e in recip_engines if e and e.get('Model') == model_name), None)
                
                if selected_engine:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        num_units = st.number_input("Number of Units", min_value=1, max_value=20, value=4, key="recip_qty")
                    with col2:
                        cap_factor = st.slider("Capacity Factor", 0.0, 1.0, 0.7, key="recip_cf")
                    with col3:
                        total_cap = selected_engine.get('Capacity_MW', 0) * num_units
                        st.metric("Total Capacity", f"{total_cap} MW")
                    
                    # Store sizing
                    sizing['recip_engines'] = [{
                        'capacity_mw': selected_engine.get('Capacity_MW', 0),
                        'capacity_factor': cap_factor,
                        'heat_rate_btu_kwh': selected_engine.get('Heat_Rate_BTU_kWh', 7700),
                        'nox_lb_mmbtu': selected_engine.get('NOx_lb_MMBtu', 0.099),
                        'co_lb_mmbtu': selected_engine.get('CO_lb_MMBtu', 0.015),
                        'capex_per_kw': selected_engine.get('CAPEX_per_kW', 1650),
                        'quantity': num_units
                    }] * num_units
    
    if equipment_enabled.get('turbine'):
        with st.expander("⚡ Gas Turbines", expanded=True):
            turbines = equipment_data.get("Gas_Turbines", [])
            if turbines:
                st.markdown("**Select model and quantity:**")
                
                model_options = [f"{e.get('Model', 'Unknown')} ({e.get('Capacity_MW', 0)} MW)" 
                                for e in turbines if e]
                selected_model = st.selectbox("Turbine Model", model_options, key="turbine_model")
                
                model_name = selected_model.split(" (")[0]
                selected_turbine = next((e for e in turbines if e and e.get('Model') == model_name), None)
                
                if selected_turbine:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        num_units = st.number_input("Number of Units", min_value=1, max_value=10, value=2, key="turbine_qty")
                    with col2:
                        cap_factor = st.slider("Capacity Factor", 0.0, 1.0, 0.5, key="turbine_cf")
                    with col3:
                        total_cap = selected_turbine.get('Capacity_MW', 0) * num_units
                        st.metric("Total Capacity", f"{total_cap} MW")
                    
                    sizing['gas_turbines'] = [{
                        'capacity_mw': selected_turbine.get('Capacity_MW', 0),
                        'capacity_factor': cap_factor,
                        'heat_rate_btu_kwh': selected_turbine.get('Heat_Rate_BTU_kWh', 8500),
                        'nox_lb_mmbtu': selected_turbine.get('NOx_lb_MMBtu', 0.099),
                        'co_lb_mmbtu': selected_turbine.get('CO_lb_MMBtu', 0.015),
                        'capex_per_kw': selected_turbine.get('CAPEX_per_kW', 1300),
                        'quantity': num_units
                    }] * num_units
    
    if equipment_enabled.get('bess'):
        with st.expander("🔋 BESS", expanded=True):
            bess_systems = equipment_data.get("BESS", [])
            if bess_systems:
                st.markdown("**Select model and quantity:**")
                
                model_options = [f"{e.get('Model', 'Unknown')} ({e.get('Energy_MWh', 0)} MWh)" 
                                for e in bess_systems if e]
                selected_model = st.selectbox("BESS Model", model_options, key="bess_model")
                
                model_name = selected_model.split(" (")[0]
                selected_bess = next((e for e in bess_systems if e and e.get('Model') == model_name), None)
                
                if selected_bess:
                    col1, col2 = st.columns(2)
                    with col1:
                        num_units = st.number_input("Number of Units", min_value=1, max_value=50, value=10, key="bess_qty")
                    with col2:
                        total_energy = selected_bess.get('Energy_MWh', 0) * num_units
                        total_power = selected_bess.get('Power_MW', 0) * num_units
                        st.metric("Total Energy", f"{total_energy:.1f} MWh")
                        st.metric("Total Power", f"{total_power:.1f} MW")
                    
                    sizing['bess'] = [{
                        'energy_mwh': selected_bess.get('Energy_MWh', 0),
                        'power_mw': selected_bess.get('Power_MW', 0),
                        'capex_per_kwh': selected_bess.get('CAPEX_per_kWh', 236),
                        'quantity': num_units
                    }] * num_units
    
    if equipment_enabled.get('solar'):
        with st.expander("☀️ Solar PV", expanded=True):
            solar_systems = equipment_data.get("Solar_PV", [])
            if solar_systems:
                st.markdown("**Configure solar capacity:**")
                
                # Find appropriate system for this site
                site_region = "National"  # Default
                if "Texas" in site.get('State', ''):
                    site_region = "Southwest"
                elif "Virginia" in site.get('State', ''):
                    site_region = "Southeast"
                elif "Oklahoma" in site.get('State', ''):
                    site_region = "Midwest"
                
                matching_solar = next((s for s in solar_systems if s and site_region in s.get('Region', '')), solar_systems[0] if solar_systems else None)
                
                if matching_solar:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        solar_mw = st.number_input("Solar DC Capacity (MW)", min_value=0, max_value=500, value=25, key="solar_mw")
                    with col2:
                        st.metric("Capacity Factor", f"{matching_solar.get('Capacity_Factor_Pct', 0)}%")
                        st.caption(f"Region: {matching_solar.get('Region', 'Unknown')}")
                    with col3:
                        land_needed = solar_mw * matching_solar.get('Land_Use_acres_per_MW', 4.25)
                        st.metric("Land Required", f"{land_needed:.1f} acres")
                    
                    sizing['solar_mw_dc'] = solar_mw
                    sizing['solar_capex_per_w'] = matching_solar.get('CAPEX_per_W_DC', 0.95)
    
    if equipment_enabled.get('grid'):
        with st.expander("🔌 Grid Connection", expanded=True):
            st.markdown("**Configure grid import:**")
            
            col1, col2 = st.columns(2)
            with col1:
                grid_mw = st.number_input("Grid Import (MW)", min_value=0, max_value=500, value=50, key="grid_mw")
            with col2:
                avail_grid = constraints.get('Grid_Available_MW', 0)
                st.metric("Available", f"{avail_grid} MW")
                if grid_mw > avail_grid:
                    st.error(f"⚠️ Exceeds available capacity!")
            
            sizing['grid_import_mw'] = grid_mw
    
    # Run Constraint Validation
    st.markdown("---")
    st.markdown("#### ✅ Constraint Validation")
    
    if st.button("🔍 Check Constraints", type="primary", use_container_width=False):
        with st.spinner("Validating configuration against site constraints..."):
            
            is_feasible, violations, warnings, metrics = validate_configuration(
                site, constraints, sizing
            )
            
            # Display Results
            if is_feasible:
                st.success("✅ **FEASIBLE** - Configuration meets all hard constraints!")
            else:
                st.error(f"❌ **INFEASIBLE** - {len(violations)} constraint violation(s)")
            
            # Show violations
            if violations:
                st.markdown("##### 🚫 Constraint Violations:")
                for v in violations:
                    st.error(f"• {v}")
            
            # Show warnings
            if warnings:
                st.markdown("##### ⚠️ Warnings:")
                for w in warnings:
                    st.warning(f"• {w}")
            
            # Show metrics
            st.markdown("##### 📊 Configuration Metrics:")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Capacity", f"{metrics.get('total_capacity_mw', 0):.1f} MW")
            with col2:
                st.metric("Total CAPEX", f"${metrics.get('total_capex_m', 0):.1f}M")
            with col3:
                if sizing.get('solar_mw_dc'):
                    st.metric("Solar DC", f"{sizing.get('solar_mw_dc', 0)} MW")
            
            # Store validation results
            st.session_state.validation_result = {
                'feasible': is_feasible,
                'violations': violations,
                'warnings': warnings,
                'metrics': metrics,
                'sizing': sizing
            }
    
    # Show previous validation if exists
    if 'validation_result' in st.session_state:
        result = st.session_state.validation_result
        
        st.markdown("---")
        st.markdown("#### 📈 Run Full Optimization")
        
        if result['feasible']:
            col_opt1, col_opt2 = st.columns([3, 1])
            
            with col_opt1:
                st.info("""
                **Full optimization will:**
                - Calculate LCOE (Levelized Cost of Energy)
                - Estimate deployment timeline and critical path
                - Compute annual costs (CAPEX, OPEX, fuel)
                - Generate detailed economics and ranking
                """)
            
            with col_opt2:
                if st.button("⚡ Optimize", type="primary", use_container_width=True):
                    with st.spinner("Running optimization..."):
                        from app.utils.optimizer import optimize_scenario
                        
                        # Run full optimization
                        opt_result = optimize_scenario(
                            site=config['site'],
                            constraints=config['constraints'],
                            scenario=config['scenario'],
                            equipment_config=result['sizing'],
                            objectives=config['objectives']
                        )
                        
                        # Store in session state
                        st.session_state.optimization_result = opt_result
                        
                        # Navigate to results
                        st.success("✅ Optimization complete! Navigating to Results...")
                        st.session_state.current_page = 'results'
                        st.rerun()
        else:
            st.error("❌ Cannot optimize - please fix constraint violations first")
    
    # Quick Economics Preview (if validated)
    if 'validation_result' in st.session_state and st.session_state.validation_result.get('feasible'):
        st.markdown("---")
        st.markdown("#### 💰 Quick Economics Preview")
        
        if st.button("📊 Calculate LCOE", use_container_width=False):
            with st.spinner("Calculating economics..."):
                from app.utils.optimizer import calculate_lcoe, calculate_deployment_timeline
                
                result = st.session_state.validation_result
                
                economics = calculate_lcoe(
                    result['sizing'],
                    config['site'],
                    config.get('objectives', {})
                )
                
                timeline = calculate_deployment_timeline(
                    result['sizing'],
                    config['scenario']
                )
                
                # Display results
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("LCOE", f"${economics['lcoe_mwh']:.2f}/MWh")
                with col2:
                    st.metric("Total CAPEX", f"${economics['total_capex_m']:.1f}M")
                with col3:
                    st.metric("Deployment", f"{timeline['timeline_months']} months")
                    st.caption(f"{timeline['timeline_years']:.1f} years")
                with col4:
                    st.metric("Annual Gen", f"{economics['annual_generation_gwh']:.1f} GWh")
                
                st.info(f"**Critical Path:** {timeline['critical_path']}")


if __name__ == "__main__":
    render()

