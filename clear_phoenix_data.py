#!/usr/bin/env python3
"""
Clear old Phoenix AI Campus optimization data from Google Sheets
This will force a fresh save with the new schema
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
    
    # Get all records
    stages = worksheet.get_all_records()
    
    # Find Phoenix rows
    rows_to_delete = []
    for idx, stage_data in enumerate(stages):
        if stage_data.get('site_name') == 'Phoenix AI Campus':
            rows_to_delete.append(idx + 2)  # +2 for header row and 0-indexing
    
    # Delete from bottom to top to avoid index shifting
    for row_num in sorted(rows_to_delete, reverse=True):
        worksheet.delete_rows(row_num)
        print(f"✓ Deleted row {row_num}")
    
    print(f"\n✅ Deleted {len(rows_to_delete)} old Phoenix records")
    print("Now run a new optimization for Phoenix and save it!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
