#!/usr/bin/env python3
"""
Test Fast Wrapper with Standard Model
Verifies that using CBC solver + fast settings with standard model works
"""

import numpy as np
from app.utils.milp_optimizer_wrapper_fast import optimize_with_milp

print("=" * 60)
print("FAST WRAPPER TEST (Standard Model + CBC)")
print("=" * 60)

# Test configuration  
peak_it_mw = 160
pue = 1.25
load_factor = 0.75
base_load = peak_it_mw * pue * load_factor

# Generate load profile
load_8760 = base_load * (1 + 0.1 * np.sin(2 * np.pi * np.arange(8760) / 24))
load_8760 = np.maximum(load_8760, base_load * 0.7)

load_profile_dr = {
    'peak_it_mw': peak_it_mw,
    'pue': pue,
    'load_factor': load_factor,
    'load_data': {
        'total_load_mw': load_8760.tolist(),
        'pue': pue
    },
    'workload_mix': {
        'pre_training': 0.30,
        'fine_tuning': 0.20,
        'batch_inference': 0.30,
        'realtime_inference': 0.20
    },
    'cooling_flex': 0.25
}

constraints = {
    'NOx_Limit_tpy': 99,
    'Gas_Supply_MCF_day': 50000,
    'Available_Land_Acres': 1000,
    'grid_available_year': 2030
}

site = {'name': 'Test Site'}
years = list(range(2026, 2036))

# Test scenarios
scenarios = [
    {'Scenario_Name': 'BTM Only', 'Grid_Enabled': False},
    {'Scenario_Name': 'All Technologies', 'Grid_Enabled': True},
]

print(f"\nTesting {len(scenarios)} scenarios...")
print(f"Using: Standard MILP Model + CBC Solver + Fast Settings")
print(f"Load: {base_load:.1f} MW base")

results = []

for idx, scenario in enumerate(scenarios):
    print(f"\n[{idx+1}/{len(scenarios)}] {scenario['Scenario_Name']}")
    print("-" * 60)
    
    try:
        result = optimize_with_milp(
            site=site,
            constraints=constraints,
            load_profile_dr=load_profile_dr,
            years=years,
            solver='cbc',
            time_limit=60,
            scenario=scenario
        )
        
        if result['feasible']:
            print(f"  ✅ FEASIBLE!")
            print(f"    LCOE: ${result['economics']['lcoe_mwh']:.2f}/MWh")
            print(f"    Coverage: {result['power_coverage']['final_coverage_pct']:.1f}%")
            print(f"    Total Cap: {result['equipment_config']['total_capacity_mw']:.1f} MW")
            results.append({'scenario': scenario['Scenario_Name'], 'feasible': True})
        else:
            print(f"  ❌ INFEASIBLE")
            print(f"    Violations: {result['violations']}")
            results.append({'scenario': scenario['Scenario_Name'], 'feasible': False})
    
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append({'scenario': scenario['Scenario_Name'], 'feasible': False})

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

feasible_count = sum(1 for r in results if r['feasible'])
print(f"\nFeasible scenarios: {feasible_count}/{len(results)}")

for r in results:
    status = "✅" if r['feasible'] else "❌"
    print(f"  {status} {r['scenario']}")

if feasible_count == len(results):
    print("\n🎉 SUCCESS - Fast wrapper with standard model works!")
    print("Speed gains come from: CBC solver + 60s timeout + 5% MIP gap")
    exit(0)
else:
    print(f"\n⚠️ {len(results) - feasible_count} scenarios failed")
    exit(1)
