"""
Optimization Engine
Calculates LCOE, deployment timelines, and ranks scenarios
"""

from typing import Dict, List, Tuple
import math


def calculate_lcoe(
    equipment_config: Dict,
    site: Dict,
    objectives: Dict,
    years: int = 20
) -> Dict:
    """
    Calculate Levelized Cost of Energy (LCOE)
    
    Returns:
        Dict with LCOE, CAPEX, OPEX, fuel costs, etc.
    """
    
    # Check if phased optimizer provided lifecycle LCOE
    if '_lifecycle_lcoe' in equipment_config:
        lifecycle_lcoe = equipment_config['_lifecycle_lcoe']
        # Use stored total CAPEX from phased deployment
        total_capex = equipment_config.get('_total_capex', 0)
        return {
            'lcoe_mwh': lifecycle_lcoe,
            'total_capex_m': total_capex / 1_000_000,
            'annual_opex_m': 0,  # Included in lifecycle LCOE
            'annual_fuel_cost_m': 0,  # Included in lifecycle LCOE
            'annual_generation_gwh': 0,  # Not needed for phased optimizer
            'capacity_factor_pct': 0
        }
    
    # Constants
    gas_price_mmbtu = 3.50  # $/MMBtu
    discount_rate = 0.08  # 8% WACC
    
    # Initialize totals
    total_capex = 0
    annual_vom = 0
    annual_fom = 0
    annual_fuel_cost = 0
    annual_generation_mwh = 0
    
    # Reciprocating Engines
    for engine in equipment_config.get('recip_engines', []):
        capacity_mw = engine.get('capacity_mw', 0)
        capacity_factor = engine.get('capacity_factor', 0.7)
        capex_per_kw = engine.get('capex_per_kw', 1650)
        vom_per_mwh = engine.get('vom_per_mwh', 8.5)
        fom_per_kw_yr = engine.get('fom_per_kw_yr', 18.5)
        heat_rate = engine.get('heat_rate_btu_kwh', 7700)
        
        # CAPEX
        total_capex += capacity_mw * 1000 * capex_per_kw
        
        # Annual generation
        annual_gen = capacity_mw * capacity_factor * 8760
        annual_generation_mwh += annual_gen
        
        # O&M
        annual_vom += annual_gen * vom_per_mwh
        annual_fom += capacity_mw * 1000 * fom_per_kw_yr
        
        # Fuel
        annual_fuel_mmbtu = annual_gen * heat_rate / 1000
        annual_fuel_cost += annual_fuel_mmbtu * gas_price_mmbtu
    
    # Gas Turbines
    for turbine in equipment_config.get('gas_turbines', []):
        capacity_mw = turbine.get('capacity_mw', 0)
        capacity_factor = turbine.get('capacity_factor', 0.5)
        capex_per_kw = turbine.get('capex_per_kw', 1300)
        vom_per_mwh = turbine.get('vom_per_mwh', 6.5)
        fom_per_kw_yr = turbine.get('fom_per_kw_yr', 12.5)
        heat_rate = turbine.get('heat_rate_btu_kwh', 8500)
        
        total_capex += capacity_mw * 1000 * capex_per_kw
        
        annual_gen = capacity_mw * capacity_factor * 8760
        annual_generation_mwh += annual_gen
        
        annual_vom += annual_gen * vom_per_mwh
        annual_fom += capacity_mw * 1000 * fom_per_kw_yr
        
        annual_fuel_mmbtu = annual_gen * heat_rate / 1000
        annual_fuel_cost += annual_fuel_mmbtu * gas_price_mmbtu
    
    # BESS
    for bess in equipment_config.get('bess', []):
        energy_mwh = bess.get('energy_mwh', 0)
        capex_per_kwh = bess.get('capex_per_kwh', 236)
        vom_per_mwh = bess.get('vom_per_mwh', 1.5)
        fom_per_kw_yr = bess.get('fom_per_kw_yr', 8.0)
        power_mw = bess.get('power_mw', 0)
        
        # Apply 30% Investment Tax Credit (ITC) for BESS
        itc_multiplier = 0.70
        total_capex += energy_mwh * 1000 * capex_per_kwh * itc_multiplier
        
        # Assume 1 cycle per day
        annual_discharge = energy_mwh * 365
        
        annual_vom += annual_discharge * vom_per_mwh
        annual_fom += power_mw * 1000 * fom_per_kw_yr
    
    # Solar PV
    solar_mw_dc = equipment_config.get('solar_mw_dc', 0)
    if solar_mw_dc > 0:
        solar_capex_per_w = equipment_config.get('solar_capex_per_w', 0.95)
        solar_cf = equipment_config.get('solar_cf', 0.30)  # 30% default
        solar_vom = 2.0  # $/MWh
        solar_fom = 15.0  # $/kW-yr
        
        # Apply 30% Investment Tax Credit (ITC) under Inflation Reduction Act
        # Net CAPEX = 70% of gross CAPEX
        itc_multiplier = 0.70
        total_capex += solar_mw_dc * 1_000_000 * solar_capex_per_w * itc_multiplier
        
        annual_gen = solar_mw_dc * solar_cf * 8760
        annual_generation_mwh += annual_gen
        
        annual_vom += annual_gen * solar_vom
        annual_fom += solar_mw_dc * 1000 * solar_fom
    
    # Grid Connection (if applicable)
    grid_mw = equipment_config.get('grid_import_mw', 0)
    if grid_mw > 0:
        # Interconnection cost (one-time, amortized)
        interconnection_cost = 10_000_000  # $10M assumption
        total_capex += interconnection_cost
        
        # Grid energy purchase (assume baseload)
        grid_cf = 0.85
        annual_grid_purchase = grid_mw * grid_cf * 8760
        grid_price_mwh = 45  # $/MWh wholesale
        annual_fuel_cost += annual_grid_purchase * grid_price_mwh  # Treating as "fuel"
        annual_generation_mwh += annual_grid_purchase
    
    # Calculate LCOE using NPV method
    # LCOE = (CAPEX + NPV(OPEX + Fuel)) / NPV(Generation)
    
    total_annual_cost = annual_vom + annual_fom + annual_fuel_cost
    
    # NPV of costs with fuel escalation
    npv_opex = 0
    npv_generation = 0
    fuel_escalation_rate = 0.025  # 2.5% annual escalation for natural gas
    
    for year in range(1, years + 1):
        discount_factor = 1 / ((1 + discount_rate) ** year)
        
        # Fuel costs escalate, O&M stays constant (conservative assumption)
        escalated_fuel = annual_fuel_cost * ((1 + fuel_escalation_rate) ** year)
        annual_cost_with_escalation = annual_vom + annual_fom + escalated_fuel
        
        npv_opex += annual_cost_with_escalation * discount_factor
        npv_generation += annual_generation_mwh * discount_factor
    
    # LCOE
    if npv_generation > 0:
        lcoe = (total_capex + npv_opex) / npv_generation
    else:
        lcoe = 999  # Invalid
    
    return {
        'lcoe_mwh': lcoe,
        'total_capex_m': total_capex / 1_000_000,
        'annual_opex_m': (annual_vom + annual_fom) / 1_000_000,
        'annual_fuel_cost_m': annual_fuel_cost / 1_000_000,
        'annual_generation_gwh': annual_generation_mwh / 1000,
        'capacity_factor_pct': (annual_generation_mwh / (site.get('Total_Facility_MW', 200) * 8760)) * 100 if site.get('Total_Facility_MW') else 0
    }


