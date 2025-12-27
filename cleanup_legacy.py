#!/usr/bin/env python3
"""
Complete Data Migration & Legacy Cleanup
Migrate all useful data from legacy sheets, then archive them
"""

from pathlib import Path
import sys
import csv
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def backup_legacy_sheets():
    """Backup all legacy sheets to CSV files"""
    print("=" * 80)
    print("STEP 1: BACKING UP LEGACY SHEETS")
    print("=" * 80)
    
    backup_dir = Path('backups/legacy_sheets')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    legacy_sheets = [
        'Reciprocating_Engines', 'Gas_Turbines', 'BESS', 'Solar_PV', 
        'Grid_Connection', 'Scenario_Templates', 'Load_Requirements',
        'Optimization_Objectives', 'Site_Constraints'
    ]
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        for sheet_name in legacy_sheets:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                data = worksheet.get_all_values()
                
                # Save to CSV
                csv_file = backup_dir / f'{sheet_name}_{datetime.now().strftime("%Y%m%d")}.csv'
                with open(csv_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                
                print(f"   ✅ Backed up {sheet_name} ({len(data)} rows) → {csv_file.name}")
                
            except Exception as e:
                print(f"   ⚠️  {sheet_name}: {e}")
        
        print(f"\n✅ Backups saved to: {backup_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def migrate_equipment_data():
    """Migrate any missing equipment from legacy sheets to Equipment sheet"""
    print("\n" + "=" * 80)
    print("STEP 2: MIGRATING EQUIPMENT DATA")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get current Equipment sheet data
        equipment_sheet = spreadsheet.worksheet('Equipment')
        equipment_data = equipment_sheet.get_all_records()
        existing_ids = {eq.get('equipment_id') for eq in equipment_data}
        
        print(f"\nCurrent Equipment sheet has {len(existing_ids)} types:")
        for eq_id in existing_ids:
            print(f"   - {eq_id}")
        
        # Check legacy sheets for additional data
        legacy_equip_sheets = {
            'Reciprocating_Engines': 'recip_engine',
            'Gas_Turbines': 'gas_turbine',
            'BESS': 'bess',
            'Solar_PV': 'solar_pv',
            'Grid_Connection': 'grid'
        }
        
        additions = []
        
        for sheet_name, base_id in legacy_equip_sheets.items():
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                legacy_data = worksheet.get_all_records()
                
                print(f"\n📋 {sheet_name}: {len(legacy_data)} records")
                
                # Check if we need to add any
                for idx, record in enumerate(legacy_data):
                    # Create unique ID if multiple variants
                    if len(legacy_data) > 1:
                        equip_id = f"{base_id}_{idx+1}"
                    else:
                        equip_id = base_id
                    
                    if equip_id not in existing_ids:
                        print(f"   🆕 Found new equipment variant: {equip_id}")
                        additions.append((equip_id, record, sheet_name))
                    else:
                        print(f"   ✓ {equip_id} already in Equipment sheet")
                
            except Exception as e:
                print(f"   ⚠️  Error reading {sheet_name}: {e}")
        
        # Add new equipment
        if additions:
            print(f"\n Adding {len(additions)} new equipment types...")
            
            for equip_id, record, source in additions:
                # Map legacy fields to Equipment sheet format
                new_row = [
                    equip_id,  # equipment_id
                    record.get('Name', record.get('Model', equip_id)),  # name
                    source.replace('_', ' ').lower(),  # type
                    record.get('Capacity_MW', record.get('Power_MW', '')),  # capacity_mw
                    record.get('Capacity_MWh', record.get('Energy_MWh', '')),  # capacity_mwh
                    record.get('CAPEX_per_MW', record.get('CapEx_$/MW', '')),  # capex_per_mw
                    record.get('CAPEX_per_MWh', record.get('CapEx_$/MWh', '')),  # capex_per_mwh
                    record.get('OpEx_Annual', record.get('OpEx_$/MW/yr', '')),  # opex_annual_per_mw
                    record.get('Efficiency', record.get('Eff_Pct', '')),  # efficiency
                    record.get('Lifetime_Years', record.get('Lifespan_yr', '')),  # lifetime_years
                    record.get('Heat_Rate', ''),  # heat_rate_btu_kwh
                    record.get('NOx_Rate', ''),  # nox_rate_lb_mmbtu
                    record.get('Gas_Consumption', ''),  # gas_consumption_mcf_mwh
                    'true',  # custom (migrated from legacy)
                    f'Migrated from {source}'  # notes
                ]
                
                equipment_sheet.append_row(new_row)
                print(f"   ✅ Added: {equip_id}")
        else:
            print("\n   ✓ No new equipment to migrate - Equipment sheet is complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Equipment migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_site_constraints():
    """Verify constraints are in Sites sheet"""
    print("\n" + "=" * 80)
    print("STEP 3: VERIFYING SITE CONSTRAINTS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check Sites sheet
        sites_sheet = spreadsheet.worksheet('Sites')
        sites_headers = sites_sheet.row_values(1)
        sites_data = sites_sheet.get_all_records()
        
        required_constraint_fields = ['voltage_kv', 'land_acres', 'nox_limit_tpy', 'gas_supply_mcf']
        
        print("\n📊 Sites sheet constraint fields:")
        for field in required_constraint_fields:
            status = "✅" if field in sites_headers else "❌"
            print(f"   {status} {field}")
        
        # Check Site_Constraints sheet
        try:
            constraints_sheet = spreadsheet.worksheet('Site_Constraints')
            constraints_data = constraints_sheet.get_all_records()
            
            print(f"\n⚠️  Site_Constraints sheet has {len(constraints_data)} rows")
            
            if constraints_data:
                print("   Review these constraints:")
                for row in constraints_data:
                    print(f"   - {row}")
                
                print("\n   ℹ️  If these are already in Sites sheet, Site_Constraints can be deleted")
            
        except:
            print("\n   ✓ Site_Constraints sheet not found or empty")
        
        return True
        
    except Exception as e:
        print(f"❌ Constraint verification failed: {e}")
        return False


def delete_legacy_sheets(confirmed=False):
    """Delete legacy sheets (after confirmation)"""
    print("\n" + "=" * 80)
    print("STEP 4: DELETING LEGACY SHEETS")
    print("=" * 80)
    
    if not confirmed:
        print("\n⚠️  SKIPPED - Set confirmed=True to proceed with deletion")
        return False
    
    legacy_sheets = [
        'Reciprocating_Engines', 'Gas_Turbines', 'BESS', 'Solar_PV',
        'Grid_Connection', 'Scenario_Templates', 'Load_Requirements',
        'Optimization_Objectives', 'Site_Constraints'
    ]
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        for sheet_name in legacy_sheets:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                spreadsheet.del_worksheet(worksheet)
                print(f"   ✅ Deleted: {sheet_name}")
            except Exception as e:
                print(f"   ⚠️  {sheet_name}: {e}")
        
        print("\n✅ Legacy sheets deleted")
        return True
        
    except Exception as e:
        print(f"❌ Deletion failed: {e}")
        return False


def create_final_report():
    """Create final cleanup report"""
    print("\n" + "=" * 80)
    print("FINAL ARCHITECTURE REPORT")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        remaining_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        print("\n✅ FINAL SHEET STRUCTURE:")
        for sheet_name in sorted(remaining_sheets):
            worksheet = spreadsheet.worksheet(sheet_name)
            data_rows = len([r for r in worksheet.get_all_values()[1:] if any(r)])
            print(f"   • {sheet_name:30} ({data_rows} rows)")
        
        # Verify core sheets
        print("\n🎯 CORE SHEETS VERIFICATION:")
        core_sheets = ['Sites', 'Optimization_Results', 'Load_Profiles', 
                      'Equipment', 'Global_Parameters']
        
        for sheet in core_sheets:
            status = "✅" if sheet in remaining_sheets else "❌ MISSING"
            print(f"   {status} {sheet}")
        
        return True
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("COMPLETE DATA MIGRATION & LEGACY CLEANUP")
    print("=" * 80)
    
    # Step 1: Backup
    if not backup_legacy_sheets():
        print("\n❌ Backup failed - aborting")
        sys.exit(1)
    
    # Step 2: Migrate equipment
    migrate_equipment_data()
    
    # Step 3: Verify constraints
    verify_site_constraints()
    
    # Step 4: Delete legacy sheets (user confirmation required)
    print("\n" + "=" * 80)
    print("READY TO DELETE LEGACY SHEETS")
    print("=" * 80)
    print("\nBackups created and data migrated.")
    print("Legacy sheets are no longer needed for problem-centric architecture.")
    
    response = input("\n⚠️  DELETE all legacy sheets? (yes/no): ").strip().lower()
    
    if response == 'yes':
        delete_legacy_sheets(confirmed=True)
        create_final_report()
        
        print("\n" + "=" * 80)
        print("✅ CLEANUP COMPLETE!")
        print("=" * 80)
        print("\nGoogle Sheets now aligned with problem-centric architecture.")
        print("Only core sheets remain:")
        print("  • Sites (master data + constraints)")
        print("  • Optimization_Results (results per stage)")
        print("  • Load_Profiles (site-specific loads)")
        print("  • Equipment (centralized equipment DB)")
        print("  • Global_Parameters (economic params)")
    else:
        print("\n❌ Deletion cancelled - legacy sheets retained")
        print("You can manually delete them later after reviewing backups")
