#!/usr/bin/env python3
"""
Fix 1: Update Northern Virginia site name in Google Sheets
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

if __name__ == "__main__":
    print("=" * 60)
    print("FIXING SITE NAME")
    print("=" * 60)
    
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # Fix in Sites sheet
    sites_ws = spreadsheet.worksheet("Sites")
    sites = sites_ws.get_all_records()
    
    for idx, site in enumerate(sites):
        name = site.get('name', '')
        if 'Northern Virginia' in name and name != 'Northern Virginia Bridge':
            row = idx + 2
            print(f"Found truncated name: '{name}' at row {row}")
            sites_ws.update(f'A{row}', [['Northern Virginia Bridge']])
            print(f"✅ Updated to: 'Northern Virginia Bridge'")
    
    # Fix in Optimization_Results sheet
    results_ws = spreadsheet.worksheet("Optimization_Results")
    results = results_ws.get_all_records()
    
    for idx, result in enumerate(results):
        name = result.get('site_name', '')
        if 'Northern Virginia' in name and name != 'Northern Virginia Bridge':
            row = idx + 2
            print(f"Found truncated name in results: '{name}' at row {row}")
            results_ws.update(f'A{row}', [['Northern Virginia Bridge']])
            print(f"✅ Updated results to: 'Northern Virginia Bridge'")
    
    print("\n✅ Site name fixes complete")
