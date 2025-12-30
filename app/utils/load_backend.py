"""
Load Configuration Backend
Save and load facility load trajectories and parameters to/from Google Sheets
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
    
    Stores only growth_steps (source data), NOT load_trajectory (derived data).
    Trajectory will be regenerated from growth_steps on load.
    
    Args:
        site_name: Name of the site
        load_config: Dict with load parameters and trajectory
            - peak_it_load_mw: float
            - pue: float
            - load_factor_pct: float
            - growth_enabled: bool
            - growth_steps: list of {'year': int, 'load_mw': float}
    
    Returns:
        True if successful
    """
    try:
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
        peak_it_load_mw = float(load_config.get('peak_it_load_mw', 600.0))
        pue = float(load_config.get('pue', 1.25))
        load_factor_pct = float(load_config.get('load_factor_pct', 85.0))
        growth_enabled = bool(load_config.get('growth_enabled', True))
        growth_steps = load_config.get('growth_steps', [])
        
        # Prepare row data for columns J-O (NEW schema)
        # NOTE: We do NOT save load_trajectory_json - it's regenerated from growth_steps
        new_cols_data = [
            round(peak_it_load_mw, 1),  # J: peak_it_load_mw
            float(pue),  # K: pue
            float(load_factor_pct),  # L: load_factor_pct
            growth_enabled,  # M: growth_enabled
            json.dumps(growth_steps),  # N: growth_steps_json
            datetime.now().isoformat(),  # O: last_updated
        ]
        
        if existing_row:
            # Update existing (columns J-O only)
            update_range = f'J{existing_row}:O{existing_row}'
            worksheet.update(range_name=update_range, values=[new_cols_data])
            print(f"✓ Updated load config for {site_name}")
        else:
            # For new rows, need ALL columns A-O
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
            # Add new columns J-O
            full_row.extend(new_cols_data)
            
            worksheet.append_row(full_row)
            print(f"✓ Created new load config for {site_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving load configuration: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_load_configuration(site_name: str) -> Dict:
    """
    Load load configuration from Google Sheets
    
    Regenerates load_trajectory from growth_steps - does NOT read stored trajectory.
    
    Args:
        site_name: Name of the site
    
    Returns:
       Dict with load config including regenerated trajectory, or default config if not found
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
                growth_steps = json.loads(growth_steps_json) if growth_steps_json else []
                
                # Get PUE for trajectory generation
                pue = float(record.get('pue', 1.25))
                
                config = {
                    'peak_it_load_mw': float(record.get('peak_it_load_mw', 600)),
                    'pue': pue,
                    'load_factor_pct': float(record.get('load_factor_pct', 85)),
                    'growth_enabled': bool(record.get('growth_enabled', True)),
                    'growth_steps': growth_steps,
                    'last_updated': record.get('last_updated', ''),
                }
                
                # REGENERATE trajectory from growth_steps (don't use stored trajectory)
                if growth_steps:
                    config['load_trajectory'] = generate_full_trajectory(growth_steps, pue, planning_horizon=15)
                else:
                    # If no growth steps, create flat trajectory
                    config['load_trajectory'] = {y: 0.0 for y in range(2027, 2042)}
                
                print(f"✓ Loaded load config for {site_name} (regenerated trajectory from {len(growth_steps)} growth steps)")
                return config
        
        # Return default if not found
        print(f"⚠️  No saved config for {site_name}, using defaults")
        return get_default_load_config()
        
    except Exception as e:
        print(f"❌ Error loading load configuration: {e}")
        import traceback
        traceback.print_exc()
        return get_default_load_config()


def generate_full_trajectory(growth_steps: list, pue: float, planning_horizon: int = 15) -> dict:
    """
    Generate full 15-year trajectory from growth steps
    
    Args:
        growth_steps: List of {'year': int, 'load_mw': float}
        pue: Power Usage Effectiveness
        planning_horizon: Number of years
    
    Returns:
        Dict of {year: facility_load_mw}
    """
    trajectory = {}
    start_year = 2027
    
    if not growth_steps:
        # No growth steps defined, use flat trajectory
        return {start_year + i: 0.0 for i in range(planning_horizon)}
    
    # Sort steps by year
    sorted_steps = sorted(growth_steps, key=lambda x: x['year'])
    
    for i in range(planning_horizon):
        year = start_year + i
        
        # Find applicable IT load for this year
        it_load = 0
        for step in sorted_steps:
            if year >= step['year']:
                it_load = step['load_mw']
        
        # Convert IT load to facility load
        facility_load = it_load * pue
        trajectory[year] = round(facility_load, 2)
    
    return trajectory


def get_default_load_config() -> Dict:
    """Return default load configuration with regenerated trajectory"""
    default_steps = [
        {'year': 2027, 'load_mw': 0},
        {'year': 2028, 'load_mw': 150},
        {'year': 2029, 'load_mw': 300},
        {'year': 2030, 'load_mw': 450},
        {'year': 2031, 'load_mw': 600},
    ]
    
    default_pue = 1.25
    
    return {
        'peak_it_load_mw': 600.0,
        'pue': default_pue,
        'load_factor_pct': 85.0,
        'growth_enabled': True,
        'growth_steps': default_steps,
        'load_trajectory': generate_full_trajectory(default_steps, default_pue, 15),
        'last_updated': '',
    }


def infer_growth_steps_from_trajectory(trajectory_json: str, pue: float = 1.25) -> list:
    """
    Infer growth steps from existing trajectory JSON
    For backward compatibility with old data
    
    Args:
        trajectory_json: JSON string of {year: facility_load_mw}
        pue: PUE to convert facility load back to IT load
    
    Returns:
        List of {'year': int, 'load_mw': float}
    """
    try:
        trajectory = json.loads(trajectory_json)
        steps = []
        
        prev_it_load = 0
        for year_str, facility_load in sorted(trajectory.items()):
            year = int(year_str)
            it_load = round(facility_load / pue, 1)
            
            # Only add step if load changed
            if it_load != prev_it_load:
                steps.append({'year': year, 'load_mw': it_load})
                prev_it_load = it_load
        
        return steps
    except:
        return []
