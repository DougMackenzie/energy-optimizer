#!/usr/bin/env python3
"""Replace map loading code to handle multi-layer GeoJSON from Google Sheets"""

with open('app/pages_custom/page_01_dashboard.py', 'r') as f:
    lines = f.readlines()

# Find the section to replace (from "# Layer 1: Site Boundary" to before except block)
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if '# Layer 1: Site Boundary - Try Google Sheets first' in line:
        start_idx = i
    if start_idx and 'except Exception as e:' in line and 'GeoJSON' in lines[i+1]:
        end_idx = i
        break

if start_idx and end_idx:
    # New unified code for multi-layer GeoJSON
    new_code = '''            # Load multi-layer GeoJSON from Google Sheets
            site_geojson_str = site.get('geojson', '')
            
            if site_geojson_str:
                try:
                    geojson_data = json.loads(site_geojson_str)
                    
                    # Process each feature/layer in the GeoJSON
                    if 'features' in geojson_data:
                        for feature in geojson_data['features']:
                            props = feature.get('properties', {})
                            layer_type = props.get('layer_type', 'unknown')
                            
                            # Determine layer name and style based on layer_type
                            if layer_type == 'site_boundary':
                                layer_name = 'Site Boundary'
                                style_fn = lambda x: {'fillColor': '#fbbf24', 'color': '#f59e0b', 'weight': 3, 'fillOpacity': 0.3}
                                tooltip_fields = ['name', 'area_acres']
                                tooltip_aliases = ['Site:', 'Area:']
                            elif layer_type == 'transmission':
                                layer_name = 'Transmission'
                                style_fn = lambda x: {'color': '#ef4444', 'weight': 4, 'opacity': 0.8}
                                tooltip_fields = ['name', 'voltage_kv']
                                tooltip_aliases = ['Facility:', 'Voltage:']
                            elif layer_type == 'gas':
                                layer_name = 'Natural Gas'
                                style_fn = lambda x: {'color': '#f97316', 'weight': 3, 'opacity': 0.7, 'dashArray': '10, 5'}
                                tooltip_fields = ['name']
                                tooltip_aliases = ['Pipeline:']
                            elif layer_type == 'fiber':
                                layer_name = 'Fiber'
                                style_fn = lambda x: {'color': '#a855f7', 'weight': 2, 'opacity': 0.7, 'dashArray': '5, 5'}
                                tooltip_fields = ['name']
                                tooltip_aliases = ['Route:']
                            elif layer_type == 'water':
                                layer_name = 'Water'
                                style_fn = lambda x: {'color': '#3b82f6', 'weight': 3, 'opacity': 0.6}
                                tooltip_fields = ['name', 'type']
                                tooltip_aliases = ['Feature:', 'Type:']
                            else:
                                continue  # Skip unknown layer types
                            
                            # Add feature to map
                            feature_collection = {
                                "type": "FeatureCollection",
                                "features": [feature]
                            }
                            
                            folium.GeoJson(
                                feature_collection,
                                name=layer_name,
                                style_function=style_fn,
                                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)
                            ).add_to(m)
                    
                except Exception as e:
                    print(f"Error parsing multi-layer GeoJSON from Google Sheets: {e}")
                    # Fall back to files if Google Sheets GeoJSON fails
                    file_suffix = f"_{geojson_prefix}" if geojson_prefix else ""
                    
                    # Try loading individual layer files
                    layers_to_load = [
                        ('site_boundary', 'Site Boundary', '#fbbf24', {'fillColor': '#fbbf24', 'color': '#f59e0b', 'weight': 3, 'fillOpacity': 0.3}),
                        ('transmission', 'Transmission', '#ef4444', {'color': '#ef4444', 'weight': 4, 'opacity': 0.8}),
                        ('gas_pipeline', 'Natural Gas', '#f97316', {'color': '#f97316', 'weight': 3, 'opacity': 0.7, 'dashArray': '10, 5'}),
                        ('fiber', 'Fiber', '#a855f7', {'color': '#a855f7', 'weight': 2, 'opacity': 0.7, 'dashArray': '5, 5'}),
                        ('water', 'Water', '#3b82f6', {'color': '#3b82f6', 'weight': 3, 'opacity': 0.6'})
                    ]
                    
                    for file_base, layer_name, color, style in layers_to_load:
                        layer_path = SAMPLE_DATA_DIR / f"{file_base}{file_suffix}.geojson"
                        if layer_path.exists():
                            with open(layer_path) as f:
                                layer_data = json.load(f)
                            folium.GeoJson(
                                layer_data,
                                name=layer_name,
                                style_function=lambda x, s=style: s
                            ).add_to(m)
            
'''
    
    # Replace the section
    lines[start_idx:end_idx] = [new_code]
    
    with open('app/pages_custom/page_01_dashboard.py', 'w') as f:
        f.writelines(lines)
    
    print("✅ Replaced map loading code")
    print("   - Now processes multi-layer GeoJSON from Google Sheets")
    print("   - Falls back to individual files if needed")
else:
    print("❌ Could not find section to replace")
