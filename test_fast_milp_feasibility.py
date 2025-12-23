#!/usr/bin/env python3
"""
Test Fast MILP Model Feasibility
Ensures the fast model can find feasible solutions for common scenarios
"""

import numpy as np
from app.optimization.milp_model_dr_fast import bvNexusMILP_DR

print("=" * 60)
print("FAST MILP FEASIBILITY TEST")
print("=" * 60)

# Test configuration
peak_it_mw = 160
pue = 1.25
load_factor = 0.75
base_load = peak_it_mw * pue * load_factor  # ~150 MW

# Generate simple load profile
load_8760 = base_load * (1 + 0.1 * np.sin(2 * np.pi * np.arange(8760) / 24))
load_8760 = np.maximum(load_8760, base_load * 0.7)

load_data = {
    'total_load_mw': load_8760.tolist(),
    'pue': pue
}

# Realistic constraints for datacenter
constraints = {
    'NOx_Limit_tpy': 99,
    'Gas_Supply_MCF_day': 50000,
    'Available_Land_Acres': 1000
}

site = {'name': 'Test Site'}
workload_mix = {
    'pre_training': 0.30,
    'fine_tuning': 0.20,
    'batch_inference': 0.30,
    'realtime_inference': 0.20
}
years = list(range(2026, 2036))  # 10 years

# Test scenarios
scenarios = [
    {'name': 'BTM Only (Recip + BESS)', 'grid_enabled': False, 'solar_enabled': False},
    {'name': 'All Technologies', 'grid_enabled': True, 'solar_enabled': True},
    {'name': 'Recip + Grid', 'grid_enabled': True, 'solar_enabled': False},
]

print(f"\nTesting {len(scenarios)} scenarios with fast MILP...")
print(f"Load: {base_load:.1f} MW base, {peak_it_mw} MW IT peak")
print(f"Years: {years[0]}-{years[-1]}")

results = []

for idx, scenario in enumerate(scenarios):
    print(f"\n[{idx+1}/{len(scenarios)}] {scenario['name']}")
    print("-" * 60)
    
    try:
        # Build model
        optimizer = bvNexusMILP_DR()
        
        grid_config = {
            'available_year': 2030 if scenario['grid_enabled'] else 9999,
            'capex': 5_000_000
        }
        
        optimizer.build(
            site=site,
            constraints=constraints,
            load_data=load_data,
            workload_mix=workload_mix,
            years=years,
            dr_config={'cooling_flex': 0.25},
            existing_equipment=None,
            grid_config=grid_config,
        )
        
        # Fix variables based on scenario
        if not scenario['grid_enabled']:
            for y in years:
                optimizer.model.grid_mw[y].fix(0)
                optimizer.model.grid_active[y].fix(0)
        
        if not scenario['solar_enabled']:
            for y in years:
                optimizer.model.solar_mw[y].fix(0)
        
        print("  Building model... ✓")
        
        # Solve
        print("  Solving with CBC (60s timeout)...")
        solution = optimizer.solve(solver='cbc', time_limit=60, verbose=False)
        
        # Check result
        status = solution.get('status')
        termination = solution.get('termination')
        
        print(f"  Status: {status}")
        print(f"  Termination: {termination}")
        
        if termination in ['optimal', 'feasible']:
            final_year = max(years)
            eq = solution['equipment'].get(final_year, {})
            cov = solution['power_coverage'].get(final_year, {})
            
            print(f"  ✅ FEASIBLE!")
            print(f"    LCOE: ${solution.get('objective_lcoe', 0):.2f}/MWh")
            print(f"    Recips: {eq.get('n_recip', 0)} units ({eq.get('recip_mw', 0):.1f} MW)")
            print(f"    Turbines: {eq.get('n_turbine', 0)} units ({eq.get('turbine_mw', 0):.1f} MW)")
            print(f"    BESS: {eq.get('bess_mwh', 0):.1f} MWh")
            print(f"    Solar: {eq.get('solar_mw', 0):.1f} MW")
            print(f"    Grid: {eq.get('grid_mw', 0):.1f} MW")
            print(f"    Coverage: {cov.get('coverage_pct', 0):.1f}%")
            
            results.append({'scenario': scenario['name'], 'feasible': True, 'lcoe': solution.get('objective_lcoe', 0)})
        else:
            print(f"  ❌ INFEASIBLE - Solver could not find solution")
            results.append({'scenario': scenario['name'], 'feasible': False, 'lcoe': 0})
    
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append({'scenario': scenario['name'], 'feasible': False, 'lcoe': 0})

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

feasible_count = sum(1 for r in results if r['feasible'])
print(f"\nFeasible scenarios: {feasible_count}/{len(results)}")

for r in results:
    status = "✅" if r['feasible'] else "❌"
    lcoe_str = f"${r['lcoe']:.2f}/MWh" if r['feasible'] else "N/A"
    print(f"  {status} {r['scenario']}: {lcoe_str}")

if feasible_count == len(results):
    print("\n🎉 ALL SCENARIOS FEASIBLE - Fast MILP is working correctly!")
    exit(0)
else:
    print(f"\n⚠️ {len(results) - feasible_count} scenarios infeasible - needs investigation")
    exit(1)
