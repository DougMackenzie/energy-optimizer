#!/usr/bin/env python3
"""
Diagnostic script to check Google Sheets access and tab names
"""

import gspread

GOOGLE_SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

print(f"Connecting to spreadsheet ID: {GOOGLE_SHEET_ID}")

try:
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    
    print(f"✅ Connected to: {spreadsheet.title}")
    print(f"\n📋 Available worksheets:")
    
    for worksheet in spreadsheet.worksheets():
        print(f"  - '{worksheet.title}' (ID: {worksheet.id})")
    
    # Try to access Equipment tab
    print(f"\n🔍 Testing Equipment tab access...")
    try:
        equipment_ws = spreadsheet.worksheet('Equipment')
        data = equipment_ws.get_all_values()
        print(f"  ✅ Equipment tab accessible - {len(data)} rows")
        if data:
            print(f"  Headers: {data[0]}")
    except gspread.exceptions.WorksheetNotFound:
        print(f"  ❌ Equipment tab NOT FOUND")
        print(f"  Trying case variations...")
        for ws in spreadsheet.worksheets():
            if 'equipment' in ws.title.lower():
                print(f"    Found similar: '{ws.title}'")
    except Exception as e:
        print(f"  ❌ Error accessing Equipment: {e}")
    
    # Try to access Global_Parameters tab
    print(f"\n🔍 Testing Global_Parameters tab access...")
    try:
        params_ws = spreadsheet.worksheet('Global_Parameters')
        data = params_ws.get_all_values()
        print(f"  ✅ Global_Parameters tab accessible - {len(data)} rows")
        if data:
            print(f"  Headers: {data[0]}")
    except gspread.exceptions.WorksheetNotFound:
        print(f"  ❌ Global_Parameters tab NOT FOUND")
        print(f"  Trying case variations...")
        for ws in spreadsheet.worksheets():
            if 'global' in ws.title.lower() or 'parameter' in ws.title.lower():
                print(f"    Found similar: '{ws.title}'")
    except Exception as e:
        print(f"  ❌ Error accessing Global_Parameters: {e}")

except gspread.exceptions.APIError as e:
    print(f"❌ API Error: {e}")
    if '429' in str(e):
        print("  Quota exceeded - wait 1 minute and try again")
    elif '404' in str(e):
        print("  Spreadsheet not found - check GOOGLE_SHEET_ID in .env")
    elif '403' in str(e):
        print("  Permission denied - check service account has access")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
