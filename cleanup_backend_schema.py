"""
Backend Schema Cleanup Script

Removes duplicative columns from Google Sheets backend based on systematic analysis.

CHANGES:
1. Equipment Tab: Delete 'lead_time_months' column (duplicates Global_Parameters)
2. Load_Profiles Tab: 
   - RENAME 'load_profile_json' → 'load_trajectory_json' (stores annual demand by year)
   - DELETE 'workload_mix_json' (duplicates individual percentage columns)
   - DELETE 'dr_params_json' (duplicates individual percentage columns)
3. Site_Loads Tab: Delete entire tab (duplicates Load_Profiles structure)

RATIONALE:
- Equipment.lead_time_months is READ by BackendDataLoader but NOT USED for sizing
- EquipmentSizer uses Global_Parameters.{equip}_lead_time_months as source of truth
- load_trajectory_json needed to store annual demand trajectory (e.g., {2028: 150, 2029: 300})
- workload_mix_json and dr_params_json duplicate individual percentage columns
- Site_Loads tab has same structure as Load_Profiles but no data
"""

import gspread
import pandas as pd

# Connect
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

print("=" * 70)
print("Backend Schema Cleanup for Greenfield Heuristic v2.1.1")
print("=" * 70)
print("\n⚠️  WARNING: This will DELETE columns. Backup recommended!")
print("\nPress Enter to continue, or Ctrl+C to cancel...")
input()

# ============================================================================
# 1. DELETE EQUIPMENT.LEAD_TIME_MONTHS COLUMN
# ============================================================================

print("\n[1/4] Cleaning Equipment Tab...")
try:
    equipment_ws = spreadsheet.worksheet("Equipment")
    headers = equipment_ws.row_values(1)
    
    if 'lead_time_months' in headers:
        col_idx = headers.index('lead_time_months') + 1
        col_letter = chr(ord('A') + col_idx - 1)
        
        print(f"   Deleting column '{col_letter}' (lead_time_months)...")
        equipment_ws.delete_columns(col_idx)
        print(f"   ✅ Deleted Equipment.lead_time_months")
        print(f"   Reason: Duplicates Global_Parameters; not used in sizing logic")
    else:
        print("   ℹ️  lead_time_months column already removed")
        
except Exception as e:
    print(f"   ❌ Error cleaning Equipment tab: {e}")

# ============================================================================
# 2. RENAME AND CLEAN LOAD_PROFILES TAB
# ============================================================================

print("\n[2/4] Cleaning Load_Profiles Tab...")
try:
    profiles_ws = spreadsheet.worksheet("Load_Profiles")
    headers = profiles_ws.row_values(1)
    
    # Step 2a: Rename load_profile_json to load_trajectory_json
    if 'load_profile_json' in headers:
        col_idx = headers.index('load_profile_json') + 1
        col_letter = chr(ord('A') + col_idx - 1)
        print(f"   Renaming column '{col_letter}' (load_profile_json → load_trajectory_json)...")
        profiles_ws.update_cell(1, col_idx, 'load_trajectory_json')
        print(f"   ✅ Renamed to load_trajectory_json")
        print(f"   Purpose: Store annual demand by year (e.g., {{2028: 150, 2029: 300}})")
    elif 'load_trajectory_json' in headers:
        print("   ℹ️  load_trajectory_json already exists")
    
    # Step 2b: Delete duplicative JSON columns
    # Refresh headers after rename
    headers = profiles_ws.row_values(1)
    json_columns_to_delete = ['workload_mix_json', 'dr_params_json']
    deleted_count = 0
    
    # Delete in reverse order to maintain column indices
    for col_name in json_columns_to_delete:
        if col_name in headers:
            # Recalculate headers after each deletion
            headers = profiles_ws.row_values(1)
            col_idx = headers.index(col_name) + 1
            col_letter = chr(ord('A') + col_idx - 1)
            
            print(f"   Deleting column '{col_letter}' ({col_name})...")
            profiles_ws.delete_columns(col_idx)
            deleted_count += 1
    
    if deleted_count > 0:
        print(f"   ✅ Deleted {deleted_count} duplicative JSON columns")
        print(f"   Reason: Duplicate individual percentage columns")
    
    print(f"   Final columns: load_trajectory_json, flexibility_pct, workload mix %s")
        
