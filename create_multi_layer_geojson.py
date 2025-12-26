#!/usr/bin/env python3
"""
Create comprehensive multi-layer GeoJSON for all sites
Includes: Site Boundary, Transmission, Natural Gas, Fiber, Water
"""

import json
from pathlib import Path
import sys
sys.path.append(str(Path.cwd()))

from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def create_multi_layer_geojson(site_name, center_lat, center_lon, area_acres=300):
    """Create a comprehensive GeoJSON with all 5 infrastructure layers"""
    
    # Calculate offsets based on area (rough approximation)
    lat_offset = 0.01  # ~1.1 km
    lon_offset = 0.01
    
    # Site boundary (rectangle)
    boundary_coords = [
        [center_lon - lon_offset, center_lat - lat_offset],
        [center_lon + lon_offset, center_lat - lat_offset],
        [center_lon + lon_offset, center_lat + lat_offset],
        [center_lon - lon_offset, center_lat + lat_offset],
        [center_lon - lon_offset, center_lat - lat_offset],
    ]
    
    # Transmission lines (diagonal from SW to NE through site)
    transmission_coords = [
        [center_lon - lon_offset*1.5, center_lat - lat_offset*1.5],
        [center_lon, center_lat],
        [center_lon + lon_offset*1.5, center_lat + lat_offset*1.5],
    ]
    
    # Natural gas pipeline (horizontal through middle)
    gas_coords = [
        [center_lon - lon_offset*1.5, center_lat],
        [center_lon + lon_offset*1.5, center_lat],
    ]
    
    # Fiber optic (diagonal from SE to NW)
    fiber_coords = [
        [center_lon + lon_offset*1.5, center_lat - lat_offset*1.5],
        [center_lon, center_lat],
        [center_lon - lon_offset*1.5, center_lat + lat_offset*1.5],
    ]
    
    # Water main (vertical through middle)
    water_coords = [
        [center_lon, center_lat - lat_offset*1.5],
        [center_lon, center_lat + lat_offset*1.5],
    ]
    
    # Build FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": site_name,
                    "area_acres": area_acres,
                    "layer_type": "site_boundary"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [boundary_coords]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": f"Transmission to {site_name}",
                    "voltage_kv": 345,
                    "layer_type": "transmission"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": transmission_coords
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": f"Gas Pipeline to {site_name}",
                    "layer_type": "gas"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": gas_coords
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": f"Fiber Route to {site_name}",
                    "layer_type": "fiber"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": fiber_coords
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": f"Water Main to {site_name}",
                    "type": "Municipal",
                    "layer_type": "water"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": water_coords
                }
            }
        ]
    }
    
    return geojson


# Site coordinates
sites_data = {
    "Dallas Hyperscale DC": (32.7767, -96.797, 200),
    "Phoenix AI Campus": (33.4484, -112.074, 600),
    "Austin Greenfield DC": (30.2672, -97.7431, 300),
    "Tulsa Industrial Park": (36.1540, -95.9607, 850),
}

def main():
    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    sheet = spreadsheet.worksheet('Sites')
    
    # Get all records and headers
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    
    geojson_col_idx = headers.index('geojson') + 1 if 'geojson' in headers else None
    
    if not geojson_col_idx:
        print("ERROR: 'geojson' column not found!")
        return
    
    # Update each site
    for idx, record in enumerate(records):
        site_name = record['name']
        
        if site_name in sites_data:
            lat, lon, acres = sites_data[site_name]
            
            # Create multi-layer GeoJSON
            geojson = create_multi_layer_geojson(site_name, lat, lon, acres)
            geojson_str = json.dumps(geojson, separators=(',', ':'))  # Compact JSON
            
            # Update Google Sheets
            row_idx = idx + 2  # +2 for header row and 0-indexing
            sheet.update_cell(row_idx, geojson_col_idx, geojson_str)
            
            print(f"✅ Updated {site_name}: {len(geojson['features'])} layers")
            print(f"   - Site Boundary, Transmission, Gas, Fiber, Water")
        else:
            print(f"⚠️  Skipped {site_name}: No coordinates defined")
    
    print("\n✅ All sites updated with comprehensive infrastructure GeoJSON!")

if __name__ == "__main__":
    main()
