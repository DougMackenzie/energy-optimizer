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
    for solver in ['cbc', 'glpk', 'gurobi']:
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


# ==============================================================================
# EQUIPMENT PARAMETERS (bvNexus v3 Corrected)
# ==============================================================================
EQUIPMENT_PARAMS = {
    'recip': {
        'capacity_mw': 10.0,      # Per unit
        'heat_rate': 7200,        # BTU/kWh
        'capex': 1200,            # $/kW
        'vom': 8.0,               # $/MWh
        'fom': 15.0,              # $/kW-yr
        'lead_time': 18,          # months
    },
    'turbine': {
        'capacity_mw': 50.0,      # Per unit
        'heat_rate': 8500,        # BTU/kWh
        'capex': 900,             # $/kW
        'vom': 6.0,               # $/MWh
        'fom': 12.0,              # $/kW-yr
        'lead_time': 24,          # months
    },
    'bess': {
        'capex_kwh': 250,         # $/kWh
        'fom': 10.0,              # $/kW-yr
        'lead_time': 12,          # months
    },
    'solar': {
        'capex': 950,             # $/kW
        'fom': 10.0,              # $/kW-yr
        'cf': 0.25,               # capacity factor
        'lead_time': 12,          # months
    },
}

DEFAULT_LOAD_TRAJECTORY = {
    2025: 0, 2026: 0, 2027: 0,  # Pre-construction (no load)
    2028: 150, 2029: 300, 2030: 450,  # Ramp-up
    2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,  # Steady state
    2036: 600, 2037: 600, 2038: 600, 2039: 600, 2040: 600,  # Extended
}

