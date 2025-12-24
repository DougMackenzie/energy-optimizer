#!/usr/bin/env python3
"""
Quick diagnostic to check why MILP is returning infeasible for all scenarios.
Tests the exact same data flow as the Streamlit app.
"""

import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

from sample_problem_600mw import get_sample_problem
from app.utils.site_loader import load_scenario_templates
from app.utils.multi_scenario import run_all_scenarios

# Load the 600MW sample problem (same as session_init.py does)
problem = get_sample_problem()
site = problem['site']
constraints = {
    **problem['constraints'],
    'N_Minus_1_Required': False  # Same as session_init.py
}
load_profile_dr = problem['load_profile']

# Load scenarios
scenarios = load_scenario_templates()

# Define objectives (same as page_09_results.py)
objectives = {
    'Primary_Objective': 'Minimize_LCOE',
    'LCOE_Max_MWh': 100,
    'Deployment_Max_Months': 36,
}

print("=" * 80)
print("DIAGNOSTIC: Testing MILP with exact session_init.py data")
print("=" * 80)
print(f"\nSite: {site.get('site_name', 'Unknown')}")
print(f"Peak IT MW: {load_profile_dr.get('peak_it_mw', 'NOT SET')}")
print(f"PUE: {load_profile_dr.get('pue', 'NOT SET')}")
print(f"N_Minus_1_Required: {constraints.get('N_Minus_1_Required', 'NOT SET')}")
print(f"Number of scenarios: {len(scenarios)}")
print(f"\nScenarios:")
for s in scenarios:
    print(f"  - {s.get('Scenario_Name', 'Unknown')}")

print(f"\nCalling run_all_scenarios with use_milp=True...")
print("=" * 80)

# Run optimization (use_milp defaults to True now)
results = run_all_scenarios(
    site=site,
    constraints=constraints,
    objectives=objectives,
    scenarios=scenarios,
    grid_config=None,
    use_milp=True,
    load_profile_dr=load_profile_dr
)

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
for i, result in enumerate(results):
    print(f"\n[{i+1}] {result.get('scenario_name', 'Unknown')}")
    print(f"    Feasible: {result.get('feasible', False)}")
    if not result.get('feasible'):
        violations = result.get('violations', [])
        print(f"    Violations: {violations[:3]}")  # Show first 3
    else:
        econ = result.get('economics', {})
        print(f"    LCOE: ${econ.get('lcoe_mwh', 0):.2f}/MWh")
        print(f"    CAPEX: ${econ.get('total_capex_m', 0):.1f}M")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
