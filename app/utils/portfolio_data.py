"""
Portfolio Data Aggregation Functions
Helper functions to fetch and aggregate data from Google Sheets for reporting
"""

from typing import Dict, List, Optional
from app.utils.site_backend import (
    load_all_sites, 
    load_site_stage_result,
    load_site_geojson,
    get_google_sheets_client,
    SHEET_ID
)
import json


def load_all_site_results() -> List[Dict]:
    """
    Load all sites with their latest optimization results
    
    Returns:
        List of site dictionaries with results attached
    """
    sites = load_all_sites()
    site_results = []
    
    for site in sites:
        site_name = site.get('name') or site.get('site_name')
        if not site_name:
            continue
        
        # Find latest complete stage
        latest_result = None
        for stage in ['detailed', 'preliminary', 'concept', 'screening']:
            result = load_site_stage_result(site_name, stage)
            if result and result.get('complete'):
                latest_result = result
                latest_result['stage'] = stage
                break
        
        if latest_result:
            site_results.append({
                'site_name': site_name,
                'location': site.get('location', 'Unknown'),
                'it_capacity_mw': site.get('it_capacity_mw', 0),
                'facility_mw': site.get('facility_mw', 0),
                'land_acres': site.get('land_acres', 0),
                'coordinates': site.get('coordinates'),
                'geojson': site.get('geojson'),
                'stage': latest_result.get('stage'),
                'lcoe': latest_result.get('lcoe', 0),
                'npv': latest_result.get('npv', 0),
                'equipment': latest_result.get('equipment', {}),
                'dispatch_summary': latest_result.get('dispatch_summary', {}),
                'capex': latest_result.get('capex', {}),
                'constraints': latest_result.get('constraints', {}),
                'complete': latest_result.get('complete', False),
                'completion_date': latest_result.get('completion_date'),
                'load_coverage_pct': latest_result.get('load_coverage_pct', 0)
            })
    
    return site_results


def get_portfolio_summary(site_results: List[Dict] = None) -> Dict:
    """
    Calculate portfolio-wide aggregate metrics
    
    Args:
        site_results: Optional list of site results (if None, will fetch)
    
    Returns:
        Dictionary with portfolio metrics
    """
    if site_results is None:
        site_results = load_all_site_results()
    
    if not site_results:
        return {
            'num_sites': 0,
            'total_capacity_mw': 0,
            'weighted_lcoe': 0,
            'total_npv_m': 0,
            'total_capex_m': 0,
            'portfolio_irr': 0
        }
    
    # Calculate metrics
    num_sites = len(site_results)
    total_capacity = sum(s.get('it_capacity_mw', 0) for s in site_results)
    
    # Weighted average LCOE (weighted by capacity)
    total_weighted_lcoe = 0
    total_weight = 0
    for site in site_results:
        capacity = site.get('it_capacity_mw', 0)
        lcoe = site.get('lcoe', 0)
        if capacity > 0 and lcoe > 0:
            total_weighted_lcoe += lcoe * capacity
            total_weight += capacity
    
    weighted_lcoe = total_weighted_lcoe / total_weight if total_weight > 0 else 0
    
    # Total NPV (convert to millions)
    total_npv_m = sum(s.get('npv', 0) / 1_000_000 for s in site_results)
    
    # Total CapEx estimate (from equipment data)
    total_capex_m = 0
    for site in site_results:
        equipment = site.get('equipment', {})
        # Estimate CapEx from equipment if not directly provided
        capex = 0
        if isinstance(equipment, dict):
            capex += equipment.get('recip_mw', 0) * 1.8
            capex += equipment.get('turbine_mw', 0) * 1.2
            capex += equipment.get('bess_mwh', 0) * 0.35
            capex += equipment.get('solar_mw', 0) * 1.0
            capex += equipment.get('grid_mw', 0) * 0.5
        total_capex_m += capex
    
    # Estimate portfolio IRR (simplified)
    if total_capex_m > 0:
        annual_cash_flow = total_npv_m * 0.1  # Rough estimate
        portfolio_irr = (annual_cash_flow / total_capex_m) * 100
    else:
        portfolio_irr = 0
    
    return {
        'num_sites': num_sites,
        'total_capacity_mw': total_capacity,
        'weighted_lcoe': weighted_lcoe,
        'total_npv_m': total_npv_m,
        'total_capex_m': total_capex_m,
        'portfolio_irr': portfolio_irr,
        'avg_load_coverage': sum(s.get('load_coverage_pct', 0) for s in site_results) / num_sites if num_sites > 0 else 0
    }


