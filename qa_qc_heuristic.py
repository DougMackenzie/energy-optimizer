import sys
import os
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.optimization.heuristic_optimizer import (
    GreenFieldHeuristic, BrownfieldHeuristic, LandDevHeuristic, 
    GridServicesHeuristic, BridgePowerHeuristic
)
from config.settings import CAPACITY_CREDITS

def run_qa_qc():
    print("="*80)
    print("HEURISTIC OPTIMIZER QA/QC REPORT")
    print("="*80)
    
    # Common constraints
    constraints = {
        'nox_tpy_annual': 98,  # Just under 100 limit
        'land_area_acres': 500,
        'gas_supply_mcf_day': 50000,
        'n_minus_1_required': True,
        'grid_import_mw': 0, # Initially 0
    }
    
    # Load trajectory (5 years ramp, then flat)
    load_trajectory = {
        2028: 195, 2029: 390, 2030: 585, 2031: 780, 2032: 780, 
        2033: 780, 2034: 780, 2035: 780
    }
    
    site = {'name': 'QA_Site', 'latitude': 30, 'longitude': -97}
    
    # --------------------------------------------------------------------------
    # 1. GREENFIELD QA/QC
    # --------------------------------------------------------------------------
    print("\n1. GREENFIELD HEURISTIC (Problem 1)")
    print("-" * 40)
    optimizer = GreenFieldHeuristic(
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints,
    )
    result = optimizer.optimize()
    
    # Check 1: Grid Timing
    stack = result.dispatch_summary['annual_stack']
    grid_y5 = stack[2032]['equipment'].get('grid_mw', 0)
    grid_y6 = stack[2033]['equipment'].get('grid_mw', 0)
    
    print(f"Grid Year 5 (2032): {grid_y5:.1f} MW (Expected: 0)")
    print(f"Grid Year 6 (2033): {grid_y6:.1f} MW (Expected: >0)")
    if grid_y5 == 0 and grid_y6 > 0:
        print("✅ Grid Timing: Correct (starts Year 6)")
    else:
        print("❌ Grid Timing: FAILED")

    # Check 2: Firm Capacity & Credits
    y6_eq = stack[2033]['equipment']
    recip = y6_eq.get('recip_mw', 0)
    turbine = y6_eq.get('turbine_mw', 0)
    solar = y6_eq.get('solar_mw', 0)
    bess = y6_eq.get('bess_mw', 0)
    grid = y6_eq.get('grid_mw', 0)
    
    firm_cap = (
        recip * 1.0 + turbine * 1.0 + grid * 1.0 +
        solar * CAPACITY_CREDITS['solar'] +
        bess * CAPACITY_CREDITS['bess']
    )
    target_firm = 780 * 1.15
    
    print(f"Year 6 Firm Capacity: {firm_cap:.1f} MW")
    print(f"Target Firm (N-1):    {target_firm:.1f} MW")
    print(f"  Recip: {recip:.1f}, Turbine: {turbine:.1f}, Grid: {grid:.1f}")
    print(f"  Solar Credit: {solar * CAPACITY_CREDITS['solar']:.1f} ({solar:.1f}*{CAPACITY_CREDITS['solar']})")
    print(f"  BESS Credit:  {bess * CAPACITY_CREDITS['bess']:.1f} ({bess:.1f}*{CAPACITY_CREDITS['bess']})")
    
    if abs(firm_cap - target_firm) < 5.0:
        print("✅ Firm Capacity Sizing: Correct (Matches Target)")
    else:
        print(f"❌ Firm Capacity Sizing: FAILED (Diff: {firm_cap - target_firm:.1f} MW)")

    # --------------------------------------------------------------------------
    # 2. BROWNFIELD QA/QC
    # --------------------------------------------------------------------------
    print("\n2. BROWNFIELD HEURISTIC (Problem 2)")
    print("-" * 40)
    # Existing: 100 MW Recip
    existing = {'recip_mw': 100, 'existing_lcoe': 60}
    optimizer = BrownfieldHeuristic(
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints,
        existing_equipment=existing,
        lcoe_threshold=120
    )
    result = optimizer.optimize()
    
    print(f"Objective (Max Expansion): {result.objective_value:.1f} MW")
    print(f"Blended LCOE: ${result.lcoe:.2f}/MWh (Ceiling: $120)")
    
    if result.lcoe <= 120:
        print("✅ LCOE Ceiling: Respected")
    else:
        print("❌ LCOE Ceiling: VIOLATED")
        
    # Check if expansion accounts for credits
    # Total firm should be ~897. Existing 100. Expansion ~797.
    # If objective is ~797, it's counting firm capacity correctly.
    # If it's ~1100 (total MW), it's wrong.
    if 750 < result.objective_value < 950:
         print("✅ Expansion Metric: Likely Firm Capacity")
    else:
         print(f"⚠️ Expansion Metric: Check definition ({result.objective_value:.1f} MW)")

    # --------------------------------------------------------------------------
    # 3. LAND DEV QA/QC
    # --------------------------------------------------------------------------
    print("\n3. LAND DEV HEURISTIC (Problem 3)")
    print("-" * 40)
    optimizer = LandDevHeuristic(
        site=site,
        load_trajectory={2028: 1000}, # High request to hit limits
        constraints=constraints
    )
    result = optimizer.optimize()
    
    print(f"Max Firm Capacity: {result.objective_value:.1f} MW")
    print(f"Binding Constraint: {result.binding_constraint}")
    
    # Check if credits increased capacity
    # NOx limit 98 tpy -> ~280 MW Recip (0.10 lb/MWh) or ~400 MW Turbine (0.12 lb/MWh)
    # If result > 450, credits are likely working or it's using mixed tech.
    if result.objective_value > 0:
        print("✅ Optimization ran")
    else:
        print("❌ Optimization failed")

    # --------------------------------------------------------------------------
    # 4. GRID SERVICES QA/QC
    # --------------------------------------------------------------------------
    print("\n4. GRID SERVICES HEURISTIC (Problem 4)")
    print("-" * 40)
    optimizer = GridServicesHeuristic(
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints
    )
    result = optimizer.optimize()
    
    print(f"DR Revenue: ${result.objective_value:,.0f}")
    if result.objective_value > 0:
        print("✅ DR Revenue Calculated")
    else:
        print("❌ No DR Revenue")

    # --------------------------------------------------------------------------
    # 5. BRIDGE POWER QA/QC
    # --------------------------------------------------------------------------
    print("\n5. BRIDGE POWER HEURISTIC (Problem 5)")
    print("-" * 40)
    optimizer = BridgePowerHeuristic(
        site=site,
        load_trajectory={2028: 780},
        constraints=constraints,
        grid_available_month=60
    )
    result = optimizer.optimize()
    
    print(f"Min NPV: ${result.objective_value:,.0f}")
    print(f"Recommended: {result.dispatch_summary.get('recommended')}")
    if result.objective_value > 0:
        print("✅ NPV Calculated")
    else:
        print("❌ NPV Failed")

if __name__ == "__main__":
    run_qa_qc()
