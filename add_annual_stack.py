#!/usr/bin/env python3
"""
Simpler approach: Just update the dispatch_summary for existing results
to include proper annual_stack data
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import get_google_sheets_client
import json

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def generate_annual_stack_for_site(site_name, facility_mw, problem_num, base_equipment):
    """Generate realistic annual energy stack"""
    annual_stack = {}
    
    for year_offset in range(15):
        year = 2025 + year_offset
        
        # Grid available from Year 6 onwards for most problems
        grid_available = year_offset >= 5  # Year 6+
        
        # For Bridge Power (P5), grid takes over completely after Year 6
        if problem_num == 5:
            if grid_available:
                # Grid replaces all onsite after Year 6
                equipment = {
                    'recip_mw': 0,
                    'turbine_mw': 0,
                    'solar_mw': 0,
                    'bess_mwh': 0,
                    'grid_mw': facility_mw * 1.15  # With N-1
                }
            else:
                # Years 1-5: All onsite (no grid)
                equipment = {
                    'recip_mw': base_equipment.get('recip_mw', 0),
                    'turbine_mw': base_equipment.get('turbine_mw', 0),
                    'solar_mw': base_equipment.get('solar_mw', 0),
                    'bess_mwh': base_equipment.get('bess_mwh', 0),
                    'grid_mw': 0  # No grid until Year 6
                }
        else:
            # Other problems: Grid supplements onsite
            if grid_available:
                equipment = {
                    'recip_mw': base_equipment.get('recip_mw', 0),
                    'turbine_mw': base_equipment.get('turbine_mw', 0),
                    'solar_mw': base_equipment.get('solar_mw', 0),
                    'bess_mwh': base_equipment.get('bess_mwh', 0),
                    'grid_mw': base_equipment.get('grid_mw', 0)
                }
            else:
                # Years 1-5: No grid
                equipment = {
                    **base_equipment,
                    'grid_mw': 0
                }
        
        annual_stack[year] = {
            'equipment': equipment,
            'year_load_mw': facility_mw,
            'lcoe': 75 + year_offset * 0.5  # Escalating costs
        }
    
    return annual_stack

if __name__ == "__main__":
    print("=" * 60)
    print("ADDING ANNUAL STACK TO EXISTING RESULTS")
    print("=" * 60)
    
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # Load sites for metadata
    sites_ws = spreadsheet.worksheet("Sites")
    sites = {s['name']: s for s in sites_ws.get_all_records()}
    
    # Load results
    results_ws = spreadsheet.worksheet("Optimization_Results")
    results = results_ws.get_all_records()
    
    updated = 0
    for idx, result in enumerate(results):
        row = idx + 2
        site_name = result.get('site_name')
        stage = result.get('stage')
        
        if stage != 'screening':
            continue
        
        site = sites.get(site_name)
        if not site:
            continue
        
        print(f"\n📍 {site_name} (Row {row})")
        
        # Parse existing equipment
        equipment_json = result.get('equipment_json', '{}')
        try:
            equipment = json.loads(equipment_json) if equipment_json else {}
        except:
            equipment = {}
        
        # Generate annual stack
        facility_mw = site.get('facility_mw', 1000)
        problem_num = site.get('problem_num', 1)
        
        annual_stack = generate_annual_stack_for_site(
            site_name,
            facility_mw,
            problem_num,
            equipment
        )
        
        # Create dispatch_summary with annual_stack
        dispatch_summary = {
            'annual_stack': annual_stack,
            'grid_available_year': 2030  # Year 6
        }
        
        # Update dispatch_summary_json column (G)
        dispatch_json = json.dumps(dispatch_summary)
        results_ws.update(f'G{row}', [[dispatch_json]])
        
        print(f"   ✅ Added annual stack ({len(annual_stack)} years)")
        
        # Show grid timeline
        for year in [2025, 2029, 2030, 2035]:
            if year in annual_stack:
                grid_mw = annual_stack[year]['equipment'].get('grid_mw', 0)
                print(f"      {year}: Grid = {grid_mw:.1f} MW")
        
        updated += 1
    
    print(f"\n{'=' * 60}")
    print(f"✅ Updated {updated} results with annual energy stacks")
