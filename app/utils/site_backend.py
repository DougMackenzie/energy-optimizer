"""
Site-Centric Backend for Google Sheets Integration
Handles all site data, load profiles, and optimization stage results
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import streamlit as st
import json
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


# Google Sheets Configuration
SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
CREDENTIALS_PATH = str(Path(__file__).parent.parent.parent / "credentials.json")


def get_google_sheets_client():
    """Get authenticated Google Sheets client"""
    if not GSPREAD_AVAILABLE:
        raise ImportError("gspread library not installed")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
    return gspread.authorize(credentials)


# =============================================================================
# SITE MANAGEMENT
# =============================================================================

def load_all_sites(use_cache: bool = True) -> List[Dict]:
    """Load all sites from Google Sheets"""
    
    # Check cache first
    if use_cache and 'sites_list' in st.session_state:
        return st.session_state.sites_list
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Try to get Sites worksheet, create if doesn't exist
        try:
            worksheet = spreadsheet.worksheet("Sites")
        except gspread.WorksheetNotFound:
            # Create Sites worksheet with headers
            worksheet = spreadsheet.add_worksheet(title="Sites", rows=100, cols=20)
            headers = [
                "site_name", "location", "iso", "it_capacity_mw", "pue", "facility_mw",
                "land_acres", "nox_limit_tpy", "gas_supply_mcf", "voltage_kv",
                "coordinates_lat", "coordinates_lon", "geojson_prefix",
                "problem_num", "problem_name", "created_date", "updated_date"
            ]
            worksheet.append_row(headers)
            return []
        
        sites = worksheet.get_all_records()
        
        # Cache in session state
        if use_cache:
            st.session_state.sites_list = sites
        
        return sites
    except Exception as e:
        print(f"Error loading sites: {e}")
        return []


def save_site(site_data: Dict) -> bool:
    """Save or update a site in Google Sheets"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Sites")
        
        site_name = site_data['name']
        
        # Check if site already exists
        sites = worksheet.get_all_records()
        existing_row = None
        for idx, site in enumerate(sites):
            if site.get('site_name') == site_name:
                existing_row = idx + 2  # +2 for header row and 0-indexing
                break
        
        # Prepare row data
        row_data = [
            site_data.get('name'),
            site_data.get('location'),
            site_data.get('iso'),
            site_data.get('it_capacity_mw'),
            site_data.get('pue'),
            site_data.get('facility_mw'),
            site_data.get('land_acres'),
            site_data.get('nox_limit_tpy'),
            site_data.get('gas_supply_mcf'),
            site_data.get('voltage_kv'),
            site_data.get('coordinates', [0, 0])[0],  # lat
            site_data.get('coordinates', [0, 0])[1],  # lon
            site_data.get('geojson_prefix', ''),
            site_data.get('problem_num'),
            site_data.get('problem_name'),
            site_data.get('created_date', datetime.now().isoformat()),
            datetime.now().isoformat()  # updated_date
        ]
        
        if existing_row:
            # Update existing row
            worksheet.update(f'A{existing_row}:Q{existing_row}', [row_data])
        else:
            # Append new row
            worksheet.append_row(row_data)
        
        # Clear cache
        if 'sites_list' in st.session_state:
            del st.session_state.sites_list
        
        return True
    except Exception as e:
        print(f"Error saving site: {e}")
        return False


