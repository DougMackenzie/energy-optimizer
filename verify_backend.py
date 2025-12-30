#!/usr/bin/env python3
"""
Verify sites in Google Sheets
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import load_all_sites

if __name__ == "__main__":
    print("=" * 60)
    print("VERIFYING SITES IN GOOGLE SHEETS")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    print(f"\nTotal Sites: {len(sites)}\n")
    
    for i, site in enumerate(sites, 1):
        print(f"{i}. {site.get('name', 'N/A')}")
        print(f"   - Location: {site.get('location', 'N/A')}")
        print(f"   - Problem: {site.get('problem_num', 'N/A')} - {site.get('problem_name', 'N/A')}")
        print(f"   - Capacity: {site.get('it_capacity_mw', 'N/A')} MW IT")
        print()
