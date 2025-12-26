"""
Portfolio Maps Module
National portfolio map generation and site visualization
"""

import folium
from typing import List, Dict
from datetime import datetime, timedelta

def create_national_portfolio_map(sites_list: List[Dict], stage_filter: List[str], 
                                   min_capacity: int, max_lcoe: float) -> folium.Map:
    """
    Create interactive national map with all portfolio sites
    
    Args:
        sites_list: List of site dicts
        stage_filter: List of stages to include
        min_capacity: Minimum IT capacity filter
        max_lcoe: Maximum LCOE filter
    
    Returns:
        Folium map object
    """
    # Create map centered on US
    m = folium.Map(
        location=[39.8283, -98.5795],  # US geographic center
        zoom_start=4,
        tiles='CartoDB positron'
    )
    
    # Add markers for each site
    from app.utils.site_backend import load_site_stage_result
    from app.utils.financial_calculations import calculate_site_financials
    
    for site in sites_list:
        # Apply filters
        if site.get('it_capacity_mw', 0) < min_capacity:
            continue
        
        # Determine current stage
        latest_stage = determine_latest_stage(site.get('name', 'Unknown'))
        
        # Filter by stage
        if latest_stage not in [s.lower() for s in stage_filter]:
            continue
        
        # Get LCOE
        result = load_site_stage_result(site.get('name', 'Unknown'), latest_stage)
        lcoe = result.get('lcoe', 0) if result else 0
        
        if max_lcoe > 0 and lcoe > max_lcoe:  # Only filter if max_lcoe is set and lcoe exceeds it
            continue
        
        # Get coordinates
        coords_str = site.get('coordinates', '36.1512, -95.9607')
        if isinstance(coords_str, str):
            coords_parts = coords_str.split(',')
            lat = float(coords_parts[0].strip())
            lon = float(coords_parts[1].strip())
        else:
            lat, lon = coords_str
        
        # Determine marker color based on stage
        marker_color = get_marker_color(latest_stage)
        
        # Calculate financials for popup
        npv_m = 0
        capex_m = 0
        if result:
            financials = calculate_site_financials(site, result)
            npv_m = financials.get('npv_m', 0)
            capex_m = financials.get('capex_m', 0)
        
        # Create enhanced popup content with improved styling
        site_name = site.get('name', 'Unknown')
        location = site.get('location', '')
        it_cap = site.get('it_capacity_mw', 0)
        land = site.get('land_acres', 0)
        
        popup_html = f"""
        <div style="width: 280px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #1f4788; border-bottom: 2px solid #1f4788; padding-bottom: 5px;">
                {site_name}
            </h3>
            <table style="width: 100%; font-size: 13px;">
                <tr>
                    <td style="padding: 4px 0;"><b>📍 Location:</b></td>
                    <td style="text-align: right;">{location}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0;"><b>⚡ IT Capacity:</b></td>
                    <td style="text-align: right;">{it_cap} MW</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0;"><b>🏗️ Stage:</b></td>
                    <td style="text-align: right;">{latest_stage.capitalize()}</td>
                </tr>
                <tr style="border-top: 1px solid #ddd;">
                    <td style="padding: 4px 0;"><b>💰 LCOE:</b></td>
                    <td style="text-align: right; color: #10b981;"><b>${lcoe:.1f}/MWh</b></td>
                </tr>
                <tr>
                    <td style="padding: 4px 0;"><b>📊 NPV:</b></td>
                    <td style="text-align: right; color: #3b82f6;"><b>${npv_m:.1f}M</b></td>
                </tr>
                <tr>
                    <td style="padding: 4px 0;"><b>💵 CapEx:</b></td>
                    <td style="text-align: right;">${capex_m:.1f}M</td>
                </tr>
                <tr style="border-top: 1px solid #ddd;">
                    <td style="padding: 4px 0;"><b>🌾 Land:</b></td>
                    <td style="text-align: right;">{land} acres</td>
                </tr>
            </table>
        </div>
        """
        
        # Add marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=site_name,
            icon=folium.Icon(color=marker_color, icon='info-sign')
        ).add_to(m)
    
    return m


def determine_latest_stage(site_name: str) -> str:
    """Determine the latest completed stage for a site"""
    from app.utils.site_backend import load_site_stage_result
    
    for stage in ['detailed', 'preliminary', 'concept', 'screening']:
        result = load_site_stage_result(site_name, stage)
        if result and str(result.get('complete', '')).upper() == 'TRUE':
            return stage
    
    return 'screening'


def get_marker_color(stage: str) -> str:
    """Get marker color based on development stage"""
    stage_colors = {
        'detailed': 'green',
        'preliminary': 'lightgreen',
        'concept': 'orange',
        'screening': 'blue'
    }
    return stage_colors.get(stage.lower(), 'gray')


def calculate_power_on_date(stage_num: int) -> str:
    """
    Estimate power-on date based on current stage
    
    Args:
        stage_num: Current stage (0-4)
    
    Returns:
        Power-on date string (e.g., "Q2 2026")
    """
    # Typical timelines from each stage
    months_to_power_on = {
        0: 36,  # Not started: 3 years
        1: 30,  # Screening: 2.5 years
        2: 24,  # Concept: 2 years
        3: 18,  # Preliminary: 1.5 years
        4: 12   # Detailed: 1 year
    }
    
    months = months_to_power_on.get(stage_num, 36)
    
    power_on = datetime.now() + timedelta(days=months * 30)
    
    quarter = (power_on.month - 1) // 3 + 1
    return f"Q{quarter} {power_on.year}"


def determine_critical_path(stage_num: int, site: Dict) -> str:
    """
    Determine critical path item based on stage
    
    Args:
        stage_num: Current stage (0-4)
        site: Site dict
    
    Returns:
        Critical path description
    """
    critical_paths = {
        0: "Initial Screening",
        1: "Concept Development",
        2: "Permitting",
        3: "Interconnection",
        4: "Equipment Delivery"
    }
    
    return critical_paths.get(stage_num, "Not Started")
