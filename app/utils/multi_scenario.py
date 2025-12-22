"""
Multi-Scenario Runner
Batch run multiple scenarios and compare results
Uses multi-year phased deployment optimization
"""

from typing import List, Dict, Tuple
from app.utils.optimizer import optimize_scenario, rank_scenarios
from app.utils.data_io import load_equipment_from_sheets
from app.utils.optimization_engine import optimize_equipment_configuration, calculate_pareto_frontier
from app.utils.phased_optimizer import PhasedDeploymentOptimizer
import pandas as pd
import numpy as np


def auto_size_equipment_optimized(
    scenario: Dict, 
    site: Dict, 
    equipment_data: Dict, 
    constraints: Dict,
    grid_config: Dict = None
) -> Tuple[Dict, bool, List[str]]:
    """
    Use multi-year phased deployment optimizer.
    
   Returns:
        (deployment_schedule, feasible, violations)
    """
    
    # Get load trajectory from site - 10 years
    load_trajectory = site.get('load_trajectory', {
        2026: 0, 2027: 0, 2028: 150, 2029: 300, 2030: 450, 2031: 600,
        2032: 600, 2033: 600, 2034: 600, 2035: 600
    })
    
    # Ensure constraints have realistic defaults for datacenter projects
    # Override any missing or unrealistically tight constraints
    if 'land_area_acres' not in constraints or constraints.get('land_area_acres', 0) < 200:
        constraints['land_area_acres'] = 1000  # 1000 acres for 10-year planning
        print(f"  ⚠️ Land constraint missing or too low, setting to 1000 acres (10-year campus)")
    
    if 'nox_tpy_annual' not in constraints:
        constraints['nox_tpy_annual'] = 100  # 100 tpy with SCR (realistic)
    
    if 'co_tpy_annual' not in constraints:
        constraints['co_tpy_annual'] = 100  # 100 tpy with OxCat
    
    if 'gas_supply_mcf_day' not in constraints:
        constraints['gas_supply_mcf_day'] = 50000  # 50k MCF/day
    
    # Use COMBINATION OPTIMIZER to test different equipment type combinations
    from app.utils.combination_optimizer import CombinationOptimizer
    
    combo_optimizer = CombinationOptimizer(
        site=site,
        scenario=scenario,
        equipment_data=equipment_data,
        constraints=constraints
    )
    
    # Run combination optimization
    try:
        import streamlit as st
        st.write(f"🔄 Testing equipment combinations for '{scenario.get('Scenario_Name', 'Unknown')}'...")
        print(f"🔄 Testing combinations for '{scenario.get('Scenario_Name', 'Unknown')}'...")
        
        all_results = combo_optimizer.optimize_all()
        feasible_results = [r for r in all_results if r['feasible']]
        
        if not feasible_results:
            st.error(f"❌ No feasible combinations")
            return auto_size_equipment(scenario, site, equipment_data, constraints), False, ["No feasible combinations"]
        
        best = feasible_results[0]
        deployment = best['deployment']
        lcoe = best['lcoe']
        violations = best['violations']
        feasible = True
        
        st.success(f"✅ {best['combination_name']}: ${lcoe:.2f}/MWh")
        print(f"  ✅ Best: {best['combination_name']}")
        
        # Convert deployment schedule to equipment config format
        years = list(range(2026, 2036))  # 2026-2035 (10 years)
        final_year = max(years)
        
        # Calculate total CAPEX from deployment
        total_capex = 0
        for year in years:
            recip_added = deployment['recip_mw'].get(year, 0)
            turbine_added = deployment['turbine_mw'].get(year, 0)
            bess_added = deployment['bess_mwh'].get(year, 0)
            solar_added = deployment['solar_mw'].get(year, 0)
            
            total_capex += (
                recip_added * 1000 * 1650 +           # $1650/kW for recips
                turbine_added * 1000 * 1300 +         # $1300/kW for turbines
                bess_added * 1000 * 236 * 0.70 +      # $236/kWh * 70% (30% ITC)
                solar_added * 1000000 * 0.95 * 0.70   # $0.95/W * 70% (30% ITC)
            )
        
        # Calculate annual OPEX from final year deployment
        total_recip_mw_final = deployment['cumulative_recip_mw'].get(final_year, 0)
        total_turbine_mw_final = deployment['cumulative_turbine_mw'].get(final_year, 0)
        total_bess_mwh_final = deployment['cumulative_bess_mwh'].get(final_year, 0)
        total_solar_mw_final = deployment['cumulative_solar_mw'].get(final_year, 0)
        
        # Variable O&M (depends on generation)
        recip_gen_mwh = total_recip_mw_final * 0.70 * 8760  # 70% CF
        turbine_gen_mwh = total_turbine_mw_final * 0.30 * 8760  # 30% CF
        bess_cycles = (total_bess_mwh_final / 4) * 365  # Daily cycling, 4-hr BESS
        solar_gen_mwh = total_solar_mw_final * 0.25 * 8760  # 25% CF
        
        vom_annual = (
            recip_gen_mwh * 8.5 +      # $8.50/MWh
            turbine_gen_mwh * 6.5 +    # $6.50/MWh
            bess_cycles * 1.5 +        # $1.50/MWh
            solar_gen_mwh * 2.0        # $2.00/MWh
        )
        
        # Fixed O&M (depends on capacity)
        fom_annual = (
            total_recip_mw_final * 1000 * 18.5 +      # $18.50/kW-yr
            total_turbine_mw_final * 1000 * 12.5 +    # $12.50/kW-yr
            (total_bess_mwh_final / 4) * 1000 * 8.0 + # $8.00/kW-yr (power capacity)
            total_solar_mw_final * 1000 * 15.0        # $15.00/kW-yr
        )
        
        total_opex_annual = vom_annual + fom_annual
        
        equipment_config = {
            'recip_engines': [],
            'gas_turbines': [],
            'bess': [],
            'solar_mw_dc': deployment['cumulative_solar_mw'].get(final_year, 0),
            'grid_import_mw': deployment['grid_mw'].get(final_year, 0),
            '_phased_deployment': deployment,  # Store full deployment schedule
            '_lifecycle_lcoe': lcoe,
            '_total_capex': total_capex,  # Store total CAPEX
            '_annual_opex': total_opex_annual,  # Store annual OPEX ($)
            '_annual_vom': vom_annual,  # Variable O&M
            '_annual_fom': fom_annual,  # Fixed O&M
            '_combination_results': all_results  # ALL combinations tested for comparison
        }
        
        # Add recips
        total_recip_mw = deployment['cumulative_recip_mw'].get(final_year, 0)
        if total_recip_mw > 0:
            num_units = int(np.ceil(total_recip_mw / 4.7))  # 4.7 MW Wärtsilä units
            # Create individual items (not quantity field) for constraint_validator
            equipment_config['recip_engines'] = []
            for i in range(num_units):
                equipment_config['recip_engines'].append({
                    'capacity_mw': 4.7,
                    'capacity_factor': 0.70,
                    'heat_rate_btu_kwh': 7700,
                    'nox_lb_mmbtu': 0.099,
                    'co_lb_mmbtu': 0.015,
                    'capex_per_kw': 1650,
                    'vom_per_mwh': 8.5,
                    'fom_per_kw_yr': 18.5
                })
        
        # Add turbines
        total_turbine_mw = deployment['cumulative_turbine_mw'].get(final_year, 0)
        if total_turbine_mw > 0:
            num_units = int(np.ceil(total_turbine_mw / 35.0))  # 35 MW GE TM2500
            # Create individual items (not quantity field)
            equipment_config['gas_turbines'] = []
            for i in range(num_units):
                equipment_config['gas_turbines'].append({
                    'capacity_mw': 35.0,
                    'capacity_factor': 0.30,
                    'heat_rate_btu_kwh': 8500,
                    'nox_lb_mmbtu': 0.099,
                    'co_lb_mmbtu': 0.015,
                    'capex_per_kw': 1300,
                    'vom_per_mwh': 6.5,
                    'fom_per_kw_yr': 12.5
                })
        
        # Add BESS
        total_bess_mwh = deployment['cumulative_bess_mwh'].get(final_year, 0)
        if total_bess_mwh > 0:
            equipment_config['bess'] = [{
                'energy_mwh': total_bess_mwh,
                'power_mw': total_bess_mwh / 4,  # 4-hour duration
                'capex_per_kwh': 236,
                'vom_per_mwh': 1.5,
                'fom_per_kw_yr': 8.0
            }]
        
        return equipment_config, feasible, violations
        
    except Exception as e:
        # Fallback to simple sizing if optimizer fails
        import traceback
        error_msg = f"⚠️ Phased optimizer failed: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        try:
            import streamlit as st
            st.error(error_msg)
        except:
            pass
        return auto_size_equipment(scenario, site, equipment_data, constraints), False, [str(e)]



