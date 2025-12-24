#!/usr/bin/env python3
"""
Simulate the exact Streamlit session state initialization and MILP call
to diagnose why the UI shows infeasible but CLI shows feasible.
"""

import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

# Simulate what session_init.py does
print("=" * 80)
print("SIMULATING STREAMLIT SESSION INITIALIZATION")
print("=" * 80)

# Load exactly as session_init.py does
from app.utils.site_loader import load_sites, load_site_constraints, load_scenario_templates
from sample_problem_600mw import get_sample_problem

problem = get_sample_problem()
scenarios = load_scenario_templates()

# Create session_state dict (simulating st.session_state)
session_state = {}

# Set default config (exactly as session_init.py does)
session_state['current_config'] = {
    'site': problem['site'],
    'scenario': scenarios[1] if len(scenarios) > 1 else scenarios[0],  # All Technologies
    'constraints': {
        **problem['constraints'],
        'N_Minus_1_Required': False  # Ensure feasibility
    },
    'objectives': {
        'Primary_Objective': 'Minimize_LCOE',
        'LCOE_Max_MWh': 100,
        'Deployment_Max_Months': 36,
    },
    'equipment_enabled': {
        'recip': True, 'turbine': True, 'bess': True, 'solar': True, 'grid': True
    }
}

# Set Load Profile (CRITICAL for MILP)
session_state['load_profile_dr'] = problem['load_profile']

# Force Accurate Mode
session_state['use_fast_milp'] = False

print(f"\n✓ Initialized session_state with:")
print(f"  - Site: {session_state['current_config']['site'].get('site_name')}")
print(f"  - Peak IT MW: {session_state['load_profile_dr'].get('peak_it_mw')}")
print(f"  - PUE: {session_state['load_profile_dr'].get('pue')}")
print(f"  - N_Minus_1_Required: {session_state['current_config']['constraints'].get('N_Minus_1_Required')}")
print(f"  - use_fast_milp: {session_state['use_fast_milp']}")

# Now simulate what page_07_optimizer.py does
print("\n" + "=" * 80)
print("SIMULATING OPTIMIZER PAGE RUN_ALL_SCENARIOS CALL")
print("=" * 80)

from app.utils.multi_scenario import run_all_scenarios

# Get data from session_state (as page_07_optimizer.py does)
site = session_state['current_config']['site']
constraints = session_state['current_config']['constraints']
objectives = session_state['current_config']['objectives']
load_profile_dr = session_state['load_profile_dr']

print(f"\nCalling run_all_scenarios with:")
print(f"  - use_milp=True")
print(f"  - load_profile_dr peak_it_mw: {load_profile_dr.get('peak_it_mw')}")
print(f"  - scenarios: {len(scenarios)}")

# Run optimization
results = run_all_scenarios(
    site=site,
    constraints=constraints,
    objectives=objectives,
    scenarios=scenarios,
    grid_config=None,
    use_milp=True,
    load_profile_dr=load_profile_dr
)

# Analyze results
print("\n" + "=" * 80)
print("RESULTS ANALYSIS")
print("=" * 80)

for i, result in enumerate(results):
    print(f"\n[{i+1}] {result.get('scenario_name', 'Unknown')}")
    print(f"    feasible: {result.get('feasible', False)}")
    print(f"    rank: {result.get('rank', 999)}")
    
    violations = result.get('violations', [])
    if violations:
        print(f"    violations: {violations}")
    
    econ = result.get('economics', {})
    if econ:
        print(f"    lcoe_mwh: ${econ.get('lcoe_mwh', 0):.2f}")
        print(f"    total_capex_m: ${econ.get('total_capex_m', 0):.1f}M")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\nIf all scenarios show feasible=True here but infeasible in the UI,")
print("the issue is DEFINITELY stale session state in your browser.")
print("Use the Debug page (🐛 Debug) to clear session state and reload.")
