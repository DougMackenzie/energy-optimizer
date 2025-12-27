"""
Optimizer Backend
Wrapper functions to run heuristic and MILP optimizations
"""

from typing import Dict, Optional
from datetime import datetime
import traceback


def run_heuristic_optimization(site_data: Dict, problem_num: int, load_profile: Dict = None) -> Optional[Dict]:
    """
    Run heuristic optimization for a site
    
    Args:
        site_data: Site configuration dict
        problem_num: Problem number (1-5)
        load_profile: Load profile data (optional)
    
    Returns:
        Result dict with equipment, costs, metrics, etc.
    """
    try:
        from app.optimization.heuristic_optimizer import (
            GreenFieldHeuristic, BrownfieldHeuristic, LandDevHeuristic,
            GridServicesHeuristic, BridgePowerHeuristic
        )
        from config.settings import CONSTRAINT_DEFAULTS, EQUIPMENT_DEFAULTS, ECONOMIC_DEFAULTS
        
        # Prepare site parameters
        site = {
            'name': site_data.get('name'),
            'location': site_data.get('location'),
            'iso': site_data.get('iso')
        }
        
        # Prepare load trajectory (single year for heuristic)
        load_mw = site_data.get('facility_mw', 500)
        load_trajectory = {0: load_mw}  # Year 0
        
        # Prepare constraints from site data
        constraints = {
            'nox_tpy_annual': site_data.get('nox_limit_tpy', 100),
            'gas_supply_mcf_day': site_data.get('gas_supply_mcf', 150000) / 365,  # Convert annual to daily
            'land_area_acres': site_data.get('land_acres', 400),
            'n_minus_1_required': True,
            'min_availability_pct': 99.5
        }
        
        # Select optimizer based on problem number
        if problem_num == 1:
            optimizer = GreenFieldHeuristic(site, load_trajectory, constraints)
        elif problem_num == 2:
            optimizer = BrownfieldHeuristic(site, load_trajectory, constraints, lcoe_ceiling=80.0)
        elif problem_num == 3:
            optimizer = LandDevHeuristic(site, load_trajectory, constraints)
        elif problem_num == 4:
            optimizer = GridServicesHeuristic(site, load_trajectory, constraints)
        elif problem_num == 5:
            optimizer = BridgePowerHeuristic(site, load_trajectory, constraints)
        else:
            raise ValueError(f"Unknown problem number: {problem_num}")
        
        # Run optimization
        result = optimizer.optimize()
        
        # Accept result even if heuristic marks it "infeasible" due to constraint violations
        # We'll report coverage % and unserved load instead of rejecting it
        if not result:
            return {
                'feasible': False,
                'error': 'Optimizer returned no result',
                'violations': ['Unknown error']
            }
        
        # Convert result to dict format for storage
        result_dict = {
            'site_name': site['name'],
            'problem_type': f'P{problem_num}',
            'stage': 'screening',
            'version': 1,
            'solver': 'heuristic',
            'run_timestamp': datetime.now().isoformat(),
            'runtime_seconds': getattr(result, 'solve_time_seconds', 0) if not isinstance(result, dict) else result.get('runtime_seconds', 0),
            'feasible': True,  # Always mark as feasible - report coverage instead
            
            # Key metrics
            'lcoe': getattr(result, 'lcoe', 0) if not isinstance(result, dict) else result.get('lcoe', 0),
            'npv': -getattr(result, 'capex_total', 0) if not isinstance(result, dict) else -result.get('capex_total', 0),  # Simplified NPV
            'irr': 0.08,  # Placeholder
            'payback_years': (getattr(result, 'capex_total', 0) if not isinstance(result, dict) else result.get('capex_total', 0)) / (
                (getattr(result, 'opex_annual', 1) if not isinstance(result, dict) else result.get('opex_annual', 1)) * 0.1
            ) if (getattr(result, 'opex_annual', 0) if not isinstance(result, dict) else result.get('opex_annual', 0)) > 0 else 15,
            
            # Equipment (MW/MWh)
            'equipment': getattr(result, 'equipment_config', {}) if not isinstance(result, dict) else result.get('equipment_config', {}),
            
            # Capital costs ($ - use totals from heuristic)
            'capex': {
                'total': getattr(result, 'capex_total', 0) if not isinstance(result, dict) else result.get('capex_total', 0)
            },
            
            # Operating costs
            'opex_annual': {
                'total': getattr(result, 'opex_annual', 0) if not isinstance(result, dict) else result.get('opex_annual', 0)
            },
            
            # Constraints
            'constraints': getattr(result, 'constraint_status', {}) if not isinstance(result, dict) else result.get('constraint_status', {}),
            
            # Coverage
            'load_coverage_pct': min(100, (sum([
                (getattr(result, 'equipment_config', {}) if not isinstance(result, dict) else result.get('equipment_config', {})).get('recip_mw', 0),
                (getattr(result, 'equipment_config', {}) if not isinstance(result, dict) else result.get('equipment_config', {})).get('turbine_mw', 0),
                (getattr(result, 'equipment_config', {}) if not isinstance(result, dict) else result.get('equipment_config', {})).get('solar_mw', 0)
            ]) / load_mw * 100)) if load_mw > 0 else 0,
            'avg_load_mw': load_mw * 0.8,
            'peak_load_mw': load_mw,
            
            # Additional
            'warnings': getattr(result, 'warnings', []) if not isinstance(result, dict) else result.get('warnings', []),
            'user_notes': f'Heuristic optimization - {getattr(result, "solve_time_seconds", 0) if not isinstance(result, dict) else result.get("runtime_seconds", 0):.1f}s runtime'
        }
        
        return result_dict
        
    except Exception as e:
        print(f"Error in heuristic optimization: {e}")
        traceback.print_exc()
        return {
            'feasible': False,
            'error': str(e),
            'violations': [str(e)]
        }


def run_milp_optimization(site_data: Dict, problem_num: int, load_profile: Dict = None) -> Optional[Dict]:
    """
    Run MILP optimization for a site
    
    Args:
        site_data: Site configuration dict
        problem_num: Problem number (1-5)
        load_profile: Load profile data (optional)
    
    Returns:
        Result dict with equipment, costs, metrics, etc.
    """
    # Placeholder for MILP - to be implemented
    return {
        'feasible': False,
        'error': 'MILP optimization not yet implemented',
        'violations': ['Feature coming soon']
    }
