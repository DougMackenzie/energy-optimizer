"""
Fix script to update all references from result.get('complete') to checking for LCOE
This matches the actual Google Sheets structure
"""

import re

files_to_fix = [
    '/Users/douglasmackenzie/energy-optimizer/app/pages_custom/page_portfolio_overview.py',
    '/Users/douglasmackenzie/energy-optimizer/app/pages_custom/page_investor_portal.py'
]

for filepath in files_to_fix:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace the check
    original = "if result and result.get('complete'):"
    replacement = "if result and result.get('lcoe') and float(result.get('lcoe', 0)) > 0:"
    
    content = content.replace(original, replacement)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

print("All files updated!")
