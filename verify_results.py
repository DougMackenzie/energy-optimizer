#!/usr/bin/env python3
"""
Verify optimization results in Google Sheets
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICATION: OPTIMIZATION RESULTS")
    print("=" * 60)
    
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Optimization_Results")
    
    results = worksheet.get_all_records()
    
    # Group by site
    by_site = {}
    for result in results:
        site_name = result.get('site_name')
        if site_name not in by_site:
            by_site[site_name] = []
        by_site[site_name].append(result)
    
    print(f"\nTotal Results: {len(results)} across {len(by_site)} sites\n")
    
    for site_name, site_results in sorted(by_site.items()):
        print(f"📍 {site_name}")
        for res in site_results:
            stage = res.get('stage', 'N/A')
            lcoe = res.get('lcoe', 'N/A')
            complete = res.get('complete', False)
            status = "✅" if complete else "⏳"
            print(f"   {status} {stage:12s} - LCOE: ${lcoe}/MWh")
        print()
