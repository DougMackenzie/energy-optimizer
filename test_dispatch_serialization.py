#!/usr/bin/env python3
"""
Debug script to check dispatch_by_year structure before saving
"""

import sys
import pandas as pd

# Mock optimizer result
class MockDispatchResult:
    def __init__(self, year):
        # Create fake 8760 dataframe
        self.dispatch_df = pd.DataFrame({
            'hour': range(8760),
            'load_mw': [600] * 8760,
            'recip_mw': [35] * 8760,
            'turbine_mw': [0] * 8760,
            'solar_mw': [0] * 8760,
            'bess_mw': [0] * 8760,
            'grid_mw': [0 if year < 2031 else 565] * 8760,  # Grid only after 2031
            'unserved_mw': [0] * 8760,
        })

# Create mock dispatch_by_year
dispatch_by_year = {}
for year in range(2027, 2042):  # 15 years
    dispatch_by_year[year] = MockDispatchResult(year)

print(f"Created dispatch_by_year with {len(dispatch_by_year)} years")
for year, disp in dispatch_by_year.items():
    print(f"  Year {year}: type={type(disp)}, has dispatch_df={hasattr(disp, 'dispatch_df')}")

# Now serialize it (this is what optimizer_backend.py does)
dispatch_by_year_serialized = {}
for year, disp_result in dispatch_by_year.items():
    if hasattr(disp_result, 'dispatch_df'):
        # Convert DataFrame to dict of lists (JSON-serializable)
        dispatch_by_year_serialized[year] = {
            'dispatch_data': disp_result.dispatch_df.to_dict('list'),
            'columns': list(disp_result.dispatch_df.columns)
        }
    elif isinstance(disp_result, dict):
        dispatch_by_year_serialized[year] = disp_result

print(f"\nSerialized dispatch_by_year has {len(dispatch_by_year_serialized)} years")
for year, data in dispatch_by_year_serialized.items():
    if 'dispatch_data' in data:
        num_hours = len(data['dispatch_data'].get('load_mw', []))
        print(f"  Year {year}: {num_hours} hours")
    else:
        print(f"  Year {year}: MISSING dispatch_data!")

# Test what save_dispatch_data would receive
print(f"\nThis is what save_dispatch_data() would receive:")
print(f"  Type: {type(dispatch_by_year_serialized)}")
print(f"  Keys: {list(dispatch_by_year_serialized.keys())}")
