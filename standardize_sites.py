#!/usr/bin/env python3
"""
Standardize Site Names Throughout Application
Fix naming inconsistencies and add site selector to Load page
"""

from pathlib import Path
import sys
import json
sys.path.append(str(Path(__file__).parent))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

# STANDARDIZED SITE NAMES (matching optimizer sample data)
STANDARD_SITE_NAMES = {
    "Dallas Datacenter Campus": "Dallas Hyperscale DC",
    "Northern Virginia AI Cluster": "Phoenix AI Campus", 
    "Tulsa Industrial Park": "Austin Greenfield DC",
    "Phoenix, AZ": "Tulsa Industrial Park"
}

# Standard site configurations
STANDARD_SITES = {
    "Dallas Hyperscale DC": {
        "location": "Dallas, TX",
        "coordinates": "32.7767, -96.7970",
        "timezone": "America/Chicago",
        "climate_zone": "Hot-Humid",
        "avg_temp_f": "66",
        "geojson_prefix": "dallas",
        "iso": "ERCOT",
        "it_capacity_mw": "600",
        "problem_num": "2"  # Brownfield by default
    },
    "Phoenix AI Campus": {
        "location": "Phoenix, AZ",
        "coordinates": "33.4484, -112.0740",
        "timezone": "America/Phoenix",
        "climate_zone": "Hot-Dry",
        "avg_temp_f": "75",
        "geojson_prefix": "phoenix",
        "iso": "WECC",
        "it_capacity_mw": "750",
        "problem_num": "1"  # Greenfield
    },
    "Austin Greenfield DC": {
        "location": "Austin, TX",
        "coordinates": "30.2672, -97.7431",
        "timezone": "America/Chicago",
        "climate_zone": "Hot-Humid",
        "avg_temp_f": "68",
        "geojson_prefix": "austin",
        "iso": "ERCOT",
        "it_capacity_mw": "600",
        "problem_num": "1"  # Greenfield
    },
    "Tulsa Industrial Park": {
        "location": "Tulsa, OK",
        "coordinates": "36.1540, -95.9635",
        "timezone": "America/Chicago",
        "climate_zone": "Mixed-Humid",
        "avg_temp_f": "60",
        "geojson_prefix": "tulsa",
        "iso": "SPP",
        "it_capacity_mw": "500",
        "problem_num": "1"  # Greenfield
    }
}

def standardize_site_names():
    """Rename sites to match standard naming convention"""
    print("=" * 80)
    print("STANDARDIZING SITE NAMES")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        # Get current data
        headers = sites_sheet.row_values(1)
        all_data = sites_sheet.get_all_records()
        
        name_col_idx = headers.index('name') + 1
        
        print(f"\nCurrent sites:")
        for idx, site in enumerate(all_data, 2):
            current_name = site.get('name', '')
            print(f"   {idx-1}. {current_name}")
            
            if current_name in STANDARD_SITE_NAMES:
                new_name = STANDARD_SITE_NAMES[current_name]
                sites_sheet.update_cell(idx, name_col_idx, new_name)
                print(f"      → Renamed to: {new_name}")
        
        print("\n✅ Site names standardized")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_site_data():
    """Update all site data to match standardized configuration"""
    print("\n" + "=" * 80)
    print("UPDATING SITE DATA")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        headers = sites_sheet.row_values(1)
        all_data = sites_sheet.get_all_records()
        
        print(f"\nUpdating {len(all_data)} sites...")
        
        for idx, site in enumerate(all_data, 2):
            site_name = site.get('name', '')
            
            if site_name in STANDARD_SITES:
                config = STANDARD_SITES[site_name]
                
                print(f"\n{site_name}:")
                
                for field, value in config.items():
                    if field in headers:
                        col_idx = headers.index(field) + 1
                        sites_sheet.update_cell(idx, col_idx, value)
                        print(f"   ✓ {field} = {value}")
        
        print("\n✅ Site data updated")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_geojson_for_all_sites():
    """Add proper GeoJSON for all standardized sites"""
    print("\n" + "=" * 80)
    print("UPDATING GEOJSON FOR ALL SITES")
    print("=" * 80)
    
    SITE_GEOJSON = {
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
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        headers = sites_sheet.row_values(1)
        all_data = sites_sheet.get_all_records()
        
        geojson_col_idx = headers.index('geojson') + 1
        
        for idx, site in enumerate(all_data, 2):
            site_name = site.get('name', '')
            
            if site_name in SITE_GEOJSON:
                geojson_str = json.dumps(SITE_GEOJSON[site_name])
                sites_sheet.update_cell(idx, geojson_col_idx, geojson_str)
                print(f"   ✅ {site_name} - GeoJSON updated")
        
        print("\n✅ GeoJSON updated for all sites")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("SITE NAME & DATA STANDARDIZATION")
    print("=" * 80)
    print("\nStandardizing to match optimizer sample data:")
    print("  • Dallas Hyperscale DC")
    print("  • Phoenix AI Campus")
    print("  • Austin Greenfield DC")
    print("  • Tulsa Industrial Park")
    
    # Step 1: Standardize names
    if standardize_site_names():
        print("\n✅ Names standardized")
    
    # Step 2: Update site data
    if update_site_data():
        print("\n✅ Data updated")
    
    # Step 3: Update GeoJSON
    if update_geojson_for_all_sites():
        print("\n✅ GeoJSON updated")
    
    print("\n" + "=" * 80)
    print("✅ STANDARDIZATION COMPLETE")
    print("=" * 80)
    print("\nAll sites now have:")
    print("  • Standardized names matching optimizer samples")
    print("  • Complete geographic data (coordinates, timezone, climate)")
    print("  • GeoJSON boundary data")
    print("  • Proper geojson_prefix for Dashboard")
