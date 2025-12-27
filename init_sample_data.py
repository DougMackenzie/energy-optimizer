#!/usr/bin/env python3
"""
Manually initialize sample optimization data
Run this to populate Google Sheets with Austin Greenfield DC and optimization results
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.sample_optimization_data import get_sample_site, get_sample_optimization_results, save_sample_data_to_sheets

if __name__ == "__main__":
    print("Initializing sample optimization data...")
    
    result = save_sample_data_to_sheets()
    
    if result:
        print("\n✅ Sample data successfully saved to Google Sheets!")
        print("\nSite: Austin Greenfield DC")
        print("Stages: Screening, Concept, Preliminary, Detailed")
        print("\nRefresh Streamlit to see the results!")
    else:
        print("\n❌ Failed to save sample data")
        print("Check Google Sheets credentials and permissions")