GAS_PRICE = 3.50        # $/MMBtu
GRID_PRICE = 75         # $/MWh
GRID_LEAD_TIME = 60     # months (default)

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
        
        # STEP 3.5: Load trajectory passthrough (bvNexus v3 fix)
        # Apply default load trajectory if not provided
        if 'load_trajectory' not in load_profile_dr:
            # Default: 600 MW utility, 150 MW start in 2028, +150 MW/year
            default_trajectory = {
                2025: 0, 2026: 0, 2027: 0,
                2028: 150, 2029: 300, 2030: 450,
                2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,
            }
            load_profile_dr['load_trajectory'] = default_trajectory
            logger.info("  Applied default load trajectory: 0→150→300→450→600 MW")
        
        # Pass trajectory to site parameter AND load_data
        if site is None:
            site = {}
        site['load_trajectory'] = load_profile_dr.get('load_trajectory', {})
        load_data['load_trajectory'] = load_profile_dr.get('load_trajectory', DEFAULT_LOAD_TRAJECTORY)

        
        logger.info("  Building model...")
        
        optimizer.build(
            site=site,
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
    # ========================================================================
    # STEP 5: Apply scenario constraints + load-following + lead times
    # ========================================================================
    
    try:
        scenario_name = scenario.get('Scenario_Name', 'Unknown') if scenario else 'Default'
        logger.info(f"  Applying constraints for scenario: {scenario_name}")
        
        m = optimizer.model
        
        # =====================
        # 5A: SCENARIO EQUIPMENT CONSTRAINTS
        # =====================
        if scenario:
            # Fixed is_disabled function (uses OR logic, not AND)
            def is_disabled(primary_key, alt_key=None):
                """Returns True if equipment is explicitly disabled."""
                for key in [primary_key, alt_key]:
                    if key and key in scenario:
                        val = scenario[key]
                        if isinstance(val, str):
                            if val.lower() in ('false', 'no', '0', 'disabled'):
                                return True
                        elif val == False:
                            return True
                return False
            
            if is_disabled('Recip_Enabled', 'Recip_Engines'):
                logger.info("    🚫 RECIPS: Disabled by scenario")
                for y in years:
                    m.n_recip[y].fix(0)
            
            if is_disabled('Turbine_Enabled', 'Gas_Turbines'):
                logger.info("    🚫 TURBINES: Disabled by scenario")
                for y in years:
                    m.n_turbine[y].fix(0)
            
            if is_disabled('Solar_Enabled', 'Solar_PV'):
                logger.info("    🚫 SOLAR: Disabled by scenario")
                for y in years:
                    m.solar_mw[y].fix(0)
            
            if is_disabled('BESS_Enabled', 'BESS'):
                logger.info("    🚫 BESS: Disabled by scenario")
                for y in years:
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
            
            if is_disabled('Grid_Enabled', 'Grid_Connection'):
                logger.info("    🚫 GRID: Disabled by scenario (BTM mode)")
                for y in years:
                    m.grid_mw[y].fix(0)
                    if hasattr(m, 'grid_active'):
                        m.grid_active[y].fix(0)
        
        # =====================
        # 5B: LOAD-FOLLOWING CONSTRAINTS
        # =====================
        # Don't deploy equipment in years with zero load
        trajectory = load_data.get('load_trajectory', DEFAULT_LOAD_TRAJECTORY)
        
        for y in years:
            load_y = trajectory.get(y, 0)
            if load_y == 0:
                logger.info(f"    📉 Year {y}: Load=0 MW, fixing all equipment to 0")
                m.n_recip[y].fix(0)
                m.n_turbine[y].fix(0)
                m.solar_mw[y].fix(0)
                m.bess_mwh[y].fix(0)
                m.bess_mw[y].fix(0)
                if hasattr(m, 'grid_mw'):
                    m.grid_mw[y].fix(0)
                if hasattr(m, 'grid_active'):
                    m.grid_active[y].fix(0)
        
        # =====================
        # 5C: LEAD TIME CONSTRAINTS
        # =====================
        # Equipment not available before procurement + construction
        start_year = min(years)
        
        # Get grid lead time from scenario or default
        grid_lead = scenario.get('Grid_Timeline_Months', GRID_LEAD_TIME) if scenario else GRID_LEAD_TIME
        
        for y in years:
            months_from_start = (y - start_year) * 12
            
            # BESS: 12 months
            if months_from_start < EQUIPMENT_PARAMS['bess']['lead_time']:
                if not m.bess_mwh[y].is_fixed():
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
                    if months_from_start == 0:
                        logger.info(f"    ⏰ Year {y}: BESS not available (lead time)")
            
            # Solar: 12 months
            if months_from_start < EQUIPMENT_PARAMS['solar']['lead_time']:
                if not m.solar_mw[y].is_fixed():
                    m.solar_mw[y].fix(0)
                    if months_from_start == 0:
                        logger.info(f"    ⏰ Year {y}: Solar not available (lead time)")
            
            # Recip: 18 months
            if months_from_start < EQUIPMENT_PARAMS['recip']['lead_time']:
                if not m.n_recip[y].is_fixed():
                    m.n_recip[y].fix(0)
                    if months_from_start == 0:
                        logger.info(f"    ⏰ Year {y}: Recips not available (lead time)")
            
            # Turbine: 24 months
            if months_from_start < EQUIPMENT_PARAMS['turbine']['lead_time']:
                if not m.n_turbine[y].is_fixed():
                    m.n_turbine[y].fix(0)
                    if months_from_start == 0:
                        logger.info(f"    ⏰ Year {y}: Turbines not available (lead time)")
            
            # Grid: 60 months (default)
            if months_from_start < grid_lead:
                if hasattr(m, 'grid_mw') and not m.grid_mw[y].is_fixed():
                    m.grid_mw[y].fix(0)
                if hasattr(m, 'grid_active') and not m.grid_active[y].is_fixed():
                    m.grid_active[y].fix(0)
                if months_from_start == 0:  # Only log once
                    logger.info(f"    ⏰ Grid not available until {start_year + grid_lead // 12}")
        
        logger.info("✓ STEP 5: All constraints applied")
        
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
    """
    Format MILP solution with COMPLETE economics calculation.
    Fixes: LCOE=0, missing fuel cost, missing generation, wrong capacity.
    """
    
    # Check termination status
    term = solution.get('termination', 'unknown')
    acceptable = ['optimal', 'feasible', 'maxTimeLimit', 'maxIterations', 'maxEvaluations']
    if term not in acceptable:
        return _create_empty_result(f"Solver status: {term}")
    
    final_year = max(years)
    
    # ==========================================================================
    # EXTRACT EQUIPMENT FROM SOLUTION
    # ==========================================================================
    eq = solution.get('equipment', {}).get(final_year, {})
    
    n_recip = int(eq.get('n_recip', 0))
    n_turbine = int(eq.get('n_turbine', 0))
    bess_mwh = float(eq.get('bess_mwh', 0))
    solar_mw = float(eq.get('solar_mw', 0))
    grid_mw = float(eq.get('grid_mw', 0))
    grid_active = bool(eq.get('grid_active', False) or grid_mw > 0)
    
    # ==========================================================================
    # CALCULATE CAPACITIES (using CORRECT equipment sizes!)
    # ==========================================================================
    RECIP_MW = EQUIPMENT_PARAMS['recip']['capacity_mw']      # 10.0 MW
    TURBINE_MW = EQUIPMENT_PARAMS['turbine']['capacity_mw']  # 50.0 MW
    
    recip_mw = n_recip * RECIP_MW
    turbine_mw = n_turbine * TURBINE_MW
    bess_mw = bess_mwh / 4  # 4-hour duration
    
    total_capacity_mw = recip_mw + turbine_mw + solar_mw + bess_mw + grid_mw
    
    logger.info(f"Equipment: {n_recip} recips ({recip_mw:.0f} MW), {n_turbine} turbines ({turbine_mw:.0f} MW), {solar_mw:.0f} MW solar, {bess_mwh:.0f} MWh BESS, {grid_mw:.0f} MW grid")
    logger.info(f"Total capacity: {total_capacity_mw:.0f} MW")
    
    # ==========================================================================
    # CALCULATE ANNUAL GENERATION
    # ==========================================================================
    CF_THERMAL = 0.70
    CF_SOLAR = EQUIPMENT_PARAMS['solar']['cf']  # 0.25
    CF_GRID = 0.85
    HOURS = 8760
    
    recip_gen_mwh = recip_mw * CF_THERMAL * HOURS
    turbine_gen_mwh = turbine_mw * CF_THERMAL * HOURS
    solar_gen_mwh = solar_mw * CF_SOLAR * HOURS
    grid_gen_mwh = grid_mw * CF_GRID * HOURS if grid_active else 0
    
    annual_gen_mwh = recip_gen_mwh + turbine_gen_mwh + solar_gen_mwh + grid_gen_mwh
    annual_gen_gwh = annual_gen_mwh / 1000
    
    logger.info(f"Annual generation: {annual_gen_gwh:.1f} GWh")
    
    # ==========================================================================
    # CALCULATE CAPEX
    # ==========================================================================
    capex = (
        recip_mw * 1000 * EQUIPMENT_PARAMS['recip']['capex'] +
        turbine_mw * 1000 * EQUIPMENT_PARAMS['turbine']['capex'] +
        bess_mwh * 1000 * EQUIPMENT_PARAMS['bess']['capex_kwh'] +
        solar_mw * 1000 * EQUIPMENT_PARAMS['solar']['capex']
    )
    if grid_active:
        capex += 5_000_000  # Grid interconnection
    
    total_capex_m = capex / 1e6
    
    # ==========================================================================
    # CALCULATE FUEL COST (was missing!)
    # ==========================================================================
    recip_fuel_mmbtu = recip_gen_mwh * 1000 * EQUIPMENT_PARAMS['recip']['heat_rate'] / 1e6
    turbine_fuel_mmbtu = turbine_gen_mwh * 1000 * EQUIPMENT_PARAMS['turbine']['heat_rate'] / 1e6
    
    fuel_cost = (recip_fuel_mmbtu + turbine_fuel_mmbtu) * GAS_PRICE
    grid_cost = grid_gen_mwh * GRID_PRICE
    
    annual_fuel_cost_m = (fuel_cost + grid_cost) / 1e6
    
    logger.info(f"Annual fuel cost: ${annual_fuel_cost_m:.2f}M")
    
    # ==========================================================================
    # CALCULATE O&M (was missing!)
    # ==========================================================================
    fixed_om = (
        recip_mw * 1000 * EQUIPMENT_PARAMS['recip']['fom'] +
        turbine_mw * 1000 * EQUIPMENT_PARAMS['turbine']['fom'] +
        bess_mw * 1000 * EQUIPMENT_PARAMS['bess']['fom'] +
        solar_mw * 1000 * EQUIPMENT_PARAMS['solar']['fom']
    ) / 1e6
    
    variable_om = (
        recip_gen_mwh * EQUIPMENT_PARAMS['recip']['vom'] +
        turbine_gen_mwh * EQUIPMENT_PARAMS['turbine']['vom']
    ) / 1e6
    
    annual_opex_m = fixed_om + variable_om
    
    logger.info(f"Annual O&M: ${annual_opex_m:.2f}M")
    
    # ==========================================================================
    # CALCULATE LCOE (was returning 0!)
    # ==========================================================================
    r = 0.08  # Discount rate
    n = 20    # Project life
    crf = r * (1 + r)**n / ((1 + r)**n - 1)  # Capital recovery factor
    
    annualized_capex = total_capex_m * crf
    annual_costs = annualized_capex + annual_opex_m + annual_fuel_cost_m
    
    if annual_gen_gwh > 0:
        lcoe_mwh = annual_costs * 1000 / annual_gen_gwh
    else:
        lcoe_mwh = 0
    
    logger.info(f"LCOE: ${lcoe_mwh:.2f}/MWh")
    
    # ==========================================================================
    # CALCULATE CAPACITY FACTOR (was missing!)
    # ==========================================================================
    max_gen = total_capacity_mw * HOURS
    capacity_factor_pct = (annual_gen_mwh / max_gen * 100) if max_gen > 0 else 0
    
    # ==========================================================================
    # BUILD PHASED DEPLOYMENT (for charts)
    # ==========================================================================
    phased = {
        'cumulative_recip_mw': {},
        'cumulative_turbine_mw': {},
        'cumulative_bess_mwh': {},
        'cumulative_solar_mw': {},
        'grid_mw': {},
    }
    
    for y in years:
        e = solution.get('equipment', {}).get(y, {})
        phased['cumulative_recip_mw'][y] = int(e.get('n_recip', 0)) * RECIP_MW
        phased['cumulative_turbine_mw'][y] = int(e.get('n_turbine', 0)) * TURBINE_MW
        phased['cumulative_bess_mwh'][y] = float(e.get('bess_mwh', 0))
        phased['cumulative_solar_mw'][y] = float(e.get('solar_mw', 0))
        phased['grid_mw'][y] = float(e.get('grid_mw', 0))
    
    # ==========================================================================
    # POWER COVERAGE
    # ==========================================================================
    coverage = solution.get('power_coverage', {})
    final_cov = coverage.get(final_year, {})
    
    coverage_pct = final_cov.get('coverage_pct', 100)
    power_gap_mw = final_cov.get('power_gap_mw', 0)
    unserved_mwh = final_cov.get('unserved_mwh', 0)
    is_fully_served = final_cov.get('is_fully_served', True)
    
    # ==========================================================================
    # EMISSIONS & GAS
    # ==========================================================================
    emissions = solution.get('emissions', {})
    final_em = emissions.get(final_year, {})
    nox_tpy = final_em.get('nox_tpy', 0)
    nox_limit = constraints.get('NOx_Limit_tpy', 100)
    
    gas = solution.get('gas_usage', {})
    final_gas = gas.get(final_year, {})
    avg_mcf = final_gas.get('avg_daily_mcf', 0)
    gas_limit = constraints.get('Gas_Supply_MCF_day', 75000)
    
    # ==========================================================================
    # TIMELINE
    # ==========================================================================
    first_deploy = None
    for y in sorted(years):
        e = solution.get('equipment', {}).get(y, {})
        if e.get('n_recip', 0) > 0 or e.get('n_turbine', 0) > 0 or e.get('solar_mw', 0) > 0:
            first_deploy = y
            break
    
    if first_deploy:
        timeline_months = max(24, (final_year - first_deploy + 1) * 12)
    else:
        timeline_months = 72
    
    timeline_months = min(timeline_months, 120)
    
    # ==========================================================================
    # VIOLATIONS
    # ==========================================================================
    violations = []
    if power_gap_mw > 1:
        violations.append(f"Power gap: {power_gap_mw:.1f} MW")
    if nox_tpy > nox_limit:
        violations.append(f"NOx exceeded: {nox_tpy:.1f} > {nox_limit} tpy")
    
    # ==========================================================================
    # BUILD COMPLETE RESULT
    # ==========================================================================
    return {
        'feasible': True,
        'violations': violations,
        'warnings': [],
        
        'equipment_config': {
            'n_recip': n_recip,
            'n_turbine': n_turbine,
            'recip_mw': recip_mw,
            'turbine_mw': turbine_mw,
            'bess_mwh': bess_mwh,
            'bess_mw': bess_mw,
            'solar_mw': solar_mw,
            'grid_mw': grid_mw,
            'grid_active': grid_active,
            'total_capacity_mw': total_capacity_mw,
            'solar_mw_dc': solar_mw,
            'grid_import_mw': grid_mw,
            'recip_engines': [{'capacity_mw': RECIP_MW}] * n_recip,
            'gas_turbines': [{'capacity_mw': TURBINE_MW}] * n_turbine,
            'bess': [{'energy_mwh': bess_mwh, 'power_mw': bess_mw}] if bess_mwh > 0 else [],
            '_phased_deployment': phased,
        },
        
        'economics': {
            'lcoe_mwh': lcoe_mwh,
            'total_capex_m': total_capex_m,
            'annual_opex_m': annual_opex_m,
            'annual_fuel_cost_m': annual_fuel_cost_m,      # WAS MISSING!
            'annual_generation_gwh': annual_gen_gwh,       # WAS MISSING!
            'capacity_factor_pct': capacity_factor_pct,    # WAS MISSING!
        },
        
        'power_coverage': {
            'final_coverage_pct': coverage_pct,
            'power_gap_mw': power_gap_mw,
            'unserved_mwh': unserved_mwh,
            'is_fully_served': is_fully_served,
            'by_year': coverage,
        },
        
        'emissions': {
            'nox_tpy': nox_tpy,
            'nox_limit_tpy': nox_limit,
            'nox_utilization_pct': (nox_tpy / nox_limit * 100) if nox_limit > 0 else 0,
            'by_year': emissions,
        },
        
        'gas_usage': {
            'avg_daily_mcf': avg_mcf,
            'gas_limit_mcf_day': gas_limit,
            'gas_utilization_pct': (avg_mcf / gas_limit * 100) if gas_limit > 0 else 0,
            'by_year': gas,
        },
        
        'timeline': {
            'timeline_months': timeline_months,
            'timeline_years': timeline_months / 12,
            'critical_path': 'MILP Optimized',
            'deployment_speed': 'Fast' if timeline_months <= 24 else 'Medium' if timeline_months <= 48 else 'Slow',
        },
        
        'dr_metrics': {
            'total_dr_mw': 0,
        },
        
        'metrics': {
            'nox_tpy': nox_tpy,
            'gas_mcf_day': avg_mcf,
            'coverage_pct': coverage_pct,
            'total_capacity_mw': total_capacity_mw,
        },
        
        'score': 100 if is_fully_served else max(0, coverage_pct),
    }



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
