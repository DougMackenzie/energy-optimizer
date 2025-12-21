"""
Enhanced Word Report Generator with Visualizations
Includes 8760 dispatch charts, power quality analysis, and comprehensive appendices
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
from typing import Dict, List
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np


def create_8760_dispatch_chart(equipment_config: Dict, site: Dict, save_path: str = None) -> str:
    """
    Generate 8760 hourly dispatch visualization
    
    Returns:
        path to saved image file
    """
    # Simulate 8760 hours (simplified - real version would use actual dispatch)
    hours = np.arange(8760)
    total_load = site.get('Total_Facility_MW', 200)
    load_factor = site.get('Load_Factor_Pct', 70) / 100
    
    # Create synthetic load profile with daily and seasonal patterns
    base_load = total_load * load_factor
    daily_pattern = np.sin(hours * 2 * np.pi / 24) * (total_load * 0.15)
    seasonal_pattern = np.sin(hours * 2 * np.pi / 8760) * (total_load * 0.10)
    load_profile = base_load + daily_pattern + seasonal_pattern
    load_profile = np.clip(load_profile, total_load * 0.5, total_load)
    
    # Equipment dispatch (stacked)
    grid_import = np.zeros(8760)
    solar_output = np.zeros(8760)
    recip_output = np.zeros(8760)
    turbine_output = np.zeros(8760)
    bess_discharge = np.zeros(8760)
    
    # Grid (if available)
    if equipment_config.get('grid_import_mw', 0) > 0:
        grid_cap = equipment_config['grid_import_mw']
        grid_import = np.full(8760, min(grid_cap, total_load * 0.4))
    
    # Solar (daytime only, 6am-8pm)
    if equipment_config.get('solar_mw_dc', 0) > 0:
        solar_cap = equipment_config['solar_mw_dc']
        for h in range(8760):
            hour_of_day = h % 24
            if 6 <= hour_of_day <= 20:
                # Peak at noon
                sun_factor = np.sin((hour_of_day - 6) * np.pi / 14)
                solar_output[h] = solar_cap * sun_factor * 0.25  # 25% AC derate
    
    # Reciprocating engines (baseload)
    if equipment_config.get('recip_engines'):
        recip_cap = sum(e.get('capacity_mw', 0) for e in equipment_config['recip_engines'])
        recip_cf = equipment_config['recip_engines'][0].get('capacity_factor', 0.7) if equipment_config['recip_engines'] else 0.7
        recip_output = np.full(8760, recip_cap * recip_cf)
    
    # Gas turbines (peaking)
    if equipment_config.get('gas_turbines'):
        turbine_cap = sum(t.get('capacity_mw', 0) for t in equipment_config['gas_turbines'])
        # Turbines run during high load periods
        for h in range(8760):
            if load_profile[h] > base_load:
                turbine_output[h] = min(turbine_cap, (load_profile[h] - base_load) * 0.5)
    
    # BESS (peak shaving)
    if equipment_config.get('bess'):
        bess_power = sum(b.get('power_mw', 0) for b in equipment_config['bess'])
        for h in range(8760):
            hour_of_day = h % 24
            # Discharge during evening peak (6pm-10pm)
            if 18 <= hour_of_day <= 22:
                bess_discharge[h] = bess_power * 0.8
   
    # Create stacked area chart (show first week for clarity - 168 hours)
    fig, ax = plt.subplots(figsize=(14, 6))
    
    week_hours = hours[:168]
    ax.fill_between(week_hours, 0, grid_import[:168], label='Grid Import', alpha=0.8, color='#808080')
    ax.fill_between(week_hours, grid_import[:168], 
                     grid_import[:168] + solar_output[:168], 
                     label='Solar PV', alpha=0.8, color='#FFD700')
    ax.fill_between(week_hours, grid_import[:168] + solar_output[:168],
                     grid_import[:168] + solar_output[:168] + recip_output[:168],
                     label='Recip Engines', alpha=0.8, color='#4169E1')
    ax.fill_between(week_hours, 
                     grid_import[:168] + solar_output[:168] + recip_output[:168],
                     grid_import[:168] + solar_output[:168] + recip_output[:168] + turbine_output[:168],
                     label='Gas Turbines', alpha=0.8, color='#DC143C')
    ax.fill_between(week_hours,
                     grid_import[:168] + solar_output[:168] + recip_output[:168] + turbine_output[:168],
                     grid_import[:168] + solar_output[:168] + recip_output[:168] + turbine_output[:168] + bess_discharge[:168],
                     label='BESS Discharge', alpha=0.8, color='#FF8C00')
    
    # Load demand line
    ax.plot(week_hours, load_profile[:168], 'k--', linewidth=2, label='Load Demand')
    
    ax.set_xlabel('Hour', fontsize=12)
    ax.set_ylabel('Power (MW)', fontsize=12)
    ax.set_title('Hourly Dispatch - First Week (168 hours)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 168)
    
    # Save
    if save_path is None:
        save_path = f'/tmp/dispatch_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_emissions_chart(equipment_config: Dict, constraints: Dict, save_path: str = None) -> str:
    """
    Generate hourly emissions chart
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Simulate hourly emissions for first week
    hours = np.arange(168)
    
    # NOx emissions (based on generator output)
    recip_cap = sum(e.get('capacity_mw', 0) for e in equipment_config.get('recip_engines', []))
    turbine_cap = sum(t.get('capacity_mw', 0) for t in equipment_config.get('gas_turbines', []))
    
    # Typical emission rates
    nox_rate_recip = 0.099  # lb/MMBtu
    nox_rate_turbine = 0.099
    heat_rate = 8000  # Btu/kWh avg
    
    # Hourly NOx (lb/hr)
    nox_hourly = (recip_cap * 1000 * heat_rate / 1_000_000 * nox_rate_recip * 0.7) * np.ones(168)
    nox_hourly += (turbine_cap * 1000 * heat_rate / 1_000_000 * nox_rate_turbine * 0.3) * (np.random.rand(168) * 0.5 + 0.5)
    
    ax1.fill_between(hours, 0, nox_hourly, alpha=0.7, color='#DC143C', label='NOx Emissions')
    ax1.axhline(constraints.get('NOx_Limit_tpy', 100) * 2000 / 8760, color='red', linestyle='--', linewidth=2, label='Annual Avg Limit')
    ax1.set_xlabel('Hour', fontsize=11)
    ax1.set_ylabel('NOx (lb/hr)', fontsize=11)
    ax1.set_title('Hourly NOx Emissions', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # CO emissions
    co_rate = 0.015  # lb/MMBtu
    co_hourly = (recip_cap * 1000 * heat_rate / 1_000_000 * co_rate * 0.7) * np.ones(168)
    co_hourly += (turbine_cap * 1000 * heat_rate / 1_000_000 * co_rate * 0.3) * (np.random.rand(168) * 0.5 + 0.5)
    
    ax2.fill_between(hours, 0, co_hourly, alpha=0.7, color='#4169E1', label='CO Emissions')
    ax2.axhline(constraints.get('CO_Limit_tpy', 250) * 2000 / 8760, color='red', linestyle='--', linewidth=2, label='Annual Avg Limit')
    ax2.set_xlabel('Hour', fontsize=11)
    ax2.set_ylabel('CO (lb/hr)', fontsize=11)
    ax2.set_title('Hourly CO Emissions', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    if save_path is None:
        save_path = f'/tmp/emissions_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_deployment_timeline_chart(timeline: Dict, save_path: str = None) -> str:
    """
    Generate deployment timeline Gantt chart
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Equipment deployment phases
    phases = [
        ('Permitting', 0, 12, '#808080'),
        ('Grid Interconnection', 6, timeline.get('grid_timeline_months', 96), '#FFD700'),
        ('Solar Installation', 80, 95, '#FF8C00'),
        ('Generator Procurement', 12, 30, '#4169E1'),
        ('BESS Installation', 85, 97, '#DC143C'),
        ('Commissioning', 95, timeline.get('timeline_months', 108), '#32CD32')
    ]
    
    for i, (phase, start, end, color) in enumerate(phases):
        ax.barh(i, end - start, left=start, height=0.5, color=color, alpha=0.8, label=phase)
        ax.text(start + (end - start) / 2, i, phase, ha='center', va='center', fontsize=10, fontweight='bold')
    
    ax.set_yticks(range(len(phases)))
    ax.set_yticklabels([p[0] for p in phases])
    ax.set_xlabel('Months from Start', fontsize=12)
    ax.set_title('Equipment Deployment Timeline (Gantt Chart)', fontsize=14, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3)
    ax.set_xlim(0, timeline.get('timeline_months', 108) + 5)
    
    if save_path is None:
        save_path = f'/tmp/timeline_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_bess_soc_chart(equipment_config: Dict, save_path: str = None) -> str:
    """
    Generate BESS State of Charge chart
    """
    if not equipment_config.get('bess'):
        return None
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    hours = np.arange(168)  # First week
    soc = np.zeros(168)
    
    # Simulate charge/discharge cycles
    for h in range(168):
        hour_of_day = h % 24
        if 10 <= hour_of_day <= 16:  # Solar charging
            soc[h] = min(100, soc[h-1] + 15 if h > 0 else 50)
        elif 18 <= hour_of_day <= 22:  # Evening discharge
            soc[h] = max(20, soc[h-1] - 20 if h > 0 else 80)
        else:
            soc[h] = soc[h-1] if h > 0 else 50
    
    ax.plot(hours, soc, linewidth=2, color='#DC143C', label='State of Charge')
    ax.fill_between(hours, 0, soc, alpha=0.3, color='#DC143C')
    ax.axhline(80, color='orange', linestyle='--', alpha=0.7, label='High SOC (80%)')
    ax.axhline(20, color='red', linestyle='--', alpha=0.7, label='Low SOC (20%)')
    
    ax.set_xlabel('Hour', fontsize=12)
    ax.set_ylabel('State of Charge (%)', fontsize=12)
    ax.set_title('BESS State of Charge - First Week', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    if save_path is None:
        save_path = f'/tmp/bess_soc_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path
