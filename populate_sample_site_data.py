"""
Populate Sample Site Data in Backend

Creates realistic load trajectories and grid configuration for 5 sample sites.

LOGIC:
- Load trajectory starts in 2027
- Growth rate based on site size: 
  - <700 MW sites: 150 MW/year
  - 700-1000 MW sites: 200 MW/year
  - >1000 MW sites: 250 MW/year
- Grid available in 2031 for all sites
- Grid capacity = 1.2 x facility_MW (20% headroom)
- Default workload mix: 45% pre-training, 20% fine-tuning, 15% batch, 20% real-time
"""

import gspread
import json

# Connect
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

print("=" * 70)
print("Populating Sample Site Data")
print("=" * 70)

# Define sample sites with their characteristics
SAMPLE_SITES = [
    {
        'name': 'Austin Greenfield DC',
        'facility_mw': 610,
        'land_acres': 380,
        'growth_mw_year': 150,  # <700 MW site
    },
    {
        'name': 'Dallas Brownfield Exp',
        'facility_mw': 750,
        'land_acres': 600,
        'growth_mw_year': 200,  # 700-1000 MW site
    },
    {
        'name': 'Phoenix Land Constrained',
        'facility_mw': 900,
        'land_acres': 200,
        'growth_mw_year': 200,  # 700-1000 MW site
    },
    {
        'name': 'Chicago Grid Hub',
        'facility_mw': 1000,
        'land_acres': 400,
        'growth_mw_year': 200,  # 700-1000 MW site
    },
    {
        'name': 'Northern Virginia Bridge',
        'facility_mw': 1200,
        'land_acres': 500,
        'growth_mw_year': 250,  # >1000 MW site
    },
]

# Default workload mix (from DR Economics study)
DEFAULT_WORKLOAD_MIX = {
    'flexibility_pct': 30.6,
    'pre_training_pct': 45.0,
    'fine_tuning_pct': 20.0,
    'batch_inference_pct': 15.0,
    'real_time_inference_pct': 20.0,
}

# ============================================================================
# 1. UPDATE SITES TAB WITH GRID INFORMATION
# ============================================================================

print("\n[1/2] Updating Sites Tab with Grid Information...")

sites_ws = spreadsheet.worksheet("Sites")
sites_data = sites_ws.get_all_records()
headers = sites_ws.row_values(1)

# Find column indices
name_col = headers.index('name') + 1
grid_year_col = headers.index('grid_available_year') + 1
grid_capacity_col = headers.index('grid_capacity_mw') + 1
grid_lead_time_col = headers.index('grid_lead_time_months') + 1

for site in SAMPLE_SITES:
    # Find row for this site
    row_idx = None
    for i, row in enumerate(sites_data, start=2):  # start=2 because of header
        if row['name'] == site['name']:
            row_idx = i
            break
    
    if row_idx is None:
        print(f"   ⚠️  Site '{site['name']}' not found")
        continue
    
    # Calculate grid capacity (20% headroom)
    grid_capacity = int(site['facility_mw'] * 1.2)
    
    # Update grid information
    updates = [
        {
            'range': f'{chr(ord("A") + grid_year_col - 1)}{row_idx}',
            'values': [[2031]]
        },
        {
            'range': f'{chr(ord("A") + grid_capacity_col - 1)}{row_idx}',
            'values': [[grid_capacity]]
        },
        {
            'range': f'{chr(ord("A") + grid_lead_time_col - 1)}{row_idx}',
            'values': [[60]]  # Default 60 months
        },
    ]
    
    sites_ws.batch_update(updates)
    
    print(f"   ✅ {site['name']}: Grid 2031, {grid_capacity} MW capacity, 60 mo lead time")

# ============================================================================
# 2. CREATE LOAD PROFILES
# ============================================================================

print("\n[2/2] Creating Load Profiles...")

profiles_ws = spreadsheet.worksheet("Load_Profiles")
profile_headers = profiles_ws.row_values(1)

# Clear existing data (keep headers)
existing_data = profiles_ws.get_all_records()
if len(existing_data) > 0:
    profiles_ws.delete_rows(2, len(existing_data) + 1)
    print(f"   Cleared {len(existing_data)} existing load profiles")

for site in SAMPLE_SITES:
    # Calculate load trajectory
    facility_mw = site['facility_mw']
    growth_rate = site['growth_mw_year']
    
    # Start in 2027, grow until facility_mw reached
    load_trajectory = {}
    current_year = 2027
    current_mw = growth_rate  # Start with first year's growth
    
    while current_mw < facility_mw:
        load_trajectory[current_year] = round(current_mw, 1)
        current_year += 1
        current_mw += growth_rate
    
    # Final year at full capacity
    load_trajectory[current_year] = facility_mw
    
    # Convert to JSON string
    trajectory_json = json.dumps(load_trajectory)
    
    # Create row data
    row_data = [
        site['name'],  # site_name
        trajectory_json,  # load_trajectory_json
        '2025-12-30',  # created_date
        '2025-12-30',  # updated_date
        DEFAULT_WORKLOAD_MIX['flexibility_pct'],
        DEFAULT_WORKLOAD_MIX['pre_training_pct'],
        DEFAULT_WORKLOAD_MIX['fine_tuning_pct'],
        DEFAULT_WORKLOAD_MIX['batch_inference_pct'],
        DEFAULT_WORKLOAD_MIX['real_time_inference_pct'],
    ]
    
    profiles_ws.append_row(row_data)
    
    years = f"{min(load_trajectory.keys())}-{max(load_trajectory.keys())}"
    print(f"   ✅ {site['name']}: {years}, {growth_rate} MW/yr → {facility_mw} MW")
    print(f"      Trajectory: {trajectory_json}")

# ============================================================================
# VERIFICATION
# ============================================================================

print("\n" + "=" * 70)
print("Data Population Complete!")
print("=" * 70)

print("\n📊 Site Summary:")
for site in SAMPLE_SITES:
    print(f"\n{site['name']}:")
    print(f"   Facility: {site['facility_mw']} MW")
    print(f"   Grid: 2031, {int(site['facility_mw'] * 1.2)} MW (20% headroom)")
    print(f"   Growth: {site['growth_mw_year']} MW/year starting 2027")
    
    # Calculate number of years
    years_to_full = (site['facility_mw'] / site['growth_mw_year'])
    final_year = 2027 + int(years_to_full)
    print(f"   Timeline: 2027 → {final_year} ({int(years_to_full)} years)")

print("\n📋 Workload Mix (All Sites):")
print(f"   Overall Flexibility: {DEFAULT_WORKLOAD_MIX['flexibility_pct']}%")
print(f"   Pre-training: {DEFAULT_WORKLOAD_MIX['pre_training_pct']}%")
print(f"   Fine-tuning: {DEFAULT_WORKLOAD_MIX['fine_tuning_pct']}%")
print(f"   Batch Inference: {DEFAULT_WORKLOAD_MIX['batch_inference_pct']}%")
print(f"   Real-time Inference: {DEFAULT_WORKLOAD_MIX['real_time_inference_pct']}%")

print("\n✅ Backend ready for application testing!")
print("=" * 70)
