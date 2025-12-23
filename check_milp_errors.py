#!/usr/bin/env python3
"""
Run MILP diagnostic from command line to see detailed error messages.
This will show you WHY scenarios are failing.

Usage:
    python check_milp_errors.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import sample problem
from sample_problem_600mw import get_sample_problem

# Import MILP optimizer
from app.utils.milp_optimizer_wrapper import optimize_with_milp

# Configure detailed logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s | %(message)s'
)

print("\n" + "="*70)
print("MILP DIAGNOSTIC - Detailed Error Analysis")
print("="*70 + "\n")

# Load 600MW sample problem
problem = get_sample_problem()

# Extract components
site = problem['site']
constraints = problem['constraints']
load_profile = problem['load_profile']

# Test scenarios
test_scenarios = [
    {
        'Scenario_Name': 'BTM Only',
        'Grid_Enabled': False,
        'Solar_Enabled': True,
        'Recip_Enabled': True,
        'Turbine_Enabled': False,
        'BESS_Enabled': True,
    },
    {
        'Scenario_Name': 'All Technologies',
        'Grid_Enabled': True,
        'Solar_Enabled': True,
        'Recip_Enabled': True,
        'Turbine_Enabled': True,
        'BESS_Enabled': True,
    },
]

print(f"Testing {len(test_scenarios)} scenarios with 600MW sample problem\\n")
print(f"Constraints:")
print(f"  NOx Limit: {constraints['NOx_Limit_tpy']} tpy")
print(f"  Gas Supply: {constraints['Gas_Supply_MCF_day']} MCF/day")
print(f"  Land: {constraints['Available_Land_Acres']} acres")
print(f"  Grid: {constraints['Grid_Available_MW']} MW ({constraints['grid_interconnection_year']})")
print(f"\\nLoad:")
print(f"  Peak IT: {load_profile['peak_it_mw']} MW")
print(f"  PUE: {load_profile['pue']}")
print(f"  Peak Facility: {load_profile['peak_facility_mw']} MW")
print("\\n" + "="*70 + "\\n")

# Run each scenario
for i, scenario in enumerate(test_scenarios):
    scenario_name = scenario['Scenario_Name']
    
    print(f"\\n{'='*70}")
    print(f"SCENARIO {i+1}/{len(test_scenarios)}: {scenario_name}")
    print("="*70)
    
    print(f"\\nEnabled equipment:")
    print(f"  Recips: {scenario.get('Recip_Enabled', False)}")
    print(f"  Turbines: {scenario.get('Turbine_Enabled', False)}")
    print(f"  BESS: {scenario.get('BESS_Enabled', False)}")
    print(f"  Solar: {scenario.get('Solar_Enabled', False)}")
    print(f"  Grid: {scenario.get('Grid_Enabled', False)}")
    print()
    
    # Prepare load profile in expected format
    load_profile_dr = {
        'peak_it_mw': load_profile['peak_it_mw'],
        'pue': load_profile['pue'],
        'load_factor': load_profile['load_factor'],
        'workload_mix': load_profile['workload_mix'],
        'load_data': load_profile['load_data'],
    }
    
    # Run optimization
    result = optimize_with_milp(
        site=site,
        constraints=constraints,
        load_profile_dr=load_profile_dr,
        years=list(range(2028, 2036)),  # Use problem years
        scenario=scenario,
        solver='cbc',
        time_limit=60,
    )
    
    # Print results
    print(f"\\n{'='*70}")
    print(f"RESULTS for {scenario_name}")
    print("="*70)
    print(f"Feasible: {result['feasible']}")
    print(f"Violations: {result.get('violations', [])}")
    
    if result['feasible']:
        eq = result['equipment_config']
        print(f"\\nEquipment:")
        print(f"  Recips: {eq['n_recip']} units ({eq['recip_mw']:.0f} MW)")
        print(f"  Turbines: {eq['n_turbine']} units ({eq['turbine_mw']:.0f} MW)")
        print(f"  BESS: {eq['bess_mwh']:.0f} MWh ({eq['bess_mw']:.0f} MW)")
        print(f"  Solar: {eq['solar_mw']:.0f} MW")
        print(f"  Grid: {eq['grid_mw']:.0f} MW")
        print(f"\\nEconomics:")
        print(f"  LCOE: ${result['economics']['lcoe_mwh']:.2f}/MWh")
        print(f"  CAPEX: ${result['economics']['total_capex_m']:.1f}M")
        print(f"\\nPower Coverage:")
        print(f"  Coverage: {result['power_coverage']['final_coverage_pct']:.1f}%")
        print(f"  Unserved: {result['power_coverage']['unserved_mwh']:.0f} MWh")
    else:
        print(f"\\n⚠️  INFEASIBLE - See violations above for details")
    
    print()

print("\\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70 + "\\n")
print("If all scenarios failed, check the violations messages above.")
print("Common issues:")
print("  - Solar land constraint too tight")
print("  - Grid not available in early years")
print("  - NOx/gas constraints too restrictive")
print("  - Load trajectory mismatch with constraint years")
print()
