#!/usr/bin/env python3
"""
Complete Sheets Architecture Audit
Identify legacy sheets vs. current problem-centric architecture
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def audit_all_sheets():
    """Complete audit of all sheets"""
    print("=" * 80)
    print("COMPLETE GOOGLE SHEETS ARCHITECTURE AUDIT")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        all_sheets = []
        
        for worksheet in spreadsheet.worksheets():
            sheet_info = {
                'name': worksheet.title,
                'rows': worksheet.row_count,
                'cols': worksheet.col_count,
                'headers': worksheet.row_values(1) if worksheet.row_count > 0 else [],
                'data_rows': len([r for r in worksheet.get_all_values()[1:] if any(r)])
            }
            all_sheets.append(sheet_info)
        
        # Categorize sheets
        print("\n" + "=" * 80)
        print("SHEET CATEGORIZATION")
        print("=" * 80)
        
        # Current architecture (problem-centric)
        current_sheets = {
            'Sites': 'Core - Site master data with constraints',
            'Optimization_Results': 'Core - Results per site/stage (just renamed)',
            'Load_Profiles': 'Core - Load profile data per site (just renamed)',
            'Equipment': 'Phase 2 - Centralized equipment database',
            'Global_Parameters': 'Phase 2 - Economic & constraint parameters'
        }
        
        # Legacy scenario-based architecture
        legacy_sheets = {
            'Reciprocating_Engines': 'LEGACY - Equipment data (now in Equipment sheet)',
            'Gas_Turbines': 'LEGACY - Equipment data (now in Equipment sheet)',
            'BESS': 'LEGACY - Equipment data (now in Equipment sheet)',
            'Solar_PV': 'LEGACY - Equipment data (now in Equipment sheet)',
            'Grid_Connection': 'LEGACY - Equipment data (now in Equipment sheet)',
            'Scenario_Templates': 'LEGACY - Old scenario-based approach',
            'Load_Requirements': 'LEGACY - Now site-specific (in Sites)',
            'Optimization_Objectives': 'LEGACY - Now problem-type specific',
            'Site_Constraints': 'LEGACY - Now in Sites sheet'
        }
        
        print("\n✅ CURRENT ARCHITECTURE (Problem-Centric):")
        for sheet_name, purpose in current_sheets.items():
            found = next((s for s in all_sheets if s['name'] == sheet_name), None)
            if found:
                print(f"   ✅ {sheet_name:25} - {found['data_rows']:3} rows  | {purpose}")
            else:
                print(f"   ❌ {sheet_name:25} - MISSING | {purpose}")
        
        print("\n⚠️  LEGACY SHEETS (Scenario-Based - Can be archived):")
        for sheet_name, purpose in legacy_sheets.items():
            found = next((s for s in all_sheets if s['name'] == sheet_name), None)
            if found:
                print(f"   ⚠️  {sheet_name:25} - {found['data_rows']:3} rows  | {purpose}")
        
        # Check for orphaned sheets
        known_sheets = set(current_sheets.keys()) | set(legacy_sheets.keys())
        orphaned = [s for s in all_sheets if s['name'] not in known_sheets]
        
        if orphaned:
            print("\n❓ UNKNOWN/ORPHANED SHEETS:")
            for sheet in orphaned:
                print(f"   ❓ {sheet['name']:25} - {sheet['data_rows']:3} rows")
        
        # Analysis
        print("\n" + "=" * 80)
        print("ARCHITECTURE ANALYSIS")
        print("=" * 80)
        
        print("\n📊 Current Problem-Centric Flow:")
        print("   1. User selects SITE (from Sites sheet)")
        print("   2. User selects PROBLEM TYPE (1-5, stored in site.problem_num)")
        print("   3. User configures LOAD (stored in Load_Profiles sheet)")
        print("   4. System loads EQUIPMENT specs (from Equipment sheet)")
        print("   5. System applies CONSTRAINTS (from Sites sheet)")
        print("   6. System applies PARAMETERS (from Global_Parameters sheet)")
        print("   7. Optimizer runs problem-specific analysis")
        print("   8. Results saved (to Optimization_Results sheet)")
        
        print("\n⚠️  Legacy Scenario-Based Flow (DEPRECATED):")
        print("   1. User selected scenario template")
        print("   2. Template referenced separate equipment sheets")
        print("   3. Load requirements were generic")
        print("   4. No problem-type concept")
        
        print("\n🔄 Data Migration Status:")
        
        # Check if Equipment sheet has all equipment types
        equipment_sheet = next((s for s in all_sheets if s['name'] == 'Equipment'), None)
        if equipment_sheet:
            print(f"\n   Equipment sheet: {equipment_sheet['data_rows']} equipment types")
            print("   ✅ Centralized equipment database exists")
            
            # Check legacy equipment sheets
            legacy_equip = ['Reciprocating_Engines', 'Gas_Turbines', 'BESS', 'Solar_PV', 'Grid_Connection']
            legacy_data_rows = sum(s['data_rows'] for s in all_sheets if s['name'] in legacy_equip)
            print(f"   ⚠️  Legacy equipment sheets: {legacy_data_rows} total rows")
            
            if legacy_data_rows > equipment_sheet['data_rows']:
                print("   ⚠️  WARNING: Legacy sheets have more data than Equipment sheet")
                print("   ➡️  ACTION: Review legacy data before deletion")
            else:
                print("   ✅ Equipment sheet appears complete")
        
        # Check Sites sheet for constraints
        sites_sheet = next((s for s in all_sheets if s['name'] == 'Sites'), None)
        if sites_sheet:
            required_constraint_fields = ['voltage_kv', 'land_acres', 'nox_limit_tpy', 'gas_supply_mcf']
            has_constraints = all(field in sites_sheet['headers'] for field in required_constraint_fields)
            
            if has_constraints:
                print("\n   ✅ Sites sheet has all constraint fields")
                
                # Check Site_Constraints
                site_constraints = next((s for s in all_sheets if s['name'] == 'Site_Constraints'), None)
                if site_constraints and site_constraints['data_rows'] > 0:
                    print(f"   ⚠️  Site_Constraints sheet exists with {site_constraints['data_rows']} rows")
                    print("   ➡️  ACTION: Verify constraints migrated to Sites sheet")
                else:
                    print("   ✅ Site_Constraints can be safely archived")
            else:
                print("   ❌ Sites sheet missing constraint fields!")
        
        return all_sheets, current_sheets, legacy_sheets
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def create_cleanup_plan(all_sheets, current_sheets, legacy_sheets):
    """Create detailed cleanup/migration plan"""
    print("\n" + "=" * 80)
    print("CLEANUP & MIGRATION PLAN")
    print("=" * 80)
    
    print("\n📋 RECOMMENDED ACTIONS:")
    
    print("\n1️⃣ IMMEDIATE - Verify Data Migration:")
    print("   [ ] Compare Equipment sheet vs. legacy equipment sheets")
    print("   [ ] Verify all equipment types present in Equipment sheet")
    print("   [ ] Check if any custom equipment in legacy sheets")
    print("   [ ] Verify Sites constraints vs. Site_Constraints")
    
    print("\n2️⃣ SAFE TO ARCHIVE (After Verification):")
    print("   Legacy equipment sheets:")
    for name in ['Reciprocating_Engines', 'Gas_Turbines', 'BESS', 'Solar_PV', 'Grid_Connection']:
        sheet = next((s for s in all_sheets if s['name'] == name), None)
        if sheet:
            print(f"   [ ] {name:25} ({sheet['data_rows']} rows)")
    
    print("\n   Legacy process sheets:")
    for name in ['Scenario_Templates', 'Load_Requirements', 'Optimization_Objectives', 'Site_Constraints']:
        sheet = next((s for s in all_sheets if s['name'] == name), None)
        if sheet:
            print(f"   [ ] {name:25} ({sheet['data_rows']} rows)")
    
    print("\n3️⃣ BACKUP BEFORE DELETION:")
    print("   [ ] Export each legacy sheet to CSV")
    print("   [ ] Store in /backups/legacy_sheets/ folder")
    print("   [ ] Document what was in each sheet")
    
    print("\n4️⃣ DELETE LEGACY SHEETS:")
    print("   [ ] Only after verification and backup")
    print("   [ ] Delete in order (least critical first)")
    print("   [ ] Test app after each deletion")
    
    print("\n5️⃣ FINAL VERIFICATION:")
    print("   [ ] App loads without errors")
    print("   [ ] All problems (P1-P5) work correctly")
    print("   [ ] Equipment database complete")
    print("   [ ] Site constraints working")


if __name__ == '__main__':
    all_sheets, current_sheets, legacy_sheets = audit_all_sheets()
    
    if all_sheets:
        create_cleanup_plan(all_sheets, current_sheets, legacy_sheets)
        
        print("\n" + "=" * 80)
        print("✅ AUDIT COMPLETE")
        print("=" * 80)
        print("\nNext: Review output and decide on cleanup approach")
