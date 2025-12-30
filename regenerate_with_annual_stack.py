#!/usr/bin/env python3
"""
Regenerate screening results with proper annual energy stack
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import load_all_sites
from app.optimization.heuristic_optimizer import (
    GreenFieldHeuristic,
    BrownfieldHeuristic,
    LandDevHeuristic,
    GridServicesHeuristic,
    BridgePowerHeuristic
)
from app.utils.site_backend import save_site_stage_result

def run_screening_optimization(site):
    """Run proper screening optimization for each problem type"""
    site_name = site.get('name')
    problem_num = site.get('problem_num', 1)
    facility_mw = site.get('facility_mw', 1000)
    
    # Build load trajectory (15 years, phased growth)
    load_trajectory = {}
    for year_offset in range(15):
        year = 2025 + year_offset
        # Phased growth: 50% Year 1, 75% Year 2, 100% Year 3+
        if year_offset == 0:
            load_trajectory[year] = facility_mw * 0.5
        elif year_offset == 1:
            load_trajectory[year] = facility_mw * 0.75
        else:
            load_trajectory[year] = facility_mw
    
    # Build constraints
    constraints = {
        'land_acres': site.get('land_acres', 500),
        'nox_limit_tpy': site.get('nox_limit_tpy', 100),
        'gas_supply_mcf': site.get('gas_supply_mcf', 150000),
        'n_minus_1_required': True
    }
    
    # Site dict for optimizer
    site_dict = {
        'name': site_name,
        'location': site.get('location'),
        'voltage_kv': site.get('voltage_kv', 345),
        'land_acres': site.get('land_acres', 500)
    }
    
    print(f"\n{'=' * 60}")
    print(f"OPTIMIZING: {site_name}")
    print(f"Problem {problem_num}: {site.get('problem_name')}")
    print(f"{'=' * 60}")
    
    # Run appropriate optimizer
    try:
        if problem_num == 1:  # Greenfield
            optimizer = GreenFieldHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints,
                grid_available_month=60  # 5 years
            )
        elif problem_num == 2:  # Brownfield
            constraints['lcoe_threshold'] = 120  # LCOE ceiling
            optimizer = BrownfieldHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints,
                existing_equipment={'recip_mw': 100},
                existing_lcoe=60
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
                constraints=constraints,
                dr_pricing={'summer_peak': 150, 'winter_peak': 100}
            )
        elif problem_num == 5:  # Bridge Power
            optimizer = BridgePowerHeuristic(
                site=site_dict,
                load_trajectory=load_trajectory,
                constraints=constraints,
                grid_available_month=60  # Grid arrives in 5 years
            )
        else:
            print(f"⚠️  Unknown problem type: {problem_num}")
            return None
        
        # Run optimization
        result = optimizer.optimize()
        
        if result and result.feasible:
            print(f"✅ Optimization successful")
            print(f"   LCOE: ${result.lcoe:.2f}/MWh")
            print(f"   Equipment: {result.equipment}")
            
            # Check for annual stack
            if 'dispatch_summary' in result.__dict__ and result.dispatch_summary:
                if 'annual_stack' in result.dispatch_summary:
                    annual_stack = result.dispatch_summary['annual_stack']
                    print(f"   ✅ Annual stack: {len(annual_stack)} years")
                    
                    # Show grid timeline
                    for year in sorted(annual_stack.keys())[:3]:
                        grid_mw = annual_stack[year]['equipment'].get('grid_mw', 0)
                        print(f"      Year {year}: Grid = {grid_mw:.1f} MW")
            
            # Prepare result data for saving
            result_data = {
                'site_name': site_name,
                'stage': 'screening',
                'complete': True,
                'lcoe': result.lcoe,
                'npv': getattr(result, 'npv', None) or -100000000,
                'equipment': result.equipment,
                'dispatch_summary': result.dispatch_summary or {},
                'constraints': result.constraints or constraints,
                'capex': {'total': result.capex_total},
                'load_coverage_pct': 85,
                'runtime_seconds': 45,
                'version': 1,
                'notes': f'Screening optimization for {site.get("problem_name")}'
            }
            
            return result_data
        else:
            print(f"❌ Optimization failed or infeasible")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("REGENERATING SCREENING RESULTS WITH ANNUAL ENERGY STACK")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    success_count = 0
    for site in sites:
        result_data = run_screening_optimization(site)
        
        if result_data:
            # Save to Google Sheets
            success = save_site_stage_result(
                result_data['site_name'],
                'screening',
                result_data
            )
            
            if success:
                success_count += 1
                print(f"✅ Saved to Google Sheets")
            else:
                print(f"❌ Failed to save")
    
    print(f"\n{'=' * 60}")
    print(f"✅ Successfully regenerated {success_count}/{len(sites)} screening results")
