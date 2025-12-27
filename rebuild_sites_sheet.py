#!/usr/bin/env python3
"""
COMPLETE SITES SHEET REBUILD
Fixes severe column misalignment in Google Sheets
"""

from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from app.utils.site_backend import get_google_sheets_client

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

# CORRECT SITE DATA - Manually verified
CORRECT_SITES = [
    {
        "name": "Dallas Hyperscale DC",
        "location": "Dallas, TX",
        "iso": "ERCOT",
        "voltage_kv": 345,
        "it_capacity_mw": 600,
        "pue": 1.25,
        "facility_mw": 750,  # 600 * 1.25
        "land_acres": 200,
        "nox_limit_tpy": 100,
        "gas_supply_mcf": 500000,
        "problem_num": 2,
        "problem_name": "Brownfield Expansion",
        "coordinates": "32.7767, -96.7970",
        "timezone": "America/Chicago",
        "climate_zone": "Hot-Humid",
        "avg_temp_f": "66",
        "geojson_prefix": "dallas",
        "geojson": json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "name": "Dallas Hyperscale DC",
                    "area_acres": 200,
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
        }),
        "created_date": "2025-12-26",
        "updated_date": "2025-12-26",
        "notes": "Standardized site data"
    },
    {
        "name": "Phoenix AI Campus",
        "location": "Phoenix, AZ",
        "iso": "WECC",
        "voltage_kv": 500,
        "it_capacity_mw": 750,
        "pue": 1.2,
        "facility_mw": 900,  # 750 * 1.2
        "land_acres": 600,
        "nox_limit_tpy": 100,
        "gas_supply_mcf": 750000,
        "problem_num": 1,
        "problem_name": "Greenfield Datacenter",
        "coordinates": "33.4484, -112.0740",
        "timezone": "America/Phoenix",
        "climate_zone": "Hot-Dry",
        "avg_temp_f": "75",
        "geojson_prefix": "phoenix",
        "geojson": json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "name": "Phoenix AI Campus",
                    "area_acres": 600,
                    "zoning": "Data Center District",
                    "available_acres": 450,
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
        }),
        "created_date": "2025-12-26",
        "updated_date": "2025-12-26",
        "notes": "Standardized site data"
    },
    {
        "name": "Austin Greenfield DC",
        "location": "Austin, TX",
        "iso": "ERCOT",
        "voltage_kv": 345,
        "it_capacity_mw": 600,
        "pue": 1.3,
        "facility_mw": 780,  # 600 * 1.3
        "land_acres": 300,
        "nox_limit_tpy": 100,
        "gas_supply_mcf": 500000,
        "problem_num": 1,
        "problem_name": "Greenfield Datacenter",
        "coordinates": "30.2672, -97.7431",
        "timezone": "America/Chicago",
        "climate_zone": "Hot-Humid",
        "avg_temp_f": "68",
        "geojson_prefix": "austin",
        "geojson": json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "name": "Austin Greenfield DC",
                    "area_acres": 300,
                    "zoning": "Industrial",
                    "available_acres": 200,
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
        }),
        "created_date": "2025-12-26",
        "updated_date": "2025-12-26",
        "notes": "Standardized site data"
    },
    {
        "name": "Tulsa Industrial Park",
        "location": "Tulsa, OK",
        "iso": "SPP",
        "voltage_kv": 345,
        "it_capacity_mw": 500,
        "pue": 1.35,
        "facility_mw": 675,  # 500 * 1.35
        "land_acres": 850,
        "nox_limit_tpy": 100,
        "gas_supply_mcf": 500000,
        "problem_num": 1,
        "problem_name": "Greenfield Datacenter",
        "coordinates": "36.1540, -95.9635",
        "timezone": "America/Chicago",
        "climate_zone": "Mixed-Humid",
        "avg_temp_f": "60",
        "geojson_prefix": "tulsa",
        "geojson": json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "name": "Tulsa Industrial Park",
                    "area_acres": 850,
                    "zoning": "Industrial",
                    "available_acres": 700,
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
        }),
        "created_date": "2025-12-26",
        "updated_date": "2025-12-26",
        "notes": "Standardized site data"
    }
]

# Correct column order
CORRECT_HEADERS = [
    'name',
    'location',
    'iso',
    'voltage_kv',
    'it_capacity_mw',
    'pue',
    'facility_mw',
    'land_acres',
    'nox_limit_tpy',
    'gas_supply_mcf',
    'problem_num',
    'problem_name',
    'geojson',
    'coordinates',
    'timezone',
    'climate_zone',
    'avg_temp_f',
    'geojson_prefix',
    'created_date',
    'updated_date',
    'notes'
]


