"""
Test script for Google Sheets site backend integration
"""

from app.utils.site_backend import (
    load_all_sites,
    save_site,
    load_site_load_profile,
    save_site_load_profile,
    load_site_optimization_stages,
    save_site_stage_result
)

# Test 1: Load all sites
print("=" * 60)
print("TEST 1: Loading all sites from Google Sheets")
print("=" * 60)
sites = load_all_sites(use_cache=False)
print(f"Found {len(sites)} sites")
for site in sites:
    print(f"  - {site.get('site_name', 'Unknown')}: {site.get('location', 'Unknown')}")

# Test 2: Save a new site
print("\n" + "=" * 60)
print("TEST 2: Saving a new site")
print("=" * 60)
test_site = {
    'name': 'Test Phoenix Site',
    'location': 'Phoenix, AZ',
    'iso': 'CAISO',
    'it_capacity_mw': 500,
    'pue': 1.25,
    'facility_mw': 625,
    'land_acres': 350,
    'nox_limit_tpy': 100,
    'gas_supply_mcf': 125000,
    'voltage_kv': 345,
    'coordinates': [33.45, -112.07],
    'geojson_prefix': 'phoenix',
    'problem_num': 1,
    'problem_name': 'Greenfield'
}

result = save_site(test_site)
print(f"Save result: {'Success' if result else 'Failed'}")

# Test 3: Save load profile for site
print("\n" + "=" * 60)
print("TEST 3: Saving load profile")
print("=" * 60)
load_profile = {
    'load_profile': {
        'year_1': 300,
        'year_2': 400,
        'year_3': 500
    },
    'workload_mix': {
        'ai_training': 45,
        'ai_inference': 25,
        'hpc': 15,
        'enterprise': 15
    },
    'dr_params': {
        'enabled': True,
        'curtail_pct': 10
    }
}

result = save_site_load_profile('Test Phoenix Site', load_profile)
print(f"Load profile save result: {'Success' if result else 'Failed'}")

# Test 4: Load load profile
print("\n" + "=" * 60)
print("TEST 4: Loading load profile")
print("=" * 60)
loaded_profile = load_site_load_profile('Test Phoenix Site')
if loaded_profile:
    print("Loaded profile:")
    print(f"  Workload mix: {loaded_profile.get('workload_mix')}")
else:
    print("No profile found")

# Test 5: Save optimization stage result
print("\n" + "=" * 60)
print("TEST 5: Saving stage result (Screening)")
print("=" * 60)
stage_result = {
    'complete': True,
    'lcoe': 75.5,
    'npv': -125000000,
    'equipment': {
        'recip': 8,
        'turbine': 2,
        'bess_mwh': 500
    },
    'dispatch_summary': {
        'total_mwh': 5000000
    },
    'notes': 'Initial screening study complete'
}

result = save_site_stage_result('Test Phoenix Site', 'screening', stage_result)
print(f"Stage result save: {'Success' if result else 'Failed'}")

# Test 6: Load all stage results for site
print("\n" + "=" * 60)
print("TEST 6: Loading all stage results")
print("=" * 60)
stages = load_site_optimization_stages('Test Phoenix Site')
print("Stages loaded:")
for stage_name, stage_data in stages.items():
    complete = stage_data.get('complete', False)
    lcoe = stage_data.get('lcoe')
    print(f"  {stage_name}: Complete={complete}, LCOE={lcoe}")

print("\n" + "=" * 80)
print("All tests complete! Check Google Sheets to verify data was saved.")
print("=" * 80)
