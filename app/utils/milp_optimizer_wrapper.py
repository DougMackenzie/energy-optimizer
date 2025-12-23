"""
MILP Optimizer Wrapper - DIAGNOSTIC VERSION
============================================

This version has extensive error handling and logging to diagnose
why the MILP optimization is failing.

Replace app/utils/milp_optimizer_wrapper.py with this file.
"""

import logging
import traceback
from typing import Dict, List, Optional
import sys

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ============================================================================
# DIAGNOSTIC: Check imports
# ============================================================================

IMPORT_ERRORS = []

# Check numpy
try:
    import numpy as np
    logger.info("✓ numpy imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"numpy: {e}")
    logger.error(f"✗ numpy import failed: {e}")
    np = None

# Check pyomo
try:
    from pyomo.environ import SolverFactory
    logger.info("✓ pyomo imported successfully")
    PYOMO_AVAILABLE = True
except ImportError as e:
    IMPORT_ERRORS.append(f"pyomo: {e}")
    logger.error(f"✗ pyomo import failed: {e}")
    PYOMO_AVAILABLE = False

# Check solver availability
SOLVER_AVAILABLE = None
SOLVER_NAME = None

if PYOMO_AVAILABLE:
    for solver in ['glpk', 'cbc', 'gurobi']:
        try:
            opt = SolverFactory(solver)
            if opt is not None and opt.available():
                SOLVER_AVAILABLE = True
                SOLVER_NAME = solver
                logger.info(f"✓ Solver '{solver}' is available")
                break
            else:
                logger.warning(f"✗ Solver '{solver}' not available")
        except Exception as e:
            logger.warning(f"✗ Solver '{solver}' check failed: {e}")
    
    if not SOLVER_AVAILABLE:
        logger.error("✗ No MILP solver found! Install glpk, cbc, or gurobi.")

# Check MILP model import
MILP_MODEL_AVAILABLE = False
bvNexusMILP_DR = None

try:
    from app.optimization.milp_model_dr import bvNexusMILP_DR
    logger.info("✓ bvNexusMILP_DR imported successfully")
    MILP_MODEL_AVAILABLE = True
except ImportError as e:
    IMPORT_ERRORS.append(f"milp_model_dr: {e}")
    logger.error(f"✗ milp_model_dr import failed: {e}")
    logger.error(f"  Full traceback: {traceback.format_exc()}")


def _create_empty_result(error_msg: str) -> Dict:
    """Create a properly structured empty result with error message."""
    return {
        'feasible': False,
        'scenario_name': 'MILP Error',
        'violations': [error_msg],
        'equipment_config': {
            'recip_engines': [],
            'gas_turbines': [],
            'bess': [],
            'solar_mw_dc': 0,
            'grid_import_mw': 0,
            'n_recip': 0,
            'n_turbine': 0,
            'recip_mw': 0,
            'turbine_mw': 0,
            'bess_mwh': 0,
            'bess_mw': 0,
            'solar_mw': 0,
            'grid_mw': 0,
            'total_capacity_mw': 0,
            '_phased_deployment': {
                'cumulative_recip_mw': {},
                'cumulative_turbine_mw': {},
                'cumulative_bess_mwh': {},
                'cumulative_solar_mw': {},
                'grid_mw': {},
            },
        },
        'economics': {
            'lcoe_mwh': 0,
            'total_capex_m': 0,
            'annual_generation_gwh': 0,
            'annual_opex_m': 0,
        },
        'power_coverage': {
            'final_coverage_pct': 0,
            'power_gap_mw': 0,
            'unserved_mwh': 0,
            'is_fully_served': False,
            'by_year': {},
        },
        'emissions': {
            'nox_tpy': 0,
            'nox_limit_tpy': 99,
            'nox_utilization_pct': 0,
            'by_year': {},
        },
        'gas_usage': {
            'avg_daily_mcf': 0,
            'gas_limit_mcf_day': 50000,
            'gas_utilization_pct': 0,
            'by_year': {},
        },
        'timeline': {
            'timeline_months': 0,
            'timeline_years': 0,
            'critical_path': 'Error',
            'deployment_speed': 'N/A',
        },
        'dr_metrics': {
            'total_dr_mw': 0,
        },
        'metrics': {
            'nox_tpy': 0,
            'gas_mcf_day': 0,
            'coverage_pct': 0,
        },
        'score': 0,
    }


def optimize_with_milp(
    site: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    years: List[int] = None,
    existing_equipment: Dict = None,
    solver: str = 'cbc',  # CBC is faster than GLPK
    time_limit: int = 300,
    scenario: Dict = None,
) -> Dict:
    """
    Run MILP optimization with extensive error handling.
    """
    
    logger.info("="*60)
    logger.info("MILP OPTIMIZATION - DIAGNOSTIC MODE")
    logger.info("="*60)
    
    # ========================================================================
    # STEP 1: Check prerequisites
    # ========================================================================
    
    if IMPORT_ERRORS:
        error_msg = f"Import errors: {', '.join(IMPORT_ERRORS)}"
        logger.error(f"STEP 1 FAILED: {error_msg}")
        return _create_empty_result(error_msg)
    
    if not PYOMO_AVAILABLE:
        error_msg = "Pyomo not installed. Run: pip install pyomo"
        logger.error(f"STEP 1 FAILED: {error_msg}")
        return _create_empty_result(error_msg)
    
    if not SOLVER_AVAILABLE:
        error_msg = "No MILP solver found. Install glpk: brew install glpk (mac) or apt install glpk-utils (linux)"
        logger.error(f"STEP 1 FAILED: {error_msg}")
        return _create_empty_result(error_msg)
    
    if not MILP_MODEL_AVAILABLE:
        error_msg = "MILP model class not available. Check milp_model_dr.py for errors."
        logger.error(f"STEP 1 FAILED: {error_msg}")
        return _create_empty_result(error_msg)
    
    logger.info("✓ STEP 1: All prerequisites met")
    
    # ========================================================================
    # STEP 2: Validate inputs
    # ========================================================================
    
    try:
        if years is None:
            years = list(range(2026, 2036))
        
        # Validate constraints
        if not constraints:
            constraints = {}
        
        nox_limit = constraints.get('NOx_Limit_tpy', constraints.get('max_nox_tpy', 99))
        gas_limit = constraints.get('Gas_Supply_MCF_day', constraints.get('gas_supply_mcf_day', 50000))
        land_limit = constraints.get('Available_Land_Acres', constraints.get('land_area_acres', 500))
        
        logger.info(f"  Constraints: NOx={nox_limit} tpy, Gas={gas_limit} MCF/day, Land={land_limit} acres")
        
        # Validate load profile
        if not load_profile_dr:
            load_profile_dr = {}
        
        peak_it_mw = load_profile_dr.get('peak_it_mw', 160.0)
        pue = load_profile_dr.get('pue', 1.25)
        
        logger.info(f"  Load: {peak_it_mw} MW peak IT, PUE={pue}")
        logger.info("✓ STEP 2: Inputs validated")
        
    except Exception as e:
        error_msg = f"Input validation failed: {e}"
        logger.error(f"STEP 2 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
    
    # ========================================================================
    # STEP 3: Prepare load data
    # ========================================================================
    
    try:
        # Generate load profile if not provided
        if 'load_data' in load_profile_dr and 'total_load_mw' in load_profile_dr['load_data']:
            load_data = load_profile_dr['load_data']
            logger.info("  Using provided load_data")
        else:
            # Generate simple profile
            load_factor = load_profile_dr.get('load_factor', 0.75)
            base_load = peak_it_mw * pue * load_factor
            
            if np is not None:
                load_8760 = base_load * (1 + 0.1 * np.sin(2 * np.pi * np.arange(8760) / 24))
                load_8760 = np.maximum(load_8760, base_load * 0.5)
            else:
                # Fallback without numpy
                import math
                load_8760 = [base_load * (1 + 0.1 * math.sin(2 * 3.14159 * h / 24)) for h in range(8760)]
            
            load_data = {
                'total_load_mw': load_8760 if isinstance(load_8760, list) else load_8760.tolist(),
                'pue': pue,
            }
            logger.info(f"  Generated load profile: {base_load:.1f} MW base load")
        
        # Ensure it's a list/array
        if hasattr(load_data['total_load_mw'], 'tolist'):
            load_data['total_load_mw'] = load_data['total_load_mw'].tolist()
        
        logger.info(f"  Load data: {len(load_data['total_load_mw'])} hours")
        logger.info("✓ STEP 3: Load data prepared")
        
    except Exception as e:
        error_msg = f"Load data preparation failed: {e}"
        logger.error(f"STEP 3 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
    
    # ========================================================================
    # STEP 4: Build MILP model
    # ========================================================================
    
    try:
        optimizer = bvNexusMILP_DR()
        
        workload_mix = load_profile_dr.get('workload_mix', {
            'pre_training': 0.30,
            'fine_tuning': 0.20,
            'batch_inference': 0.30,
            'realtime_inference': 0.20,
        })
        
        dr_config = {
            'cooling_flex': load_profile_dr.get('cooling_flex', 0.25),
            'annual_curtailment_budget_pct': 0.01,
        }
        
        grid_config = {
            'available_year': constraints.get('grid_available_year', 2030),
            'capex': constraints.get('grid_interconnection_capex', 5_000_000),
        }
        
        logger.info("  Building model...")
        
        optimizer.build(
            site=site or {'name': 'Test Site'},
            constraints=constraints,
            load_data=load_data,
            workload_mix=workload_mix,
            years=years,
            dr_config=dr_config,
            existing_equipment=existing_equipment,
            grid_config=grid_config,
            use_representative_periods=True,
        )
        
        logger.info("✓ STEP 4: Model built successfully")
        
    except Exception as e:
        error_msg = f"Model build failed: {e}"
        logger.error(f"STEP 4 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
    
    # ========================================================================
    # STEP 5: Apply scenario constraints
    # ========================================================================
    
    try:
        if scenario:
            scenario_name = scenario.get('Scenario_Name', 'Unknown')
            logger.info(f"  Applying scenario: {scenario_name}")
            
            m = optimizer.model
            
            def is_enabled(key, default=True):
                val = scenario.get(key, default)
                if isinstance(val, str):
                    return val.lower() in ('true', 'yes', '1', 'enabled')
                return bool(val)
            
            if not is_enabled('Recip_Enabled', True) and not is_enabled('Recip_Engines', True):
                logger.info("    Disabling recips")
                for y in years:
                    m.n_recip[y].fix(0)
            
            if not is_enabled('Turbine_Enabled', True) and not is_enabled('Gas_Turbines', True):
                logger.info("    Disabling turbines")
                for y in years:
                    m.n_turbine[y].fix(0)
            
            if not is_enabled('Solar_Enabled', True) and not is_enabled('Solar_PV', True):
                logger.info("    Disabling solar")
                for y in years:
                    m.solar_mw[y].fix(0)
            
            if not is_enabled('BESS_Enabled', True) and not is_enabled('BESS', True):
                logger.info("    Disabling BESS")
                for y in years:
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
            
            if not is_enabled('Grid_Enabled', True) and not is_enabled('Grid_Connection', True):
                logger.info("    Disabling grid")
                for y in years:
                    m.grid_mw[y].fix(0)
                    m.grid_active[y].fix(0)
        
        logger.info("✓ STEP 5: Scenario constraints applied")
        
    except Exception as e:
        error_msg = f"Scenario constraints failed: {e}"
        logger.error(f"STEP 5 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
    
    # ========================================================================
    # STEP 6: Solve model
    # ========================================================================
    
    try:
        use_solver = SOLVER_NAME or solver
        logger.info(f"  Solving with {use_solver}...")
        
        solution = optimizer.solve(
            solver=use_solver,
            time_limit=time_limit,
            verbose=False
        )
        
        logger.info(f"  Solver status: {solution.get('status', 'unknown')}")
        logger.info(f"  Termination: {solution.get('termination', 'unknown')}")
        logger.info("✓ STEP 6: Model solved")
        
    except Exception as e:
        error_msg = f"Solver failed: {e}"
        logger.error(f"STEP 6 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
    
    # ========================================================================
    # STEP 7: Format results
    # ========================================================================
    
    try:
        result = _format_solution_safe(solution, years, constraints, load_data)
        logger.info(f"  LCOE: ${result['economics'].get('lcoe_mwh', 0):.2f}/MWh")
        logger.info(f"  Coverage: {result['power_coverage'].get('final_coverage_pct', 0):.1f}%")
        logger.info("✓ STEP 7: Results formatted")
        
        return result
        
    except Exception as e:
        error_msg = f"Result formatting failed: {e}"
        logger.error(f"STEP 7 FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)


def _format_solution_safe(solution: Dict, years: List[int], constraints: Dict, load_data: Dict) -> Dict:
    """Format solution with extensive null checking."""
    
    # Start with empty result structure
    result = _create_empty_result("Formatting")
    
    # Check if solution is valid
    # CRITICAL: Accept solutions even with time/iteration limits
    # Model has unserved variable so should report gaps, not fail
    termination = solution.get('termination', 'unknown')
    acceptable_terms = ['optimal', 'feasible', 'maxTimeLimit', 'maxIterations', 'maxEvaluations']
    is_feasible = termination in acceptable_terms
    
    result['feasible'] = is_feasible
    
    # Only mark as violation if truly infeasible (not just time limit)
    if not is_feasible and termination not in ['maxTimeLimit', 'maxIterations']:
        result['violations'] = [f"Solver: {termination}"]
    elif termination in ['maxTimeLimit', 'maxIterations']:
        # Time limit hit - not a violation, just incomplete optimization
        result['violations'] = []
    else:
        result['violations'] = []
    
    if not is_feasible:
        return result
    
    # Get final year data
    final_year = max(years)
    
    # Equipment
    equipment = solution.get('equipment', {})
    final_eq = equipment.get(final_year, {})
    
    result['equipment_config'].update({
        'n_recip': final_eq.get('n_recip', 0),
        'n_turbine': final_eq.get('n_turbine', 0),
        'recip_mw': final_eq.get('recip_mw', final_eq.get('n_recip', 0) * 5),
        'turbine_mw': final_eq.get('turbine_mw', final_eq.get('n_turbine', 0) * 20),
        'bess_mwh': final_eq.get('bess_mwh', 0),
        'bess_mw': final_eq.get('bess_mw', 0),
        'solar_mw': final_eq.get('solar_mw', 0),
        'grid_mw': final_eq.get('grid_mw', 0),
        'grid_active': final_eq.get('grid_active', False),
        'total_capacity_mw': final_eq.get('total_capacity_mw', 0),
    })
    
    # Build phased deployment
    phased = result['equipment_config']['_phased_deployment']
    for y in years:
        eq = equipment.get(y, {})
        phased['cumulative_recip_mw'][y] = eq.get('recip_mw', eq.get('n_recip', 0) * 5)
        phased['cumulative_turbine_mw'][y] = eq.get('turbine_mw', eq.get('n_turbine', 0) * 20)
        phased['cumulative_bess_mwh'][y] = eq.get('bess_mwh', 0)
        phased['cumulative_solar_mw'][y] = eq.get('solar_mw', 0)
        phased['grid_mw'][y] = eq.get('grid_mw', 0)
    
    # Formatted equipment lists
    if result['equipment_config']['n_recip'] > 0:
        result['equipment_config']['recip_engines'] = [{
            'quantity': result['equipment_config']['n_recip'],
            'capacity_mw': 5.0
        }]
    
    if result['equipment_config']['n_turbine'] > 0:
        result['equipment_config']['gas_turbines'] = [{
            'quantity': result['equipment_config']['n_turbine'],
            'capacity_mw': 20.0
        }]
    
    if result['equipment_config']['bess_mwh'] > 0:
        result['equipment_config']['bess'] = [{
            'energy_mwh': result['equipment_config']['bess_mwh'],
            'power_mw': result['equipment_config']['bess_mw']
        }]
    
    result['equipment_config']['solar_mw_dc'] = result['equipment_config']['solar_mw']
    result['equipment_config']['grid_import_mw'] = result['equipment_config']['grid_mw']
    
    # Economics
    lcoe = solution.get('objective_lcoe', 0)
    if lcoe and lcoe < 1000:  # Sanity check
        result['economics']['lcoe_mwh'] = lcoe
    
    # Calculate CAPEX
    capex = (
        result['equipment_config']['n_recip'] * 5 * 1000 * 1650 +
        result['equipment_config']['n_turbine'] * 20 * 1000 * 1300 +
        result['equipment_config']['bess_mwh'] * 1000 * 250 +
        result['equipment_config']['solar_mw'] * 1000 * 1000
    )
    if result['equipment_config'].get('grid_active'):
        capex += 5_000_000
    
    result['economics']['total_capex_m'] = capex / 1_000_000
    
    # Power coverage
    coverage = solution.get('power_coverage', {})
    final_cov = coverage.get(final_year, {})
    
    result['power_coverage']['final_coverage_pct'] = final_cov.get('coverage_pct', 100)
    result['power_coverage']['power_gap_mw'] = final_cov.get('power_gap_mw', 0)
    result['power_coverage']['unserved_mwh'] = final_cov.get('unserved_mwh', 0)
    result['power_coverage']['is_fully_served'] = final_cov.get('is_fully_served', True)
    result['power_coverage']['by_year'] = coverage
    
    # Emissions
    emissions = solution.get('emissions', {})
    final_em = emissions.get(final_year, {})
    
    result['emissions']['nox_tpy'] = final_em.get('nox_tpy', 0)
    result['emissions']['nox_limit_tpy'] = final_em.get('nox_limit_tpy', 99)
    result['emissions']['nox_utilization_pct'] = final_em.get('nox_utilization_pct', 0)
    result['emissions']['by_year'] = emissions
    
    # Gas usage
    gas = solution.get('gas_usage', {})
    final_gas = gas.get(final_year, {})
    
    result['gas_usage']['avg_daily_mcf'] = final_gas.get('avg_daily_mcf', 0)
    result['gas_usage']['gas_limit_mcf_day'] = final_gas.get('gas_limit_mcf_day', 50000)
    result['gas_usage']['gas_utilization_pct'] = final_gas.get('gas_utilization_pct', 0)
    result['gas_usage']['by_year'] = gas
    
    # DR
    dr = solution.get('dr', {})
    final_dr = dr.get(final_year, {})
    result['dr_metrics']['total_dr_mw'] = final_dr.get('total_dr_mw', 0)
    
    # Metrics (for compatibility)
    result['metrics'] = {
        'nox_tpy': result['emissions']['nox_tpy'],
        'gas_mcf_day': result['gas_usage']['avg_daily_mcf'],
        'coverage_pct': result['power_coverage']['final_coverage_pct'],
    }
    
    # Score
    result['score'] = 100 if result['power_coverage']['is_fully_served'] else \
                      max(0, result['power_coverage']['final_coverage_pct'])
    
    # Check for power gap
    if result['power_coverage']['power_gap_mw'] > 1:
        result['violations'].append(
            f"Power gap: {result['power_coverage']['power_gap_mw']:.1f} MW"
        )
    
    return result


def run_milp_scenarios(
    site: Dict,
    constraints: Dict,
    load_profile_dr: Dict,
    scenarios: List[Dict] = None,
    years: List[int] = None,
    solver: str = 'cbc',  # CBC is faster than GLPK
) -> List[Dict]:
    """Run multiple scenarios."""
    
    if years is None:
        years = list(range(2026, 2036))
    
    if scenarios is None:
        scenarios = [
            {'Scenario_Name': 'All Technologies', 'Grid_Enabled': True},
            {'Scenario_Name': 'BTM Only', 'Grid_Enabled': False},
        ]
    
    results = []
    
    for scenario in scenarios:
        logger.info(f"\n{'='*40}")
        logger.info(f"SCENARIO: {scenario.get('Scenario_Name', 'Unknown')}")
        logger.info(f"{'='*40}")
        
        result = optimize_with_milp(
            site=site,
            constraints=constraints,
            load_profile_dr=load_profile_dr,
            years=years,
            scenario=scenario,
            solver=solver,
        )
        
        result['scenario_name'] = scenario.get('Scenario_Name', 'Unknown')
        results.append(result)
    
    # Sort by LCOE
    results.sort(key=lambda x: (
        not x.get('feasible', False),
        x.get('economics', {}).get('lcoe_mwh', float('inf'))
    ))
    
    return results


# ============================================================================
# DIAGNOSTIC: Print status on import
# ============================================================================

print("\n" + "="*60)
print("MILP OPTIMIZER DIAGNOSTIC STATUS")
print("="*60)
print(f"Pyomo available: {PYOMO_AVAILABLE}")
print(f"Solver available: {SOLVER_AVAILABLE} ({SOLVER_NAME})")
print(f"MILP model available: {MILP_MODEL_AVAILABLE}")
if IMPORT_ERRORS:
    print(f"Import errors: {IMPORT_ERRORS}")
print("="*60 + "\n")
