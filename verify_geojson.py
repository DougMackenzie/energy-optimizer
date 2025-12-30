#!/usr/bin/env python3
"""
Verify GeoJSON is in Google Sheets
"""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.site_backend import load_all_sites

if __name__ == "__main__":
    print("=" * 60)
    print("VERIFYING GEOJSON IN GOOGLE SHEETS")
    print("=" * 60)
    
    sites = load_all_sites(use_cache=False)
    
    for site in sites:
        site_name = site.get('name')
        geojson_str = site.get('geojson', '')
        
        print(f"\n📍 {site_name}")
        
        if geojson_str:
            try:
                geojson_data = json.loads(geojson_str)
                feature_count = len(geojson_data.get('features', []))
                print(f"   ✅ Has GeoJSON: {feature_count} features")
                
                # Show feature types
                layers = set()
                for feature in geojson_data.get('features', []):
                    layer = feature.get('properties', {}).get('layer', 'unknown')
                    layers.add(layer)
                print(f"   📊 Layers: {', '.join(sorted(layers))}")
            except:
                print(f"   ⚠️  Has data but invalid JSON")
        else:
            print(f"   ❌ No GeoJSON data")