def delete_site(site_name: str) -> bool:
    """Delete a site and all associated data"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Delete from Sites
        worksheet = spreadsheet.worksheet("Sites")
        sites = worksheet.get_all_records()
        for idx, site in enumerate(sites):
            if site.get('site_name') == site_name:
                worksheet.delete_rows(idx + 2)  # +2 for header
                break
        
        # Delete from Site_Loads
        try:
            loads_ws = spreadsheet.worksheet("Load_Profiles")
            loads = loads_ws.get_all_records()
            for idx, load in enumerate(loads):
                if load.get('site_name') == site_name:
                    loads_ws.delete_rows(idx + 2)
        except:
            pass
        
        # Delete from Site_Optimization_Stages
        try:
            stages_ws = spreadsheet.worksheet("Optimization_Results")
            stages = stages_ws.get_all_records()
            rows_to_delete = []
            for idx, stage in enumerate(stages):
                if stage.get('site_name') == site_name:
                    rows_to_delete.append(idx + 2)
            # Delete in reverse order to maintain indices
            for row in sorted(rows_to_delete, reverse=True):
                stages_ws.delete_rows(row)
        except:
            pass
        
        # Clear cache
        if 'sites_list' in st.session_state:
            del st.session_state.sites_list
        
        return True
    except Exception as e:
        print(f"Error deleting site: {e}")
        return False


# =============================================================================
# LOAD PROFILE MANAGEMENT
# =============================================================================



def update_site(site_name: str, updates: dict) -> bool:
    """
    Update specific fields for an existing site
    
    Args:
        site_name: Name of the site to update
        updates: Dictionary of field names and new values
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet('Sites')
        
        # Get all records
        records = sheet.get_all_records()
        
        # Find the site
        site_row = None
        for idx, row in enumerate(records):
            if row.get('name') == site_name:
                site_row = idx + 2  # +2 because header is row 1, and enumerate starts at 0
                break
        
        if not site_row:
            print(f"Site '{site_name}' not found")
            return False
        
        # Get header row to find column indices
        headers = sheet.row_values(1)
        
        # Update each field
        for field_name, new_value in updates.items():
            if field_name in headers:
                col_idx = headers.index(field_name) + 1  # +1 for 1-indexed
                sheet.update_cell(site_row, col_idx, new_value)
            else:
                print(f"Warning: Field '{field_name}' not found in sheet headers")
        
        print(f"Successfully updated site '{site_name}' with {len(updates)} field(s)")
        return True
        
    except Exception as e:
        print(f"Error updating site: {e}")
        return False


def save_site_geojson(site_name: str, geojson_data: dict) -> bool:
    """
    Save GeoJSON data for a site
    
    Args:
        site_name: Name of the site
        geojson_data: GeoJSON dictionary
    
    Returns:
        True if successful, False otherwise
    """
    import json
    
    try:
        # Convert GeoJSON to string
        geojson_str = json.dumps(geojson_data)
        
        # Update the geojson field for this site
        return update_site(site_name, {'geojson': geojson_str})
        
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
        return False


def load_site_geojson(site_name: str) -> Optional[dict]:
    """
    Load GeoJSON data for a site
    
    Args:
        site_name: Name of the site
    
    Returns:
        GeoJSON dictionary if found, None otherwise
    """
    import json
    
    try:
        site = get_site_by_name(site_name)
        
        if not site:
            return None
        
        geojson_str = site.get('geojson', '')
        
        if not geojson_str:
            return None
        
        # Parse JSON string back to dict
        return json.loads(geojson_str)
        
    except Exception as e:
        print(f"Error loading GeoJSON: {e}")
        return None



def load_site_load_profile(site_name: str) -> Optional[Dict]:
    """Load load profile for a specific site"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Try to get Site_Loads worksheet
        try:
            worksheet = spreadsheet.worksheet("Load_Profiles")
        except gspread.WorksheetNotFound:
            # Create Site_Loads worksheet
            worksheet = spreadsheet.add_worksheet(title="Load_Profiles", rows=100, cols=10)
            headers = [
                "site_name", "load_profile_json", "workload_mix_json",
                "dr_params_json", "created_date", "updated_date"
            ]
            worksheet.append_row(headers)
            return None
        
        loads = worksheet.get_all_records()
        for load in loads:
            if load.get('site_name') == site_name:
                # Deserialize JSON fields
                result = {
                    'site_name': site_name,
                    'load_profile': json.loads(load.get('load_profile_json', '{}')),
                    'workload_mix': json.loads(load.get('workload_mix_json', '{}')),
                    'dr_params': json.loads(load.get('dr_params_json', '{}')),
                }
                return result
        
        return None
    except Exception as e:
        print(f"Error loading site load profile: {e}")
        return None


def save_site_load_profile(site_name: str, load_data: Dict) -> bool:
    """Save load profile for a specific site"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Load_Profiles")
        
        # Check if load profile already exists
        loads = worksheet.get_all_records()
        existing_row = None
        for idx, load in enumerate(loads):
            if load.get('site_name') == site_name:
                existing_row = idx + 2
                break
        
        # Prepare row data (serialize complex objects to JSON)
        row_data = [
            site_name,
            json.dumps(load_data.get('load_profile', {})),
            json.dumps(load_data.get('workload_mix', {})),
            json.dumps(load_data.get('dr_params', {})),
            load_data.get('created_date', datetime.now().isoformat()),
            datetime.now().isoformat()
        ]
        
        if existing_row:
            worksheet.update(f'A{existing_row}:F{existing_row}', [row_data])
        else:
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        print(f"Error saving site load profile: {e}")
        return False


# =============================================================================
# OPTIMIZATION STAGE MANAGEMENT
# =============================================================================