def auto_size_equipment(scenario: Dict, site: Dict, equipment_data: Dict, constraints: Dict) -> Dict:
    """
    Automatically size equipment for a scenario based on site requirements
    Uses heuristics to create reasonable configurations
    """
    
    total_mw = site.get('Total_Facility_MW', 200)
    scenario_name = scenario.get('Scenario_ID', '')
    
    # Check which equipment is enabled
    recip_enabled = str(scenario.get('Recip_Engines', 'False')).lower() == 'true'
    turbine_enabled = str(scenario.get('Gas_Turbines', 'False')).lower() == 'true'
    bess_enabled = str(scenario.get('BESS', 'False')).lower() == 'true'
    solar_enabled = str(scenario.get('Solar_PV', 'False')).lower() == 'true'
    grid_enabled = str(scenario.get('Grid_Connection', 'False')).lower() == 'true'
    
    config = {}
    
    # Reciprocating Engines (if enabled)
    if recip_enabled:
        recips = equipment_data.get('Reciprocating_Engines', [])
        if recips:
            # Use smallest engine for lower emissions (Wärtsilä 34SG = 4.7 MW)
            selected = next((e for e in recips if e and '34SG' in e.get('Model', '')), recips[0])
            
            if selected:
                unit_mw = selected.get('Capacity_MW', 5)
                # Size to meet full load with N+1 redundancy
                # For 200 MW: need 43 units (200/4.7) + 1 for N+1 = 44 engines
                num_units_needed = int(np.ceil(total_mw / unit_mw))
                num_units = min(num_units_needed + 1, 50)  # Cap at 50 engines max
                
                config['recip_engines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.70,  # 70% CF for baseload
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 7700),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1650),
                    'vom_per_mwh': 8.5,
                    'fom_per_kw_yr': 18.5,
                    'quantity': 1
                }] * num_units
    
    # Gas Turbines (if enabled)
    if turbine_enabled:
        turbines = equipment_data.get('Gas_Turbines', [])
        if turbines:
            # Use smallest turbine (TM2500 = 35 MW)
            selected = next((t for t in turbines if t and 'TM2500' in t.get('Model', '')), turbines[0])
            
            if selected:
                unit_mw = selected.get('Capacity_MW', 35)
                # Size to meet full load with N+1 redundancy
                # For 200 MW: need 6 units (200/35) + 1 for N+1 = 7 turbines
                num_units_needed = int(np.ceil(total_mw / unit_mw))
                num_units = num_units_needed + 1  # N+1 redundancy
                
                config['gas_turbines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.30,  # Lower CF for peaking capability
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 8500),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1300),
                    'vom_per_mwh': 6.5,
                    'fom_per_kw_yr': 12.5,
                    'quantity': 1
                }] * num_units
    
    # BESS (if enabled)
    if bess_enabled:
        bess_systems = equipment_data.get('BESS', [])
        if bess_systems:
            # Use Tesla Megapack
            selected = next((e for e in bess_systems if e and 'Megapack' in e.get('Model', '')), bess_systems[0])
            
            if selected:
                # Size for 30-50 MW power (enough to handle N-1)
                target_power_mw = min(total_mw * 0.30, 50)  # 30% of load or 50 MW max
                num_units = max(10, min(25, int(target_power_mw / selected.get('Power_MW', 2))))
                
                config['bess'] = [{
                    'energy_mwh': selected.get('Energy_MWh', 3.9),
                    'power_mw': selected.get('Power_MW', 1.9),
                    'capex_per_kwh': selected.get('CAPEX_per_kWh', 236),
                    'vom_per_mwh': 1.5,
                    'fom_per_kw_yr': 8.0,
                    'quantity': num_units
                }] * num_units
    
    # Solar PV (if enabled)
    if solar_enabled:
        solar_systems = equipment_data.get('Solar_PV', [])
        if solar_systems:
            # Match region to site
            state = site.get('State', '')
            if 'Texas' in state or 'Oklahoma' in state:
                region = 'Southwest'
            elif 'Virginia' in state:
                region = 'Southeast'
            else:
                region = 'National'
            
            selected = next((s for s in solar_systems if s and region in s.get('Region', '')), solar_systems[0])
            
            if selected:
                # Size solar conservatively based on AVAILABLE land
                available_land = constraints.get('Available_Land_Acres', 15)
                land_limit_mw = available_land / 4.25  # 4.25 acres per MW
                
                # Use only 50% of available land to leave margin
                solar_mw = min(total_mw * 0.05, land_limit_mw * 0.5)
                
                config['solar_mw_dc'] = max(0, solar_mw)  # Ensure non-negative
                config['solar_capex_per_w'] = selected.get('CAPEX_per_W_DC', 0.95)
                config['solar_cf'] = selected.get('Capacity_Factor_Pct', 30) / 100
    
    # Grid (if enabled)
    if grid_enabled:
        # Check scenario name to determine if grid should be primary or backup
        grid_available = constraints.get('Grid_Available_MW', 200)
        
        # BTM scenarios should have NO grid
        if 'BTM' in scenario_name or 'Microgrid' in scenario.get('Scenario_Name', ''):
            config['grid_import_mw'] = 0  # Explicitly zero for BTM
        elif 'Grid' in scenario.get('Scenario_Name', ''):
            # Grid primary - use majority of available capacity
            config['grid_import_mw'] = min(total_mw * 0.80, grid_available * 0.90)
        else:
            # Backup grid - minimal import
            config['grid_import_mw'] = min(total_mw * 0.15, grid_available * 0.30)
    
    return config


