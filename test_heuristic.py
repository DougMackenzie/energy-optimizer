#!/usr/bin/env python3
"""
Test script to debug heuristic optimization
Run directly to see what's happening
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.optimization.heuristic_optimizer import GreenFieldHeuristic

# Test parameters matching Problem 1
load_trajectory = {
    2025: 0, 2026: 0, 2027: 0,
    2028: 195,  # 150 IT × 1.3 PUE
    2029: 390,
    2030: 585,
    2031: 780,  # 600 IT × 1.3 PUE
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
}

economic_params = {
    'discount_rate': 0.08,
    'fuel_price_mmbtu': 3.50,
    'project_life_years': 20,
}

print("=" * 80)
print("HEURISTIC OPTIMIZATION TEST")
print("=" * 80)
print("\n📋 INPUTS:")
print(f"Load trajectory: {load_trajectory}")
print(f"Peak load: {max(load_trajectory.values())} MW")
print(f"\nConstraints:")
for k, v in constraints.items():
    print(f"  {k}: {v}")

print("\n🔧 Running optimizer...")

optimizer = GreenFieldHeuristic(
    site={'name': 'Test Site'},
    load_trajectory=load_trajectory,
    constraints=constraints,
    economic_params=economic_params,
)

result = optimizer.optimize()

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)
print(f"Feasible: {result.feasible}")
print(f"LCOE: ${result.lcoe:.2f}/MWh")
print(f"CAPEX: ${result.capex_total/1e6:.1f}M")
print(f"OPEX: ${result.opex_annual/1e6:.1f}M/year")
print(f"\n⚙️ EQUIPMENT:")
print(f"  Recip Engines: {result.equipment_config.get('n_recip', 0)} units = {result.equipment_config.get('recip_mw', 0):.1f} MW")
print(f"  Turbines: {result.equipment_config.get('n_turbine', 0)} units = {result.equipment_config.get('turbine_mw', 0):.1f} MW")
print(f"  Solar: {result.equipment_config.get('solar_mw', 0):.1f} MW")
print(f"  BESS: {result.equipment_config.get('bess_mwh', 0):.1f} MWh")
print(f"  Total Capacity: {result.equipment_config.get('total_capacity_mw', 0):.1f} MW")
print(f"  Firm Capacity: {result.equipment_config.get('firm_capacity_mw', 0):.1f} MW")

print(f"\n📊 DISPATCH:")
print(f"  Energy Delivered: {result.energy_delivered_mwh:,.0f} MWh")
print(f"  Energy Required: {optimizer.peak_load * 8760 * 0.85:,.0f} MWh")
print(f"  Unserved Energy: {result.unserved_energy_mwh:,.0f} MWh ({result.unserved_energy_pct:.1f}%)")

print(f"\n⚠️ CONSTRAINTS:")
print(f"  NOx: {result.constraint_status.get('nox_tpy', 0):.1f} / {result.constraint_status.get('nox_limit', 0):.0f} tpy ({result.constraint_utilization.get('nox', 0):.1f}%)")
print(f"  Gas: {result.constraint_status.get('gas_mcf_day', 0):,.0f} / {result.constraint_status.get('gas_limit', 0):,.0f} MCF/day ({result.constraint_utilization.get('gas', 0):.1f}%)")
print(f"  Land: {result.constraint_status.get('land_acres', 0):.1f} / {result.constraint_status.get('land_limit', 0):.0f} acres ({result.constraint_utilization.get('land', 0):.1f}%)")
print(f"  Binding Constraint: {result.binding_constraint}")

if result.violations:
    print(f"\n❌ VIOLATIONS:")
    for v in result.violations:
        print(f"  - {v}")

if result.warnings:
    print(f"\n⚠️ WARNINGS:")
    for w in result.warnings:
        print(f"  - {w}")

print("\n" + "=" * 80)
print(f"✅ Optimization complete in {result.solve_time_seconds:.2f} seconds")
print("=" * 80)
