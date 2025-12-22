"""
Data loader functions for sites, scenarios, and constraints
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


def get_google_sheets_client(credentials_path: str):
    """Get authenticated Google Sheets client"""
    if not GSPREAD_AVAILABLE:
        raise ImportError("gspread library not installed")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return gspread.authorize(credentials)


def load_sites(
    sheet_id: str = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so",
    credentials_path: Optional[str] = None,
    use_cache: bool = True
) -> List[Dict]:
    """Load available sites from Google Sheets"""
    
    # Check cache first
    if use_cache and 'sites' in st.session_state:
        return st.session_state.sites
    
    if credentials_path is None:
        credentials_path = str(Path(__file__).parent.parent.parent / "credentials.json")
    
    try:
        client = get_google_sheets_client(credentials_path)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("Sites")
        sites = worksheet.get_all_records()
        
        # Cache in session state
        if use_cache:
            st.session_state.sites = sites
        
        return sites
    except Exception as e:
        print(f"Error loading sites: {e}")
        return []


def load_site_constraints(
    site_id: str,
    sheet_id: str = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so",
    credentials_path: Optional[str] = None
) -> Dict:
    """Load constraints for a specific site"""
    
    if credentials_path is None:
        credentials_path = str(Path(__file__).parent.parent.parent / "credentials.json")
    
    try:
        client = get_google_sheets_client(credentials_path)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("Site_Constraints")
        all_constraints = worksheet.get_all_records()
        
        # Find constraints for this site
        for constraint in all_constraints:
            if constraint.get('Site_ID') == site_id:
                return constraint
        
        return {}
    except Exception as e:
        print(f"Error loading site constraints: {e}")
        return {}


def load_scenario_templates(
    sheet_id: str = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so",
    credentials_path: Optional[str] = None,
    use_cache: bool = True
) -> List[Dict]:
    """Load pre-defined scenario templates"""
    
    # Key representative scenarios for fast prototyping (5 scenarios instead of 31)
    # To restore all 31 combinations, uncomment the itertools code below
    scenarios = [
        {
            'Scenario_ID': 1,
            'Scenario_Name': 'BTM Only',
            'Description': 'Behind-the-meter: Recip + Turbine + BESS + Solar (no grid)',
            'Recip_Enabled': True,
            'Turbine_Enabled': True,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': False,
            'Objective_Priority': 'Maximum Power',
            'Grid_Timeline_Months': 0
        },
        {
            'Scenario_ID': 2,
            'Scenario_Name': 'All Technologies',
            'Description': 'Full stack: Recip + Turbine + BESS + Solar + Grid',
            'Recip_Enabled': True,
            'Turbine_Enabled': True,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': True,
            'Objective_Priority': 'Maximum Power',
            'Grid_Timeline_Months': 36
        },
        {
            'Scenario_ID': 3,
            'Scenario_Name': 'Recip Engines Only',
            'Description': 'Reciprocating engines only (most flexible)',
            'Recip_Enabled': True,
            'Turbine_Enabled': False,
            'BESS_Enabled': False,
            'Solar_Enabled': False,
            'Grid_Enabled': False,
            'Objective_Priority': 'Maximum Power',
            'Grid_Timeline_Months': 0
        },
        {
            'Scenario_ID': 4,
            'Scenario_Name': 'Recip + Grid',
            'Description': 'Engines with grid backup',
            'Recip_Enabled': True,
            'Turbine_Enabled': False,
            'BESS_Enabled': False,
            'Solar_Enabled': False,
            'Grid_Enabled': True,
            'Objective_Priority': 'Maximum Power',
            'Grid_Timeline_Months': 36
        },
        {
            'Scenario_ID': 5,
            'Scenario_Name': 'Renewables + Grid',
            'Description': 'Solar + BESS + Grid (low carbon)',
            'Recip_Enabled': False,
            'Turbine_Enabled': False,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': True,
            'Objective_Priority': 'Maximum Power',
            'Grid_Timeline_Months': 12
        }
    ]
    
    # Cache in session state
    if use_cache:
        st.session_state.scenarios = scenarios
    
    return scenarios
    
    # ORIGINAL CODE (disabled):
    """
    # Check cache first
    if use_cache and 'scenarios' in st.session_state:
        return st.session_state.scenarios
    
    if credentials_path is None:
        credentials_path = str(Path(__file__).parent.parent.parent / "credentials.json")
    
    try:
        client = get_google_sheets_client(credentials_path)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("Scenario_Templates")
        scenarios = worksheet.get_all_records()
        
        # Cache in session state
        if use_cache:
            st.session_state.scenarios = scenarios
        
        return scenarios
    except Exception as e:
        print(f"Error loading scenarios: {e}")
        return []
    """


def load_optimization_objectives(
    site_id: str,
    sheet_id: str = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so",
    credentials_path: Optional[str] = None
) -> Dict:
    """Load optimization objectives for a specific site"""
    
    if credentials_path is None:
        credentials_path = str(Path(__file__).parent.parent.parent / "credentials.json")
    
    try:
        client = get_google_sheets_client(credentials_path)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("Optimization_Objectives")
        all_objectives = worksheet.get_all_records()
        
        # Find objectives for this site
        for obj in all_objectives:
            if obj.get('Site_ID') == site_id:
                return obj
        
        return {}
    except Exception as e:
        print(f"Error loading optimization objectives: {e}")
        return {}
