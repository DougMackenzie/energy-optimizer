#!/usr/bin/env python3
"""
Migration Script: Populate new Load_Profiles schema from existing data

This script reads existing load_trajectory_json from Load_Profiles tab
and populates the new columns (peak_it_load_mw, pue, growth_steps_json, etc.)
"""

import gspread
import json
from datetime import datetime


def migrate_load_profiles():
    """Migrate Load_Profiles tab to new schema"""
    
    # Connect to Google Sheets
    client = gspread.service_account(filename='credentials.json')
    
    # Hardcode to avoid import issues
    SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Load_Profiles")
    
    print("📊 Starting Load_Profiles migration...")
    
    # Get all existing data
    all_records = worksheet.get_all_records()
    
    # Check current columns
    headers = worksheet.row_values(1)
    print(f"\n📋 Current columns: {headers}")
    
    # Add new columns if missing
    required_cols = [
        'site_name',  # A (existing)
        'load_trajectory_json',  # B (existing)
        'created_date',  # C (existing)
        'updated_date',  # D (existing - was blank)
        'flexibility_pct',  # E (existing)
        'pre_training_pct',  # F (existing)
        'fine_tuning_pct',  # G (existing)
        'batch_inference_pct',  # H (existing)
        'real_time_inference_pct',  # I (existing)
        # NEW COLUMNS:
        'peak_it_load_mw',  # J (NEW)
        'pue',  # K (NEW)
        'load_factor_pct',  # L (NEW)
        'growth_enabled',  # M (NEW)
        'growth_steps_json',  # N (NEW)
        'last_updated',  # O (NEW)
    ]
    
    # Add missing column headers
    if len(headers) < len(required_cols):
        missing = required_cols[len(headers):]
        print(f"\n➕ Adding {len(missing)} new columns: {missing}")
        
        # Expand sheet if needed
        current_cols = worksheet.col_count
        needed_cols = len(required_cols)
        if current_cols < needed_cols:
            print(f"  ⤵️ Expanding sheet from {current_cols} to {needed_cols} columns")
            worksheet.resize(rows=worksheet.row_count, cols=needed_cols)
        
        # Update header row
        header_range = f'{chr(65 + len(headers))}1:{chr(65 + len(required_cols) - 1)}1'
        worksheet.update(values=[missing], range_name=header_range)
    
    print(f"\n🔄 Processing {len(all_records)} sites...")
    
    # Process each site
    for idx, record in enumerate(all_records):
        site_name = record.get('site_name', '')
        if not site_name:
            continue
        
        print(f"\n  📍 {site_name}")
        
        # Parse existing load_trajectory_json
        traj_json = record.get('load_trajectory_json', '')
        if not traj_json:
            print(f"    ⚠️  No trajectory data, skipping")
            continue
        
        try:
            trajectory = json.loads(traj_json)
        except:
            print(f"    ❌ Failed to parse trajectory JSON")
            continue
        
        # Infer parameters from trajectory
        # Calculate peak IT load from max trajectory value
        max_facility_load = max(trajectory.values()) if trajectory else 0
        pue = record.get('pue') or 1.25  # Use existing or default
        peak_it_load = max_facility_load / pue if pue > 0 else max_facility_load
        
        # Infer growth steps from trajectory
        growth_steps = []
        prev_load = 0
        for year_str in sorted(trajectory.keys(), key=int):
            facility_load = trajectory[year_str]
            it_load = facility_load / pue
            
            # Add step if load changed
            if abs(it_load - prev_load) > 1:  # Threshold 1 MW
                growth_steps.append({
                    'year': int(year_str),
                    'load_mw': round(it_load, 1)
                })
                prev_load = it_load
        
        # Get load factor from existing data or default
        load_factor_pct = record.get('flexibility_pct', 85) or 85
        
        # Prepare update data for new columns (J-O)
        row_num = idx + 2  # +1 for header, +1 for 1-indexing
        
        update_values = [
            round(peak_it_load, 1),  # J: peak_it_load_mw
            float(pue),  # K: pue
            float(load_factor_pct),  # L: load_factor_pct
            True,  # M: growth_enabled
            json.dumps(growth_steps),  # N: growth_steps_json
            datetime.now().isoformat(),  # O: last_updated
        ]
        
        # Update row (columns J-O)
        update_range = f'J{row_num}:O{row_num}'
        worksheet.update(update_range, [update_values])
        
        print(f"    ✓ Updated: peak_it={peak_it_load:.1f} MW, pue={pue}, {len(growth_steps)} growth steps")
    
    print("\n✅ Migration complete!")
    print(f"📊 Updated {len(all_records)} sites in Load_Profiles tab")


if __name__ == '__main__':
    migrate_load_profiles()
