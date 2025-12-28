"""
Optimizer Backend
Wrapper functions to run heuristic and MILP optimizations
"""

from typing import Dict, Optional
from datetime import datetime
import traceback


def _build_equipment_details(equipment_config: Dict) -> Dict:
    """
    Build detailed equipment metadata from MW totals.
    
    Uses unit sizes from config/settings.py and electrical/reliability specs
    from config/equipment_electrical_specs.py to provide complete equipment metadata
    for integration export (ETAP, PSS/e, Windchill RAM).
    
    Args:
        equipment_config: Dict with MW totals (recip_mw, turbine_mw, etc.)
    
    Returns:
        Dict with equipment_details for each type including:
        - count: Number of units
        - unit_mw: MW per unit
        - electrical_specs: Impedances, time constants, inertia
        - reliability_specs: MTBF, MTTR, failure modes
    
    ⚠️ ASSUMPTIONS:
    - Unit sizes from EQUIPMENT_DEFAULTS (18.3 MW recip, 50 MW turbine)
    - Electrical parameters from IEEE standards (not actual datasheets)
    - Reliability from IEEE 493 generic values (not site-specific)
    """
    try:
        from config.equipment_electrical_specs import get_equipment_details, UNIT_SIZES
    except ImportError:
        # Fallback if spec library not available
        return _build_equipment_details_fallback(equipment_config)
    
    details = {}
    
    # Reciprocating engines
    recip_mw = equipment_config.get('recip_mw', 0)
    if recip_mw > 0:
        details['recip'] = get_equipment_details('recip', recip_mw)
    
    # Gas turbines
    turbine_mw = equipment_config.get('turbine_mw', 0)
    if turbine_mw > 0:
        details['turbine'] = get_equipment_details('turbine', turbine_mw)
    
    # BESS
    bess_mwh = equipment_config.get('bess_mwh', 0)
    if bess_mwh > 0:
        # BESS stored as MWh, convert to MW assuming 4hr duration
        # ASSUMPTION: 4-hour duration unless specified otherwise
        bess_mw = bess_mwh / 4.0
        details['bess'] = get_equipment_details('bess', bess_mw)
        details['bess']['energy_mwh'] = bess_mwh
        details['bess']['duration_hours'] = 4.0  # ASSUMPTION
    
    # Solar
    solar_mw = equipment_config.get('solar_mw', 0)
    if solar_mw > 0:
        # Solar doesn't need detailed electrical specs (not synchronous)
        details['solar'] = {
            'total_mw': solar_mw,
            'technology': 'photovoltaic',
            'note': 'No synchronous machine parameters - inverter-based resource'
        }
    
    # Grid connection
    grid_mw = equipment_config.get('grid_mw', 0)
    if grid_mw > 0:
        details['grid'] = {
            'total_mw': grid_mw,
            'note': 'Modeled as infinite bus in ETAP/PSS/e'
        }
    
    return details


def _build_equipment_details_fallback(equipment_config: Dict) -> Dict:
    """
    Fallback equipment details if electrical specs library not available.
    Uses only settings.py EQUIPMENT_DEFAULTS.
    """
    from config.settings import EQUIPMENT_DEFAULTS
    
    details = {}
    
    # Simple count calculation using standard unit sizes
    recip_mw = equipment_config.get('recip_mw', 0)
    if recip_mw > 0:
        unit_size = EQUIPMENT_DEFAULTS['recip']['capacity_mw']
        details['recip'] = {
            'count': round(recip_mw / unit_size),
            'unit_mw': unit_size,
            'total_mw': recip_mw,
            'note': 'Electrical specs not loaded - using minimal metadata'
        }
    
    turbine_mw = equipment_config.get('turbine_mw', 0)
    if turbine_mw > 0:
        unit_size = EQUIPMENT_DEFAULTS['turbine']['capacity_mw']
        details['turbine'] = {
            'count': round(turbine_mw / unit_size),
            'unit_mw': unit_size,
            'total_mw': turbine_mw
        }
    
    bess_mwh = equipment_config.get('bess_mwh', 0)
    if bess_mwh > 0:
        power_mw = EQUIPMENT_DEFAULTS['bess']['power_mw']
        duration_hr = EQUIPMENT_DEFAULTS['bess']['duration_hours']
        details['bess'] = {
            'count': round(bess_mwh / (power_mw * duration_hr)),
            'unit_mw': power_mw,
            'unit_mwh': power_mw * duration_hr,
            'total_mwh': bess_mwh
        }
    
    return details


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
            # Brownfield: Assume existing facility at current LCOE
            existing_equipment = {
                'recip_mw': site_data.get('it_capacity_mw', 500) * 0.5 * site_data.get('pue', 1.25),  # Assume 50% recip
                'existing_lcoe': 60  # Assume existing LCOE is $60/MWh (allows expansion to $80)
            }
            optimizer = BrownfieldHeuristic(site, load_trajectory, constraints, 
                                          existing_equipment=existing_equipment,
                                          lcoe_threshold=80.0)
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
            
            # ===NEW: Equipment Details with counts, electrical specs, reliability ===
            # Provides complete metadata for integration export (ETAP, PSS/e, Windchill RAM)
            'equipment_details': _build_equipment_details(
                getattr(result, 'equipment_config', {}) if not isinstance(result, dict) else result.get('equipment_config', {})
            ),
            
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
