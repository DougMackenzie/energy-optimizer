#!/usr/bin/env python3
"""
Update Sites Sheet - Continue migration after sheets already renamed
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client
from datetime import datetime

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def add_missing_columns():
    """Add missing columns to Optimization_Results"""
    print("=" * 80)
    print("ADDING MISSING COLUMNS TO OPTIMIZATION_RESULTS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        opt_sheet = spreadsheet.worksheet('Optimization_Results')
        
        headers = opt_sheet.row_values(1)
        print(f"\nCurrent headers ({len(headers)}): {', '.join(headers)}")
        
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
            start_col = len(headers) + 1
            for i, col_name in enumerate(cols_to_add):
                col_idx = start_col + i
                opt_sheet.update_cell(1, col_idx, col_name)
                print(f"   ✅ Added column: {col_name} at position {col_idx}")
        else:
            print("   ℹ️  All required columns already exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_sites_sheet():
    """Update Sites sheet columns"""
    print("\n" + "=" * 80)
    print("UPDATING SITES SHEET")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet('Sites')
        
        # Get current data
        current_headers = worksheet.row_values(1)
        all_data = worksheet.get_all_values()
        
        print(f"\n📊 Current headers ({len(current_headers)}):")
        for i, h in enumerate(current_headers, 1):
            print(f"   {i}. {h}")
        
        # New header schema
        new_headers = [
            'name',           # Was Site_Name
            'location',      # Was State            'iso',            # Keep
            'voltage_kv',    # NEW
            'it_capacity_mw',  # Was IT_Capacity_MW
            'pue',           # Was Design_PUE
            'facility_mw',   # Was Total_Facility_MW
            'land_acres',    # NEW
            'nox_limit_tpy', # NEW
            'gas_supply_mcf',  # NEW
            'problem_num',   # NEW
            'problem_name',  # NEW
            'geojson',       # NEW
            'created_date',  # Keep if exists
            'updated_date',  # NEW
            'notes'          # Keep if exists
        ]
        
        print(f"\n📝 New schema ({len(new_headers)} columns):")
        for header in new_headers:
            print(f"   - {header}")
        
        # Create mapping
        print("\n🔄 Migrating data...")
        new_data = [new_headers]
        
        # Process data rows
        for row in all_data[1:]:
            if not any(row):
                continue
            
            new_row = [''] * len(new_headers)
            
            # Manual mapping of existing fields
            try:
                if 'Site_Name' in current_headers:
                    new_row[0] = row[current_headers.index('Site_Name')]  # name
                if 'State' in current_headers:
                    new_row[1] = row[current_headers.index('State')]  # location
                if 'ISO' in current_headers:
                    new_row[2] = row[current_headers.index('ISO')]  # iso
                if 'IT_Capacity_MW' in current_headers:
                    new_row[4] = row[current_headers.index('IT_Capacity_MW')]  # it_capacity_mw
                if 'Design_PUE' in current_headers:
                    new_row[5] = row[current_headers.index('Design_PUE')]  # pue
                if 'Total_Facility_MW' in current_headers:
                    new_row[6] = row[current_headers.index('Total_Facility_MW')]  # facility_mw
                if 'Created_Date' in current_headers:
                    new_row[13] = row[current_headers.index('Created_Date')]  # created_date
                if 'Notes' in current_headers:
                    new_row[15] = row[current_headers.index('Notes')]  # notes
            except IndexError:
                pass  # Row might be shorter
            
            # Set defaults for new fields
            new_row[3] = '500'  # voltage_kv default
            new_row[7] = '50'   # land_acres default
            new_row[8] = '100'  # nox_limit_tpy default
            new_row[9] = '500000'  # gas_supply_mcf default
            new_row[10] = '1'   # problem_num (Greenfield)
            new_row[11] = 'Greenfield Datacenter'  # problem_name
            new_row[12] = ''    # geojson (empty)
            new_row[14] = datetime.now().isoformat()  # updated_date
            
            new_data.append(new_row)
        
        # Update sheet
        worksheet.clear()
        worksheet.update('A1', new_data)
        
        print(f"   ✅ Migrated {len(new_data)-1} data rows")
        print("   ✅ Set default values for new columns")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_migration():
    """Verify final state"""
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check sheet names
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        required_sheets = ['Sites', 'Optimization_Results', 'Load_Profiles']
        
        print("\n✅ Required Sheets:")
        for sheet in required_sheets:
            status = "✅" if sheet in existing_sheets else "❌"
            print(f"   {status} {sheet}")
        
        # Check Sites columns
        sites_sheet = spreadsheet.worksheet('Sites')
        sites_headers = sites_sheet.row_values(1)
        
        required_cols = ['name', 'location', 'problem_num', 'voltage_kv', 
                        'land_acres', 'geojson']
        
        print("\n✅ Sites Critical Columns:")
        for col in required_cols:
            status = "✅" if col in sites_headers else "❌"
            print(f"   {status} {col}")
        
        # Count data
        sites_data = len([r for r in sites_sheet.get_all_values()[1:] if any(r)])
        print(f"\n📊 Sites: {sites_data} data rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


if __name__ == '__main__':
    print("\n🚀 Continuing migration: Update Sites sheet and add columns\n")
    
    # Add missing columns to Optimization_Results
    add_missing_columns()
    
    # Update Sites sheet
    if update_sites_sheet():
        verify_migration()
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 80)
    else:
        print("\n❌ Migration failed")
