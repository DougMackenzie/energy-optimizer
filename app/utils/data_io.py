"""
Data I/O Utilities
Functions for loading/saving data from various backends
"""

import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

# Try to import Google Sheets library
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


def load_equipment_library(config_path: Optional[Path] = None) -> Dict[str, List[Dict]]:
    """
    Load equipment library from YAML config file
    
    Returns dict with keys: recip_engines, gas_turbines, bess, solar_pv, grid
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "equipment_defaults.yaml"
    
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "recip_engines": [],
            "gas_turbines": [],
            "bess": [],
            "solar_pv": [],
            "grid": [],
        }


def load_equipment_from_sheets(
    sheet_id: str = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so",
    credentials_path: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, List[Dict]]:
    """
    Load equipment library from Google Sheets - SINGLE SOURCE OF TRUTH
    
    This is the primary function for loading equipment data. All pages should use this.
    
    Args:
        sheet_id: Google Sheets ID
        credentials_path: Path to credentials.json (defaults to project root)
        use_cache: Cache results in session state for performance
    
    Returns:
        Dict with keys:
        - Reciprocating_Engines: List of recip engine specs
        - Gas_Turbines: List of gas turbine specs
        - BESS: List of battery system specs
        - Solar_PV: List of solar configurations
        - Grid_Connection: List of grid/ISO profiles
    """
    import streamlit as st
    
    # Check cache first
    if use_cache and 'equipment_library' in st.session_state:
        return st.session_state.equipment_library
    
    if credentials_path is None:
        credentials_path = str(Path(__file__).parent.parent.parent / "credentials.json")
    
    try:
        client = get_google_sheets_client(credentials_path)
        spreadsheet = client.open_by_key(sheet_id)
        
        equipment_data = {}
        
        # Load each equipment type from its worksheet
        worksheets = [
            "Reciprocating_Engines",
            "Gas_Turbines", 
            "BESS",
            "Solar_PV",
            "Grid_Connection"
        ]
        
        for worksheet_name in worksheets:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                records = worksheet.get_all_records()
                
                # Convert numeric strings to proper types
                for record in records:
                    for key, value in record.items():
                        if isinstance(value, str):
                            # Try to convert to number
                            try:
                                if '.' in value:
                                    record[key] = float(value)
                                else:
                                    record[key] = int(value)
                            except (ValueError, AttributeError):
                                pass  # Keep as string
                
                equipment_data[worksheet_name] = records
                
            except Exception as e:
                print(f"Warning: Could not load {worksheet_name}: {e}")
                equipment_data[worksheet_name] = []
        
        # Cache in session state
        if use_cache:
            st.session_state.equipment_library = equipment_data
        
        return equipment_data
        
    except Exception as e:
        print(f"Error loading from Google Sheets: {e}")
        # Return empty structure on error
        return {
            "Reciprocating_Engines": [],
            "Gas_Turbines": [],
            "BESS": [],
            "Solar_PV": [],
            "Grid_Connection": []
        }



def save_project(project: Dict[str, Any], filepath: Path) -> bool:
    """Save project to JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(project, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving project: {e}")
        return False


def load_project(filepath: Path) -> Optional[Dict[str, Any]]:
    """Load project from JSON file"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing project file: {e}")
        return None


# =============================================================================
# Google Sheets Backend
# =============================================================================

def get_google_sheets_client(credentials_path: str):
    """Get authenticated Google Sheets client"""
    if not GSPREAD_AVAILABLE:
        raise ImportError("gspread library not installed. Run: pip install gspread google-auth")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return gspread.authorize(credentials)


def load_from_sheets(sheet_id: str, worksheet_name: str, credentials_path: str) -> List[Dict]:
    """Load data from Google Sheets"""
    client = get_google_sheets_client(credentials_path)
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)
    return worksheet.get_all_records()


def save_to_sheets(data: List[Dict], sheet_id: str, worksheet_name: str, credentials_path: str) -> bool:
    """Save data to Google Sheets"""
    client = get_google_sheets_client(credentials_path)
    sheet = client.open_by_key(sheet_id)
    
    try:
        worksheet = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(worksheet_name, rows=1000, cols=26)
    
    if not data:
        return True
    
    # Clear and write
    worksheet.clear()
    headers = list(data[0].keys())
    worksheet.append_row(headers)
    
    for row in data:
        worksheet.append_row([row.get(h, "") for h in headers])
    
    return True


# =============================================================================
# SharePoint Backend (Future)
# =============================================================================

def load_from_sharepoint(site_url: str, list_name: str) -> List[Dict]:
    """Load data from SharePoint List (placeholder)"""
    raise NotImplementedError("SharePoint integration coming in Phase 8")


def save_to_sharepoint(data: List[Dict], site_url: str, list_name: str) -> bool:
    """Save data to SharePoint List (placeholder)"""
    raise NotImplementedError("SharePoint integration coming in Phase 8")
