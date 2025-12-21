"""
Multi-Scenario Runner
Batch run multiple scenarios and compare results
"""

from typing import List, Dict
from app.utils.optimizer import optimize_scenario, rank_scenarios
from app.utils.data_io import load_equipment_from_sheets
import pandas as pd


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
                # Size for only 10-15% of load to stay under air permit
                # For 200 MW site: 2 engines x 4.7 MW = 9.4 MW (~5% of load)
                num_units = max(1, min(2, int((total_mw * 0.10) / unit_mw)))
                
                config['recip_engines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.50,  # Low CF to minimize emissions
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 7700),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1650),
                    'vom_per_mwh': 8.5,
                    'fom_per_kw_yr': 18.5,
                    'quantity': num_units
                }] * num_units
    
    # Gas Turbines (if enabled)
    if turbine_enabled:
        turbines = equipment_data.get('Gas_Turbines', [])
        if turbines:
            # Use smallest turbine (TM2500 = 35 MW)
            selected = next((t for t in turbines if t and 'TM2500' in t.get('Model', '')), turbines[0])
            
            if selected:
                unit_mw = selected.get('Capacity_MW', 35)
                # Size for 10% of load max (peaking only)
                num_units = max(1, min(1, int((total_mw * 0.10) / unit_mw)))  # Usually just 1 turbine
                
                config['gas_turbines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': 0.25,  # Very low CF - peaking only
                    'heat_rate_btu_kwh': selected.get('Heat_Rate_BTU_kWh', 8500),
                    'nox_lb_mmbtu': selected.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': selected.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': selected.get('CAPEX_per_kW', 1300),
                    'vom_per_mwh': 6.5,
                    'fom_per_kw_yr': 12.5,
                    'quantity': num_units
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
        # Size based on scenario
        grid_available = constraints.get('Grid_Available_MW', 200)
        
        if 'BTM' in scenario_name or 'Microgrid' in scenario.get('Scenario_Name', ''):
            config['grid_import_mw'] = 0  # No grid if BTM only
        elif 'Grid' in scenario.get('Scenario_Name', ''):
            # Grid primary - use 70% of available or 60% of load, whichever is less
            config['grid_import_mw'] = min(total_mw * 0.60, grid_available * 0.70)
        else:
            # Grid backup - minimal import
            config['grid_import_mw'] = min(total_mw * 0.10, grid_available * 0.30)
    
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
        equipment_config = auto_size_equipment(scenario, site, equipment_data, constraints)
        
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
