"""
Multi-Scenario Runner
Batch run multiple scenarios and compare results
"""

from typing import List, Dict
from app.utils.optimizer import optimize_scenario, rank_scenarios
from app.utils.data_io import load_equipment_from_sheets
import pandas as pd


def auto_size_equipment(scenario: Dict, site: Dict, equipment_data: Dict) -> Dict:
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
            # Use mid-size engine (Jenbacher J920 = 10.4 MW)
            selected = next((e for e in recips if e and 'J920' in e.get('Model', '')), recips[0])
            
            if selected:
                unit_mw = selected.get('Capacity_MW', 10)
                num_units = max(1, int((total_mw * 0.5) / unit_mw))  # Size for 50% of load
                
                config['recip_engines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.7,
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 7700),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1650),
                    'quantity': num_units
                }] * num_units
    
    # Gas Turbines (if enabled)
    if turbine_enabled:
        turbines = equipment_data.get('Gas_Turbines', [])
        if turbines:
            # Use largest available for efficiency
            selected = max(turbines, key=lambda x: x.get('Capacity_MW', 0) if x else 0)
            
            if selected:
                unit_mw = selected.get('Capacity_MW', 50)
                num_units = max(1, int((total_mw * 0.3) / unit_mw))  # Size for 30% of load
                
                config['gas_turbines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.5,  # Lower for peaking
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 8500),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1300),
                    'quantity': num_units
                }] * num_units
    
    # BESS (if enabled)
    if bess_enabled:
        bess_systems = equipment_data.get('BESS', [])
        if bess_systems:
            # Use Tesla Megapack
            selected = next((e for e in bess_systems if e and 'Megapack' in e.get('Model', '')), bess_systems[0])
            
            if selected:
                # Size for 2-4 hours of storage
                storage_hours = 3
                num_units = max(5, int((total_mw * storage_hours) / selected.get('Energy_MWh', 4)))
                
                config['bess'] = [{
                    'energy_mwh': selected.get('Energy_MWh', 3.9),
                    'power_mw': selected.get('Power_MW', 1.9),
                    'capex_per_kwh': selected.get('CAPEX_per_kWh', 236),
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
                # Size solar for 10-20% of load
                solar_mw = min(total_mw * 0.15, site.get('Available_Land_Acres', 50) / 4.25)
                
                config['solar_mw_dc'] = solar_mw
                config['solar_capex_per_w'] = selected.get('CAPEX_per_W_DC', 0.95)
                config['solar_cf'] = selected.get('Capacity_Factor_Pct', 30) / 100
    
    # Grid (if enabled)
    if grid_enabled:
        # Size based on scenario
        if 'BTM' in scenario_name or 'Microgrid' in scenario.get('Scenario_Name', ''):
            config['grid_import_mw'] = 0  # No grid if BTM only
        elif 'Grid' in scenario.get('Scenario_Name', ''):
            config['grid_import_mw'] = total_mw * 0.7  # Grid primary
        else:
            config['grid_import_mw'] = total_mw * 0.2  # Grid backup
    
    return config


def run_all_scenarios(
    site: Dict,
    constraints: Dict,
    objectives: Dict,
    scenarios: List[Dict]
) -> List[Dict]:
    """
    Run optimization for all scenarios and return ranked results
    
    Returns:
        List of optimization results, ranked by score
    """
    
    # Load equipment once
    equipment_data = load_equipment_from_sheets()
    
    results = []
    
    for scenario in scenarios:
        # Auto-size equipment for this scenario
        equipment_config = auto_size_equipment(scenario, site, equipment_data)
        
        # Run optimization
        result = optimize_scenario(
            site=site,
            constraints=constraints,
            scenario=scenario,
            equipment_config=equipment_config,
            objectives=objectives
        )
        
        results.append(result)
    
    # Rank scenarios
    ranked_results = rank_scenarios(results, objectives)
    
    return ranked_results


def create_comparison_table(results: List[Dict]) -> pd.DataFrame:
    """
    Create comparison table from optimization results
    """
    
    rows = []
    
    for result in results:
        if not result:
            continue
        
        row = {
            'Rank': result.get('rank', 999),
            'Scenario': result.get('scenario_name', 'Unknown'),
            'Feasible': '✅' if result.get('feasible') else '❌',
            'LCOE ($/MWh)': f"${result['economics']['lcoe_mwh']:.2f}" if result.get('feasible') else 'N/A',
            'CAPEX ($M)': f"${result['economics']['total_capex_m']:.1f}" if result.get('feasible') else 'N/A',
            'Timeline (mo)': result['timeline']['timeline_months'] if result.get('feasible') else 'N/A',
            'Speed': result['timeline']['deployment_speed'] if result.get('feasible') else 'N/A',
            'Total MW': f"{result['metrics']['total_capacity_mw']:.0f}" if result.get('feasible') else 'N/A',
            'Score': f"{result.get('score', 0):.1f}" if result.get('feasible') else '0',
            'Violations': len(result.get('violations', []))
        }
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by rank
    df = df.sort_values('Rank')
    
    return df
