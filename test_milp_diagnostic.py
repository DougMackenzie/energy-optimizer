#!/usr/bin/env python3
"""
MILP Diagnostic Test
Tests basic MILP optimization with the 600MW sample problem
"""

from sample_problem_600mw import get_sample_problem
from app.utils.milp_optimizer_wrapper import optimize_with_milp
import json

print("=" * 70)
print("MILP DIAGNOSTIC TEST")
print("=" * 70)

print('\n📥 Loading 600MW sample problem...')
problem = get_sample_problem()

print(f'\n📊 Load Profile:')
print(f'  Peak IT: {problem["load_profile"]["peak_it_mw"]} MW')
print(f'  PUE: {problem["load_profile"]["pue"]}')
print(f'  Peak Facility: {problem["load_profile"]["peak_facility_mw"]} MW')

print(f'\n📈 Load Trajectory:')
for year, mw in sorted(problem["load_profile"]["load_trajectory"].items()):
    print(f'  {year}: {mw} MW')

print(f'\n🚧 Constraints:')
print(f'  NOx Limit: {problem["constraints"]["NOx_Limit_tpy"]} tpy')
print(f'  Gas Supply: {problem["constraints"]["Gas_Supply_MCF_day"]} MCF/day')
print(f'  Land: {problem["constraints"]["Available_Land_Acres"]} acres')

print('\n🎯 Running MILP optimization (BTM Only - Recip + BESS)...')

# Ensure workload_mix is in load_profile_dr
load_profile = problem['load_profile'].copy()
if 'workload_mix' not in load_profile:
    load_profile['workload_mix'] = problem['load_profile']['workload_mix']

result = optimize_with_milp(
    site=problem['site'],
    constraints=problem['constraints'],
    load_profile_dr=load_profile,
    years=problem['years'],
    scenario={
        'Recip_Enabled': True,
        'Turbine_Enabled': False,
        'BESS_Enabled': True,
        'Solar_Enabled': False,
        'Grid_Enabled': False
    }
)

print(f'\n📋 RESULTS:')
print(f'  Status: {result.get("status")}')
print(f'  Solver Status: {result.get("solver_status")}')
print(f'  Feasible: {result.get("feasible")}')

if not result.get('feasible'):
    print(f'\n❌ INFEASIBLE!')
    print(f'  Error: {result.get("error_message")}')
    
    # Check for constraint violations
    if 'constraint_violations' in result:
        print(f'\n  Constraint Violations:')
        for violation in result['constraint_violations']:
            print(f'    - {violation}')
else:
    print(f'\n✅ FEASIBLE!')
    print(f'\n💰 Economics:')
    print(f'  LCOE: ${result["economics"]["lcoe_mwh"]:.2f}/MWh')
    print(f'  CAPEX: ${result["economics"]["total_capex_m"]:.1f}M')
    
    print(f'\n🔧 Capacity:')
    print(f'  Total: {result.get("total_capacity_mw", "N/A")} MW')
    print(f'  Recips: {result.get("n_recip", 0)} units ({result.get("recip_mw", 0)} MW)')
    print(f'  BESS: {result.get("bess_mwh", 0)} MWh')
    
    print(f'\n⚡ Deployment:')
    if 'phased_deployment' in result:
        for year, data in sorted(result.get('phased_deployment', {}).items()):
            if data.get('capacity_mw', 0) > 0:
                print(f'  {year}: {data["capacity_mw"]} MW')
    else:
        print(f'  Equipment deployed across planning horizon')

print("\n" + "=" * 70)
