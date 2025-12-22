"""
MILP Optimizer Wrapper - Updated for Corrected Model
=====================================================

Drop-in replacement for app/utils/milp_optimizer_wrapper.py

Changes from original:
1. Extracts power_coverage metrics (unserved energy, gap)
2. Extracts gas_usage metrics
3. Properly formats phased deployment for charts
4. Handles new solution structure

Author: Claude AI (QA/QC Review)
Date: December 2024
"""

import logging
from typing import Dict, List, Optional
import numpy as np

# Import the corrected MILP model
from app.optimization.milp_model_dr import bvNexusMILP_DR

# Try to import load profile generator
try:
    from app.utils.load_profile_generator import generate_load_profile_with_flexibility
except ImportError:
    generate_load_profile_with_flexibility = None

logger = logging.getLogger(__name__)


def optimize_with_milp(
    site: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    years: List[int] = None,
    existing_equipment: Dict = None,
    solver: str = 'glpk',
    time_limit: int = 300,
    scenario: Dict = None,
) -> Dict:
    """
    Run MILP optimization with the corrected model.
    
    This is a drop-in replacement for the existing optimize_with_milp function,
    updated to work with the corrected MILP model that includes:
    - Unserved energy tracking (power gap)
    - Gas supply constraint (HARD)
    - CO2 constraint (conditional)
    - Ramp rate constraint
    - Grid timing enforcement
    
    Args:
        site: Site parameters including PUE, location, etc.
        constraints: Hard constraints (NOx, land, gas limits)
        load_profile_dr: Load profile with DR configuration from session state
        years: Planning horizon years (default: 2026-2035)
        existing_equipment: Brownfield equipment (default: greenfield)
        solver: MILP solver to use ('glpk', 'cbc', or 'gurobi')
        time_limit: Maximum solve time in seconds
        scenario: Scenario configuration with equipment enablement flags
    
    Returns:
        Dict with optimization results including:
        - feasible: bool
        - equipment_config: equipment counts and capacities
        - economics: LCOE, CAPEX, etc.
        - power_coverage: coverage %, power gap
        - emissions: NOx, utilization %
        - gas_usage: daily MCF, utilization %
        - timeline: deployment timeline
        - dr_metrics: DR capacity by product
    """
    
    try:
        logger.info("="*60)
        logger.info("Starting MILP Optimization (Corrected Model)")
        logger.info("="*60)
        
        # Default years
        if years is None:
            years = list(range(2026, 2036))
        
        # Extract parameters from load_profile_dr
        peak_it_mw = load_profile_dr.get('peak_it_mw', 160.0)
        pue = load_profile_dr.get('pue', 1.25)
        load_factor = load_profile_dr.get('load_factor', 0.75)
        workload_mix = load_profile_dr.get('workload_mix', {
            'pre_training': 0.30,
            'fine_tuning': 0.20,
            'batch_inference': 0.30,
            'realtime_inference': 0.20,
        })
        cooling_flex = load_profile_dr.get('cooling_flex', 0.25)
        load_trajectory = load_profile_dr.get('load_trajectory', {})
        
        # Generate or use existing load profile
        if 'load_data' in load_profile_dr and 'total_load_mw' in load_profile_dr['load_data']:
            load_data = load_profile_dr['load_data']
        elif generate_load_profile_with_flexibility is not None:
            logger.info("Generating load profile with flexibility")
            load_data = generate_load_profile_with_flexibility(
                peak_it_load_mw=peak_it_mw,
                pue=pue,
                load_factor=load_factor,
                workload_mix=workload_mix,
                cooling_flex_pct=cooling_flex
            )
        else:
            # Generate simple load profile
            logger.info("Generating simple load profile")
            base_load = peak_it_mw * pue * load_factor
            load_8760 = base_load * (1 + 0.1 * np.sin(2 * np.pi * np.arange(8760) / 24))
            load_8760 += np.random.normal(0, base_load * 0.02, 8760)
            load_8760 = np.maximum(load_8760, base_load * 0.5)
            load_data = {
                'total_load_mw': load_8760,
                'pue': pue,
            }
        
        # Ensure load_data has pue
        if 'pue' not in load_data:
            load_data['pue'] = pue
        
        # Create DR configuration
        dr_config = {
            'cooling_flex': cooling_flex,
            'annual_curtailment_budget_pct': load_profile_dr.get('annual_curtailment_budget_pct', 0.01),
        }
        
        # Grid configuration
        grid_config = {
            'available_year': constraints.get('grid_available_year', 
                              site.get('grid_available_year', 2030)),
            'capex': constraints.get('grid_interconnection_capex',
                     site.get('grid_interconnection_capex', 5_000_000)),
            'lead_time_months': constraints.get('Estimated_Interconnection_Months', 96),
        }
        
        # Update site with load trajectory
        site_with_trajectory = site.copy()
        site_with_trajectory['load_trajectory'] = load_trajectory
        site_with_trajectory['pue'] = pue
        
        # Build MILP model
        logger.info("Building MILP model")
        optimizer = bvNexusMILP_DR()
        
        optimizer.build(
            site=site_with_trajectory,
            constraints=constraints,
            load_data=load_data,
            workload_mix=workload_mix,
            years=years,
            dr_config=dr_config,
            existing_equipment=existing_equipment,
            grid_config=grid_config,
            use_representative_periods=True,
        )
        
        # Apply scenario constraints (disable equipment types)
        if scenario:
            _apply_scenario_constraints(optimizer, scenario, years)
        
        # Solve
        logger.info(f"Solving with {solver}")
        solution = optimizer.solve(solver=solver, time_limit=time_limit, verbose=False)
        
        # Format results
        result = _format_solution(solution, years, constraints, load_data)
        
        logger.info(f"Optimization complete: {result['feasible']}, "
                   f"LCOE=${result['economics'].get('lcoe_mwh', 0):.2f}/MWh, "
                   f"Coverage={result['power_coverage'].get('final_coverage_pct', 0):.1f}%")
        
        return result
        
    except Exception as e:
        logger.error(f"MILP optimization error: {e}", exc_info=True)
        return {
            'feasible': False,
            'scenario_name': 'MILP Optimized',
            'violations': [f"Optimization error: {str(e)}"],
            'equipment_config': {},
            'economics': {},
            'power_coverage': {},
            'timeline': {},
            'dr_metrics': {},
            'score': 0,
        }


