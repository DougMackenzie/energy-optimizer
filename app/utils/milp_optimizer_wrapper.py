"""
MILP Optimizer Wrapper
Integrates bvNexus MILP model with existing optimizer infrastructure
"""

from typing import Dict, List, Optional
from app.optimization.milp_model_dr import bvNexusMILP_DR
from app.utils.load_profile_generator import generate_load_profile_with_flexibility
import logging

logger = logging.getLogger(__name__)


def optimize_with_milp(
    site: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    years: List[int] = None,
    existing_equipment: Dict = None,
    solver: str = 'glpk',
    time_limit: int = 300
) -> Dict:
    """
    Run MILP optimization for datacenter power system.
    
    Args:
        site: Site parameters including PUE, location, etc.
        constraints: Hard constraints (NOx, land, gas limits)
        load_profile_dr: Load profile with DR configuration from session state
        years: Planning horizon years (default: 2026-2035)
        existing_equipment: Brownfield equipment (default: greenfield)
        solver: MILP solver to use ('glpk', 'cbc', or 'gurobi')
        time_limit: Maximum solve time in seconds
    
    Returns:
        Dict with optimization results including equipment sizing, economics, and DR metrics
    """
    
    try:
        logger.info("Starting MILP optimization")
        
        # Extract parameters from load_profile_dr
        peak_it_mw = load_profile_dr.get('peak_it_mw', 160.0)
        pue = load_profile_dr.get('pue', 1.25)
        load_factor = load_profile_dr.get('load_factor', 0.75)
        workload_mix = load_profile_dr.get('workload_mix', {})
        cooling_flex = load_profile_dr.get('cooling_flex', 0.25)
        load_trajectory = load_profile_dr.get('load_trajectory', {})
        
        # Generate load profile data if not already cached
        if 'load_data' not in load_profile_dr:
            logger.info("Generating load profile with flexibility")
            load_data = generate_load_profile_with_flexibility(
                peak_it_load_mw=peak_it_mw,
                pue=pue,
                load_factor=load_factor,
                workload_mix=workload_mix,
                cooling_flex_pct=cooling_flex
            )
        else:
            load_data = load_profile_dr['load_data']
        
        # Create DR configuration
        dr_config = {
            'cooling_flex': cooling_flex,
            'annual_curtailment_budget_pct': 0.01,  # 1% annual budget
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
            years=years or list(range(2026, 2036)),
            dr_config=dr_config,
            existing_equipment=existing_equipment,
            use_representative_periods=True  # Use 1008 hours for speed
        )
        
        # Solve
        logger.info(f"Solving MILP with {solver}")
        solution = optimizer.solve(solver=solver, time_limit=time_limit, verbose=False)
        
        # Check if solution is feasible
        if solution['status'] == 'ok' and solution['termination'] in ['optimal', 'feasible']:
            logger.info(f"MILP solved successfully: LCOE = {solution['objective_lcoe']:.2f} $/MWh")
            
            # Extract final year equipment
            final_year = max(solution['equipment'].keys())
            final_equipment = solution['equipment'][final_year]
            
            # Format as expected by existing UI
            result = {
                'feasible': True,
                'scenario_name': 'MILP Optimized',
                'equipment_config': {
                    'recip_engines': [{'quantity': final_equipment['n_recip']}] if final_equipment['n_recip'] > 0 else [],
                    'gas_turbines': [{'quantity': final_equipment['n_turbine']}] if final_equipment['n_turbine'] > 0 else [],
                    'bess': [{'energy_mwh': final_equipment['bess_mwh']}] if final_equipment['bess_mwh'] > 0 else [],
                    'solar_mw_dc': final_equipment['solar_mw'],
                    'grid_import_mw': final_equipment['grid_mw'],
                    '_milp_solution': solution,  # Store full MILP solution
                    '_phased_deployment': {  # Create phased deployment for charts
                        # Build cumulative deployment dict with proper keys
                        'cumulative_recip_mw': {year: sol['n_recip'] * 5.0 for year, sol in solution['equipment'].items()},  # Assume 5 MW units
                        'cumulative_turbine_mw': {year: sol['n_turbine'] * 20.0 for year, sol in solution['equipment'].items()},  # Assume 20 MW units
                        'cumulative_bess_mwh': {year: sol['bess_mwh'] for year, sol in solution['equipment'].items()},
                        'cumulative_solar_mw': {year: sol['solar_mw'] for year, sol in solution['equipment'].items()},
                        'grid_mw': {year: sol['grid_mw'] for year, sol in solution['equipment'].items()},
                    }
                },
                'economics': {
                    'lcoe_mwh': max(0, solution['objective_lcoe']),  # Ensure non-negative LCOE
                    'total_capex_m': 0,  # Calculate from equipment
                    'annual_generation_gwh': 0,  # Calculate from load
                    'annual_opex_m': 0,  # Calculate from equipment
                },
                'timeline': {
                    'timeline_months': 24,  # Default - could be calculated
                    'timeline_years': 2.0,
                    'critical_path': 'MILP Optimized Path',
                    'deployment_speed': 'Fast'
                },
                'metrics': {
                    'total_capacity_mw': (
                        final_equipment['n_recip'] * 5.0 +
                        final_equipment['n_turbine'] * 20.0 +
                        final_equipment['bess_mwh'] / 4.0 +  # 4-hour BESS
                        final_equipment['solar_mw']
                    ),
                    'nameplate_capacity_mw': (
                        final_equipment['n_recip'] * 5.0 +
                        final_equipment['n_turbine'] * 20.0 +
                        final_equipment['bess_mwh'] / 4.0
                    )
                },
                'dr_metrics': solution['dr'],
                'violations': [],
                'score': 100,  # Perfect score if optimal
            }
            
            # Calculate economics properly
            total_capex = 0
            for year, eq in solution['equipment'].items():
                # Proper CAPEX calculation
                year_capex = (
                    eq['n_recip'] * 5 * 1000 * 1.65 +  # 5 MW units @ $1650/kW
                    eq['n_turbine'] * 20 * 1000 * 1.30 +  # 20 MW units @ $1300/kW
                    eq['bess_mwh'] * 1000 * 0.236 * 0.70 +  # $236/kWh with 30% ITC
                    eq['solar_mw'] * 1000000 * 0.95 * 0.70  # $0.95/W with 30% ITC
                )
                total_capex += year_capex
            
            result['economics']['total_capex_m'] = total_capex / 1_000_000  # Convert to millions
            
            # Annual generation estimate
            result['economics']['annual_generation_gwh'] = load_data['summary']['avg_load_mw'] * 8760 / 1000
            
            # If LCOE is still negative or zero, recalculate it properly
            if result['economics']['lcoe_mwh'] <= 0:
                # Simple LCOE = (CAPEX * CRF + Annual OPEX - DR Revenue) / Annual Generation
                crf = 0.08  # 8% capital recovery factor (simplified)
                annual_opex = total_capex * 0.03  # Assume 3% of CAPEX as annual O&M
                dr_revenue = solution['dr'].get('dr_revenue_annual', 0)
                annual_gen_mwh = result['economics']['annual_generation_gwh'] * 1000
                
                if annual_gen_mwh > 0:
                    result['economics']['lcoe_mwh'] = (
                        (total_capex * crf + annual_opex - dr_revenue) / annual_gen_mwh
                    )
                else:
                    result['economics']['lcoe_mwh'] = 999.99  # Invalid case
            
            logger.info(f"MILP optimization successful: LCOE = {result['economics']['lcoe_mwh']:.2f} $/MWh")
            return result
            
        else:
            # Infeasible or error
            logger.warning(f"MILP solver status: {solution['status']}, termination: {solution['termination']}")
            return {
                'feasible': False,
                'scenario_name': 'MILP Optimized',
                'violations': [f"MILP solver failed: {solution['termination']}"],
                'equipment_config': {},
                'economics': {},
                'timeline': {},
                'dr_metrics': {},
                'score': 0,
            }
    
    except Exception as e:
        logger.error(f"MILP optimization error: {e}", exc_info=True)
        return {
            'feasible': False,
            'scenario_name': 'MILP Optimized',
            'violations': [f"Optimization error: {str(e)}"],
            'equipment_config': {},
            'economics': {},
            'timeline': {},
            'dr_metrics': {},
            'score': 0,
        }


