"""
Test script to debug Executive Summary data loading
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import load_site_stage_result

# Test loading data
site_name = "Phoenix AI Campus"
stage = "screening"

print(f"Loading data for: {site_name} - {stage}")
result = load_site_stage_result(site_name, stage)

if result:
    print("\n✅ Data loaded successfully!")
    print(f"LCOE: {result.get('lcoe')}")
    print(f"NPV: {result.get('npv')}")
    print(f"Load Coverage: {result.get('load_coverage_pct')}")
    print(f"Equipment: {result.get('equipment')}")
    print(f"Constraints: {result.get('constraints')}")
else:
    print("\n❌ No data found!")