def _apply_scenario_constraints(optimizer, scenario: Dict, years: List[int]):
    """Apply scenario equipment enablement constraints."""
    m = optimizer.model
    
    scenario_name = scenario.get('Scenario_Name', 'Unknown')
    logger.info(f"Applying scenario constraints for: {scenario_name}")
    
    # Helper to check boolean fields
    def is_enabled(key, default=True):
        val = scenario.get(key, default)
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', '1', 'enabled')
        return bool(val)
    
    # Disable equipment types based on scenario
    if not is_enabled('Recip_Enabled', True) and not is_enabled('Recip_Engines', True):
        logger.info("  Disabling recips")
        for y in years:
            m.n_recip[y].fix(0)
    
    if not is_enabled('Turbine_Enabled', True) and not is_enabled('Gas_Turbines', True):
        logger.info("  Disabling turbines")
        for y in years:
            m.n_turbine[y].fix(0)
    
    if not is_enabled('Solar_Enabled', True) and not is_enabled('Solar_PV', True):
        logger.info("  Disabling solar")
        for y in years:
            m.solar_mw[y].fix(0)
    
    if not is_enabled('BESS_Enabled', True) and not is_enabled('BESS', True):
        logger.info("  Disabling BESS")
        for y in years:
            m.bess_mwh[y].fix(0)
            m.bess_mw[y].fix(0)
    
    if not is_enabled('Grid_Enabled', True) and not is_enabled('Grid_Connection', True):
        logger.info("  Disabling grid")
        for y in years:
            m.grid_mw[y].fix(0)
            m.grid_active[y].fix(0)


