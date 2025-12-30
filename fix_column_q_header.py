#!/usr/bin/env python3
"""
Quick fix: Add header to column Q in Optimization_Results
"""

import gspread
from config.settings import GOOGLE_SHEET_ID as SHEET_ID

def add_header():
    """Add equipment_by_year_json header to column Q"""
    try:
        client = gspread.service_account(filename='credentials.json')
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Optimization_Results")
        
        # Check current header
        headers = worksheet.row_values(1)
        print(f"Current headers ({len(headers)} columns):")
        for i, h in enumerate(headers):
            print(f"  {chr(65+i)}: {h}")
        
        # Add header to column Q (index 16, 0-based)
        if len(headers) >= 17:
            print(f"\n Column Q current value: '{headers[16]}'")
            if not headers[16]:
                worksheet.update('Q1', 'equipment_by_year_json')
                print("✅ Added 'equipment_by_year_json' header to column Q")
            else:
                print(f"⚠️  Column Q already has header: {headers[16]}")
        else:
            print(f"\n⚠️  Only {len(headers)} columns found, adding header to Q")
            worksheet.update('Q1', 'equipment_by_year_json')
            print("✅ Added 'equipment_by_year_json' header to column Q")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_header()
