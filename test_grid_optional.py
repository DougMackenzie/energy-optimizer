#!/usr/bin/env python3
"""
Test to confirm grid is evaluated as an option, not automatic replacement

Expected behavior:
- Years 1-5: Onsite generation (grid not available)
- Year 6+: Optimizer chooses between:
  a) Grid only (if cheaper)
  b) Onsite only (if cheaper)
  c) Hybrid mix (if optimal)
  
Goal: Minimize blended LCOE over 15 years
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use v2.1.1 Greenfield optimizer with backend integration
from app.optimization import GreenfieldHeuristicV2

# Test with realistic constraints
load_trajectory = {
    2028: 195,  # Year 1
    2029: 390,  # Year 2
    2030: 585,  # Year 3
    2031: 780,  # Year 4
    2032: 780,  # Year 5
    2033: 780,  # Year 6 - Grid available
    2034: 780,  # Year 7
   2035: 780,   # Year 8
}

constraints = {
    'nox_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 300,
}

print("=" * 80)
print("TEST: Grid Integration as Optional Technology")
print("=" * 80)
print("\n📋 SCENARIO:")
print("  - Load ramps from 195 MW → 780 MW over 4 years")
print("  - Grid available: Year 6 (2033)")
print("  - NOx: 100 tpy, Gas: 50k MCF/day, Land: 300 acres")
print("\n🎯 EXPECTED BEHAVIOR:")
print("  - Years 1-5: Onsite generation (no grid)")
print("  - Year 6+: Optimal mix of grid + onsite")
print("  - Grid competes with onsite based on LCOE")

optimizer = GreenfieldHeuristicV2(
    site={'name': 'Grid Option Test'},
    load_trajectory=load_trajectory,
    constraints=constraints,
)

result = optimizer.optimize()

print(f"\n{'='*80}")
print("OPTIMIZATION RESULTS")
print(f"{'='*80}")
print(f"\nBlended LCOE: ${result.lcoe:.2f}/MWh")
print(f"Feasible: {result.feasible}")
print(f"Unserved: {result.unserved_energy_pct:.1f}%")

print(f"\nFINAL EQUIPMENT MIX (Year 8):")
eq = result.equipment_config
print(f"  Recips: {eq.get('recip_mw', 0):.1f} MW")
print(f"  Turbines: {eq.get('turbine_mw', 0):.1f} MW")
print(f"  Solar: {eq.get('solar_mw', 0):.1f} MW")
print(f"  BESS: {eq.get('bess_mwh', 0):.1f} MWh")
print(f"  Grid: {eq.get('grid_mw', 0):.1f} MW")
print(f"  Total Firm: {eq.get('firm_capacity_mw', 0):.1f} MW")

if 'annual_stack' in result.dispatch_summary:
    print(f"\n{'='*80}")
    print("ANNUAL ENERGY STACK (Equipment by Year)")
    print(f"{'='*80}")
    print(f"\n{'Year':<6} {'Load':<8} {'Recip':<8} {'Turbine':<8} {'Solar':<8} {'BESS':<8} {'Grid':<8} {'Grid?':<8}")
    print("-" * 80)
    
    annual_stack = result.dispatch_summary['annual_stack']
    for year in sorted(annual_stack.keys()):
        data = annual_stack[year]
        eq = data['equipment']
        print(f"{year:<6} "
              f"{data['load_mw']:<8.0f} "
              f"{eq.get('recip_mw', 0):<8.0f} "
              f"{eq.get('turbine_mw', 0):<8.0f} "
              f"{eq.get('solar_mw', 0):<8.1f} "
              f"{eq.get('bess_mwh', 0):<8.0f} "
              f"{eq.get('grid_mw', 0):<8.0f} "
              f"{'Yes' if data.get('grid_available') else 'No':<8}")
    
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}")
    
    # Check if grid replaced everything
    year_6_eq = annual_stack[2033]['equipment']
    onsite_mw_year6 = year_6_eq.get('recip_mw', 0) + year_6_eq.get('turbine_mw', 0)
    grid_mw_year6 = year_6_eq.get('grid_mw', 0)
    
    if grid_mw_year6 > 0 and onsite_mw_year6 == 0:
        print("\n❌ ISSUE: Grid REPLACED all onsite generation")
        print("   This suggests grid is being used automatically, not optimally")
        print("   Expected: Optimizer should compare costs and choose best mix")
    elif grid_mw_year6 > 0 and onsite_mw_year6 > 0:
        print("\n✅ GOOD: Grid + Onsite hybrid solution")
        print(f"   Grid: {grid_mw_year6:.0f} MW")
        print(f"   Onsite: {onsite_mw_year6:.0f} MW")
        print("   Optimizer is evaluating trade-offs correctly")
    elif grid_mw_year6 == 0 and onsite_mw_year6 > 0:
        print("\n✅ GOOD: Onsite-only solution (grid not economical)")
        print(f"   Onsite chose to NOT use grid")
        print("   This means onsite LCOE < grid LCOE")
    else:
        print("\n⚠️  WARNING: Neither grid nor onsite in year 6?")
    
    # Check grid economics
    print(f"\n📊 GRID ECONOMICS:")
    print(f"   CIAC (interconnection): ${780 * 100_000 / 1e6:.1f}M")
    print(f"   Capacity charges: ${780 * 1000 * 180 / 1e6:.1f}M/year")
    print(f"   Energy (@ $65/MWh): ${780 * 8760 * 0.85 * 65 / 1e6:.1f}M/year")
    print(f"   Total grid cost: ~${780 * 1000 * 180 / 1e6 + 780 * 8760 * 0.85 * 65 / 1e6:.1f}M/year")
    
    print(f"\n🎯 RECOMMENDATION:")
    if grid_mw_year6 > 0 and onsite_mw_year6 == 0:
        print("   Need to update logic so grid is EVALUATED, not AUTOMATIC")
        print("   Grid should compete with onsite based on LCOE comparison")
    else:
        print("   ✅ Grid integration working correctly as optional technology")

else:
    print("\n❌ No annual stack found - optimization may not be using annual method")

print(f"\n{'='*80}\n")
