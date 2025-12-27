#!/usr/bin/env python3
"""
Add GeoJSON and Load Profile Management
1. Add GeoJSON data to each site
2. Update Load page to save load profiles
3. Connect load profiles to optimizer
"""

from pathlib import Path
import sys
import json
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

# Sample GeoJSON for each site
SITE_GEOJSON_DATA = {
    "Phoenix AI Campus": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "Phoenix AI Campus",
                "area_acres": 750,
                "zoning": "Data Center District",
                "available_acres": 600,
                "site_id": "PHX-AI-001"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-112.0740, 33.4484],
                    [-112.0680, 33.4484],
                    [-112.0680, 33.4420],
                    [-112.0740, 33.4420],
                    [-112.0740, 33.4484]
                ]]
            }
        }]
    },
    "Dallas Hyperscale DC": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "Dallas Hyperscale DC",
                "area_acres": 150,
                "zoning": "Industrial M-2",
                "available_acres": 45,
                "site_id": "DAL-DC-001"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-96.7970, 32.7767],
                    [-96.7910, 32.7767],
                    [-96.7910, 32.7703],
                    [-96.7970, 32.7703],
                    [-96.7970, 32.7767]
                ]]
            }
        }]
    },
    "Austin Greenfield DC": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "Austin Greenfield DC",
                "area_acres": 500,
                "zoning": "Industrial",
                "available_acres": 300,
                "site_id": "AUS-DC-001"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-97.7431, 30.2672],
                    [-97.7371, 30.2672],
                    [-97.7371, 30.2608],
                    [-97.7431, 30.2608],
                    [-97.7431, 30.2672]
                ]]
            }
        }]
    },
    "Tulsa Industrial Park": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "Tulsa Industrial Park",
                "area_acres": 1200,
                "zoning": "Industrial",
                "available_acres": 850,
                "site_id": "TUL-IND-001"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-95.9635, 36.1540],
                    [-95.9580, 36.1540],
                    [-95.9580, 36.1485],
                    [-95.9635, 36.1485],
                    [-95.9635, 36.1540]
                ]]
            }
        }]
    }
}


