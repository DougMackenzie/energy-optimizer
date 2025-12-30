# IMMEDIATE CACHING FIX
# Add these wrapper functions to cache Equipment and Global_Parameters loading

import streamlit as st

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_equipment_from_sheets_cached(spreadsheet_id: str):
    """Cached wrapper for loading equipment specs."""
    import gspread
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open_by_key(spreadsheet_id)
    ws = spreadsheet.worksheet('Equipment')
    data = ws.get_all_records()
    print(f"📥 FRESH LOAD: Equipment specs from Google Sheets ({len(data)} rows)")
    return data

@st.cache_data(ttl=300)  # Cache for 5 minutes  
def load_global_params_from_sheets_cached(spreadsheet_id: str):
    """Cached wrapper for loading global parameters."""
    import gspread
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open_by_key(spreadsheet_id)
    ws = spreadsheet.worksheet('Global_Parameters')
    data = ws.get_all_records()
    print(f"📥 FRESH LOAD: Global params from Google Sheets ({len(data)} rows)")
    return data

# Then in BackendDataLoader.load_equipment_specs(), replace the _read_sheet_range call with:
# equipment_df = pd.DataFrame(load_equipment_from_sheets_cached(self.spreadsheet_id))

# This will cache at the Streamlit level and prevent quota issues!
