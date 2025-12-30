#!/usr/bin/env python3
"""
Check if Google Sheets API quota has reset
"""

import gspread
import time

GOOGLE_SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

print("Checking Google Sheets API quota...")
print(f"Spreadsheet ID: {GOOGLE_SHEET_ID}")

for attempt in range(1, 4):
    print(f"\nAttempt {attempt}/3: Testing Equipment tab access...")
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
        equipment_ws = spreadsheet.worksheet('Equipment')
        data = equipment_ws.get_all_values()
        
        print(f"✅ SUCCESS! Quota has reset!")
        print(f"✅ Equipment tab accessible - {len(data)} rows")
        print(f"\n🎯 You can now run optimization in Streamlit!")
        break
    except gspread.exceptions.APIError as e:
        if '429' in str(e):
            print(f"❌ Quota still exceeded")
            if attempt < 3:
                wait_time = 60
                print(f"⏳ Waiting {wait_time} seconds for quota reset...")
                time.sleep(wait_time)
        else:
            print(f"❌ Other error: {e}")
            break
    except Exception as e:
        print(f"❌ Error: {e}")
        break