def _format_solution(solution: Dict, years: List[int], constraints: Dict, load_data: Dict) -> Dict:
    """Format MILP solution into standard result structure."""
    
    # Check feasibility
    is_feasible = solution.get('termination') in ['optimal', 'feasible']
    
    if not is_feasible:
        return {
            'feasible': False,
            'scenario_name': 'MILP Optimized',
            'violations': [f"Solver failed: {solution.get('termination', 'unknown')}"],
            'equipment_config': {},
            'economics': {},
            'power_coverage': {},
            'timeline': {},
            'dr_metrics': {},
            'score': 0,
        }
    
    # Get final year equipment
    final_year = max(years)
    final_equipment = solution.get('equipment', {}).get(final_year, {})
    final_coverage = solution.get('power_coverage', {}).get(final_year, {})
    final_emissions = solution.get('emissions', {}).get(final_year, {})
    final_gas = solution.get('gas_usage', {}).get(final_year, {})
    final_dr = solution.get('dr', {}).get(final_year, {})
    
    # Build phased deployment for charts
    phased_deployment = {
        'cumulative_recip_mw': {},
        'cumulative_turbine_mw': {},
        'cumulative_bess_mwh': {},
        'cumulative_solar_mw': {},
        'grid_mw': {},
    }
    
    for y in years:
        eq = solution.get('equipment', {}).get(y, {})
        phased_deployment['cumulative_recip_mw'][y] = eq.get('recip_mw', 0)
        phased_deployment['cumulative_turbine_mw'][y] = eq.get('turbine_mw', 0)
        phased_deployment['cumulative_bess_mwh'][y] = eq.get('bess_mwh', 0)
        phased_deployment['cumulative_solar_mw'][y] = eq.get('solar_mw', 0)
        phased_deployment['grid_mw'][y] = eq.get('grid_mw', 0)
    
    # Calculate totals
    total_capex = (
        final_equipment.get('n_recip', 0) * 5 * 1000 * 1650 +
        final_equipment.get('n_turbine', 0) * 20 * 1000 * 1300 +
        final_equipment.get('bess_mwh', 0) * 1000 * 250 +
        final_equipment.get('solar_mw', 0) * 1000 * 1000
    )
    if final_equipment.get('grid_active', False):
        total_capex += 5_000_000  # Grid interconnection
    
    # Annual generation estimate
    load_array = np.array(load_data.get('total_load_mw', [100]*8760))
    annual_gen_mwh = float(np.sum(load_array))
    
    # Check for violations
    violations = []
    
    # Power gap violation (informational, not a hard failure)
    if final_coverage.get('power_gap_mw', 0) > 1:
        gap_mw = final_coverage.get('power_gap_mw', 0)
        coverage_pct = final_coverage.get('coverage_pct', 100)
        violations.append(f"Power gap: {gap_mw:.1f} MW average ({100-coverage_pct:.1f}% unserved)")
    
    # Build result
    result = {
        'feasible': True,
        'scenario_name': 'MILP Optimized',
        'violations': violations,
        
        'equipment_config': {
            'recip_engines': [{'quantity': final_equipment.get('n_recip', 0), 'capacity_mw': 5.0}] 
                            if final_equipment.get('n_recip', 0) > 0 else [],
            'gas_turbines': [{'quantity': final_equipment.get('n_turbine', 0), 'capacity_mw': 20.0}]
                           if final_equipment.get('n_turbine', 0) > 0 else [],
            'bess': [{'energy_mwh': final_equipment.get('bess_mwh', 0), 
                     'power_mw': final_equipment.get('bess_mw', 0)}]
                   if final_equipment.get('bess_mwh', 0) > 0 else [],
            'solar_mw_dc': final_equipment.get('solar_mw', 0),
            'grid_import_mw': final_equipment.get('grid_mw', 0),
            
            # Summary fields
            'n_recip': final_equipment.get('n_recip', 0),
            'n_turbine': final_equipment.get('n_turbine', 0),
            'recip_mw': final_equipment.get('recip_mw', 0),
            'turbine_mw': final_equipment.get('turbine_mw', 0),
            'bess_mwh': final_equipment.get('bess_mwh', 0),
            'bess_mw': final_equipment.get('bess_mw', 0),
            'solar_mw': final_equipment.get('solar_mw', 0),
            'grid_mw': final_equipment.get('grid_mw', 0),
            'grid_active': final_equipment.get('grid_active', False),
            'total_capacity_mw': final_equipment.get('total_capacity_mw', 0),
            
            # Store full solution for debugging
            '_milp_solution': solution,
            '_phased_deployment': phased_deployment,
        },
        
        'economics': {
            'lcoe_mwh': max(0, solution.get('objective_lcoe', 0)),
            'total_capex_m': total_capex / 1_000_000,
            'annual_generation_gwh': annual_gen_mwh / 1000,
            'annual_opex_m': total_capex * 0.03 / 1_000_000,  # Estimate 3% of CAPEX
        },
        
        'power_coverage': {
            'final_coverage_pct': final_coverage.get('coverage_pct', 100),
            'power_gap_mw': final_coverage.get('power_gap_mw', 0),
            'unserved_mwh': final_coverage.get('unserved_mwh', 0),
            'is_fully_served': final_coverage.get('is_fully_served', True),
            'by_year': {
                y: solution.get('power_coverage', {}).get(y, {})
                for y in years
            },
        },
        
        'emissions': {
            'nox_tpy': final_emissions.get('nox_tpy', 0),
            'nox_limit_tpy': final_emissions.get('nox_limit_tpy', 99),
            'nox_utilization_pct': final_emissions.get('nox_utilization_pct', 0),
            'by_year': {
                y: solution.get('emissions', {}).get(y, {})
                for y in years
            },
        },
        
        'gas_usage': {
            'avg_daily_mcf': final_gas.get('avg_daily_mcf', 0),
            'gas_limit_mcf_day': final_gas.get('gas_limit_mcf_day', 50000),
            'gas_utilization_pct': final_gas.get('gas_utilization_pct', 0),
            'by_year': {
                y: solution.get('gas_usage', {}).get(y, {})
                for y in years
            },
        },
        
        'timeline': {
            'timeline_months': 24,  # Could calculate from deployment
            'timeline_years': 2.0,
            'critical_path': 'MILP Optimized',
            'deployment_speed': 'Optimized',
            'grid_first_year': solution.get('summary', {}).get('grid_first_year'),
        },
        
        'dr_metrics': {
            'total_dr_mw': final_dr.get('total_dr_mw', 0),
            'spinning_reserve_mw': final_dr.get('spinning_reserve', 0),
            'non_spinning_reserve_mw': final_dr.get('non_spinning_reserve', 0),
            'economic_dr_mw': final_dr.get('economic_dr', 0),
            'emergency_dr_mw': final_dr.get('emergency_dr', 0),
            'dr_revenue_annual': final_dr.get('total_dr_mw', 0) * 8760 * 10 / 1000,  # Rough estimate
        },
        
        'metrics': {
            'nox_tpy': final_emissions.get('nox_tpy', 0),
            'gas_mcf_day': final_gas.get('avg_daily_mcf', 0),
            'coverage_pct': final_coverage.get('coverage_pct', 100),
        },
        
        'score': 100 if final_coverage.get('is_fully_served', True) else 
                 max(0, final_coverage.get('coverage_pct', 0)),
    }
    
    return result