def load_site_optimization_stages(site_name: str) -> Dict:
    """Load all optimization stage data for a site"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet("Optimization_Results")
        except gspread.WorksheetNotFound:
            # Create worksheet
            worksheet = spreadsheet.add_worksheet(title="Optimization_Results", rows=100, cols=15)
            headers = [
                "site_name", "stage", "complete", "lcoe", "npv",
                "equipment_json", "dispatch_summary_json", "completion_date", "notes",
                "load_coverage_pct", "constraints_json", "capex_json", "runtime_seconds"
                "site_name", "stage", "complete", "lcoe", "npv",
                "equipment_json", "dispatch_summary_json", "completion_date", "notes",
                "load_coverage_pct", "constraints_json", "capex_json", "runtime_seconds"
            ]
            worksheet.append_row(headers)
            return {
                'screening': {'complete': False, 'lcoe': None, 'date': None},
                'concept': {'complete': False, 'lcoe': None, 'date': None},
                'preliminary': {'complete': False, 'lcoe': None, 'date': None},
                'detailed': {'complete': False, 'lcoe': None, 'date': None},
            }
        
        stages_data = worksheet.get_all_records()
        
        # Build stages dictionary
        stages = {
            'screening': {'complete': False, 'lcoe': None, 'date': None},
            'concept': {'complete': False, 'lcoe': None, 'date': None},
            'preliminary': {'complete': False, 'lcoe': None, 'date': None},
            'detailed': {'complete': False, 'lcoe': None, 'date': None},
        }
        
        for stage_data in stages_data:
            if stage_data.get('site_name') == site_name:
                stage_name = stage_data.get('stage')
                if stage_name in stages:
                    stages[stage_name] = {
                        'complete': stage_data.get('complete', False),
                        'lcoe': stage_data.get('lcoe'),
                        'npv': stage_data.get('npv'),
                        'equipment': json.loads(stage_data.get('equipment_json', '{}')),
                        'dispatch_summary': json.loads(stage_data.get('dispatch_summary_json', '{}')),
                        'date': stage_data.get('completion_date'),
                        'notes': stage_data.get('notes')
                    }
        
        return stages
    except Exception as e:
        print(f"Error loading site optimization stages: {e}")
        return {
            'screening': {'complete': False, 'lcoe': None, 'date': None},
            'concept': {'complete': False, 'lcoe': None, 'date': None},
            'preliminary': {'complete': False, 'lcoe': None, 'date': None},
            'detailed': {'complete': False, 'lcoe': None, 'date': None},
        }


def save_site_stage_result(site_name: str, stage: str, result_data: Dict) -> bool:
    """Save optimization result for a specific stage"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Optimization_Results")  # Updated sheet name
        
        # Check if stage result already exists
        stages = worksheet.get_all_records()
        existing_row = None
        for idx, stage_data in enumerate(stages):
            if stage_data.get('site_name') == site_name and stage_data.get('stage') == stage:
                existing_row = idx + 2
                break
        
        # Prepare row data - save ALL fields as JSON for flexibility
        row_data = [
            site_name,
            stage,
            result_data.get('complete', True),
            result_data.get('lcoe'),
            result_data.get('npv'),
            json.dumps(result_data.get('equipment', {})),
            json.dumps(result_data.get('dispatch_summary', {})),
            datetime.now().isoformat(),
            result_data.get('notes', ''),
            result_data.get('load_coverage_pct', 0),  # Add coverage
            json.dumps(result_data.get('constraints', {})),  # Add constraints
            json.dumps(result_data.get('capex', {})),  # Add capex
            result_data.get('runtime_seconds', 0)  # Add runtime
        ]
        
        if existing_row:
            worksheet.update(f'A{existing_row}:I{existing_row}', [row_data])
        else:
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        print(f"Error saving site stage result: {e}")
        return False



