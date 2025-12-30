import json
import os

SITES = {
    'austin': {'lat': 30.267, 'lon': -97.743, 'name': 'Austin Greenfield DC'},
    'chicago': {'lat': 41.878, 'lon': -87.629, 'name': 'Chicago Grid Hub'},
    'ashburn': {'lat': 39.043, 'lon': -77.487, 'name': 'Northern Virginia Bridge'},
}

OUTPUT_DIR = 'sample_data'

def create_polygon(lat, lon, size_deg=0.01):
    return [
        [lon - size_deg, lat + size_deg],
        [lon + size_deg, lat + size_deg],
        [lon + size_deg, lat - size_deg],
        [lon - size_deg, lat - size_deg],
        [lon - size_deg, lat + size_deg]
    ]

def create_line(lat, lon, offset_lat, offset_lon):
    return [
        [lon - 0.02, lat + offset_lat],
        [lon + 0.02, lat + offset_lat + offset_lon]
    ]

def generate_geojson(site_key, site_data):
    lat = site_data['lat']
    lon = site_data['lon']
    name = site_data['name']
    
    # 1. Site Boundary
    boundary = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": name, "type": "Boundary", "area_acres": 500},
            "geometry": {"type": "Polygon", "coordinates": [create_polygon(lat, lon)]}
        }]
    }
    with open(f"{OUTPUT_DIR}/site_boundary_{site_key}.geojson", 'w') as f:
        json.dump(boundary, f, indent=4)

    # 2. Transmission
    transmission = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "HV Line", "voltage_kv": 345, "type": "Transmission"},
            "geometry": {"type": "LineString", "coordinates": create_line(lat, lon, 0.015, 0)}
        }]
    }
    with open(f"{OUTPUT_DIR}/transmission_{site_key}.geojson", 'w') as f:
        json.dump(transmission, f, indent=4)

    # 3. Gas Pipeline
    gas = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Gas Main", "pressure_psi": 800, "type": "Gas"},
            "geometry": {"type": "LineString", "coordinates": create_line(lat, lon, -0.015, 0.01)}
        }]
    }
    with open(f"{OUTPUT_DIR}/gas_pipeline_{site_key}.geojson", 'w') as f:
        json.dump(gas, f, indent=4)

    # 4. Water
    water = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Water Main", "diameter_in": 24, "type": "Water"},
            "geometry": {"type": "LineString", "coordinates": create_line(lat, lon, -0.01, -0.01)}
        }]
    }
    with open(f"{OUTPUT_DIR}/water_{site_key}.geojson", 'w') as f:
        json.dump(water, f, indent=4)

    # 5. Fiber
    fiber = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Fiber Trunk", "provider": "Dark Fiber Co", "type": "Fiber"},
            "geometry": {"type": "LineString", "coordinates": create_line(lat, lon, 0.005, 0.02)}
        }]
    }
    with open(f"{OUTPUT_DIR}/fiber_{site_key}.geojson", 'w') as f:
        json.dump(fiber, f, indent=4)

    print(f"Generated 5 GeoJSON files for {name} ({site_key})")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for key, data in SITES.items():
        generate_geojson(key, data)