def run_all_scenarios(
    site: Dict,
    constraints: Dict,
    objectives: Dict,
    scenarios: List[Dict],
    grid_config: Dict = None,
    use_milp: bool = False,
    load_profile_dr: Dict = None
) -> List[Dict]:
    """
    Run optimization for all scenarios using scipy optimizer OR new MILP
    Includes automatic RAM and Transient analysis
    
    Args:
        site: Site parameters
        constraints: Hard constraints
        objectives: Objective weights
        scenarios: List of scenario dicts
        grid_config: Grid configuration (for scipy)
        use_milp: If True, use new MILP optimizer instead of scipy (RECOMMENDED)
        load_profile_dr: Load profile with DR (required if use_milp=True)
    
    Returns:
        List of optimization results with constraint violations, RAM, and Transient data
    """
    
    # Load equipment once
    equipment_data = load_equipment_from_sheets()
    
    results = []
    
    # MILP Mode (NEW - Recommended)
    if use_milp:
        if not load_profile_dr:
            raise ValueError("load_profile_dr required when use_milp=True. Generate via Load Composer.")
        
        from app.utils.milp_optimizer_wrapper import optimize_with_milp
        
        print(f"\n🚀 Running {len(scenarios)} scenarios with bvNexus MILP")
        print(f"  Expected time: {len(scenarios) * 45} seconds (~{len(scenarios) * 45 / 60:.1f} minutes)")
        
        for idx, scenario in enumerate(scenarios):
            scenario_name = scenario.get('Scenario_Name', 'Unknown')
            print(f"\n[{idx+1}/{len(scenarios)}] Optimizing: {scenario_name}")
            
            try:
                # Run MILP optimization
                milp_result = optimize_with_milp(
                    site=site,
                    constraints=constraints,
                    load_profile_dr=load_profile_dr,
                    years=list(range(2026, 2036)),
                    solver='glpk',  # or 'cbc' if available
                    time_limit=300,
                    scenario=scenario
                )
                
                # Format result to match existing structure
                equipment_config = milp_result['equipment_config']
                is_feasible = milp_result['feasible']
                violations = milp_result['violations']
                
                # Run standard result formatting
                result = optimize_scenario(
                    site=site,
                    constraints=constraints,
                    scenario=scenario,
                    equipment_config=equipment_config,
                    objectives=objectives
                )
                
                # Override with MILP results
                result['feasible'] = is_feasible
                result['violations'] = violations
                result['economics'] = milp_result['economics']
                result['dr_metrics'] = milp_result.get('dr_metrics', {})
                result['milp_optimized'] = True
                
                if milp_result.get('economics', {}).get('lcoe_mwh'):
                    print(f"  ✓ LCOE: ${milp_result['economics']['lcoe_mwh']:.2f}/MWh")
                if milp_result.get('dr_metrics'):
                    print(f"  ✓ DR Revenue: ${milp_result['dr_metrics'].get('dr_revenue_annual', 0):,.0f}/yr")
                
            except Exception as e:
                print(f"  ✗ MILP failed: {e}")
                result = {
                    'scenario_name': scenario_name,
                    'feasible': False,
                    'violations': [f"MILP optimization failed: {str(e)}"],
                    'economics': {},
                    'timeline': {},
                    'metrics': {},
                    'milp_optimized': False
                }
            
            # AUTO-RUN: RAM Analysis
            if result.get('feasible'):
                try:
                    from app.pages_custom.page_08_ram import calculate_ram_metrics
                    ram_metrics = calculate_ram_metrics(equipment_config)
                    result['ram_analysis'] = ram_metrics
                except Exception as e:
                    result['ram_analysis'] = {'error': str(e)}
            
            # AUTO-RUN: Transient Analysis
            if result.get('feasible'):
                try:
                    from app.utils.highres_transient import generate_high_res_transient, calculate_power_quality_metrics
                    
                    total_mw = site.get('Total_Facility_MW', 200)
                    transient_data = generate_high_res_transient(
                        base_load_mw=total_mw,
                        event_type='step_change',
                        duration_seconds=300,
                        event_magnitude_pct=20
                    )
                    
                    pq_metrics = calculate_power_quality_metrics(transient_data)
                    
                    result['transient_analysis'] = {
                        'pq_metrics': pq_metrics,
                        'transient_data': transient_data
                    }
                except Exception as e:
                    result['transient_analysis'] = {'error': str(e)}
            
            results.append(result)
        
        print(f"\n✓ Completed {len(results)} MILP optimizations")
    
    # Legacy scipy Mode (OLD - Deprecated)
    else:
        print(f"\n⚠️ Using legacy scipy optimizer (deprecated)")
        print(f"  Recommended: Set use_milp=True for 40x faster, deterministic results")
        
        for scenario in scenarios:
            # Use scipy optimizer for equipment sizing
            equipment_config, is_feasible, violations = auto_size_equipment_optimized(
                scenario=scenario,
                site=site,
                equipment_data=equipment_data,
                constraints=constraints,
                grid_config=grid_config
            )
            
            # Run full optimization with the optimized config
            result = optimize_scenario(
                site=site,
                constraints=constraints,
                scenario=scenario,
                equipment_config=equipment_config,
                objectives=objectives
            )
            
            # Override feasibility with optimizer result
            result['feasible'] = is_feasible
            result['violations'] = violations
            result['milp_optimized'] = False
            
            # AUTO-RUN: RAM Analysis
            if is_feasible:
                try:
                    from app.pages_custom.page_08_ram import calculate_ram_metrics
                    ram_metrics = calculate_ram_metrics(equipment_config)
                    result['ram_analysis'] = ram_metrics
                except Exception as e:
                    result['ram_analysis'] = {'error': str(e)}
            
            # AUTO-RUN: Transient Analysis
            if is_feasible:
                try:
                    from app.utils.highres_transient import generate_high_res_transient, calculate_power_quality_metrics
                    
                    # Run transient simulation for typical step change
                    total_mw = site.get('Total_Facility_MW', 200)
                    transient_data = generate_high_res_transient(
                        base_load_mw=total_mw,
                        event_type='step_change',
                        duration_seconds=300,
                        event_magnitude_pct=20  # 20% step change
                    )
                    
                    # Calculate power quality metrics
                    pq_metrics = calculate_power_quality_metrics(transient_data)
                    
                    result['transient_analysis'] = {
                        'pq_metrics': pq_metrics,
                        'transient_data': transient_data  # Store for visualization
                    }
                except Exception as e:
                    result['transient_analysis'] = {'error': str(e)}
            
            results.append(result)
    
    # Rank scenarios
    ranked_results = rank_scenarios(results, objectives)
    
    return ranked_results


