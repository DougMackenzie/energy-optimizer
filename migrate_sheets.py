#!/usr/bin/env python3
"""
Google Sheets Migration Script - Option 1
Renames sheets and adds missing columns to match code expectations
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client
import json
from datetime import datetime

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def backup_sheet_data():
    """Backup all current data before migration"""
    print("=" * 80)
    print("STEP 1: BACKING UP CURRENT DATA")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        backup = {}
        backup_time = datetime.now().isoformat()
        
        for worksheet in spreadsheet.worksheets():
            sheet_name = worksheet.title
            print(f"\n📦 Backing up: {sheet_name}")
            
            # Get all data including headers
            all_data = worksheet.get_all_values()
            backup[sheet_name] = all_data
            
            print(f"   ✅ Backed up {len(all_data)} rows")
        
        # Save to JSON file
        backup_file = f'sheets_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(backup_file, 'w') as f:
            json.dump({
                'timestamp': backup_time,
                'sheets': backup
            }, f, indent=2)
        
        print(f"\n✅ Backup saved to: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def rename_sheets():
    """Rename Sheet_Optimization_Stages and Site_Loads"""
    print("\n" + "=" * 80)
    print("STEP 2: RENAMING SHEETS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get list of current sheets
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        # Rename Site_Optimization_Stages -> Optimization_Results
        if 'Site_Optimization_Stages' in existing_sheets:
            print("\n📝 Renaming: Site_Optimization_Stages → Optimization_Results")
            worksheet = spreadsheet.worksheet('Site_Optimization_Stages')
            worksheet.update_title('Optimization_Results')
            print("   ✅ Renamed successfully")
        else:
            print("\n   ℹ️  Site_Optimization_Stages not found (may already be renamed)")
        
        # Rename Site_Loads -> Load_Profiles
        if 'Site_Loads' in existing_sheets:
            print("\n📝 Renaming: Site_Loads → Load_Profiles")
            worksheet = spreadsheet.worksheet('Site_Loads')
            worksheet.update_title('Load_Profiles')
            print("   ✅ Renamed successfully")
        else:
            print("\n   ℹ️  Site_Loads not found (may already be renamed)")
        
        # Add missing columns to Optimization_Results
        print("\n📝 Adding missing columns to Optimization_Results...")
        opt_sheet = spreadsheet.worksheet('Optimization_Results')
        headers = opt_sheet.row_values(1)
        
        cols_to_add = []
        if 'run_timestamp' not in headers:
            cols_to_add.append('run_timestamp')
        if 'version' not in headers:
            cols_to_add.append('version')
        if 'solver' not in headers:
            cols_to_add.append('solver')
        if 'opex_annual' not in headers:
            cols_to_add.append('opex_annual')
        
        if cols_to_add:
            # Add to end of headers
            start_col = len(headers) + 1
            for i, col_name in enumerate(cols_to_add):
                col_idx = start_col + i
                # Use update with range notation
                opt_sheet.update_cell(1, col_idx, col_name)
                print(f"   ✅ Added column: {col_name}")
        else:
            print("   ℹ️  All required columns already exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Sheet renaming failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_sites_sheet():
    """Update Sites sheet columns"""
    print("\n" + "=" * 80)
    print("STEP 3: UPDATING SITES SHEET")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet('Sites')
        
        # Get current headers and data
        current_headers = worksheet.row_values(1)
        all_data = worksheet.get_all_values()
        
        print(f"\n📊 Current headers ({len(current_headers)}): {', '.join(current_headers)}")
        
        # Create new header mapping
        new_headers = [
            'name',  # Was Site_Name
            'location',  # Was State, will need manual update
            'iso',  # Keep as-is
            'voltage_kv',  # NEW
            'it_capacity_mw',  # Was IT_Capacity_MW
            'pue',  # Was Design_PUE
            'facility_mw',  # Was Total_Facility_MW
            'land_acres',  # NEW
            'nox_limit_tpy',  # NEW
            'gas_supply_mcf',  # NEW
            'problem_num',  # NEW
            'problem_name',  # NEW
            'geojson',  # NEW
            'created_date',  # Keep
            'updated_date',  # NEW
            'notes'  # Keep
        ]
        
        # Column mapping (old index -> new index)
        # Map existing data to new positions
        old_to_new = {
            current_headers.index('Site_Name'): new_headers.index('name'),
            current_headers.index('State'): new_headers.index('location'),
            current_headers.index('ISO'): new_headers.index('iso'),
            current_headers.index('IT_Capacity_MW'): new_headers.index('it_capacity_mw'),
            current_headers.index('Design_PUE'): new_headers.index('pue'),
            current_headers.index('Total_Facility_MW'): new_headers.index('facility_mw'),
        }
        
        if 'Created_Date' in current_headers:
            old_to_new[current_headers.index('Created_Date')] = new_headers.index('created_date')
        if 'Notes' in current_headers:
            old_to_new[current_headers.index('Notes')] = new_headers.index('notes')
        
        print(f"\n📝 New schema ({len(new_headers)} columns):")
        for header in new_headers:
            print(f"   - {header}")
        
        # Clear sheet and write new structure
        print("\n🔄 Migrating data to new structure...")
        
        # Create new data array
        new_data = []
        new_data.append(new_headers)  # Headers
        
        # Migrate existing data rows
        for row_idx, row in enumerate(all_data[1:], 1):  # Skip header
            if not any(row):  # Skip empty rows
                continue
            
            new_row = [''] * len(new_headers)
            
            # Map existing columns
            for old_idx, new_idx in old_to_new.items():
                if old_idx < len(row):
                    new_row[new_idx] = row[old_idx]
            
            # Set defaults for new columns
            new_row[new_headers.index('voltage_kv')] = '500'  # Default
            new_row[new_headers.index('land_acres')] = '50'  # Default
            new_row[new_headers.index('nox_limit_tpy')] = '100'  # Default
            new_row[new_headers.index('gas_supply_mcf')] = '500000'  # Default
            new_row[new_headers.index('problem_num')] = '1'  # Default to Greenfield
            new_row[new_headers.index('problem_name')] = 'Greenfield Datacenter'
            new_row[new_headers.index('geojson')] = ''  # Empty initially
            new_row[new_headers.index('updated_date')] = datetime.now().isoformat()
            
            new_data.append(new_row)
        
        # Clear and update
        worksheet.clear()
        worksheet.update('A1', new_data)
        
        print(f"   ✅ Migrated {len(new_data)-1} data rows")
        print("   ✅ Added default values for new columns")
        
        return True
        
    except Exception as e:
        print(f"❌ Sites sheet update failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_migration():
    """Verify migration was successful"""
    print("\n" + "=" * 80)
    print("STEP 4: VERIFICATION")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        required_sheets = ['Sites', 'Optimization_Results', 'Load_Profiles', 
                          'Equipment', 'Global_Parameters']
        
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        print("\n✅ Sheet Names:")
        for sheet in required_sheets:
            status = "✅" if sheet in existing_sheets else "❌"
            print(f"   {status} {sheet}")
        
        # Check Sites columns
        sites_sheet = spreadsheet.worksheet('Sites')
        sites_headers = sites_sheet.row_values(1)
        
        required_cols = ['name', 'location', 'problem_num', 'problem_name', 
                        'voltage_kv', 'land_acres', 'nox_limit_tpy', 
                        'gas_supply_mcf', 'geojson']
        
        print("\n✅ Sites Sheet Columns:")
        for col in required_cols:
            status = "✅" if col in sites_headers else "❌"
            print(f"   {status} {col}")
        
        # Count data
        opt_sheet = spreadsheet.worksheet('Optimization_Results')
        opt_data = len([r for r in opt_sheet.get_all_values()[1:] if any(r)])
        
        sites_data = len([r for r in sites_sheet.get_all_values()[1:] if any(r)])
        
        print(f"\n📊 Data Preserved:")
        print(f"   Sites: {sites_data} rows")
        print(f"   Optimization_Results: {opt_data} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("GOOGLE SHEETS MIGRATION - OPTION 1")
    print("Rename sheets and add columns to match code")
    print("=" * 80)
    
    # Step 1: Backup
    if not backup_sheet_data():
        print("\n❌ Migration aborted - backup failed")
        sys.exit(1)
    
    print("\n⚠️  Backup complete. Proceeding with migration...")
    input("Press ENTER to continue or Ctrl+C to abort...")
    
    # Step 2: Rename sheets
    if not rename_sheets():
        print("\n❌ Migration failed at sheet renaming")
        sys.exit(1)
    
    # Step 3: Update Sites sheet
    if not update_sites_sheet():
        print("\n❌ Migration failed at Sites sheet update")
        sys.exit(1)
    
    # Step 4: Verify
    if not verify_migration():
        print("\n⚠️  Migration completed but verification had issues")
    else:
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review Sites sheet - update 'location' field manually if needed")
        print("2. Update site-specific values (voltage_kv, land_acres, etc.)")
        print("3. Set correct problem_num for each site")
        print("4. Test application to ensure data loads correctly")
        print("\nBackup file saved for rollback if needed")
