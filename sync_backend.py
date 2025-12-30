#!/usr/bin/env python3
"""
Sync sample sites to Google Sheets
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.sample_optimization_data import save_sample_data_to_sheets

if __name__ == "__main__":
    print("=" * 60)
    print("SYNCING SAMPLE SITES TO GOOGLE SHEETS")
    print("=" * 60)
    
    success = save_sample_data_to_sheets()
    
    if success:
        print("\n✅ Successfully synced all sample sites to Google Sheets!")
    else:
        print("\n❌ Failed to sync - check error messages above")
