#!/usr/bin/env python3
"""
Debug script to check equipment_by_year values in the chart

Run this to see what grid_mw values are being stored for each year
"""

# This is what the chart receives:
# equipment_by_year = {
#     2027: {'recip_mw': X, 'grid_mw': Y, ...},
#     2028: {'recip_mw': X, 'grid_mw': Y, ...},
#     ...
# }

# Problem: Chart might be summing grid_mw across years instead of using per-year

# To test:
# 1. Run optimization for Austin
# 2. Check terminal for "🔍 DEBUG equipment_by_year" output
# 3. Look for grid_mw values - do they increase each year?

# Expected Austin values (if correct):
# Year 2027-2030: grid_mw = 0 (before grid_available_year=2031)
# Year 2031-2041: grid_mw = 567 (actual need to fill gap)

# If we see:
# Year 2031: 567
# Year 2032: 567 + 567 = 1134?
# Then it's cumulative bug

# Chart code suspect (energy_stack_chart.py line 138):
# grid_capacity.append(config.get('grid_mw', grid_capacity_mw))
#
# If config['grid_mw'] contains cumulative value, that's the bug
