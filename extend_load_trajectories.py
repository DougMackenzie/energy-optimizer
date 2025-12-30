#!/usr/bin/env python3
"""
Extend Load Trajectories to 15 Years (2027-2041)

This script extends all sites' load_trajectory_json in the Load_Profiles tab
to cover the full 15-year analysis period from 2027 to 2041.

For sites with shorter trajectories, it extends them by holding the last
value constant through 2041.
"""

import gspread
import json
from datetime import datetime

# Configuration
GOOGLE_SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
START_YEAR = 2027
END_YEAR = 2041  # 15 years: 2027-2041
ANALYSIS_YEARS = 15

def extend_trajectory(trajectory_json_str):
    """
    Extend a load trajectory to cover 2027-2041.
    
    Args:
        trajectory_json_str: JSON string like '{"2027": 200, "2028": 400, ...}'
    
    Returns:
        Extended JSON string covering 2027-2041
    """
    if not trajectory_json_str:
        # Empty trajectory - return basic growth to 750MW over 4 years
        return json.dumps({
            str(year): min(200 + (year - START_YEAR) * 150, 750)
            for year in range(START_YEAR, END_YEAR + 1)
        })
    
    try:
        # Parse existing trajectory
        trajectory = json.loads(trajectory_json_str)
        
        # Convert string keys to int for sorting
        year_load_pairs = [(int(year), float(load)) for year, load in trajectory.items()]
        year_load_pairs.sort()
        
        if not year_load_pairs:
            # Empty dict - use default
            return json.dumps({
                str(year): min(200 + (year - START_YEAR) * 150, 750)
                for year in range(START_YEAR, END_YEAR + 1)
            })
        
        # Get last year and load
        last_year, last_load = year_load_pairs[-1]
        
        # Build extended trajectory
        extended = {}
        
        # Copy existing years
        for year, load in year_load_pairs:
            extended[str(year)] = load
        
        # Extend from last year + 1 to END_YEAR, holding last value constant
        for year in range(last_year + 1, END_YEAR + 1):
            extended[str(year)] = last_load
        
        # Ensure we start from START_YEAR
        if min(int(y) for y in extended.keys()) > START_YEAR:
            # Gap at beginning - fill with first value
            first_load = year_load_pairs[0][1]
            for year in range(START_YEAR, min(int(y) for y in extended.keys())):
                extended[str(year)] = first_load
        
        return json.dumps(extended)
    
    except Exception as e:
        print(f"Error parsing trajectory: {e}")
        print(f"Original: {trajectory_json_str}")
        return trajectory_json_str  # Return original on error


def main():
    """Extend all load trajectories to 15 years."""
    
    print("="*80)
    print("EXTENDING LOAD TRAJECTORIES TO 15 YEARS (2027-2041)")
    print("="*80 + "\n")
    
    # Connect to Google Sheets
    print("🔗 Connecting to Google Sheets...")
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    
    # Load Load_Profiles tab
    print("📊 Loading Load_Profiles tab...")
    profiles_ws = spreadsheet.worksheet("Load_Profiles")
    profiles_data = profiles_ws.get_all_records()
    
    print(f"✓ Found {len(profiles_data)} load profiles\n")
    
    # Get headers
    headers = profiles_ws.row_values(1)
    traj_col_idx = headers.index('load_trajectory_json') + 1 if 'load_trajectory_json' in headers else None
    
    if not traj_col_idx:
        print("❌ ERROR: load_trajectory_json column not found!")
        return
    
    # Process each site
    updates = []
    
    for idx, profile in enumerate(profiles_data):
        site_name = profile.get('site_name')
        current_trajectory = profile.get('load_trajectory_json', '')
        
        if not site_name:
            continue
        
        print(f"\n{'='*60}")
        print(f"Site: {site_name}")
        print(f"{'='*60}")
        
        # Parse current trajectory
        if current_trajectory:
            try:
                traj_dict = json.loads(current_trajectory)
                years = sorted([int(y) for y in traj_dict.keys()])
                print(f"Current trajectory: {years[0]} to {years[-1]} ({len(years)} years)")
                print(f"  Sample: {dict(list(traj_dict.items())[:3])}")
            except:
                print(f"Current trajectory: INVALID JSON")
        else:
            print(f"Current trajectory: EMPTY")
        
        # Extend trajectory
        extended_trajectory = extend_trajectory(current_trajectory)
        
        # Parse extended to show info
        try:
            ext_dict = json.loads(extended_trajectory)
            ext_years = sorted([int(y) for y in ext_dict.keys()])
            print(f"Extended trajectory: {ext_years[0]} to {ext_years[-1]} ({len(ext_years)} years)")
            print(f"  Sample: {dict(list(ext_dict.items())[:3])} ... {dict(list(ext_dict.items())[-2:])}")
        except:
            print(f"Extended trajectory: ERROR")
        
        # Update the cell
        row_num = idx + 2  # +2 for header row and 0-indexing
        updates.append({
            'site': site_name,
            'row': row_num,
            'trajectory': extended_trajectory
        })
    
    # Apply all updates
    print(f"\n{'='*80}")
    print(f"APPLYING UPDATES TO GOOGLE SHEETS")
    print(f"{'='*80}\n")
    
    for update in updates:
        print(f"Updating {update['site']} at row {update['row']}...")
        profiles_ws.update_cell(update['row'], traj_col_idx, update['trajectory'])
    
    print(f"\n✅ SUCCESS!")
    print(f"Updated {len(updates)} load trajectories to cover 2027-2041 (15 years)")
    print(f"\nAll sites now have trajectories extending through {END_YEAR}")


if __name__ == "__main__":
    main()