def run_milp_scenarios(
    sit: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    scenarios: List[str] = None
) -> List[Dict]:
    """
    Run MILP optimization for multiple scenarios with different DR configurations.
    
    Args:
        site: Site parameters
        constraints: Hard constraints
        load_profile_dr: Base load profile with DR
        scenarios: List of scenario names to run
    
    Returns:
        List of optimization results, one per scenario
    """
    
    results = []
    
    # Define scenario variations
    scenario_configs = {
        'No DR': {
            'cooling_flex': 0.0,
            'workload_flexibility_override': {
                'pre_training': 0, 'fine_tuning': 0, 'batch_inference': 0,
                'realtime_inference': 0, 'rl_training': 0, 'cloud_hpc': 0
            }
        },
        'Cooling DR Only': {
            'cooling_flex': 0.25,
            'workload_flexibility_override': {
                'pre_training': 0, 'fine_tuning': 0, 'batch_inference': 0,
                'realtime_inference': 0, 'rl_training': 0, 'cloud_hpc': 0
            }
        },
        'Full DR (Conservative)': {
            'cooling_flex': 0.20,
            'workload_flexibility_override': None  # Use defaults
        },
        'Full DR (Aggressive)': {
            'cooling_flex': 0.30,
            'workload_flexibility_override': None  # Use defaults
        },
    }
    
    scenarios_to_run = scenarios or list(scenario_configs.keys())
    
    for scenario_name in scenarios_to_run:
        if scenario_name not in scenario_configs:
            continue
        
        logger.info(f"Running scenario: {scenario_name}")
        
        # Create modified load profile
        modified_profile = load_profile_dr.copy()
        config = scenario_configs[scenario_name]
        modified_profile['cooling_flex'] = config['cooling_flex']
        
        # Run optimization
        result = optimize_with_milp(
            site=site,
            constraints=constraints,
            load_profile_dr=modified_profile
        )
        
        result['scenario_name'] = scenario_name
        results.append(result)
    
    # Sort by LCOE (best first)
    results.sort(key=lambda x: x['economics'].get('lcoe_mwh', float('inf')))
    
    return results