def calculate_deployment_timeline(equipment_config: Dict, scenario: Dict) -> Dict:
    """
    Calculate deployment timeline based on equipment lead times
    
    Returns:
        Dict with timeline_months, critical_path, stages
    """
    
    # Lead times by equipment type (months)
    lead_times = {
        'recip': 18,  # Reciprocating engines
        'turbine': 24,  # Gas turbines
        'bess': 12,  # Battery storage
        'solar': 15,  # Solar PV
        'grid': 96,  # Grid interconnection (varies widely)
        'transformer': 24,  # Transformer (often critical path)
    }
    
    # Determine which equipment is in the stack
    stages = []
    
    if equipment_config.get('recip_engines'):
        stages.append(('Reciprocating Engines', lead_times['recip']))
    
    if equipment_config.get('gas_turbines'):
        stages.append(('Gas Turbines', lead_times['turbine']))
    
    if equipment_config.get('bess'):
        stages.append(('BESS', lead_times['bess']))
    
    if equipment_config.get('solar_mw_dc', 0) > 0:
        stages.append(('Solar PV', lead_times['solar']))
    
    if equipment_config.get('grid_import_mw', 0) > 0:
        # Use grid timeline from scenario or default
        grid_timeline = scenario.get('Grid_Timeline_Months', lead_times['grid'])
        stages.append(('Grid Interconnection', grid_timeline))
    
    # Transformer is always needed for >50 MW
    total_capacity = sum(e.get('capacity_mw', 0) for e in equipment_config.get('recip_engines', []))
    total_capacity += sum(e.get('capacity_mw', 0) for e in equipment_config.get('gas_turbines', []))
    
    if total_capacity > 50:
        stages.append(('Transformer (Critical)', lead_times['transformer']))
    
    # Critical path = longest lead time for parallel execution
    # BUT: If scenario has substantial BTM capacity, don't let grid dictate timeline
    
    if stages:
        # Calculate BTM capacity (non-grid)
        btm_capacity = total_capacity  # recips + turbines
        btm_capacity += sum(e.get('power_mw', 0) for e in equipment_config.get('bess', []))
        btm_capacity += equipment_config.get('solar_mw_dc', 0) * 0.25  # Solar capacity credit
        
        grid_mw = equipment_config.get('grid_import_mw', 0)
        total_mw_needed = 200  # Default assumption
        
        # If BTM can meet most of the load (>70%), use BTM timeline (ignore grid)
        if btm_capacity >= total_mw_needed * 0.70:
            # Filter out grid from stages
            btm_stages = [s for s in stages if 'Grid' not in s[0]]
            if btm_stages:
                critical_path_item = max(btm_stages, key=lambda x: x[1])
                critical_path = critical_path_item[0]
                timeline_months = critical_path_item[1]
            else:
                # Fallback to all stages if no BTM
                critical_path_item = max(stages, key=lambda x: x[1])
                critical_path = critical_path_item[0]
                timeline_months = critical_path_item[1]
        else:
            # Grid is primary - use its timeline
            critical_path_item = max(stages, key=lambda x: x[1])
            critical_path = critical_path_item[0]
            timeline_months = critical_path_item[1]
    else:
        critical_path = "No equipment"
        timeline_months = 0
    
    # Add permitting time (6 months for BTM, 12 for grid-connected)
    if equipment_config.get('grid_import_mw', 0) > 0:
        timeline_months += 12  # Permitting for grid-connected
    else:
        timeline_months += 6  # Permitting for BTM only
    
    return {
        'timeline_months': timeline_months,
        'timeline_years': timeline_months / 12,
        'critical_path': critical_path,
        'stages': stages,
        'deployment_speed': 'Fast' if timeline_months < 24 else 'Medium' if timeline_months < 48 else 'Slow'
    }


