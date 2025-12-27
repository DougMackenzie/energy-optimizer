#!/usr/bin/env python3
"""
Fix Google Sheets headers to include new columns
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import get_google_sheets_client, SHEET_ID

try:
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Site_Optimization_Stages")
    
    # Update headers to match what save_site_stage_result expects
    headers = [
        "site_name", "stage", "complete", "lcoe", "npv",
        "equipment_json", "dispatch_summary_json", "completion_date", "notes",
        "load_coverage_pct", "constraints_json", "capex_json", "runtime_seconds"
    ]
    
    # Update header row
    worksheet.update('A1:M1', [headers])
    
    print("✅ Headers updated successfully!")
    print("\nNew headers:")
    for i, h in enumerate(headers, 1):
        print(f"  Column {i}: {h}")
    
    print("\n💡 Now run optimization again and save!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
