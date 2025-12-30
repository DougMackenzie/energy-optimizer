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
    # PROMINENT DEBUG OUTPUT
    print("\n" + "=" * 80)
    print("🚀 RUN_HEURISTIC_OPTIMIZATION CALLED")
    print(f"   Site: {site_data.get('name', 'Unknown')}")
    print(f"   Problem: {problem_num}")
    print(f"   Facility MW: {site_data.get('facility_mw', 'N/A')}")
    print(f"   Has load_trajectory_json: {'load_trajectory_json' in site_data}")
    print("=" * 80 + "\n")
    
    try:
        # Import v2.1.1 optimizer via __init__.py for Problem 1
        from app.optimization import GreenfieldHeuristicV2
        
        # Import legacy optimizers for other problems
        from app.optimization.heuristic_optimizer import (
            BrownfieldHeuristic, LandDevHeuristic,
            GridServicesHeuristic, BridgePowerHeuristic
        )
        from config.settings import CONSTRAINT_DEFAULTS, EQUIPMENT_DEFAULTS, ECONOMIC_DEFAULTS
        import json
        
        # Connect to backend for v2.1.1
        import gspread
        try:
            gc = gspread.service_account(filename='credentials.json')
            from config.settings import GOOGLE_SHEET_ID
            spreadsheet_id = GOOGLE_SHEET_ID
        except Exception as e:
            print(f"Warning: Could not connect to backend: {e}")
            gc = None
            spreadsheet_id = None
        
        # Prepare site parameters
        site = {
            'name': site_data.get('name'),
            'location': site_data.get('location'),
            'iso': site_data.get('iso')
        }
        
        # EMERGENCY FIX: Load missing data from Load_Profiles if not in site dict
        site_name = site_data.get('name')
        needs_load_trajectory = not site_data.get('load_trajectory_json')
        needs_grid_params = not site_data.get('grid_available_year') or not site_data.get('grid_capacity_mw')
        
        if needs_load_trajectory or needs_grid_params:
            if needs_load_trajectory:
                print(f"⚠️ load_trajectory_json MISSING for {site_name}")
            if needs_grid_params:
                print(f"⚠️ Grid parameters MISSING for {site_name}")
            try:
                import gspread
                from config.settings import GOOGLE_SHEET_ID
                gc_emergency = gspread.service_account(filename='credentials.json')
                spreadsheet = gc_emergency.open_by_key(GOOGLE_SHEET_ID)
                profiles_ws = spreadsheet.worksheet("Load_Profiles")
                profiles_data = profiles_ws.get_all_records()
                
                for profile in profiles_data:
                    if profile.get('site_name') == site_name:
                        # Load trajectory if missing
                        if needs_load_trajectory:
                            site_data['load_trajectory_json'] = profile.get('load_trajectory_json', '')
                        
                        # ALWAYS load grid parameters from Load_Profiles
                        site_data['grid_available_year'] = profile.get('grid_available_year')
                        site_data['grid_capacity_mw'] = profile.get('grid_capacity_mw')
                        site_data['flexibility_pct'] = profile.get('flexibility_pct', 30.6)
                        
                        print(f"✓ Loaded for {site_name}: grid_year={site_data.get('grid_available_year')}, grid_cap={site_data.get('grid_capacity_mw')} MW")
                        if needs_load_trajectory:
                            print(f"✓ Loaded trajectory: {site_data.get('load_trajectory_json', '')[:50]}...")
                        break
            except Exception as e:
                print(f"Failed to load profile: {e}")
        
        # Read load trajectory from backend (for v2.1.1)
        # Define load_mw first for later use (lines 316-318)
        load_mw = site_data.get('facility_mw', 500)
        
        load_trajectory = {}
        if 'load_trajectory_json' in site_data and site_data['load_trajectory_json']:
            try:
                traj_data = json.loads(site_data['load_trajectory_json'])
                # Convert string keys to int years
                load_trajectory = {int(k): float(v) for k, v in traj_data.items()}
                print(f"✓ Loaded trajectory from backend: {load_trajectory}")
            except Exception as e:
                print(f"Warning: Could not parse load_trajectory_json: {e}")
                load_trajectory = {}
        
        # Fallback to single year if no trajectory
        if not load_trajectory:
            # Use current year as baseline
            from datetime import datetime as dt
            current_year = dt.now().year
            load_trajectory = {current_year: load_mw}
            print(f"⚠ Using fallback single-year trajectory: {load_trajectory}")
        
        # Prepare constraints from site data (including grid params for v2.1.1)
        constraints = {
            'nox_tpy_annual': site_data.get('nox_limit_tpy', 100),
            'gas_supply_mcf_day': site_data.get('gas_supply_mcf', 150000) / 365,  # Convert annual to daily
            'land_area_acres': site_data.get('land_acres', 400),
            'n_minus_1_required': True,
            'min_availability_pct': 99.5,
        }
        
        # Add grid configuration for v2.1.1
        if 'grid_available_year' in site_data and site_data.get('grid_available_year'):
            constraints['grid_available_year'] = int(site_data['grid_available_year'])
            print(f"✓ Grid available year: {constraints['grid_available_year']}")
        
        if 'grid_capacity_mw' in site_data and site_data.get('grid_capacity_mw'):
            constraints['grid_capacity_mw'] = float(site_data['grid_capacity_mw'])
            print(f"✓ Grid capacity: {constraints['grid_capacity_mw']} MW")
        
        if 'grid_lead_time_months' in site_data and site_data.get('grid_lead_time_months'):
            constraints['grid_lead_time_months'] = int(site_data['grid_lead_time_months'])
        
        # Read workload mix from backend (for v2.1.1)
        load_profile_data = {}
        if 'flexibility_pct' in site_data:
            load_profile_data['flexibility_pct'] = float(site_data.get('flexibility_pct', 30.6))
            workload_mix = {}
            if 'pre_training_pct' in site_data:
                workload_mix['pre_training'] = float(site_data.get('pre_training_pct', 45.0))
            if 'fine_tuning_pct' in site_data:
                workload_mix['fine_tuning'] = float(site_data.get('fine_tuning_pct', 20.0))
            if 'batch_inference_pct' in site_data:
                workload_mix['batch_inference'] = float(site_data.get('batch_inference_pct', 15.0))
            if 'real_time_inference_pct' in site_data:
                workload_mix['real_time_inference'] = float(site_data.get('real_time_inference_pct', 20.0))
            
            if workload_mix:
                load_profile_data['workload_mix'] = workload_mix
                print(f"✓ Workload mix: {workload_mix}")
        
        # Select optimizer based on problem number
        if problem_num == 1:
            # Use Greenfield Heuristic v2.1.1 with backend integration
            print("Using GreenfieldHeuristicV2 with backend integration")
            optimizer = GreenfieldHeuristicV2(
                site=site,
                load_trajectory=load_trajectory,
                constraints=constraints,
                sheets_client=gc,
                spreadsheet_id=spreadsheet_id,
                load_profile_data=load_profile_data
            )
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
        print("\n" + "="*80)
        print("🔧 CALLING optimizer.optimize()")
        print("="*80)
        import time
        start_time = time.time()
        
        result = optimizer.optimize()
        
        end_time = time.time()
        actual_runtime = end_time - start_time
        print("="*80)
        print(f"✅ optimizer.optimize() RETURNED")
        print(f"⏱  Actual execution time: {actual_runtime:.2f} seconds")
        print(f"📊 Result type: {type(result)}")
        if hasattr(result, 'solve_time_seconds'):
            print(f"🕐 Result.solve_time_seconds: {result.solve_time_seconds:.2f}s")
        elif isinstance(result, dict) and 'runtime_seconds' in result:
            print(f"🕐 Result runtime_seconds: {result.get('runtime_seconds')}s")
        print("="*80 + "\n")
        
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
            
            # === NEW FIELDS FOR CHART INTEGRATION ===
            # Equipment by year (from v2.1.1 optimizer)
            'equipment_by_year': getattr(result, 'equipment_by_year', None) if not isinstance(result, dict) else result.get('equipment_by_year'),
            
            # Dispatch by year (actual hourly dispatch for charts)
            'dispatch_by_year': getattr(result, 'dispatch_by_year', None) if not isinstance(result, dict) else result.get('dispatch_by_year'),
            
            # Load trajectory (from backend)
            'load_trajectory': load_trajectory,
            
            # Constraints (for chart to respect grid_available_year)
            'constraints': {
                'grid_available_year': constraints.get('grid_available_year'),
                'grid_capacity_mw': constraints.get('grid_capacity_mw', 0),
                'nox_tpy_annual': constraints.get('nox_tpy_annual'),
                'gas_supply_mcf_day': constraints.get('gas_supply_mcf_day'),
                'land_area_acres': constraints.get('land_area_acres'),
            },
            
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
