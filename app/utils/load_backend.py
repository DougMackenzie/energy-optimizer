"""
Load Configuration Backend
Save and load facility load trajectories and parameters to/from Google Sheets

ARCHITECTURE: Facility Load is source of truth, IT load is derived (Facility / PUE)
"""

import json
from datetime import datetime
from typing import Dict, Optional
import gspread


def get_google_sheets_client():
    """Get authenticated Google Sheets client"""
    return gspread.service_account(filename='credentials.json')


def save_load_configuration(site_name: str, load_config: dict) -> bool:
    """
    Save load configuration to Google Sheets Load_Profiles tab
    
   Stores growth_steps with FACILITY loads (source of truth).
    IT loads are derived: IT = Facility / PUE
    
    Args:
        site_name: Name of the site
        load_config: Dict with load parameters and trajectory
            - peak_facility_load_mw: float (derived from trajectory)
            - pue: float
            - load_factor_pct: float
            - growth_enabled: bool
            - growth_steps: list of {'year': int, 'facility_load_mw': float}
    
    Returns:
        True if successful
    """
    try:
        # Debug logging to file
        with open('/tmp/load_save_debug.txt', 'a') as f:
            f.write(f"\n=== save_load_configuration START ===\n")
            f.write(f"Time: {__import__('datetime').datetime.now()}\n")
            f.write(f"Site: {site_name}\n")
            f.write(f"Config keys: {list(load_config.keys())}\n")
            f.write(f"Config: {load_config}\n")
        
        print(f"\n=== save_load_configuration START ===")
        print(f"Site: {site_name}")
        print(f"Config keys: {load_config.keys()}")
        
        from config.settings import GOOGLE_SHEET_ID as SHEET_ID
        
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Load_Profiles")
        
        # Find existing row for this site
        all_records = worksheet.get_all_records()
        existing_row = None
        for idx, record in enumerate(all_records):
            if record.get('site_name') == site_name:
                existing_row = idx + 2  # +2 for header and 1-indexing
                break
        
        # Extract values from load_config
        pue = float(load_config.get('pue', 1.25))
        load_factor_pct = float(load_config.get('load_factor_pct', 80.0))
        growth_enabled = bool(load_config.get('growth_enabled', True))
        growth_steps = load_config.get('growth_steps', [])
        
        # Calculate peak_it_load from trajectory
        if growth_steps:
            peak_facility = max(step.get('facility_load_mw', 0) for step in growth_steps)
            peak_it_load_mw = round(peak_facility / pue, 1)
        else:
            peak_it_load_mw = float(load_config.get('peak_it_load_mw', 600.0))
        
        # Prepare row data for columns J-P (NEW schema)
        # NOTE: growth_steps now stores FACILITY loads, not IT loads
        # Extract 8760 load profile if available (from load_data)
        load_8760_json = ''
        if 'load_8760_mw' in load_config:
            # Convert numpy array to list for JSON serialization
            load_8760 = load_config['load_8760_mw']
            if hasattr(load_8760, 'tolist'):
                load_8760_json = json.dumps(load_8760.tolist())
            elif isinstance(load_8760, list):
                load_8760_json = json.dumps(load_8760)
        
        new_cols_data = [
            round(peak_it_load_mw, 1),  # J: peak_it_load_mw (derived)
            float(pue),  # K: pue
            float(load_factor_pct),  # L: load_factor_pct
            growth_enabled,  # M: growth_enabled
            json.dumps(growth_steps),  # N: growth_steps_json (FACILITY loads!)
            datetime.now().isoformat(),  # O: last_updated
            load_8760_json,  # P: load_8760_json (8760 hourly values)
        ]
        
        if existing_row:
            # Update existing (columns J-P)
            update_range = f'J{existing_row}:P{existing_row}'
            worksheet.update(range_name=update_range, values=[new_cols_data])
            print(f"✓ Updated load config for {site_name} (with 8760 profile)")
        else:
            # For new rows, need ALL columns A-P
            # Columns A-I (legacy schema - keep for backward compatibility)
            full_row = [
                site_name,  # A: site_name
                '',  # B: load_trajectory_json (DEPRECATED - leave empty)
                datetime.now().isoformat(),  # C: created_date
                datetime.now().isoformat(),  # D: updated_date
                load_factor_pct,  # E: flexibility_pct (legacy)
                45,  # F: pre_training_pct (legacy default)
                20,  # G: fine_tuning_pct (legacy default)
                15,  # H: batch_inference_pct (legacy default)
                20,  # I: real_time_inference_pct (legacy default)
            ]
            # Add new columns J-P
            full_row.extend(new_cols_data)
            
            worksheet.append_row(full_row)
            print(f"✓ Created new load config for {site_name} (with 8760 profile)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving load configuration: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_load_configuration(site_name: str) -> Dict:
    """
    Load load configuration from Google Sheets
    
    Loads growth_steps with FACILITY loads. Calculates trajectory directly.
    
    Args:
        site_name: Name of the site
    
    Returns:
        Dict with load config including facility trajectory, or default config if not found
    """
    try:
        from config.settings import GOOGLE_SHEET_ID as SHEET_ID
        
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Load_Profiles")
        
        all_records = worksheet.get_all_records()
        
        for record in all_records:
            if record.get('site_name') == site_name:
                # Parse growth_steps from JSON
                growth_steps_json = record.get('growth_steps_json', '[]')
                growth_steps_raw = json.loads(growth_steps_json) if growth_steps_json else []
                
                # Get PUE
                pue = float(record.get('pue', 1.25))
                
                # MIGRATION: Convert old IT load format to facility load format
                growth_steps = []
                for step in growth_steps_raw:
                    if 'facility_load_mw' in step:
                        # New format - already has facility load
                        growth_steps.append(step)
                    elif 'load_mw' in step:
                        # Old format - has IT load, convert to facility
                        growth_steps.append({
                            'year': step['year'],
                            'facility_load_mw': round(step['load_mw'] * pue, 1)
                        })
                
                # Calculate peak facility from trajectory
                if growth_steps:
                    peak_facility = max(step['facility_load_mw'] for step in growth_steps)
                    peak_it_load = round(peak_facility / pue, 1)
                else:
                    peak_it_load = float(record.get('peak_it_load_mw', 600))
                    peak_facility = round(peak_it_load * pue, 1)
                
                config = {
                    'peak_it_load_mw': peak_it_load,
                    'peak_facility_load_mw': peak_facility,
                    'pue': pue,
                    'load_factor_pct': float(record.get('load_factor_pct', 80)),
                    'growth_enabled': bool(record.get('growth_enabled', True)),
                    'growth_steps': growth_steps,  # FACILITY loads
                    'last_updated': record.get('last_updated', ''),
                }
                
                # Generate full trajectory from growth_steps (facility loads)
                if growth_steps:
                    config['load_trajectory'] = generate_full_trajectory_facility(growth_steps, planning_horizon=15)
                else:
                    config['load_trajectory'] = {y: 0.0 for y in range(2027, 2042)}
                
                # Load 8760 profile if available (column P)
                load_8760_json = record.get('load_8760_json', '')
                if load_8760_json:
                    try:
                        import numpy as np
                        load_8760 = json.loads(load_8760_json)
                        config['load_8760_mw'] = np.array(load_8760)
                        print(f"✓ Loaded 8760 profile (peak={np.max(load_8760):.1f} MW)")
                    except Exception as e:
                        print(f"⚠️  Could not parse 8760 profile: {e}")
                
                print(f"✓ Loaded load config for {site_name} ({len(growth_steps)} growth steps, facility loads)")
                return config
        
        # Return default if not found
        print(f"⚠️  No saved config for {site_name}, using defaults")
        return get_default_load_config()
        
    except Exception as e:
        print(f"❌ Error loading load configuration: {e}")
        import traceback
        traceback.print_exc()
        return get_default_load_config()


def generate_full_trajectory_facility(growth_steps: list, planning_horizon: int = 15) -> dict:
    """
    Generate full 15-year trajectory from growth steps (FACILITY loads)
    
    Args:
        growth_steps: List of {'year': int, 'facility_load_mw': float}
        planning_horizon: Number of years
    
    Returns:
        Dict of {year: facility_load_mw}
    """
    trajectory = {}
    start_year = 2027
    
    if not growth_steps:
        return {start_year + i: 0.0 for i in range(planning_horizon)}
    
    # Sort steps by year
    sorted_steps = sorted(growth_steps, key=lambda x: x['year'])
    
    for i in range(planning_horizon):
        year = start_year + i
        
        # Find applicable facility load for this year
        facility_load = 0
        for step in sorted_steps:
            if year >= step['year']:
                facility_load = step['facility_load_mw']
        
        trajectory[year] = round(facility_load, 2)
    
    return trajectory


def get_default_load_config() -> Dict:
    """Return default load configuration with facility loads"""
    default_steps = [
        {'year': 2027, 'facility_load_mw': 0},
        {'year': 2028, 'facility_load_mw': 187.5},
        {'year': 2029, 'facility_load_mw': 375},
        {'year': 2030, 'facility_load_mw': 562.5},
        {'year': 2031, 'facility_load_mw': 750},
    ]
    
    default_pue = 1.25
    peak_facility = 750
    peak_it = round(peak_facility / default_pue, 1)
    
    return {
        'peak_it_load_mw': peak_it,
        'peak_facility_load_mw': peak_facility,
        'pue': default_pue,
        'load_factor_pct': 85.0,
        'growth_enabled': True,
        'growth_steps': default_steps,  # FACILITY loads
        'load_trajectory': generate_full_trajectory_facility(default_steps, 15),
        'last_updated': '',
    }
