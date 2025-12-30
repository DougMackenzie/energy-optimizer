"""
Backend Schema Investigation Script

Investigates Site_Loads tab and Load_Profiles JSON columns to determine
what needs to be cleaned up.
"""

import gspread
import pandas as pd
import json

# Connect
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

print("=" * 70)
print("Backend Schema Investigation")
print("=" * 70)

# ============================================================================
# 1. INVESTIGATE SITE_LOADS TAB
# ============================================================================

print("\n[1/3] Investigating Site_Loads Tab...")
try:
    site_loads_ws = spreadsheet.worksheet("Site_Loads")
    headers = site_loads_ws.row_values(1)
    print(f"   Site_Loads columns ({len(headers)}): {headers}")
    
    # Get first few rows to see data
    data = site_loads_ws.get_all_records()
    print(f"   Rows: {len(data)}")
    if len(data) > 0:
        print(f"   Sample row keys: {list(data[0].keys())}")
except Exception as e:
    print(f"   ⚠️  Site_Loads tab does not exist or error: {e}")

# ============================================================================
# 2. INVESTIGATE LOAD_PROFILES JSON COLUMNS
# ============================================================================

print("\n[2/3] Investigating Load_Profiles Tab...")
try:
    profiles_ws = spreadsheet.worksheet("Load_Profiles")
    headers = profiles_ws.row_values(1)
    print(f"   Load_Profiles columns ({len(headers)}): {headers}")
    
    data = profiles_ws.get_all_records()
    print(f"   Rows: {len(data)}")
    
    if len(data) > 0:
        row = data[0]
        
        # Check JSON columns
        if 'load_profile_json' in row and row['load_profile_json']:
            try:
                json_data = json.loads(row['load_profile_json'])
                print(f"   load_profile_json contains: {list(json_data.keys())}")
            except:
                print(f"   load_profile_json: '{row['load_profile_json']}' (not valid JSON)")
        
        if 'workload_mix_is_dr_params_json' in row and row['workload_mix_is_dr_params_json']:
            try:
                json_data = json.loads(row['workload_mix_is_dr_params_json'])
                print(f"   workload_mix_is_dr_params_json contains: {list(json_data.keys())}")
            except:
                print(f"   workload_mix_is_dr_params_json: '{row['workload_mix_is_dr_params_json']}' (not valid JSON)")
        
        # Check individual percentage columns
        pct_columns = ['flexibility_pct', 'pre_training_pct', 'fine_tuning_pct', 
                      'batch_inference_pct', 'real_time_inference_pct']
        individual_vals = {col: row.get(col, 'N/A') for col in pct_columns}
        print(f"   Individual percentage columns: {individual_vals}")

except Exception as e:
    print(f"   ⚠️  Error reading Load_Profiles: {e}")

# ============================================================================
# 3. INVESTIGATE EQUIPMENT LEAD TIMES
# ============================================================================

print("\n[3/3] Investigating Equipment Tab Lead Times...")
try:
    equipment_ws = spreadsheet.worksheet("Equipment")
    headers = equipment_ws.row_values(1)
    
    if 'lead_time_months' in headers:
        lead_time_col_idx = headers.index('lead_time_months') + 1
        print(f"   ✓ lead_time_months column exists at position {lead_time_col_idx}")
        
        # Get data
        data = equipment_ws.get_all_records()
        lead_times = {row['equipment_id']: row.get('lead_time_months', '') 
                     for row in data if row.get('equipment_id')}
        print(f"   Lead times in Equipment tab: {lead_times}")
    else:
        print("   lead_time_months column does not exist")
        
except Exception as e:
    print(f"   ⚠️  Error reading Equipment: {e}")

# ============================================================================
# 4. GLOBAL_PARAMETERS LEAD TIMES
# ============================================================================

print("\n[4/4] Checking Global_Parameters Lead Times...")
try:
    params_ws = spreadsheet.worksheet("Global_Parameters")
    data = params_ws.get_all_records()
    
    lead_time_params = [row for row in data if 'lead_time' in row.get('parameter_name', '').lower()]
    print(f"   Lead time parameters in Global_Parameters:")
    for param in lead_time_params:
        print(f"      {param['parameter_name']}: {param.get('value')} {param.get('unit', '')}")

except Exception as e:
    print(f"   ⚠️  Error reading Global_Parameters: {e}")

print("\n" + "=" * 70)
print("Investigation Complete")
print("=" * 70)
print("\nReview output above to confirm what needs to be cleaned up.")
