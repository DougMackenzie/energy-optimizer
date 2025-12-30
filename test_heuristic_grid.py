#!/usr/bin/env python3
"""
Test with grid included
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.optimization.heuristic_optimizer import GreenFieldHeuristic

# Test parameters with GRID
load_trajectory = {
    2025: 0, 2026: 0, 2027: 0,
    2028: 195,  # 150 IT × 1.3 PUE
    2029: 390,
    2030: 585,
    2031: 780,  # 600 IT × 1.3 PUE (full load - grid should serve this)
    2032: 780,
    2033: 780,
    2034: 780,
    2035: 780,
}

constraints = {
    'nox_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 300,
    'n_minus_1_required': True,
    'grid_import_mw': 780,  # Grid can serve full load after year 5
}

print("=" * 80)
print("TEST WITH GRID (780 MW available)")
print("=" * 80)
print(f"Peak load: {max(load_trajectory.values())} MW")
print(f"Grid capacity: {constraints['grid_import_mw']} MW")

optimizer = GreenFieldHeuristic(
    site={'name': 'Test Site with Grid'},
    load_trajectory=load_trajectory,
    constraints=constraints,
)

result = optimizer.optimize()

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
print(f"Feasible: {result.feasible}")
print(f"LCOE: ${result.lcoe:.2f}/MWh")
print(f"\n⚙️ EQUIPMENT:")
print(f"  Recip Engines: {result.equipment_config.get('n_recip', 0)} units = {result.equipment_config.get('recip_mw', 0):.1f} MW")
print(f"  Turbines: {result.equipment_config.get('n_turbine', 0)} units = {result.equipment_config.get('turbine_mw', 0):.1f} MW")
print(f"  Solar: {result.equipment_config.get('solar_mw', 0):.1f} MW")
print(f"  BESS: {result.equipment_config.get('bess_mwh', 0):.1f} MWh")
print(f"  Grid: {result.equipment_config.get('grid_mw', 0):.1f} MW")
print(f"  Total Capacity: {result.equipment_config.get('total_capacity_mw', 0):.1f} MW")
print(f"  Firm Capacity: {result.equipment_config.get('firm_capacity_mw', 0):.1f} MW")

print(f"\n📊 DISPATCH:")
print(f"  Energy Delivered: {result.energy_delivered_mwh:,.0f} MWh")
print(f"  Unserved: {result.unserved_energy_mwh:,.0f} MWh ({result.unserved_energy_pct:.1f}%)")

print(f"\n⚠️ CONSTRAINTS:")
print(f"  NOx: {result.constraint_status.get('nox_tpy', 0):.1f} / {result.constraint_status.get('nox_limit', 0):.0f} tpy")
print(f"  Land: {result.constraint_status.get('land_acres', 0):.1f} / {result.constraint_status.get('land_limit', 0):.0f} acres")

if result.violations:
    print(f"\n❌ VIOLATIONS:")
    for v in result.violations:
        print(f"  - {v}")
else:
    print(f"\n✅ All constraints satisfied!")