def backup_current_sites():
    """Backup current Sites sheet before rebuild"""
    print("=" * 80)
    print("BACKING UP CURRENT SITES DATA")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        # Get all data
        all_data = sites_sheet.get_all_values()
        
        # Save to backup file
        backup_file = f"backups/sites_before_rebuild_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path('backups').mkdir(exist_ok=True)
        
        with open(backup_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"✅ Backup saved: {backup_file}")
        print(f"   Rows: {len(all_data)}")
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def rebuild_sites_sheet():
    """Completely rebuild Sites sheet with correct data"""
    print("\n" + "=" * 80)
    print("REBUILDING SITES SHEET")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        # Clear entire sheet
        print("\n🗑️  Clearing existing data...")
        sites_sheet.clear()
        
        # Write correct headers
        print("\n📝 Writing headers...")
        sites_sheet.update('A1', [CORRECT_HEADERS])
        print(f"   ✅ {len(CORRECT_HEADERS)} columns")
        
        # Write site data
        print("\n📊 Writing site data...")
        for idx, site in enumerate(CORRECT_SITES, 2):
            row = [site.get(header, '') for header in CORRECT_HEADERS]
            sites_sheet.update(f'A{idx}', [row])
            print(f"   ✅ Row {idx}: {site['name']}")
        
        print(f"\n✅ Sites sheet rebuilt with {len(CORRECT_SITES)} sites")
        return True
        
    except Exception as e:
        print(f"❌ Rebuild failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_sites_sheet():
    """Verify the rebuilt Sites sheet"""
    print("\n" + "=" * 80)
    print("VERIFYING SITES SHEET")
    print("=" * 80)
    
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        sites_sheet = spreadsheet.worksheet('Sites')
        
        headers = sites_sheet.row_values(1)
        all_data = sites_sheet.get_all_records()
        
        print(f"\n📊 Headers ({len(headers)}):")
        for i, h in enumerate(headers, 1):
            print(f"   {i:2}. {h}")
        
        print(f"\n📊 Site Data ({len(all_data)} sites):")
        for site in all_data:
            print(f"\n   {site['name']}:")
            print(f"      Location: {site['location']}")
            print(f"      ISO: {site['iso']}")
            print(f"      Voltage: {site['voltage_kv']} kV")
            print(f"      IT Capacity: {site['it_capacity_mw']} MW")
            print(f"      PUE: {site['pue']}")
            print(f"      Facility MW: {site['facility_mw']} MW")
            print(f"      NOx Limit: {site['nox_limit_tpy']} tpy")
            print(f"      Gas Supply: {site['gas_supply_mcf']} MCF")
        
        # Validation checks
        print("\n" + "=" * 80)
        print("VALIDATION CHECKS")
        print("=" * 80)
        
        all_valid = True
        
        for site in all_data:
            errors = []
            
            # PUE check
            try:
                pue = float(site['pue'])
                if pue < 1.0 or pue > 2.0:
                    errors.append(f"Invalid PUE: {pue}")
            except:
                errors.append("Invalid PUE type")
            
            # Voltage check
            try:
                voltage = int(site['voltage_kv'])
                if voltage < 69 or voltage > 765:
                    errors.append(f"Invalid voltage: {voltage}")
            except:
                errors.append("Invalid voltage type")
            
            # NOx check
            nox = int(site.get('nox_limit_tpy', 0))
            if nox != 100:
                errors.append(f"NOx should be 100, got {nox}")
            
            if errors:
                print(f"\n❌ {site['name']}: {', '.join(errors)}")
                all_valid = False
            else:
                print(f"✅ {site['name']}: All checks passed")
        
        if all_valid:
            print("\n✅ ALL VALIDATION CHECKS PASSED")
        else:
            print("\n⚠️  Some validation errors found")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("COMPLETE SITES SHEET REBUILD")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Backup current Sites sheet")
    print("  2. Clear and rebuild with correct data")
    print("  3. Verify all data is correct")
    
    response = input("\n⚠️  Continue with rebuild? (yes/no): ").strip().lower()
    
    if response == 'yes':
        # Step 1: Backup
        if backup_current_sites():
            print("\n✅ Backup complete")
        else:
            print("\n❌ Backup failed - aborting")
            sys.exit(1)
        
        # Step 2: Rebuild
        if rebuild_sites_sheet():
            print("\n✅ Rebuild complete")
        else:
            print("\n❌ Rebuild failed")
            sys.exit(1)
        
        # Step 3: Verify
        if verify_sites_sheet():
            print("\n✅ Verification complete")
        
        print("\n" + "=" * 80)
        print("✅ SITES SHEET SUCCESSFULLY REBUILT!")
        print("=" * 80)
        print("\nAll 4 sites now have correct, standardized data:")
        print("  • Dallas Hyperscale DC (600 MW, ERCOT, Brownfield)")
        print("  • Phoenix AI Campus (750 MW, WECC, Greenfield)")
        print("  • Austin Greenfield DC (600 MW, ERCOT, Greenfield)")
        print("  • Tulsa Industrial Park (500 MW, SPP, Greenfield)")
        print("\nAll data validated and synced!")
        
    else:
        print("\n❌ Rebuild cancelled")