except Exception as e:
    print(f"   ❌ Error cleaning Load_Profiles tab: {e}")

# ============================================================================
# 3. DELETE SITE_LOADS TAB (IF EXISTS)
# ============================================================================

print("\n[3/4] Cleaning Site_Loads Tab...")
try:
    site_loads_ws = spreadsheet.worksheet("Site_Loads")
    
    # Check if it has any data
    data = site_loads_ws.get_all_records()
    if len(data) == 0:
        print(f"   Site_Loads tab exists but has no data")
        print(f"   Deleting entire tab (duplicates Load_Profiles structure)...")
        spreadsheet.del_worksheet(site_loads_ws)
        print(f"   ✅ Deleted Site_Loads tab")
        print(f"   Reason: Empty tab duplicating Load_Profiles structure")
    else:
        print(f"   ⚠️  Site_Loads has {len(data)} rows - skipping deletion")
        print(f"   Manual review needed to determine if data should be migrated")
        
except gspread.exceptions.WorksheetNotFound:
    print("   ℹ️  Site_Loads tab does not exist (already cleaned)")
except Exception as e:
    print(f"   ❌ Error with Site_Loads tab: {e}")

# ============================================================================
# 4. VERIFY CLEANUP
# ============================================================================

print("\n[4/4] Verifying Cleanup...")
try:
    # Check Equipment
    equipment_ws = spreadsheet.worksheet("Equipment")
    equip_headers = equipment_ws.row_values(1)
    print(f"\n   Equipment columns ({len(equip_headers)}):")
    print(f"      {', '.join(equip_headers)}")
    
    # Check Load_Profiles
    profiles_ws = spreadsheet.worksheet("Load_Profiles")
    profile_headers = profiles_ws.row_values(1)
    print(f"\n   Load_Profiles columns ({len(profile_headers)}):")
    print(f"      {', '.join(profile_headers)}")
    
    # Check for Site_Loads
    try:
        site_loads_ws = spreadsheet.worksheet("Site_Loads")
        print(f"\n   ⚠️  Site_Loads tab still exists")
    except:
        print(f"\n   ✅ Site_Loads tab removed")
    
except Exception as e:
    print(f"   ❌ Error during verification: {e}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("Cleanup Complete!")
print("=" * 70)

print("\n✅ REMOVED (Duplicative):")
print("   - Equipment.lead_time_months (Global_Parameters is source of truth)")
print("   - Load_Profiles.workload_mix_json (individual columns preferred)")
print("   - Load_Profiles.dr_params_json (individual columns preferred)")
print("   - Site_Loads tab (empty, duplicates Load_Profiles)")

print("\n🔄 RENAMED (For Clarity):")
print("   - Load_Profiles.load_profile_json → load_trajectory_json")

print("\n✅ KEPT (Source of Truth):")
print("   - Global_Parameters.recip_lead_time_months")
print("   - Global_Parameters.gt_lead_time_months")
print("   - Global_Parameters.bess_lead_time_months")
print("   - Global_Parameters.solar_lead_time_months")
print("   - Global_Parameters.default_grid_lead_time_months")
print("   - Sites.grid_lead_time_months (site-specific override)")
print("   - Sites.grid_available_year")
print("   - Sites.grid_capacity_mw")
print("   - Load_Profiles.load_trajectory_json (annual demand by year)")
print("   - Load_Profiles.flexibility_pct")
print("   - Load_Profiles.pre_training_pct")
print("   - Load_Profiles.fine_tuning_pct")
print("   - Load_Profiles.batch_inference_pct")
print("   - Load_Profiles.real_time_inference_pct")
print("   - Equipment.ramp_rate_pct_per_min")
print("   - Equipment.time_to_full_load_min")
print("   - Equipment.land_acres_per_mw")

print("\n📝 Next Steps:")
print("   1. Test GreenfieldHeuristicV2 with cleaned backend")
print("   2. Ensure application constructs workload_mix dict from individual columns")
print("   3. Verify no code references deleted columns")

print("\n" + "=" * 70)
