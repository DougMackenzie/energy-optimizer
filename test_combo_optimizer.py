#!/usr/bin/env python3
"""
Test combination optimizer standalone
"""

import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

from app.utils.combination_optimizer import CombinationOptimizer

# Test configuration
site = {
    'site_id': 'TEST',
    'load_trajectory': {
        2026: 0, 2027: 0, 2028: 150, 2029: 300, 2030: 450, 2031: 600,
        2032: 600, 2033: 600
    }
}

scenario = {
    'Scenario_Name': 'BTM Only',
    'Recip_Enabled': True,
    'Turbine_Enabled': True,
    'BESS_Enabled': True,
    'Solar_Enabled': True,
    'Grid_Enabled': False,
    'Grid_Timeline_Months': 0
}

equipment_data = {}

constraints = {
    'nox_tpy_annual': 100,
    'co_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 1000
}

print("Creating combination optimizer...")
combo_optimizer = CombinationOptimizer(site, scenario, equipment_data, constraints)

print("\nGenerating combinations...")
combos = combo_optimizer.generate_combinations()
print(f"Generated {len(combos)} combinations:")
for combo in combos:
    print(f"  - {combo['name']}")

print("\nTesting first combination only...")
try:
    deployment, lcoe, violations, power, timeline = combo_optimizer.optimize_combination(combos[0])
    print(f"\nResult:")
    print(f"  LCOE: ${lcoe:.2f}/MWh")
    print(f"  Power: {power:.0f} MW-years")
    print(f"  Feasible: {len(violations) == 0}")
    print(f"  Violations: {len(violations)}")
    if violations:
        for v in violations[:3]:
            print(f"    - {v}")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