def create_comparison_table(results: List[Dict]) -> pd.DataFrame:
    """
    Create comparison table from optimization results
    Shows constraint violations for infeasible scenarios
    """
    
    rows = []
    
    for result in results:
        if not result:
            continue
        
        # Get constraint violations summary
        violations = result.get('violations', [])
        if violations:
            # Summarize first 2 violations
            violations_text = '; '.join(violations[:2])
            if len(violations) > 2:
                violations_text += f" (+{len(violations)-2} more)"
        else:
            violations_text = '-'
        
        row = {
            'Rank': result.get('rank', 999),
            'Scenario': result.get('scenario_name', 'Unknown'),
            'Feasible': '✅' if result.get('feasible') else '❌',
            'LCOE ($/MWh)': f"${result['economics']['lcoe_mwh']:.2f}" if result.get('feasible') and result.get('economics', {}).get('lcoe_mwh') else 'N/A',
            'CAPEX ($M)': f"${result['economics']['total_capex_m']:.1f}" if result.get('feasible') and result.get('economics', {}).get('total_capex_m') else 'N/A',
            'Timeline (mo)': result['timeline']['timeline_months'] if result.get('feasible') and result.get('timeline', {}).get('timeline_months') else 'N/A',
            'Speed': result['timeline']['deployment_speed'] if result.get('feasible') and result.get('timeline', {}).get('deployment_speed') else 'N/A',
            'Total MW': f"{result['metrics']['total_capacity_mw']:.0f}" if result.get('feasible') and result.get('metrics', {}).get('total_capacity_mw') else 'N/A',
            'Score': f"{result.get('score', 0):.1f}" if result.get('feasible') else '0',
            'Constraint Violations': violations_text
        }
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by rank
    df = df.sort_values('Rank')
    
    return df
