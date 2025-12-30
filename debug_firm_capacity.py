#!/usr/bin/env python3
"""
Systematic Debug: Equipment Sizing & Firm Capacity

Questions to answer:
1. What equipment is being sized each year?
2. What is firm capacity vs total capacity?
3. Why is grid showing 780 MW instead of shortfall?
4. Are solar/BESS being counted as firm capacity?
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.optimization.heuristic_optimizer import GreenFieldHeuristic

# Simple scenario
load_trajectory = {
    2028: 195,   # Year 1
    2029: 390,   # Year 2
    2030: 585,   # Year 3
    2031: 780,   # Year 4
    2032: 780,   # Year 5
    2033: 780,   # Year 6 - Grid available
}

constraints = {
    'nox_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 300,
    'n_minus_1_required': True,
}

print("=" * 80)
print("SYSTEMATIC DEBUG: Equipment Sizing & Firm Capacity")
print("=" * 80)

optimizer = GreenFieldHeuristic(
    site={'name': 'Debug Test'},
    load_trajectory=load_trajectory,
    constraints=constraints,
)

result = optimizer.optimize()

if 'annual_stack' in result.dispatch_summary:
    annual_stack = result.dispatch_summary['annual_stack']
    
    print(f"\n{'='*80}")
    print("DETAILED ANALYSIS BY YEAR")
    print(f"{'='*80}")
    
    for year in sorted(annual_stack.keys()):
        data = annual_stack[year]
        eq = data['equipment']
        
        # Calculate capacities
        recip_mw = eq.get('recip_mw', 0)
        turbine_mw = eq.get('turbine_mw', 0)
        solar_mw = eq.get('solar_mw', 0)
        bess_mw = eq.get('bess_mw', 0)
        bess_mwh = eq.get('bess_mwh', 0)
        grid_mw = eq.get('grid_mw', 0)
        
        firm_capacity = recip_mw + turbine_mw + grid_mw  # Only firm!
        total_capacity = recip_mw + turbine_mw + solar_mw + bess_mw + grid_mw
        
        load_mw = data['load_mw']
        required_firm = load_mw * 1.15  # With N-1
        
        print(f"\n{'='*80}")
        print(f"YEAR {year} - Load: {load_mw:.0f} MW")
        print(f"{'='*80}")
        
        print(f"\n📋 EQUIPMENT:")
        print(f"  Recips:       {recip_mw:>7.1f} MW  (FIRM)")
        print(f"  Turbines:     {turbine_mw:>7.1f} MW  (FIRM)")
        print(f"  Solar:        {solar_mw:>7.1f} MW  (Intermittent - NOT firm)")
        print(f"  BESS:         {bess_mw:>7.1f} MW / {bess_mwh:.0f} MWh  (Storage - NOT firm)")
        print(f"  Grid:         {grid_mw:>7.1f} MW  (FIRM)")
        print(f"  {'─'*40}")
        print(f"  FIRM Total:   {firm_capacity:>7.1f} MW  ← Should meet load + N-1")
        print(f"  Total Cap:    {total_capacity:>7.1f} MW")
        
        print(f"\n📊 CAPACITY ANALYSIS:")
        print(f"  Load target:       {load_mw:>7.1f} MW")
        print(f"  Required (N-1):    {required_firm:>7.1f} MW  (load × 1.15)")
        print(f"  Firm capacity:     {firm_capacity:>7.1f} MW")
        print(f"  Shortfall:         {max(0, required_firm - firm_capacity):>7.1f} MW")
        print(f"  Surplus:           {max(0, firm_capacity - required_firm):>7.1f} MW")
        
        if firm_capacity < required_firm:
            print(f"  ❌ UNDERSIZED: Need {required_firm - firm_capacity:.0f} MW more firm capacity!")
        elif firm_capacity > required_firm * 1.05:  # >5% oversized
            print(f"  ⚠️  OVERSIZED: {firm_capacity - required_firm:.0f} MW excess firm capacity")
        else:
            print(f"  ✅ PROPERLY SIZED: Firm capacity meets requirement")
        
        # Check if solar/BESS are being counted as firm
        if data.get('grid_available', False):
            print(f"\n🔌 GRID LOGIC CHECK:")
            print(f"  Grid available: Yes")
            existing_onsite = recip_mw + turbine_mw
            print(f"  Existing onsite firm: {existing_onsite:.0f} MW")
            expected_grid = max(0, required_firm - existing_onsite)
            print(f"  Expected grid: {expected_grid:.0f} MW (required {required_firm:.0f} - existing {existing_onsite:.0f})")
            print(f"  Actual grid:   {grid_mw:.0f} MW")
            if abs(grid_mw - expected_grid) > 1:
                print(f"  ❌ MISMATCH: Grid should be {expected_grid:.0f} MW, not {grid_mw:.0f} MW!")
                
                # Check if solar/BESS are being subtracted from requirement
                if grid_mw < expected_grid:
                    possible_issue = expected_grid - grid_mw
                    if abs(possible_issue - solar_mw) < 10:
                        print(f"  ⚠️  Solar ({solar_mw:.0f} MW) may be counted as firm capacity!")
                    if abs(possible_issue - bess_mw) < 10:
                        print(f"  ⚠️  BESS ({bess_mw:.0f} MW) may be counted as firm capacity!")
            else:
                print(f"  ✅ Grid sizing correct")

    print(f"\n{'='*80}")
    print("KEY FINDINGS:")
    print(f"{'='*80}")
    
    # Check final year
    final_year = max(annual_stack.keys())
    final_eq = annual_stack[final_year]['equipment']
    final_firm = final_eq.get('recip_mw', 0) + final_eq.get('turbine_mw', 0) + final_eq.get('grid_mw', 0)
    final_load = annual_stack[final_year]['load_mw']
    
    print(f"\nFinal Year ({final_year}):")
    print(f"  Load: {final_load:.0f} MW")
    print(f"  Required firm (N-1): {final_load * 1.15:.0f} MW")
    print(f"  Actual firm: {final_firm:.0f} MW")
    print(f"  Ratio: {final_firm / (final_load * 1.15):.2f}")
    
    if final_firm / (final_load * 1.15) > 1.20:
        print(f"\n❌ ISSUE: Equipment is {((final_firm / (final_load * 1.15)) - 1) * 100:.0f}% oversized!")
    elif final_firm / (final_load * 1.15) < 0.98:
        print(f"\n❌ ISSUE: Equipment is {(1 - (final_firm / (final_load * 1.15))) * 100:.0f}% undersized!")
    else:
        print(f"\n✅ GOOD: Equipment properly sized to load + N-1 reserve")

else:
    print("\n❌ No annual stack in results!")

print(f"\n{'='*80}\n")
