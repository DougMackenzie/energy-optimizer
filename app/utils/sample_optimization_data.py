"""
Sample Data Generator for Demo Site
Creates a complete Greenfield optimization result set for all 4 EPC stages
"""

from datetime import datetime
import json


def get_sample_site():
    """Sample site: Austin Greenfield Datacenter"""
    return {
        'name': 'Austin Greenfield DC',
        'location': 'Austin, TX',
        'iso': 'ERCOT',
        'it_capacity_mw': 500,
        'pue': 1.22,
        'facility_mw': 610,
        'land_acres': 380,
        'nox_limit_tpy': 95,
        'gas_supply_mcf': 125000,
        'voltage_kv': 345,
        'coordinates': [30.267, -97.743],
        'geojson_prefix': 'austin',
        'problem_num': 1,
        'problem_name': 'Greenfield Datacenter'
    }


def get_sample_optimization_results():
    """
    Sample optimization results for all 4 EPC stages
    Returns dict with results for: screening, concept, preliminary, detailed
    """
    
    base_timestamp = datetime.now().isoformat()
    
    results = {
        'screening': {
            'site_name': 'Austin Greenfield DC',
            'problem_type': 'P1',
            'stage': 'screening',
            'version': 1,
            'solver': 'heuristic',
            'run_timestamp': base_timestamp,
            'runtime_seconds': 45,
            
            # Key metrics
            'lcoe': 82.5,
            'npv': -128000000,
            'irr': 0.067,
            'payback_years': 12.5,
            
            # Equipment (MW/MWh)
            'equipment': {
                'recip_mw': 220,
                'turbine_mw': 50,
                'bess_mwh': 400,
                'solar_mw': 120,
                'grid_mw': 150
            },
            
            # Capital costs ($M)
            'capex': {
                'recip': 308,  # 220 MW * $1,400/kW
                'turbine': 47.5,  # 50 MW * $950/kW
                'bess': 140,  # 400 MWh * $350/kWh
                'solar': 132,  # 120 MW * $1,100/kW
                'grid': 33,  # 150 MW * $220/kW
                'total': 660.5
            },
            
            # Operating costs ($M/yr)
            'opex_annual': {
                'fuel': 28.5,
                'om_recip': 9.9,
                'om_turbine': 1.4,
                'om_bess': 3.2,
                'om_solar': 1.8,
                'grid_electricity': 2.1,
                'total': 46.9
            },
            
            # Constraint utilization
            'constraints': {
                'nox_used_tpy': 78.2,
                'nox_limit_tpy': 95,
                'nox_utilization': 0.823,
                'gas_used_mcf': 98500,
                'gas_limit_mcf': 125000,
                'gas_utilization': 0.788,
                'land_used_acres': 298,
                'land_limit_acres': 380,
                'land_utilization': 0.784
            },
            
            # Coverage
            'load_coverage_pct': 75.2,
            'avg_load_mw': 488,
            'peak_load_mw': 610,
            
            'user_notes': 'Initial screening study - heuristic optimization for fast feasibility check'
        },
        
        'concept': {
            'site_name': 'Austin Greenfield DC',
            'problem_type': 'P1',
            'stage': 'concept',
            'version': 1,
            'solver': 'milp',
            'run_timestamp': base_timestamp,
            'runtime_seconds': 420,
            
            # Key metrics (improved from screening)
            'lcoe': 76.8,
            'npv': -115000000,
            'irr': 0.082,
            'payback_years': 10.8,
            
            # Equipment (optimized)
            'equipment': {
                'recip_mw': 200,
                'turbine_mw': 80,
                'bess_mwh': 450,
                'solar_mw': 150,
                'grid_mw': 150
            },
            
            # Capital costs
            'capex': {
                'recip': 280,
                'turbine': 76,
                'bess': 157.5,
                'solar': 165,
                'grid': 33,
                'total': 711.5
            },
            
            # Operating costs
            'opex_annual': {
                'fuel': 25.8,
                'om_recip': 9.0,
                'om_turbine': 2.24,
                'om_bess': 3.6,
                'om_solar': 2.25,
                'grid_electricity': 1.8,
                'total': 44.69
            },
            
            # Constraints
            'constraints': {
                'nox_used_tpy': 72.5,
                'nox_limit_tpy': 95,
                'nox_utilization': 0.763,
                'gas_used_mcf': 89200,
                'gas_limit_mcf': 125000,
                'gas_utilization': 0.714,
                'land_used_acres': 315,
                'land_limit_acres': 380,
                'land_utilization': 0.829
            },
            
            # Coverage
            'load_coverage_pct': 82.5,
            'avg_load_mw': 488,
            'peak_load_mw': 610,
            
            'user_notes': 'Concept development - first detailed MILP optimization with refined equipment sizing'
        },
        
        'preliminary': {
            'site_name': 'Austin Greenfield DC',
            'problem_type': 'P1',
            'stage': 'preliminary',
            'version': 1,
            'solver': 'milp',
            'run_timestamp': base_timestamp,
            'runtime_seconds': 680,
            
            # Key metrics (vendor quotes incorporated)
            'lcoe': 74.2,
            'npv': -108000000,
            'irr': 0.091,
            'payback_years': 9.8,
            
            # Equipment (vendor-optimized)
            'equipment': {
                'recip_mw': 190,
                'turbine_mw': 90,
                'bess_mwh': 480,
                'solar_mw': 165,
                'grid_mw': 150
            },
            
            # Capital costs (actual quotes)
            'capex': {
                'recip': 256.5,  # Better pricing from vendor
                'turbine': 85.5,
                'bess': 153.6,  # Lithium pricing drop
                'solar': 173.25,
                'grid': 33,
                'total': 701.85
            },
            
            # Operating costs
            'opex_annual': {
                'fuel': 24.2,
                'om_recip': 8.55,
                'om_turbine': 2.52,
                'om_bess': 3.84,
                'om_solar': 2.475,
                'grid_electricity': 1.65,
                'total': 43.235
            },
            
            # Constraints
            'constraints': {
                'nox_used_tpy': 68.8,
                'nox_limit_tpy': 95,
                'nox_utilization': 0.724,
                'gas_used_mcf': 82400,
                'gas_limit_mcf': 125000,
                'gas_utilization': 0.659,
                'land_used_acres': 328,
                'land_limit_acres': 380,
                'land_utilization': 0.863
            },
            
            # Coverage
            'load_coverage_pct': 87.3,
            'avg_load_mw': 488,
            'peak_load_mw': 610,
            
            'user_notes': 'Preliminary design - vendor quotes incorporated, procurement strategy defined'
        },
        
        'detailed': {
            'site_name': 'Austin Greenfield DC',
            'problem_type': 'P1',
            'stage': 'detailed',
            'version': 1,
            'solver': 'milp',
            'run_timestamp': base_timestamp,
            'runtime_seconds': 1240,
            
            # Key metrics (final as-built)
            'lcoe': 72.8,
            'npv': -102000000,
            'irr': 0.098,
            'payback_years': 9.2,
            
            # Equipment (final design)
            'equipment': {
                'recip_mw': 185,
                'turbine_mw': 95,
                'bess_mwh': 500,
                'solar_mw': 175,
                'grid_mw': 150
            },
            
            # Capital costs (final contracts)
            'capex': {
                'recip': 250.75,
                'turbine': 90.25,
                'bess': 160,
                'solar': 183.75,
                'grid': 33,
                'total': 717.75
            },
            
            # Operating costs
            'opex_annual': {
                'fuel': 23.5,
                'om_recip': 8.325,
                'om_turbine': 2.66,
                'om_bess': 4.0,
                'om_solar': 2.625,
                'grid_electricity': 1.5,
                'total': 42.61
            },
            
            # Constraints
            'constraints': {
                'nox_used_tpy': 66.2,
                'nox_limit_tpy': 95,
                'nox_utilization': 0.697,
                'gas_used_mcf': 78800,
                'gas_limit_mcf': 125000,
                'gas_utilization': 0.630,
                'land_used_acres': 338,
                'land_limit_acres': 380,
                'land_utilization': 0.889
            },
            
            # Coverage
            'load_coverage_pct': 91.5,
            'avg_load_mw': 488,
            'peak_load_mw': 610,
            
            'user_notes': 'Detailed design - final as-built parameters, construction schedule optimized'
        }
    }
    
    return results


def save_sample_data_to_sheets():
    """Save sample site and optimization results to Google Sheets"""
    try:
        from app.utils.site_backend import save_site, save_site_stage_result
        
        # Save sample site
        sample_site = get_sample_site()
        save_site(sample_site)
        print(f"✓ Saved sample site: {sample_site['name']}")
        
        # Save all 4 stage results
        results = get_sample_optimization_results()
        for stage_name, stage_data in results.items():
            save_site_stage_result(
                site_name=sample_site['name'],
                stage=stage_name,
                result_data=stage_data
            )
            print(f"✓ Saved {stage_name} results")
        
        return True
    except Exception as e:
        print(f"Error saving sample data: {e}")
        return False


if __name__ == "__main__":
    # Test data generation
    site = get_sample_site()
    results = get_sample_optimization_results()
    
    print("Sample Site:")
    print(json.dumps(site, indent=2))
    
    print("\nSample Results (Screening):")
    print(json.dumps(results['screening'], indent=2))
