#!/usr/bin/env python3
"""
PROPER Regeneration: Run real optimizations with 15-year load trajectories
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import load_all_sites, save_site_stage_result
from app.optimization.heuristic_optimizer import (
    GreenFieldHeuristic,
    BrownfieldHeuristic,
    LandDevHeuristic,
    GridServicesHeuristic,
    BridgePowerHeuristic
)

def create_15_year_trajectory(facility_mw):
    """Create 15-year phased load trajectory"""
    trajectory = {}
    for year_offset in range(15):
        year = 2025 + year_offset
        if year_offset == 0:
            trajectory[year] = facility_mw * 0.5
        elif year_offset == 1:
            trajectory[year] = facility_mw * 0.75
        else:
            trajectory[year] = facility_mw
    return trajectory

def run_proper_optimization(site):
    """Run REAL optimization for each problem type"""
    site_name = site.get('name')
    problem_num = site.get('problem_num', 1)
    facility_mw = site.get('facility_mw', 1000)
    
    print(f"\n{'=' * 60}")
    print(f"OPTIMIZING: {site_name}")
    print(f"Problem {problem_num}: {site.get('problem_name')}")
    print(f"Facility: {facility_mw} MW")
    print(f"{'=' * 60}")
    
    # Create 15-year trajectory
    load_trajectory = create_15_year_trajectory(facility_mw)
    print(f"Load trajectory: {len(load_trajectory)} years")
    print(f"  Year 1: {load_trajectory[2025]:.0f} MW")
    print(f"  Year 3+: {load_trajectory[2027]:.0f} MW")
    
    # Build constraints
    constraints = {
        'land_acres': site.get('land_acres', 500),
        'nox_limit_tpy': site.get('nox_limit_tpy', 100),
        'gas_supply_mcf': site.get('gas_supply_mcf', 150000),
        'n_minus_1_required': True
    }
    
    # Site dict
    site_dict = {
        'name': site_name,
        'location': site.get('location'),
        'voltage_kv': site.get('voltage_kv', 345),
        'land_acres': site.get('land_acres', 500)
    }
    
    try:
        # Instantiate correct optimizer
        if problem_num == 1:  # Greenfield
            optimizer = GreenFieldHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints
            )
        elif problem_num == 2:  # Brownfield
            constraints['lcoe_threshold'] = 120
            optimizer = BrownfieldHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints
            )
        elif problem_num == 3:  # Land Dev
            optimizer = LandDevHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints
            )
        elif problem_num == 4:  # Grid Services
            optimizer = GridServicesHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints
            )
        elif problem_num == 5:  # Bridge Power
            optimizer = BridgePowerHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints,
                grid_available_month=60
            )
        else:
            print(f"Unknown problem: {problem_num}")
            return None
        
        # RUN OPTIMIZATION
        print(f"\n🔄 Running optimization...")
        result = optimizer.optimize()
        
        if not result or not result.feasible:
            print(f"❌ Infeasible or failed")
            return None
        
        print(f"✅ Optimization complete!")
        print(f"   LCOE: ${result.lcoe:.2f}/MWh")
        print(f"   Feasible: {result.feasible}")
        
        # Check for annual stack
        has_annual_stack = False
        if hasattr(result, 'dispatch_summary') and result.dispatch_summary:
            if 'annual_stack' in result.dispatch_summary:
                annual_stack = result.dispatch_summary['annual_stack']
                has_annual_stack = True
                print(f"   ✅ Annual stack: {len(annual_stack)} years")
                
                # Show grid timeline
                years_to_check = [2025, 2029, 2030, 2035, 2039]
                for year in years_to_check:
                    if year in annual_stack:
                        equip = annual_stack[year]['equipment']
                        grid_mw = equip.get('grid_mw', 0)
                        unserved = annual_stack[year].get('unserved_mwh', 0)
                        print(f"      {year}: Grid={grid_mw:.0f} MW, Unserved={unserved:.0f} MWh")
            else:
                print(f"   ⚠️  No annual_stack in dispatch_summary")
        else:
            print(f"   ⚠️  No dispatch_summary")
        
        if not has_annual_stack:
            print(f"   ❌ PROBLEM: Annual stack not generated!")
            print(f"      len(self.years) = {len(optimizer.years)}")
            return None
        
        # Prepare result data
        result_data = {
            'site_name': site_name,
            'stage': 'screening',
            'complete': True,
            'lcoe': result.lcoe,
            'npv': getattr(result, 'npv', -100000000),
            'equipment': result.equipment_config,
            'dispatch_summary': result.dispatch_summary,
            'constraints': result.constraint_status,
            'capex': {'total': result.capex_total},
            'load_coverage_pct': 100 - result.unserved_energy_pct,
            'runtime_seconds': result.solve_time_seconds,
            'version': 1,
            'notes': f'Screening with 15-year trajectory - {site.get("problem_name")}'
        }
        
        return result_data
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("PROPER REGENERATION: 15-YEAR TRAJECTORIES")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    results = []
    for site in sites:
        result_data = run_proper_optimization(site)
        
        if result_data:
            # Save to Google Sheets
            print(f"\n💾 Saving to Google Sheets...")
            success = save_site_stage_result(
                result_data['site_name'],
                'screening',
                result_data
            )
            
            if success:
                results.append(site.get('name'))
                print(f"✅ Saved successfully")
            else:
                print(f"❌ Failed to save")
        
        print("\n" + "=" * 60)
    
    print(f"\n\n{'=' * 60}")
    print(f"SUMMARY: {len(results)}/{len(sites)} sites completed")
    for name in results:
        print(f"  ✅ {name}")
    print(f"{'=' * 60}")
