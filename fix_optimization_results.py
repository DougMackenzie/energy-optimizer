#!/usr/bin/env python3
"""
Fix Optimization_Results Sheet Save/Load System
Ensures column headers match save/load expectations
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client

SHEETID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

# Correct column headers for Optimization_Results sheet
CORRECT_HEADERS = [
    'site_name',
    'stage',
    'complete',
    'lcoe',
    'npv',
    'equipment_json',
    'dispatch_summary_json',
    'completion_date',
    'notes',
    'load_coverage',
    'constraints_json',
    'capex_json',
    'runtime_seconds'
]

def fix_optimization_results_headers():
    """Ensure Optimization_Results has correct headers"""
    print("=" * 80)
    print("FIXING OPTIMIZATION_RESULTS HEADERS")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        opt_results = spreadsheet.worksheet('Optimization_Results')
        
        # Get current headers
        current_headers = opt_results.row_values(1)
        print(f"\nCurrent headers ({len(current_headers)}):")
        for i, h in enumerate(current_headers, 1):
            print(f"   {i:2}. {h}")
        
        # Check if headers match
        if current_headers == CORRECT_HEADERS:
            print("\n✅ Headers already correct!")
            return True
        
        # Get all data
        all_data = opt_results.get_all_values()
        
        if len(all_data) <= 1:
            # Just headers or empty, safe to update
            opt_results.update('A1', [CORRECT_HEADERS])
            print("\n✅ Headers updated (no data rows)")
            return True
        
        print(f"\n⚠️  WARNING: {len(all_data)-1} data rows exist")
        print("   Need to verify data alignment before changing headers")
        
        # Show what we would map
        print("\n📊 Proposed header mapping:")
        for i, (curr, new) in enumerate(zip(current_headers, CORRECT_HEADERS), 1):
            if curr != new:
                print(f"   {i:2}. {curr:30} → {new}")
            else:
                print(f"   {i:2}. {curr:30} (unchanged)")
        
        response = input("\n⚠️  Update headers? (yes/no): ").strip().lower()
        
        if response == 'yes':
            opt_results.update('A1', [CORRECT_HEADERS])
            print("\n✅ Headers updated!")
            return True
        else:
            print("\n❌ Skipped header update")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_data_loading():
    """Test loading Austin results"""
    print("\n" + "=" * 80)
    print("VERIFYING DATA LOADING")
    print("=" * 80)
    
    try:
        from app.utils.site_backend import load_site_stage_result
        
        test_cases = [
            ("Austin Greenfield DC", "screening"),
            ("Austin Greenfield DC", "concept"),
            ("Austin Greenfield DC", "preliminary"),
            ("Austin Greenfield DC", "detailed"),
        ]
        
        for site, stage in test_cases:
            result = load_site_stage_result(site, stage)
            if result:
                print(f"\n✅ {site} - {stage}:")
                print(f"   LCOE: {result.get('lcoe', 'MISSING')}")
                print(f"   NPV: {result.get('npv', 'MISSING')}")
                print(f"   Equipment: {len(result.get('equipment', {}))} items")
                print(f"   Coverage: {result.get('load_coverage', 'MISSING')}")
            else:
                print(f"\n❌ {site} - {stage}: NOT FOUND")
        
        return True
        
    except Exception as e:
        print(f "\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("OPTIMIZATION_RESULTS SHEET FIX")
    print("=" * 80)
    
    # Step 1: Fix headers
    if fix_optimization_results_headers():
        print("\n✅ Headers fixed")
    
    # Step 2: Test loading
    verify_data_loading()
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
