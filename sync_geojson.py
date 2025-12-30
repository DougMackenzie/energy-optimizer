#!/usr/bin/env python3
"""
Load GeoJSON files and sync them to Google Sheets
"""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import update_site, load_all_sites

GEOJSON_DIR = PROJECT_ROOT / 'sample_data'

def load_site_geojson_from_files(geojson_prefix):
    """Load all GeoJSON files for a site and combine them"""
    geojson_types = ['site_boundary', 'transmission', 'gas_pipeline', 'water', 'fiber']
    
    features = []
    for gtype in geojson_types:
        filepath = GEOJSON_DIR / f"{gtype}_{geojson_prefix}.geojson"
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
                if 'features' in data:
                    # Add type to each feature
                    for feature in data['features']:
                        feature['properties']['layer'] = gtype
                        features.append(feature)
    
    if features:
        return {
            "type": "FeatureCollection",
            "features": features
        }
    return None

if __name__ == "__main__":
    print("=" * 60)
    print("SYNCING GEOJSON FILES TO GOOGLE SHEETS")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    synced = 0
    for site in sites:
        site_name = site.get('name')
        geojson_prefix = site.get('geojson_prefix')
        
        if geojson_prefix:
            print(f"\n📍 {site_name}")
            print(f"   Prefix: {geojson_prefix}")
            
            # Load GeoJSON from files
            geojson_data = load_site_geojson_from_files(geojson_prefix)
            
            if geojson_data:
                # Update site with GeoJSON
                geojson_str = json.dumps(geojson_data)
                success = update_site(site_name, {'geojson': geojson_str})
                
                if success:
                    feature_count = len(geojson_data['features'])
                    print(f"   ✅ Synced {feature_count} GeoJSON features")
                    synced += 1
                else:
                    print(f"   ❌ Failed to sync")
            else:
                print(f"   ⚠️  No GeoJSON files found")
        else:
            print(f"\n⏭️  {site_name}: No geojson_prefix")
    
    print(f"\n{'=' * 60}")
    print(f"✅ Synced GeoJSON for {synced}/{len(sites)} sites")
