#!/usr/bin/env python3
"""
Clean up duplicate sites in Google Sheets - keep only the 5 new ones
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import delete_site, load_all_sites

# Sites to keep (the new 5)
KEEP_SITES = [
    'Austin Greenfield DC',
    'Dallas Brownfield Exp',
    'Phoenix Land Constrained',
    'Chicago Grid Hub',
    'Northern Virginia Bridge'
]

if __name__ == "__main__":
    print("=" * 60)
    print("CLEANING UP DUPLICATE SITES")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    print(f"\nFound {len(sites)} total sites\n")
    
    deleted_count = 0
    for site in sites:
        site_name = site.get('name')
        if site_name not in KEEP_SITES:
            print(f"❌ Deleting old site: {site_name}")
            delete_site(site_name)
            deleted_count += 1
        else:
            print(f"✅ Keeping: {site_name}")
    
    print(f"\n✓ Deleted {deleted_count} old sites")
    print(f"✓ Kept {len(KEEP_SITES)} new sites")
