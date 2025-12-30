#!/usr/bin/env python3
"""
Script to replace old GreenFieldHeuristic imports with GreenfieldHeuristicV2
in test and debug files
"""

import re
from pathlib import Path

# Files to update
files_to_update = [
    "test_grid_optional.py",
    "debug_grid.py",
    "test_heuristic.py",
    "debug_firm_capacity.py",
    "test_heuristic_grid.py",
]

# Base directory
base_dir = Path(__file__).parent

for filename in files_to_update:
    filepath = base_dir / filename
    
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        continue
    
    # Read file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace old import
    old_import = "from app.optimization.heuristic_optimizer import GreenFieldHeuristic"
    new_import = "# Use v2.1.1 Greenfield optimizer with backend integration\nfrom app.optimization import GreenfieldHeuristicV2"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        
        # Also replace class instantiations
        content = re.sub(r'\bGreenFieldHeuristic\(', 'GreenfieldHeuristicV2(', content)
        
        # Write back
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated: {filename}")
    else:
        print(f"⏭️  Skipped (no old import found): {filename}")

print("\n✅ All files updated!")