def get_site_optimization_history(site_name: str) -> List[Dict]:
    """
    Get all optimization stages for a site (screening → detailed progression)
    
    Args:
        site_name: Name of the site
    
    Returns:
        List of stage results in chronological order
    """
    history = []
    
    for stage in ['screening', 'concept', 'preliminary', 'detailed']:
        result = load_site_stage_result(site_name, stage)
        if result and result.get('complete'):
            history.append({
                'stage': stage,
                'lcoe': result.get('lcoe', 0),
                'npv': result.get('npv', 0),
                'equipment': result.get('equipment', {}),
                'completion_date': result.get('completion_date'),
                'load_coverage_pct': result.get('load_coverage_pct', 0)
            })
    
    return history


def fetch_site_results_from_sheets(site_name: str) -> Optional[Dict]:
    """
    Direct fetch of all optimization data for a specific site from Google Sheets
    
    Args:
        site_name: Name of site
    
    Returns:
        Combined dictionary with site info and latest optimization result
    """
    try:
        # Get site info
        sites = load_all_sites()
        site_info = next((s for s in sites if s.get('name') == site_name or s.get('site_name') == site_name), None)
        
        if not site_info:
            return None
        
        # Get latest optimization result
        for stage in ['detailed', 'preliminary', 'concept', 'screening']:
            result = load_site_stage_result(site_name, stage)
            if result and result.get('complete'):
                # Combine site info with results
                combined = {**site_info, **result}
                combined['stage'] = stage
                
                # Load GeoJSON if available
                geojson = load_site_geojson(site_name)
                if geojson:
                    combined['geojson_data'] = geojson
                
                return combined
        
        # No complete results
        return site_info
        
    except Exception as e:
        print(f"Error fetching site results: {e}")
        return None


def get_equipment_summary(equipment_data: Dict) -> Dict:
    """
    Parse and summarize equipment configuration
    
    Args:
        equipment_data: Equipment dictionary (possibly from JSON)
    
    Returns:
        Standardized equipment summary
    """
    if not equipment_data:
        return {
            'recip_mw': 0,
            'turbine_mw': 0,
            'bess_mwh': 0,
            'solar_mw': 0,
            'grid_mw': 0,
            'total_btm_mw': 0
        }
    
    # Handle different equipment data formats
    recip_mw = equipment_data.get('recip_mw', 0)
    turbine_mw = equipment_data.get('turbine_mw', 0)
    bess_mwh = equipment_data.get('bess_mwh', 0)
    solar_mw = equipment_data.get('solar_mw', 0)
    grid_mw = equipment_data.get('grid_mw', 0)
    
    total_btm_mw = recip_mw + turbine_mw + solar_mw
    
    return {
        'recip_mw': recip_mw,
        'turbine_mw': turbine_mw,
        'bess_mwh': bess_mwh,
        'solar_mw': solar_mw,
        'grid_mw': grid_mw,
        'total_btm_mw': total_btm_mw,
        'has_generation': total_btm_mw > 0,
        'has_storage': bess_mwh > 0,
        'has_renewables': solar_mw > 0
    }


if __name__ == "__main__":
    # Test portfolio data aggregation
    print("Testing portfolio data aggregation...")
    
    try:
        results = load_all_site_results()
        print(f"\n✓ Loaded {len(results)} sites with optimization results")
        
        for r in results[:3]:  # Show first 3
            print(f"  - {r['site_name']}: LCOE ${r['lcoe']:.1f}/MWh, NPV ${r['npv']/1e6:.1f}M")
        
        portfolio = get_portfolio_summary(results)
        print(f"\n✓ Portfolio Summary:")
        print(f"  - Total Sites: {portfolio['num_sites']}")
        print(f"  - Total Capacity: {portfolio['total_capacity_mw']:.0f} MW")
        print(f"  - Weighted LCOE: ${portfolio['weighted_lcoe']:.1f}/MWh")
        print(f"  - Total NPV: ${portfolio['total_npv_m']:.1f}M")
        print(f"  - Total CapEx: ${portfolio['total_capex_m']:.1f}M")
        
    except Exception as e:
        print(f"✗ Error: {e}")