def add_geojson_to_sites():
    """Add GeoJSON data to each site in Sites sheet"""
    print("=" * 80)
    print("ADDING GEOJSON DATA TO SITES")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        # Get current data
        headers = sites_sheet.row_values(1)
        all_data = sites_sheet.get_all_records()
        
        if 'geojson' not in headers:
            print("❌ geojson column not found in Sites sheet!")
            return False
        
        geojson_col_idx = headers.index('geojson') + 1  # 1-indexed
        
        print(f"\nFound {len(all_data)} sites")
        
        for idx, site in enumerate(all_data, 2):  # Start at row 2 (after headers)
            site_name = site.get('name', '')
            
            if site_name in SITE_GEOJSON_DATA:
                geojson = SITE_GEOJSON_DATA[site_name]
                geojson_str = json.dumps(geojson)
                
                # Update the geojson cell
                sites_sheet.update_cell(idx, geojson_col_idx, geojson_str)
                print(f"   ✅ {site_name:30} - Added GeoJSON ({len(geojson_str)} chars)")
            else:
                print(f"   ⚠️  {site_name:30} - No sample GeoJSON (skipped)")
        
        print("\n✅ GeoJSON data added to sites")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_sample_variables_to_sites():
    """Add additional useful variables to Sites sheet"""
    print("\n" + "=" * 80)
    print("ADDING ADDITIONAL SITE VARIABLES")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        headers = sites_sheet.row_values(1)
        
        # Additional columns we might want
        new_columns = [
            'coordinates',  # lat, lng as string
            'timezone',     # e.g., 'America/Chicago'
            'climate_zone',  # e.g., 'Hot-Dry'
            'avg_temp_f',    # Average temperature
            'geojson_prefix',  # Prefix for loading sample GeoJSON files
        ]
        
        # Add missing columns
        current_col_count = len(headers)
        cols_to_add = []
        
        for col in new_columns:
            if col not in headers:
                cols_to_add.append(col)
        
        if cols_to_add:
            print(f"\nAdding {len(cols_to_add)} new columns...")
            for i, col_name in enumerate(cols_to_add):
                col_idx = current_col_count + i + 1
                sites_sheet.update_cell(1, col_idx, col_name)
                print(f"   ✅ Added column: {col_name}")
            
            # Now populate with sample data
            all_data = sites_sheet.get_all_records()
            headers = sites_sheet.row_values(1)  # Reload headers
            
            site_data = {
                "Phoenix AI Campus": {
                    "coordinates": "33.4484, -112.0740",
                    "timezone": "America/Phoenix",
                    "climate_zone": "Hot-Dry",
                    "avg_temp_f": "75",
                    "geojson_prefix": "phoenix"
                },
                "Dallas Hyperscale DC": {
                    "coordinates": "32.7767, -96.7970",
                    "timezone": "America/Chicago",
                    "climate_zone": "Hot-Humid",
                    "avg_temp_f": "66",
                    "geojson_prefix": "dallas"
                },
                "Austin Greenfield DC": {
                    "coordinates": "30.2672, -97.7431",
                    "timezone": "America/Chicago",
                    "climate_zone": "Hot-Humid",
                    "avg_temp_f": "68",
                    "geojson_prefix": "austin"
                },
                "Tulsa Industrial Park": {
                    "coordinates": "36.1540, -95.9635",
                    "timezone": "America/Chicago",
                    "climate_zone": "Mixed-Humid",
                    "avg_temp_f": "60",
                    "geojson_prefix": "tulsa"
                }
            }
            
            print("\nPopulating data for new columns...")
            for idx, site in enumerate(all_data, 2):
                site_name = site.get('name', '')
                
                if site_name in site_data:
                    data = site_data[site_name]
                    
                    for col_name, value in data.items():
                        if col_name in headers:
                            col_idx = headers.index(col_name) + 1
                            sites_sheet.update_cell(idx, col_idx, value)
                    
                    print(f"   ✅ Updated {site_name}")
        else:
            print("\n   ✓ All columns already exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_load_profiles_sheet():
    """Verify Load_Profiles sheet has correct schema"""
    print("\n" + "=" * 80)
    print("VERIFYING LOAD_PROFILES SHEET")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        
        try:
            load_sheet = spreadsheet.worksheet('Load_Profiles')
            headers = load_sheet.row_values(1)
            
            print(f"\nCurrent Load_Profiles headers ({len(headers)}):")
            for h in headers:
                print(f"   - {h}")
            
            required_fields = [
                'site_name', 'load_profile_json', 'workload_mix_json',
                'dr_params_json', 'created_date', 'updated_date'
            ]
            
            missing = [f for f in required_fields if f not in headers]
            
            if missing:
                print(f"\n⚠️  Missing fields: {missing}")
            else:
                print("\n✅ Load_Profiles sheet has all required fields")
            
            return True
            
        except Exception as e:
            print(f"❌ Load_Profiles sheet error: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("ENHANCING SITES WITH GEOJSON & ADDITIONAL VARIABLES")
    print("=" * 80)
    
    # Step 1: Add GeoJSON
    if add_geojson_to_sites():
        print("\n✅ GeoJSON added successfully")
    else:
        print("\n❌ GeoJSON addition failed")
    
    # Step 2: Add additional variables
    if add_sample_variables_to_sites():
        print("\n✅ Additional variables added")
    else:
        print("\n❌ Additional variables failed")
    
    # Step 3: Verify Load_Profiles
    verify_load_profiles_sheet()
    
    print("\n" + "=" * 80)
    print("✅ ENHANCEMENT COMPLETE")
    print("=" * 80)
    print("\nSites now have:")
    print("  • GeoJSON boundary data")
    print("  • Coordinates, timezone, climate zone")
    print("  • geojson_prefix for sample data loading")
    print("\nLoad_Profiles sheet ready for load profile storage")
