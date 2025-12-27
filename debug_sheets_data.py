#!/usr/bin/env python3
"""
Debug script - Check what's in Google Sheets for Phoenix
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import get_google_sheets_client, SHEET_ID
import json

try:
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Site_Optimization_Stages")
    
    # Get headers
    headers = worksheet.row_values(1)
    print("📋 HEADERS:")
    for i, h in enumerate(headers, 1):
        print(f"  Column {i}: {h}")
    
    print("\n" + "="*80)
    
    # Get all records
    stages = worksheet.get_all_records()
    
    # Find Phoenix
    for stage_data in stages:
        if stage_data.get('site_name') == 'Phoenix AI Campus':
            print(f"\n🔍 FOUND: Phoenix AI Campus - {stage_data.get('stage')}")
            print(f"\nLCOE: {stage_data.get('lcoe')}")
            print(f"NPV: {stage_data.get('npv')}")
            print(f"Load Coverage: {stage_data.get('load_coverage_pct')}")
            
            eq_json = stage_data.get('equipment_json', '')
            print(f"\nEquipment JSON (first 200 chars): {eq_json[:200]}")
            
            if eq_json:
                try:
                    eq = json.loads(eq_json)
                    print(f"\n✅ Equipment parsed successfully:")
                    print(f"  Recip: {eq.get('recip_mw', 'N/A')} MW")
                    print(f"  Turbine: {eq.get('turbine_mw', 'N/A')} MW")
                    print(f"  BESS: {eq.get('bess_mwh', 'N/A')} MWh")
                    print(f"  Solar: {eq.get('solar_mw', 'N/A')} MW")
                except Exception as e:
                    print(f"\n❌ Failed to parse equipment JSON: {e}")
            else:
                print("\n❌ equipment_json is EMPTY!")
            
            print("\n" + "="*80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
