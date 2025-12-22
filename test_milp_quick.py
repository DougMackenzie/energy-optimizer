"""
Quick test of bvNexus MILP model with demand response
"""

import numpy as np
from app.optimization.milp_model_dr import bvNexusMILP_DR
from app.utils.load_profile_generator import generate_load_profile_with_flexibility

# Test parameters
print("=" * 60)
print("bvNexus MILP Test - Quick Validation")
print("=" * 60)

# Generate load profile
print("\n1. Generating load profile with DR flexibility...")
workload_mix = {
    'pre_training': 40,
    'fine_tuning': 20,
    'batch_inference': 15,
    'realtime_inference': 15,
    'rl_training': 5,
    'cloud_hpc': 5,
}

load_data = generate_load_profile_with_flexibility(
    peak_it_load_mw=160.0,
    pue=1.25,
    load_factor=0.75,
    workload_mix=workload_mix,
    cooling_flex_pct=0.25
)

print(f"   ✓ Peak load: {load_data['summary']['peak_facility_mw']:.1f} MW")
print(f"   ✓ Avg flexibility: {load_data['summary']['avg_flexibility_pct']:.1f}%")
print(f"   ✓ Avg flexible MW: {load_data['summary']['avg_flexibility_mw']:.1f} MW")

# Build MILP model
print("\n2. Building MILP model...")
optimizer = bvNexusMILP_DR()

site = {
    'pue': 1.25,
    'grid_capex': 5_000_000,
    'load_trajectory': {y: 1.0 for y in range(2026, 2036)},  # Flat load
}

constraints = {
    'nox_tpy': 99,
    'land_acres': 500,
    'gas_mcf_day': 50000,
}

optimizer.build(
    site=site,
    constraints=constraints,
    load_data=load_data,
    workload_mix=workload_mix,
    years=[2026, 2027, 2028],  # Just 3 years for quick test
    dr_config={'cooling_flex': 0.25, 'annual_curtailment_budget_pct': 0.01},
    existing_equipment={'n_recip': 0, 'n_turbine': 0, 'bess_mwh': 0, 'solar_mw': 0, 'grid_mw': 0},
    use_representative_periods=True
)

print("   ✓ Model built successfully")
print(f"   ✓ Variables: ~{optimizer.n_hours * 3 * 10} (approx)")
print(f"   ✓ Representative hours: {optimizer.n_hours}")
print(f"   ✓ Scale factor: {optimizer.scale_factor:.2f}")

# Solve
print("\n3. Solving MILP...")
print("   (This may take 30-60 seconds...)")

try:
    solution = optimizer.solve(solver='glpk', time_limit=120, verbose=False)
    
    print(f"\n   ✓ Status: {solution['status']}")
    print(f"   ✓ Termination: {solution['termination']}")
    
    if solution['objective_lcoe']:
        print(f"\n4. Results:")
        print(f"   LCOE: ${solution['objective_lcoe']:.2f}/MWh")
        
        final_year = max(solution['equipment'].keys())
        eq = solution['equipment'][final_year]
        print(f"\n   Equipment (Year {final_year}):")
        print(f"     - Recip engines: {eq['n_recip']}")
        print(f"     - Turbines: {eq['n_turbine']}")
        print(f"     - BESS: {eq['bess_mwh']:.1f} MWh ({eq['bess_mw']:.1f} MW)")
        print(f"     - Solar: {eq['solar_mw']:.1f} MW")
        print(f"     - Grid: {eq['grid_mw']:.1f} MW (active={eq['grid_active']})")
        
        dr = solution['dr']
        print(f"\n   Demand Response:")
        print(f"     - Annual curtailment: {dr['total_curtailment_mwh']:.1f} MWh ({dr['curtailment_pct']:.2f}%)")
        print(f"     - Annual DR revenue: ${dr['dr_revenue_annual']:,.0f}")
        
        print("\n" + "=" * 60)
        print("✅ bvNexus MILP TEST PASSED")
        print("=" * 60)
    else:
        print("\n   ⚠️  No objective value - model may be infeasible")
        
except Exception as e:
    print(f"\n   ❌ Error during solve: {e}")
    import traceback
    traceback.print_exc()
