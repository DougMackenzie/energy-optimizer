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
    
    # Return 31 comprehensive scenarios with full equipment combination testing
    import itertools
    
    # Technologies to permute
    techs = ['Recip', 'Turbine', 'BESS', 'Solar', 'Grid']
    
    scenarios = []
    idx = 1
    
    # Generate all combinations (1 to 5 technologies)
    for r in range(1, len(techs) + 1):
        for combo in itertools.combinations(techs, r):
            # Create scenario dict
            name = " + ".join(combo)
            
            # Determine enablement
            recip = 'Recip' in combo
            turbine = 'Turbine' in combo
            bess = 'BESS' in combo
            solar = 'Solar' in combo
            grid = 'Grid' in combo
            
            scenario = {
                'Scenario_ID': idx,
                'Scenario_Name': name,
                'Description': f"Combination: {name}. Maximizes power subject to constraints.",
                'Recip_Enabled': recip,
                'Turbine_Enabled': turbine,
                'BESS_Enabled': bess,
                'Solar_Enabled': solar,
                'Grid_Enabled': grid,
                'Objective_Priority': 'Maximum Power',
                'Grid_Timeline_Months': 36 if grid else 0  # Default 36mo delay for grid
            }
            scenarios.append(scenario)
            idx += 1
    
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
