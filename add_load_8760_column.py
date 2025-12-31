"""Add load_8760_json column (P) to Load_Profiles sheet"""
import sys
sys.path.insert(0, '/Users/douglasmackenzie/energy-optimizer')

from app.utils.load_backend import get_google_sheets_client

SHEET_ID = "1waBVXlUL1zDE5ovDppM3iYsLhJioyE3yzwL45fLkqrA"

client = get_google_sheets_client()
spreadsheet = client.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet("Load_Profiles")

current_cols = worksheet.col_count
print(f"Current columns: {current_cols}")

if current_cols < 16:
    print("Expanding to 16 columns...")
    worksheet.resize(cols=16)

print("Adding 'load_8760_json' header to column P...")
worksheet.update_cell(1, 16, "load_8760_json")

print("✓ Column P header added!")