def run_milp_scenarios(
    site: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    scenarios: List[Dict] = None,
    years: List[int] = None,
    solver: str = 'glpk',
) -> List[Dict]:
    """
    Run MILP optimization for multiple scenarios.
    
    Args:
        site: Site parameters
        constraints: Hard constraints
        load_profile_dr: Load profile with DR
        scenarios: List of scenario dicts (if None, uses defaults)
        years: Planning years
        solver: MILP solver
    
    Returns:
        List of optimization results, sorted by LCOE
    """
    
    if years is None:
        years = list(range(2026, 2036))
    
    # Default scenarios if none provided
    if scenarios is None:
        scenarios = [
            {
                'Scenario_Name': 'All Technologies',
                'Recip_Enabled': True,
                'Turbine_Enabled': True,
                'BESS_Enabled': True,
                'Solar_Enabled': True,
                'Grid_Enabled': True,
            },
            {
                'Scenario_Name': 'BTM Only',
                'Recip_Enabled': True,
                'Turbine_Enabled': True,
                'BESS_Enabled': True,
                'Solar_Enabled': True,
                'Grid_Enabled': False,
            },
            {
                'Scenario_Name': 'Recips + BESS',
                'Recip_Enabled': True,
                'Turbine_Enabled': False,
                'BESS_Enabled': True,
                'Solar_Enabled': False,
                'Grid_Enabled': False,
            },
            {
                'Scenario_Name': 'Grid + Solar',
                'Recip_Enabled': False,
                'Turbine_Enabled': False,
                'BESS_Enabled': True,
                'Solar_Enabled': True,
                'Grid_Enabled': True,
            },
        ]
    
    results = []
    
    for scenario in scenarios:
        scenario_name = scenario.get('Scenario_Name', 'Unknown')
        logger.info(f"Running scenario: {scenario_name}")
        
        result = optimize_with_milp(
            site=site,
            constraints=constraints,
            load_profile_dr=load_profile_dr,
            years=years,
            scenario=scenario,
            solver=solver,
        )
        
        result['scenario_name'] = scenario_name
        results.append(result)
    
    # Sort by LCOE (best first), with infeasible at end
    results.sort(key=lambda x: (
        not x.get('feasible', False),
        x.get('economics', {}).get('lcoe_mwh', float('inf'))
    ))
    
    return results
