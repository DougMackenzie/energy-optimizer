"""
Additional Chart Generation Functions for Enhanced Reports
Includes LCOE analysis, CapEx breakdown, 15-year energy stack, and map visualization
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import io
from PIL import Image, ImageDraw
import folium
from folium import plugins


def create_lcoe_comparison_chart(sites_data: List[Dict], save_path: str = None) -> str:
    """
    Create LCOE comparison chart across sites with threshold line
    
    Args:
        sites_data: List of site dictionaries with lcoe values
        save_path: Path to save chart
    
    Returns:
        Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Extract data
    site_names = [s.get('site_name', 'Unknown')[:20] for s in sites_data]
    lcoe_values = [s.get('lcoe', 0) for s in sites_data]
    
    # Color code: green if < 80, yellow if 80-90, red if > 90
    colors = []
    for lcoe in lcoe_values:
        if lcoe < 80:
            colors.append('#2ECC71')  # Green
        elif lcoe < 90:
            colors.append('#F39C12')  # Yellow
        else:
            colors.append('#E74C3C')  # Red
    
    # Create bar chart
    bars = ax.bar(range(len(site_names)), lcoe_values, color=colors, alpha=0.8, edgecolor='black')
    
    # Add threshold lines
    ax.axhline(80, color='green', linestyle='--', linewidth=2, label='Target LCOE ($80/MWh)', alpha=0.7)
    ax.axhline(90, color='orange', linestyle='--', linewidth=2, label='Upper Threshold ($90/MWh)', alpha=0.7)
    
    # Value labels on bars
    for i, (bar, val) in enumerate(zip(bars, lcoe_values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${val:.1f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_ylabel('LCOE ($/MWh)', fontsize=12, fontweight='bold')
    ax.set_title('LCOE Comparison by Site', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(site_names)))
    ax.set_xticklabels(site_names, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)
    
    if save_path is None:
        save_path = f'/tmp/lcoe_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_capex_breakdown_chart(equipment_data: Dict, save_path: str = None) -> str:
    """
    Create CapEx breakdown by equipment type (pie chart)
    
    Args:
        equipment_data: Dict with equipment capacities and costs
        save_path: Path to save chart
    
    Returns:
        Path to saved chart
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Equipment capacities and costs (from equipment_data)
    categories = []
    capex_values = []
    colors = []
    
    # Recip engines
    if equipment_data.get('recip_mw', 0) > 0:
        recip_capex = equipment_data.get('recip_mw', 0) * 1.8  # $1.8M/MW typical
        categories.append(f"Recip Engines\n{equipment_data.get('recip_mw', 0):.0f} MW")
        capex_values.append(recip_capex)
        colors.append('#4169E1')
    
    # Gas turbines
    if equipment_data.get('turbine_mw', 0) > 0:
        turbine_capex = equipment_data.get('turbine_mw', 0) * 1.2  # $1.2M/MW
        categories.append(f"Gas Turbines\n{equipment_data.get('turbine_mw', 0):.0f} MW")
        capex_values.append(turbine_capex)
        colors.append('#DC143C')
    
    # BESS
    if equipment_data.get('bess_mwh', 0) > 0:
        bess_capex = equipment_data.get('bess_mwh', 0) * 0.35  # $350k/MWh
        categories.append(f"BESS\n{equipment_data.get('bess_mwh', 0):.0f} MWh")
        capex_values.append(bess_capex)
        colors.append('#FF8C00')
    
    # Solar
    if equipment_data.get('solar_mw', 0) > 0:
        solar_capex = equipment_data.get('solar_mw', 0) * 1.0  # $1M/MW
        categories.append(f"Solar PV\n{equipment_data.get('solar_mw', 0):.0f} MW")
        capex_values.append(solar_capex)
        colors.append('#FFD700')
    
    # Grid interconnection (if applicable)
    if equipment_data.get('grid_mw', 0) > 0:
        grid_capex = equipment_data.get('grid_mw', 0) * 0.5  # $0.5M/MW for interconnect
        categories.append(f"Grid Interconnect\n{equipment_data.get('grid_mw', 0):.0f} MW")
        capex_values.append(grid_capex)
        colors.append('#808080')
    
    # Pie chart
    wedges, texts, autotexts = ax1.pie(capex_values, labels=categories, autopct='%1.1f%%',
                                         colors=colors, startangle=90, textprops={'fontsize': 10})
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    ax1.set_title('CapEx Breakdown by Equipment Type', fontsize=13, fontweight='bold')
    
    # Bar chart with $ values
    y_pos = np.arange(len(categories))
    ax2.barh(y_pos, capex_values, color=colors, alpha=0.8, edgecolor='black')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(categories, fontsize=10)
    ax2.set_xlabel('CapEx ($M)', fontsize=11, fontweight='bold')
    ax2.set_title('CapEx by Equipment ($M)', fontsize=13, fontweight='bold')
    ax2.grid(True, axis='x', alpha=0.3)
    
    # Value labels
    for i, v in enumerate(capex_values):
        ax2.text(v + 1, i, f'${v:.1f}M', va='center', fontsize=10, fontweight='bold')
    
    if save_path is None:
        save_path = f'/tmp/capex_breakdown_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_15year_energy_stack_chart(equipment_data: Dict, load_data: Dict, save_path: str = None) -> str:
    """
    Create 15-year energy generation stack showing annual generation by source
    
    Args:
        equipment_data: Equipment configuration
        load_data: Load profile data
        save_path: Path to save chart
    
    Returns:
        Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(14, 7))
    
    years = np.arange(1, 16)  # Years 1-15
    
    # Calculate annual generation by source (GWh/year)
    # Assume constant capacity factors for simplicity
    
    grid_annual = equipment_data.get('grid_mw', 0) * 8760 * 0.6 / 1000  # 60% CF
    solar_annual = equipment_data.get('solar_mw', 0) * 8760 * 0.22 / 1000  # 22% CF
    recip_annual = equipment_data.get('recip_mw', 0) * 8760 * 0.7 / 1000  # 70% CF
    turbine_annual = equipment_data.get('turbine_mw', 0) * 8760 * 0.3 / 1000  # 30% CF (peaking)
    bess_annual = equipment_data.get('bess_mwh', 0) * 365 * 0.9 / 1000  # Daily cycling
    
    # Create arrays for each year
    grid_gen = np.full(15, grid_annual)
    solar_gen = np.full(15, solar_annual)
    # Degradation: solar degrades 0.5%/year
    for year in range(15):
        solar_gen[year] *= (1 - 0.005 * year)
    
    recip_gen = np.full(15, recip_annual)
    turbine_gen = np.full(15, turbine_annual)
    bess_gen = np.full(15, bess_annual)
    # BESS degrades 2%/year
    for year in range(15):
        bess_gen[year] *= (1 - 0.02 * year)
    
    # Stacked area chart
    ax.fill_between(years, 0, grid_gen, label='Grid Import', alpha=0.8, color='#808080')
    ax.fill_between(years, grid_gen, grid_gen + solar_gen, 
                     label='Solar PV', alpha=0.8, color='#FFD700')
    ax.fill_between(years, grid_gen + solar_gen, 
                     grid_gen + solar_gen + recip_gen,
                     label='Recip Engines', alpha=0.8, color='#4169E1')
    ax.fill_between(years, grid_gen + solar_gen + recip_gen,
                     grid_gen + solar_gen + recip_gen + turbine_gen,
                     label='Gas Turbines', alpha=0.8, color='#DC143C')
    ax.fill_between(years, grid_gen + solar_gen + recip_gen + turbine_gen,
                     grid_gen + solar_gen + recip_gen + turbine_gen + bess_gen,
                     label='BESS Discharge', alpha=0.8, color='#FF8C00')
    
    # Total load line
    annual_load = load_data.get('total_annual_gwh', 
                                 equipment_data.get('facility_mw', 200) * 8760 * 0.7 / 1000)
    ax.plot(years, np.full(15, annual_load), 'k--', linewidth=2, label='Total Load')
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Annual Generation (GWh)', fontsize=12, fontweight='bold')
    ax.set_title('15-Year Energy Generation Stack', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, 15)
    ax.set_xticks(years)
    
    if save_path is None:
        save_path = f'/tmp/energy_stack_15yr_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_flexibility_impact_chart(dr_data: Dict, save_path: str = None) -> str:
    """
    Create chart showing relationship between load flexibility and brownfield capacity expansion
    
    Args:
        dr_data: Demand response/flexibility data
        save_path: Path to save chart
    
    Returns:
        Path to saved chart
    """
    fig, (ax1,ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Scenario analysis: flexibility vs additional load capacity
    flexibility_pct = np.array([0, 5, 10, 15, 20, 25, 30])  # %
    additional_load_mw = flexibility_pct * 4  # Rough estimate: 1% flex = 4 MW additional
    capex_savings_m = additional_load_mw * 1.5  # Savings vs building new generation
    
    # Chart 1: Flexibility vs Additional Load Capacity
    ax1.plot(flexibility_pct, additional_load_mw, marker='o', linewidth=2.5, 
             markersize=8, color='#2ECC71', label='Additional Load Capacity')
    ax1.fill_between(flexibility_pct, 0, additional_load_mw, alpha=0.3, color='#2ECC71')
    ax1.set_xlabel('Load Flexibility (%)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Additional Brownfield Capacity (MW)', fontsize=12, fontweight='bold')
    ax1.set_title('Flexibility Impact on Brownfield Expansion', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # Chart 2: CapEx Savings from Flexibility
    ax2.bar(flexibility_pct, capex_savings_m, width=3.5, color='#3498DB', alpha=0.8, edgecolor='black')
    ax2.set_xlabel('Load Flexibility (%)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('CapEx Savings ($M)', fontsize=12, fontweight='bold')
    ax2.set_title('CapEx Savings from Demand Flexibility', fontsize=13, fontweight='bold')
    ax2.grid(True, axis='y', alpha=0.3)
    
    # Value labels
    for i, v in enumerate(capex_savings_m):
        if v > 0:
            ax2.text(flexibility_pct[i], v + 2, f'${v:.0f}M', ha='center', fontsize=9, fontweight='bold')
    
    if save_path is None:
        save_path = f'/tmp/flexibility_impact_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_site_map_image(site_data: Dict, geojson_data: Dict = None, save_path: str = None) -> str:
    """
    Create map image showing site boundary from GeoJSON
    
    Args:
        site_data: Site information including coordinates
        geojson_data: GeoJSON boundary data
        save_path: Path to save image
    
    Returns:
        Path to saved map image
    """
    try:
        # Get coordinates - handle different formats
        coords = site_data.get('coordinates')
        if isinstance(coords, str):
            coords_parts = coords.replace('(', '').replace(')', '').split(',')
            lat = float(coords_parts[0].strip())
            lon = float(coords_parts[1].strip())
        elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
            lat, lon = coords[0], coords[1]
        else:
            # Default fallback
            lat, lon = 39.8283, -98.5795  # Geographic center of US
        
        # Create folium map centered on site
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles='OpenStreetMap')
        
        # Add site marker
        folium.Marker(
            location=[lat, lon],
            popup=f"{site_data.get('name', 'Unknown Site')}",
            tooltip=f"{site_data.get('name', 'Site')}<br>{site_data.get('it_capacity_mw', 0):.0f} MW IT",
            icon=folium.Icon(color='red', icon='server', prefix='fa')
        ).add_to(m)
        
        # Add GeoJSON boundary if available
        if geojson_data:
            folium.GeoJson(
                geojson_data,
                name='Site Boundary',
                style_function=lambda x: {
                    'fillColor': '#3498DB',
                    'color': '#2C3E50',
                    'weight': 2.5,
                    'fillOpacity': 0.3
                }
            ).add_to(m)
        else:
            # Draw a simple circle boundary
            land_acres = site_data.get('land_acres', 100)
            # Convert acres to meters radius (rough approximation)
            radius = np.sqrt(land_acres * 4046.86) / 2  # sqrt(area/pi)
            
            folium.Circle(
                location=[lat, lon],
                radius=radius,
                color='#2C3E50',
                fill=True,
                fillColor='#3498DB',
                fillOpacity=0.3,
                weight=2
            ).add_to(m)
        
        # Add scale
        plugins.MeasureControl(position='bottomleft', primary_length_unit='meters').add_to(m)
        
        # Save to HTML first
        if save_path is None:
            save_path = f'/tmp/site_map_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        
        html_path = save_path.replace('.png', '.html')
        m.save(html_path)
        
        # Note: Converting HTML map to PNG requires selenium/webdriver
        # For now, we'll return the HTML path
        # In production, you'd use selenium to capture a screenshot
        
        return html_path  # Return HTML for now - can be embedded in report
        
    except Exception as e:
        print(f"Error creating site map: {e}")
        return None


if __name__ == "__main__":
    # Test chart generation
    print("Testing chart generation functions...")
    
    # Test LCOE comparison
    test_sites = [
        {'site_name': 'Austin', 'lcoe': 76.5},
        {'site_name': 'Phoenix', 'lcoe': 82.3},
        {'site_name': 'Dallas', 'lcoe': 91.2},
    ]
    lcoe_path = create_lcoe_comparison_chart(test_sites)
    print(f"✓ LCOE chart: {lcoe_path}")
    
    # Test CapEx breakdown
    test_equipment = {
        'recip_mw': 200,
        'turbine_mw': 50,
        'bess_mwh': 400,
        'solar_mw': 120,
        'grid_mw': 150
    }
    capex_path = create_capex_breakdown_chart(test_equipment)
    print(f"✓ CapEx chart: {capex_path}")
    
    # Test 15-year energy stack
    energy_path = create_15year_energy_stack_chart(test_equipment, {'total_annual_gwh': 1200})
    print(f"✓ Energy stack chart: {energy_path}")
    
    print("\nAll charts generated successfully!")
