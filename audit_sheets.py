#!/usr/bin/env python3
"""
Google Sheets Audit and Phase 2 Implementation
Audits current sheet structure and implements Phase 2 features
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client

def audit_sheets():
    """Audit current Google Sheets structure"""
    print("=" * 80)
    print("GOOGLE SHEETS STRUCTURE AUDIT")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key("1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so")
        
        sheets_info = []
        
        for worksheet in spreadsheet.worksheets():
            print(f"\n📄 Sheet: {worksheet.title}")
            print(f"   Rows: {worksheet.row_count}, Cols: {worksheet.col_count}")
            
            # Get headers
            headers = worksheet.row_values(1) if worksheet.row_count > 0 else []
            if headers:
                print(f"   Headers ({len(headers)}):")
                for i, h in enumerate(headers, 1):
                    print(f"      {i}. {h}")
            
            # Get data row count
            all_values = worksheet.get_all_values()
            data_rows = len([r for r in all_values[1:] if any(r)])  # Exclude header
            print(f"   Data rows: {data_rows}")
            
            sheets_info.append({
                'name': worksheet.title,
                'headers': headers,
                'data_rows': data_rows
            })
        
        print("\n" + "=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        
        # Check for required sheets
        sheet_names = [s['name'] for s in sheets_info]
        
        required_sheets = ['Sites', 'Optimization_Results', 'Load_Profiles']
        phase2_sheets = ['Equipment', 'Global_Parameters']
        
        print("\n✅ Required Sheets:")
        for sheet in required_sheets:
            status = "✅" if sheet in sheet_names else "❌ MISSING"
            print(f"   {status} {sheet}")
        
        print("\n📋 Phase 2 Sheets:")
        for sheet in phase2_sheets:
            status = "✅ EXISTS" if sheet in sheet_names else "❌ NEEDS CREATION"
            print(f"   {status} {sheet}")
        
        # Check for legacy/unused fields
        print("\n🔍 Field Analysis:")
        
        sites_sheet = next((s for s in sheets_info if s['name'] == 'Sites'), None)
        if sites_sheet:
            print(f"\n   Sites sheet has {len(sites_sheet['headers'])} fields:")
            essential_fields = [
                'name', 'location', 'iso', 'voltage_kv', 'it_capacity_mw', 
                'pue', 'facility_mw', 'land_acres', 'nox_limit_tpy', 
                'gas_supply_mcf', 'problem_num', 'problem_name', 'geojson'
            ]
            
            for field in sites_sheet['headers']:
                if field in essential_fields:
                    print(f"      ✅ {field} (essential)")
                elif field:
                    print(f"      ⚠️  {field} (review needed)")
        
        return sheets_info
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_phase2_sheets():
    """Create Equipment and Global_Parameters sheets if they don't exist"""
    print("\n" + "=" * 80)
    print("PHASE 2: CREATING MISSING SHEETS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key("1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so")
        
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        
        # Create Equipment sheet
        if 'Equipment' not in existing_sheets:
            print("\n📝 Creating Equipment sheet...")
            worksheet = spreadsheet.add_worksheet(title="Equipment", rows=100, cols=15)
            
            # Set headers
            headers = [
                'equipment_id', 'name', 'type', 'capacity_mw', 'capacity_mwh',
                'capex_per_mw', 'capex_per_mwh', 'opex_annual_per_mw',
                'efficiency', 'lifetime_years', 'heat_rate_btu_kwh',
                'nox_rate_lb_mmbtu', 'gas_consumption_mcf_mwh',
                'custom', 'notes'
            ]
            worksheet.update('A1:O1', [headers])
            
            # Add default equipment
            default_equipment = [
                ['recip_engine', 'Reciprocating Engine', 'generator', '1', '', '1800000', '', '45000', '0.42', '25', '8500', '0.15', '7.2', 'false', 'Natural gas recip engine'],
                ['gas_turbine', 'Gas Turbine', 'generator', '1', '', '1200000', '', '35000', '0.35', '25', '10500', '0.10', '8.5', 'false', 'Industrial gas turbine'],
                ['bess', 'Battery Energy Storage', 'storage', '', '1', '250000', '350000', '5000', '0.90', '15', '', '', '', 'false', 'Lithium-ion BESS'],
                ['solar_pv', 'Solar PV', 'renewable', '1', '', '1000000', '', '12000', '0.20', '30', '', '', '', 'false', 'Utility-scale solar'],
                ['grid', 'Grid Connection', 'utility', '1', '', '500000', '', '0', '1.00', '50', '', '', '', 'false', 'Utility grid interconnection']
            ]
            
            for i, equip in enumerate(default_equipment, 2):
                worksheet.update(f'A{i}:O{i}', [equip])
            
            print("   ✅ Equipment sheet created with default equipment")
        else:
            print("\n   ✅ Equipment sheet already exists")
        
        # Create Global_Parameters sheet
        if 'Global_Parameters' not in existing_sheets:
            print("\n📝 Creating Global_Parameters sheet...")
            worksheet = spreadsheet.add_worksheet(title="Global_Parameters", rows=50, cols=5)
            
            # Set headers
            headers = ['parameter_name', 'value', 'unit', 'category', 'description']
            worksheet.update('A1:E1', [headers])
            
            # Add default parameters
            default_params = [
                ['discount_rate', '0.08', 'decimal', 'economic', 'Annual discount rate for NPV calculations'],
                ['analysis_period_years', '15', 'years', 'economic', 'Project analysis period'],
                ['electricity_price', '80', '$/MWh', 'economic', 'Average electricity price'],
                ['gas_price', '5', '$/MCF', 'economic', 'Natural gas price'],
                ['capacity_price', '150', '$/kW-year', 'economic', 'Capacity market price'],
                ['default_availability', '0.95', 'decimal', 'constraint', 'Default equipment availability'],
                ['n_minus_1_default', 'true', 'boolean', 'constraint', 'N-1 redundancy by default'],
                ['emissions_limit_factor', '1.0', 'decimal', 'constraint', 'Emissions limit multiplier'],
            ]
            
            for i, param in enumerate(default_params, 2):
                worksheet.update(f'A{i}:E{i}', [param])
            
            print("   ✅ Global_Parameters sheet created with defaults")
        else:
            print("\n   ✅ Global_Parameters sheet already exists")
        
        print("\n✅ Phase 2 sheets ready!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sheets: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_notes_column():
    """Add 'notes' column to Optimization_Results if missing"""
    print("\n" + "=" * 80)
    print("ADDING NOTES COLUMN TO OPTIMIZATION_RESULTS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key("1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so")
        
        worksheet = spreadsheet.worksheet('Optimization_Results')
        headers = worksheet.row_values(1)
        
        if 'notes' not in headers:
            print("\n📝 Adding 'notes' column...")
            # Add to the end
            col_letter = chr(65 + len(headers))  # A=65, B=66, etc.
            worksheet.update(f'{col_letter}1', 'notes')
            print(f"   ✅ Added 'notes' column at position {col_letter}")
        else:
            print("\n   ✅ 'notes' column already exists")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("\n🚀 Starting Google Sheets Audit and Phase 2 Implementation\n")
    
    # Step 1: Audit current structure
    sheets_info = audit_sheets()
    
    if sheets_info:
        # Step 2: Create Phase 2 sheets
        create_phase2_sheets()
        
        # Step 3: Add notes column
        add_notes_column()
        
        print("\n" + "=" * 80)
        print("✅ AUDIT AND PHASE 2 IMPLEMENTATION COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review audit output above")
        print("2. Remove any unnecessary legacy fields manually if needed")
        print("3. Test Equipment and Global_Parameters sync functions")
    else:
        print("\n❌ Audit failed - cannot proceed with Phase 2")
