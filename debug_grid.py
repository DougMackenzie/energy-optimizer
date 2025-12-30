#!/usr/bin/env python3
"""Quick debug test for grid integration"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use v2.1.1 Greenfield optimizer with backend integration
from app.optimization import GreenfieldHeuristicV2

load_trajectory = {2028: 195, 2029: 390, 2030: 585, 2031: 780, 2032: 780, 2033: 780}
constraints = {'nox_tpy_annual': 100, 'gas_supply_mcf_day': 50000, 'land_area_acres': 300}

optimizer = GreenfieldHeuristicV2(
    site={'name': 'Debug Test'},
    load_trajectory=load_trajectory,
    constraints=constraints,
)

print(f"Years: {optimizer.years}")
print(f"Start year: {optimizer.start_year}")
print(f"Grid lead time: {optimizer.equipment.get('grid', {}).get('lead_time_months', 60)} months")
print(f"Grid available year: {optimizer.start_year + (60 // 12)} (2028 + 5 = 2033)")

# Check if annual stack is being called
if hasattr(optimizer, 'optimize_annual_energy_stack'):
    print("\n✅ optimize_annual_energy_stack method exists")
    
# Run optimization
result = optimizer.optimize()

print(f"\n=== RESULT ===")
print(f"Grid MW in equipment: {result.equipment_config.get('grid_mw', 0)}")
print(f"Total capacity: {result.equipment_config.get('total_capacity_mw', 0)}")
print(f"Firm capacity: {result.equipment_config.get('firm_capacity_mw', 0)}")
print(f"LCOE: ${result.lcoe:.2f}/MWh")
print(f"Unserved: {result.unserved_energy_pct:.1f}%")

# Check dispatch summary for annual stack
if 'annual_stack' in result.dispatch_summary:
    print("\n✅ Annual stack in dispatch summary!")
    annual_stack = result.dispatch_summary['annual_stack']
    for year in sorted(annual_stack.keys()):
        data = annual_stack[year]
        print(f"  Year {year}: Grid={data['equipment'].get('grid_mw', 0):.0f} MW, "
              f"Load={data['load_mw']:.0f} MW, Grid avail={data.get('grid_available', False)}")
else:
    print("\n❌ No annual stack in dispatch summary")
