#!/usr/bin/env python3
"""
Diagnose why all scenarios produce identical results.
Check if scenario constraints are being applied to the MILP model.
"""

import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

from sample_problem_600mw import get_sample_problem
from app.utils.site_loader import load_scenario_templates
from app.utils.milp_optimizer_wrapper import optimize_with_milp

# Load data
problem = get_sample_problem()
scenarios = load_scenario_templates()

# Just test 3 very different scenarios
test_scenarios = [
    scenarios[0],  # BTM Only (no grid)
    scenarios[2],  # Recip Engines Only (no solar, turbine, bess, grid)
    scenarios[4],  # Renewables + Grid (no recip, no turbine)
]

print("=" * 80)
print("SCENARIO CONSTRAINT DIAGNOSTIC")
print("=" * 80)

for scenario in test_scenarios:
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['Scenario_Name']}")
    print(f"{'='*80}")
    print(f"Expected constraints:")
    print(f"  Recip_Enabled: {scenario.get('Recip_Enabled')}")
    print(f"  Turbine_Enabled: {scenario.get('Turbine_Enabled')}")
    print(f"  Solar_Enabled: {scenario.get('Solar_Enabled')}")
    print(f"  BESS_Enabled: {scenario.get('BESS_Enabled')}")
    print(f"  Grid_Enabled: {scenario.get('Grid_Enabled')}")
    
    # Run optimization
    result = optimize_with_milp(
        site=problem['site'],
        constraints={**problem['constraints'], 'N_Minus_1_Required': False},
        load_profile_dr=problem['load_profile'],
        years=list(range(2026, 2036)),
        solver='cbc',
        time_limit=60,  # Short time limit for speed
        scenario=scenario
    )
    
    print(f"\nResult:")
    print(f"  Feasible: {result.get('feasible')}")
    print(f"  LCOE: ${result.get('economics', {}).get('lcoe_mwh', 0):.2f}/MWh")
    print(f"  CAPEX: ${result.get('economics', {}).get('total_capex_m', 0):.1f}M")
    
    # Check actual equipment in final year
    equipment = result.get('equipment_config', {})
    final_year = max(equipment.keys()) if equipment else None
    
    if final_year:
        eq = equipment[final_year]
        print(f"\nFinal Year ({final_year}) Equipment:")
        print(f"  Recip Units: {eq.get('n_recip', 0)}")
        print(f"  Turbine Units: {eq.get('n_turbine', 0)}")
        print(f"  Solar MW: {eq.get('solar_mw', 0):.1f}")
        print(f"  BESS MWh: {eq.get('bess_mwh', 0):.1f}")
        print(f"  Grid MW: {eq.get('grid_mw', 0):.1f}")
        
        # Check if constraints were respected
        violations = []
        if not scenario.get('Recip_Enabled') and eq.get('n_recip', 0) > 0:
            violations.append(f"❌ Recips installed but should be disabled!")
        if not scenario.get('Turbine_Enabled') and eq.get('n_turbine', 0) > 0:
            violations.append(f"❌ Turbines installed but should be disabled!")
        if not scenario.get('Solar_Enabled') and eq.get('solar_mw', 0) > 0:
            violations.append(f"❌ Solar installed but should be disabled!")
        if not scenario.get('BESS_Enabled') and eq.get('bess_mwh', 0) > 0:
            violations.append(f"❌ BESS installed but should be disabled!")
        if not scenario.get('Grid_Enabled') and eq.get('grid_mw', 0) > 0:
            violations.append(f"❌ Grid installed but should be disabled!")
        
        if violations:
            print(f"\n⚠️  CONSTRAINT VIOLATIONS:")
            for v in violations:
                print(f"  {v}")
        else:
            print(f"\n✅ All scenario constraints respected")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