@st.cache_data(ttl=60)  # Reduced to 1 minute to allow fresher data
def load_site_stage_result(site_name: str, stage: str) -> Optional[Dict]:
    """Load optimization result for a specific site and stage
    
    Note: This function is cached to prevent Google Sheets API rate limiting.
    Cache is cleared when generating reports to ensure fresh data.
    """
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Optimization_Results")
        
        stages = worksheet.get_all_records()
        for stage_data in stages:
            if stage_data.get('site_name') == site_name and stage_data.get('stage') == stage:
                # Deserialize JSON fields from Google Sheets strings
                print(f"DEBUG: Found {site_name} - {stage}")
                print(f"DEBUG: equipment_json = {stage_data.get('equipment_json', 'MISSING')[:100]}")
                result = dict(stage_data)
                
                # Parse JSON strings back to dicts
                if 'equipment_json' in result and result['equipment_json']:
                    try:
                        result['equipment'] = json.loads(result['equipment_json'])
                    except:
                        result['equipment'] = {}
                else:
                    result['equipment'] = {}
                
                if 'constraints_json' in result and result['constraints_json']:
                    try:
                        result['constraints'] = json.loads(result['constraints_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                if 'constraints_json' in result and result['constraints_json']:
                    try:
                        result['constraints'] = json.loads(result['constraints_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                if 'constraints_json' in result and result['constraints_json']:
                    try:
                        result['constraints'] = json.loads(result['constraints_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                if 'constraints_json' in result and result['constraints_json']:
                    try:
                        result['constraints'] = json.loads(result['constraints_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                if 'constraints_json' in result and result['constraints_json']:
                    try:
                        result['constraints'] = json.loads(result['constraints_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                
                if 'dispatch_summary_json' in result and result['dispatch_summary_json']:
                    try:
                        result['constraints'] = json.loads(result['dispatch_summary_json'])
                    except:
                        result['constraints'] = {}
                else:
                    result['constraints'] = {}
                
                return result
        
        return None
    except Exception as e:
        print(f"Error loading site stage result: {e}")
        return None

def update_site_stage_status(site_name: str, stage: str, complete: bool) -> bool:
    """Mark a stage as complete or incomplete"""
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Optimization_Results")
        
        stages = worksheet.get_all_records()
        for idx, stage_data in enumerate(stages):
            if stage_data.get('site_name') == site_name and stage_data.get('stage') == stage:
                row_num = idx + 2
                worksheet.update(f'C{row_num}', [[complete]])
                return True
        
        # If stage doesn't exist, create it
        row_data = [site_name, stage, complete, None, None, '{}', '{}', datetime.now().isoformat(), '']
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        print(f"Error updating stage status: {e}")
        return False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_site_by_name(site_name: str) -> Optional[Dict]:
    """Get a specific site by name"""
    sites = load_all_sites()
    for site in sites:
        if site.get('site_name') == site_name:
            return site
    return None




# =============================================================================
# EQUIPMENT DATABASE (Phase 2)
# =============================================================================

def load_equipment_database() -> List[Dict]:
    """
    Load all equipment from Equipment sheet
    
    Returns:
        List of equipment dictionaries
    """
    try:
        client = get_google_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet('Equipment')
        
        records = sheet.get_all_records()
        return records
        
    except Exception as e:
        print(f"Error loading equipment database: {e}")
        # Return defaults if sheet doesn't exist
        return _get_default_equipment()


def _get_default_equipment() -> List[Dict]:
    """Fallback default equipment if sheet not available"""
    return [
        {
            'equipment_id': 'recip_engine',
            'name': 'Reciprocating Engine',
            'type': 'generator',
            'capacity_mw': 1,
            'capex_per_mw': 1800000,
            'opex_annual_per_mw': 45000,
            'efficiency': 0.42,
            'lifetime_years': 25
        },
        {
            'equipment_id': 'gas_turbine',
            'name': 'Gas Turbine',
            'type': 'generator',
            'capacity_mw': 1,
            'capex_per_mw': 1200000,
            'opex_annual_per_mw': 35000,
            'efficiency': 0.35,
            'lifetime_years': 25
        },
        {
            'equipment_id': 'bess',
            'name': 'Battery Storage',
            'type': 'storage',
            'capacity_mwh': 1,
            'capex_per_mwh': 350000,
            'opex_annual_per_mw': 5000,
            'efficiency': 0.90,
            'lifetime_years': 15
        },
        {
            'equipment_id': 'solar_pv',
            'name': 'Solar PV',
            'type': 'renewable',
            'capacity_mw': 1,
            'capex_per_mw': 1000000,
            'opex_annual_per_mw': 12000,
            'efficiency': 0.20,
            'lifetime_years': 30
        }
    ]


def save_custom_equipment(equipment_data: Dict) -> bool:
    """
    Save custom equipment to Equipment sheet
    
    Args:
        equipment_data: Equipment dictionary with all fields
    
    Returns:
        True if successful
    """
    try:
        client = get_google_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet('Equipment')
        
        # Mark as custom
        equipment_data['custom'] = 'true'
        
        # Append row
        row_data = [
            equipment_data.get('equipment_id', ''),
            equipment_data.get('name', ''),
            equipment_data.get('type', ''),
            equipment_data.get('capacity_mw', ''),
            equipment_data.get('capacity_mwh', ''),
            equipment_data.get('capex_per_mw', ''),
            equipment_data.get('capex_per_mwh', ''),
            equipment_data.get('opex_annual_per_mw', ''),
            equipment_data.get('efficiency', ''),
            equipment_data.get('lifetime_years', ''),
            equipment_data.get('heat_rate_btu_kwh', ''),
            equipment_data.get('nox_rate_lb_mmbtu', ''),
            equipment_data.get('gas_consumption_mcf_mwh', ''),
            'true',  # custom
            equipment_data.get('notes', '')
        ]
        
        sheet.append_row(row_data)
        print(f"Saved custom equipment: {equipment_data.get('name')}")
        return True
        
    except Exception as e:
        print(f"Error saving custom equipment: {e}")
        return False


# =============================================================================
# GLOBAL PARAMETERS (Phase 2)
# =============================================================================

def load_global_parameters() -> Dict:
    """
    Load all global parameters from Global_Parameters sheet
    
    Returns:
        Dictionary of parameters {name: value}
    """
    try:
        client = get_google_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet('Global_Parameters')
        
        records = sheet.get_all_records()
        
        # Convert to simple dict
        params = {}
        for record in records:
            param_name = record.get('parameter_name')
            value = record.get('value')
            
            # Try to convert to appropriate type
            try:
                if value.lower() in ['true', 'false']:
                    params[param_name] = value.lower() == 'true'
                elif '.' in str(value):
                    params[param_name] = float(value)
                else:
                    params[param_name] = int(value)
            except:
                params[param_name] = value
        
        return params
        
    except Exception as e:
        print(f"Error loading global parameters: {e}")
        return _get_default_parameters()


def _get_default_parameters() -> Dict:
    """Fallback default parameters"""
    return {
        'discount_rate': 0.08,
        'analysis_period_years': 15,
        'electricity_price': 80,
        'gas_price': 5,
        'capacity_price': 150,
        'default_availability': 0.95,
        'n_minus_1_default': True,
        'emissions_limit_factor': 1.0
    }


def update_global_parameter(param_name: str, new_value: Any) -> bool:
    """
    Update a single global parameter
    
    Args:
        param_name: Name of parameter to update
        new_value: New value
    
    Returns:
        True if successful
    """
    try:
        client = get_google_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet('Global_Parameters')
        
        # Find the row
        records = sheet.get_all_records()
        for idx, record in enumerate(records):
            if record.get('parameter_name') == param_name:
                row_num = idx + 2  # +2 for header and 0-indexing
                # Update value column (column B = 2)
                sheet.update_cell(row_num, 2, str(new_value))
                print(f"Updated {param_name} = {new_value}")
                return True
        
        print(f"Parameter {param_name} not found")
        return False
        
    except Exception as e:
        print(f"Error updating parameter: {e}")
        return False


# =============================================================================  
# STAGE NOTES (Phase 2)
# =============================================================================

def save_stage_notes(site_name: str, stage: str, notes: str) -> bool:
    """
    Save notes for an optimization stage
    
    Args:
        site_name: Name of site
        stage: Stage key (screening, concept, preliminary, detailed)
        notes: Notes text
    
    Returns:
        True if successful
    """
    try:
        client = get_google_sheets_client()
        sheet = client.open_by_key(SHEET_ID).worksheet('Site_Optimization_Stages')
        
        # Find the row for this site/stage
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        
        if 'notes' not in headers:
            print("Notes column not found in sheet")
            return False
        
        notes_col = headers.index('notes') + 1
        
        for idx, record in enumerate(records):
            if record.get('site_name') == site_name and record.get('stage') == stage:
                row_num = idx + 2
                sheet.update_cell(row_num, notes_col, notes)
                print(f"Saved notes for {site_name} - {stage}")
                return True
        
        print(f"Stage {site_name}/{stage} not found")
        return False
        
    except Exception as e:
        print(f"Error saving notes: {e}")
        return False


def load_stage_notes(site_name: str, stage: str) -> Optional[str]:
    """
    Load notes for an optimization stage
    
    Args:
        site_name: Name of site
        stage: Stage key
    
    Returns:
        Notes string or None
    """
    try:
        # Use existing load_site_stage_result function
        result = load_site_stage_result(site_name, stage)
        if result:
            return result.get('notes', '')
        return None
        
    except Exception as e:
        print(f"Error loading notes: {e}")
        return None



def sync_session_sites_to_sheets():
    """Sync all sites in session state to Google Sheets"""
    if 'sites_list' not in st.session_state:
        return
    
    for site in st.session_state.sites_list:
        save_site(site)