def rank_scenarios(
    scenarios_with_results: List[Dict],
    objectives: Dict
) -> List[Dict]:
    """
    Rank scenarios based on weighted objectives
    
    scenarios_with_results: List of dicts with scenario info + lcoe + timeline results
    objectives: Optimization objectives with weights
    
    Returns:
        Sorted list of scenarios (best first)
    """
    
    # Extract weights
    weight_lcoe = objectives.get('Weight_LCOE', 0.4)
    weight_speed = objectives.get('Weight_Deployment_Speed', 0.4)
    weight_reliability = objectives.get('Weight_Reliability', 0.2)
    
    # Get max/min values for normalization
    lcoes = [s['economics']['lcoe_mwh'] for s in scenarios_with_results if s.get('feasible')]
    timelines = [s['timeline']['timeline_months'] for s in scenarios_with_results if s.get('feasible')]
    
    if not lcoes or not timelines:
        return scenarios_with_results  # Can't rank
    
    max_lcoe = max(lcoes)
    min_lcoe = min(lcoes)
    max_timeline = max(timelines)
    min_timeline = min(timelines)
    
    # Score each scenario (0-100, higher is better)
    for scenario in scenarios_with_results:
        if not scenario.get('feasible'):
            scenario['score'] = 0
            scenario['rank'] = 999
            continue
        
        lcoe = scenario['economics']['lcoe_mwh']
        timeline = scenario['timeline']['timeline_months']
        
        # Normalize and invert (lower is better for both)
        if max_lcoe > min_lcoe:
            lcoe_score = 100 * (1 - (lcoe - min_lcoe) / (max_lcoe - min_lcoe))
        else:
            lcoe_score = 100
        
        if max_timeline > min_timeline:
            speed_score = 100 * (1 - (timeline - min_timeline) / (max_timeline - min_timeline))
        else:
            speed_score = 100
        
        # Reliability score (placeholder - could calculate from equipment availability)
        reliability_score = 95  # Default high
        
        # Weighted total
        total_score = (
            lcoe_score * weight_lcoe +
            speed_score * weight_speed +
            reliability_score * weight_reliability
        )
        
        scenario['score'] = total_score
        scenario['lcoe_score'] = lcoe_score
        scenario['speed_score'] = speed_score
        scenario['reliability_score'] = reliability_score
    
    # Sort by score (descending)
    ranked = sorted(
        scenarios_with_results,
        key=lambda x: x.get('score', 0),
        reverse=True
    )
    
    # Assign ranks
    for i, scenario in enumerate(ranked):
        scenario['rank'] = i + 1
    
    return ranked


def optimize_scenario(
    site: Dict,
    constraints: Dict,
    scenario: Dict,
    equipment_config: Dict,
    objectives: Dict
) -> Dict:
    """
    Run optimization for a single scenario
    
    Returns:
        Complete results dict with feasibility, economics, timeline, rank
    """
    
    from app.utils.constraint_validator import validate_configuration
    
    # Validate constraints
    is_feasible, violations, warnings, metrics = validate_configuration(
        site, constraints, equipment_config
    )
    
    # Calculate economics
    economics = calculate_lcoe(equipment_config, site, objectives)
    
    # Calculate timeline
    timeline = calculate_deployment_timeline(equipment_config, scenario)
    
    return {
        'scenario_name': scenario.get('Scenario_Name', 'Unknown'),
        'scenario_id': scenario.get('Scenario_ID', ''),
        'feasible': is_feasible,
        'violations': violations,
        'warnings': warnings,
        'metrics': metrics,
        'economics': economics,
        'timeline': timeline,
        'equipment_config': equipment_config,
        'score': 0,  # Will be set by rank_scenarios
        'rank': 999  # Will be set by rank_scenarios
    }
