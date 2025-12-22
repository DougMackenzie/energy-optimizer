#!/usr/bin/env python3
"""
Quick diagnostic to test optimizer with 10 years
Run this to see which constraint is failing
"""

import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

from app.utils.phased_optimizer import PhasedDeploymentOptimizer
import numpy as np

# Test configuration
site = {
    'site_id': 'TEST',
    'load_trajectory': {
        2026: 0, 2027: 0, 2028: 150, 2029: 300, 2030: 450, 2031: 600,
        2032: 600, 2033: 600, 2034: 600, 2035: 600
    }
}

scenario = {
    'Scenario_Name': 'BTM Only',
    'Recip_Enabled': True,
    'Turbine_Enabled': True,
    'BESS_Enabled': True,
    'Solar_Enabled': True,
    'Grid_Enabled': False,
    'Grid_Timeline_Months': 0
}

equipment_data = {}

constraints = {
    'nox_tpy_annual': 100,
    'co_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 1000  # Increased for 10-year horizon
}

print("=" * 80)
print("OPTIMIZER DIAGNOSTIC TEST")
print("=" * 80)

print("\nCreating optimizer...")
optimizer = PhasedDeploymentOptimizer(site, scenario, equipment_data, constraints)

print(f"\nPlanning years: {optimizer.years}")
print(f"Number of years: {optimizer.num_years}")
print(f"Decision variables: {optimizer.num_years * 5}")

# Create a random test solution
np.random.seed(42)
x_test = np.random.uniform(0, 50, size=optimizer.num_years * 5)

print(f"\nTest solution shape: {x_test.shape}")
print(f"Test solution (first 10 values): {x_test[:10]}")

print("\nDecoding solution...")
deployment = optimizer.decode_solution(x_test)

print("\nDeployment by year:")
for year in optimizer.years:
    recip = deployment['cumulative_recip_mw'].get(year, 0)
    turb = deployment['cumulative_turbine_mw'].get(year, 0)
    bess = deployment['cumulative_bess_mwh'].get(year, 0)
    solar = deployment['cumulative_solar_mw'].get(year, 0)
    print(f"  {year}: Recip={recip:6.1f} MW, Turb={turb:6.1f} MW, BESS={bess:6.1f} MWh, Solar={solar:6.1f} MW")

print("\nChecking constraints for each year...")
for year in optimizer.years:
    nox = optimizer.calculate_annual_nox_tpy(deployment, year)
    co = optimizer.calculate_annual_co_tpy(deployment, year)
    gas = optimizer.calculate_annual_gas_mcf_day(deployment, year)
    land = optimizer.calculate_cumulative_land_acres(deployment, year)
    
    nox_ok = nox <= 101  # 1% tolerance
    co_ok = co <= 101
    gas_ok = gas <= 50500
    land_ok = land <= 1010  # 1% of 1000
    
    status = "✅" if all([nox_ok, co_ok, gas_ok, land_ok]) else "❌"
    
    print(f"  {year} {status}: NOx={nox:6.1f} tpy, CO={co:6.1f} tpy, Gas={gas:8.0f} MCF/day, Land={land:6.1f} acres")
    
    if not nox_ok:
        print(f"         ❌ NOx VIOLATION: {nox:.1f} > 101")
    if not co_ok:
        print(f"         ❌ CO VIOLATION: {co:.1f} > 101")
    if not gas_ok:
        print(f"         ❌ GAS VIOLATION: {gas:.0f} > 50500")
    if not land_ok:
        print(f"         ❌ LAND VIOLATION: {land:.1f} > 1010")

print("\n" + "=" * 80)
print("Test complete")
print("=" * 80)
