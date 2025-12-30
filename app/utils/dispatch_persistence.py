"""
Dispatch Data Persistence Functions
Save and load hourly dispatch data to/from Google Sheets Dispatch_Data tab
"""

import json
from typing import Dict
from datetime import datetime


# Import the client function
def get_google_sheets_client():
    """Get authenticated Google Sheets client"""
    import gspread
    return gspread.service_account(filename='credentials.json')


def save_dispatch_data(site_name: str, stage: str, version: int, dispatch_by_year: dict) -> bool:
    """
    Save hourly dispatch data to Dispatch_Data tab in Google Sheets.
    
    Args:
        site_name: Name of the site
        stage: Optimization stage (screening, concept, etc.)
        version: Version number
        dispatch_by_year: Dict of {year: {'dispatch_data': {col: [values]}, 'columns': [...]}}
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from config.settings import GOOGLE_SHEET_ID as SHEET_ID
        
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get or create Dispatch_Data worksheet
        try:
            worksheet = spreadsheet.worksheet("Dispatch_Data")
            print("📊 Found existing Dispatch_Data tab")
        except:
            worksheet = spreadsheet.add_worksheet("Dispatch_Data", rows=200000, cols=12)
            # Add header row
            headers = [['site_name', 'stage', 'version', 'year', 'hour',
                       'load_mw', 'recip_mw', 'turbine_mw', 'solar_mw', 'bess_mw', 'grid_mw', 'unserved_mw']]
            worksheet.update('A1:L1', headers)
            print("📊 Created new Dispatch_Data tab with headers")
        
        # Delete existing data for this site/stage/version
        print(f"🔍 Checking for existing dispatch data: {site_name}/{stage}/v{version}")
        all_data = worksheet.get_all_records()
        rows_to_delete = []
        for idx, row in enumerate(all_data):
            if (str(row.get('site_name')) == site_name and 
                str(row.get('stage')) == stage and 
                int(row.get('version', 0)) == version):
                rows_to_delete.append(idx + 2)  # +2 for 1-indexing and header
        
        # Delete from bottom to top to preserve row numbers
        if rows_to_delete:
            print(f"🗑️  Deleting {len(rows_to_delete)} existing rows")
            for row_idx in sorted(rows_to_delete, reverse=True):
                worksheet.delete_rows(row_idx)
        
        # Prepare batch data
        rows_to_add = []
        for year, disp_data in dispatch_by_year.items():
            # disp_data is {'dispatch_data': {...}, 'columns': [...]}
            if isinstance(disp_data, dict) and 'dispatch_data' in disp_data:
                df_dict = disp_data['dispatch_data']
                num_hours = len(df_dict.get('load_mw', []))
                
                print(f"  📅 Year {year}: {num_hours} hours")
                
                for hour in range(num_hours):
                    rows_to_add.append([
                        site_name,
                        stage,
                        version,
                        int(year),
                        hour,
                        float(df_dict.get('load_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('recip_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('turbine_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('solar_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('bess_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('grid_mw', [0]*num_hours)[hour] or 0),
                        float(df_dict.get('unserved_mw', [0]*num_hours)[hour] or 0),
                    ])
        
        if not rows_to_add:
            print("⚠️  No dispatch data to save")
            return True
        
        # Batch append (Google Sheets API can handle ~10K rows per call)
        print(f"💾 Saving {len(rows_to_add)} dispatch data rows...")
        chunk_size = 5000  # Conservative to avoid quota issues
        for i in range(0, len(rows_to_add), chunk_size):
            chunk = rows_to_add[i:i+chunk_size]
            worksheet.append_rows(chunk, value_input_option='USER_ENTERED')
            print(f"  ✓ Saved rows {i+1} to {min(i+chunk_size, len(rows_to_add))}")
        
        print(f"✅ Saved {len(rows_to_add)} dispatch data rows for {site_name}/{stage}/v{version}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving dispatch data: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_dispatch_data(site_name: str, stage: str, version: int = 1) -> Dict:
    """
    Load hourly dispatch data from Dispatch_Data tab in Google Sheets.
    
    Args:
        site_name: Name of the site
        stage: Optimization stage
        version: Version number
    
    Returns:
        Dict of {year: {'dispatch_data': {col: [values]}}}
    """
    try:
        from config.settings import GOOGLE_SHEET_ID as SHEET_ID
        
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet("Dispatch_Data")
        except:
            print("⚠️  Dispatch_Data tab not found")
            return {}
        
        print(f"🔍 Loading dispatch data: {site_name}/{stage}/v{version}")
        
        # Load all records
        all_data = worksheet.get_all_records()
        
        # Filter for this site/stage/version and group by year
        dispatch_by_year = {}
        rows_found = 0
        
        for row in all_data:
            if (str(row.get('site_name')) == site_name and 
                str(row.get('stage')) == stage and 
                int(row.get('version', 0)) == version):
                
                rows_found += 1
                year = int(row['year'])
                
                if year not in dispatch_by_year:
                    dispatch_by_year[year] = {
                        'dispatch_data': {
                            'hour': [],
                            'load_mw': [],
                            'recip_mw': [],
                            'turbine_mw': [],
                            'solar_mw': [],
                            'bess_mw': [],
                            'grid_mw': [],
                            'unserved_mw': [],
                        }
                    }
                
                # Append data for this hour
                dispatch_by_year[year]['dispatch_data']['hour'].append(int(row['hour']))
                dispatch_by_year[year]['dispatch_data']['load_mw'].append(float(row.get('load_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['recip_mw'].append(float(row.get('recip_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['turbine_mw'].append(float(row.get('turbine_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['solar_mw'].append(float(row.get('solar_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['bess_mw'].append(float(row.get('bess_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['grid_mw'].append(float(row.get('grid_mw', 0)))
                dispatch_by_year[year]['dispatch_data']['unserved_mw'].append(float(row.get('unserved_mw', 0)))
        
        if rows_found > 0:
            print(f"✅ Loaded {rows_found} rows for {len(dispatch_by_year)} years")
            for year in sorted(dispatch_by_year.keys()):
                hours = len(dispatch_by_year[year]['dispatch_data']['hour'])
                print(f"  📅 Year {year}: {hours} hours")
        else:
            print(f"⚠️  No dispatch data found for {site_name}/{stage}/v{version}")
        
        return dispatch_by_year
        
    except Exception as e:
        print(f"❌ Error loading dispatch data: {e}")
        import traceback
        traceback.print_exc()
        return {}
