"""
8760 Hourly Dispatch Simulation
Simulates hour-by-hour equipment operation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


def generate_8760_load_profile(
    base_load_mw: float,
    load_factor: float = 0.75,
    workload_mix: Dict[str, float] = None
) -> np.ndarray:
    """
    Generate realistic 8760 hourly load profile
    
    Args:
        base_load_mw: Peak facility load (MW)
        load_factor: Average capacity utilization (0-1)
        workload_mix: Dict of workload types and percentages
    
    Returns:
        Array of 8760 hourly load values (MW)
    """
    
    hours = 8760
    load_profile = np.zeros(hours)
    
    # Base load (constant component)
    base_component = base_load_mw * load_factor
    
    # Daily variation (training workloads have daily patterns)
    for hour in range(hours):
        day_hour = hour % 24
        
        # Daily pattern (lower at night, higher during day)
        if day_hour >= 6 and day_hour <= 22:
            daily_factor = 1.05  # 5% higher during day
        else:
            daily_factor = 0.95  # 5% lower at night
        
        # Weekly pattern (lower on weekends for some workloads)
        day_of_week = (hour // 24) % 7
        if day_of_week >= 5:  # Weekend
            weekly_factor = 0.98
        else:
            weekly_factor = 1.02
        
        # Add small random variation (±2%)
        random_factor = 1 + (np.random.random() - 0.5) * 0.04
        
        load_profile[hour] = base_component * daily_factor * weekly_factor * random_factor
    
    # Ensure within bounds
    load_profile = np.clip(load_profile, base_load_mw * 0.5, base_load_mw)
    
    return load_profile


def dispatch_equipment(
    load_profile: np.ndarray,
    equipment_config: Dict,
    bess_available: bool = True
) -> Dict:
    """
    Dispatch equipment hour-by-hour to meet load
    
    Returns:
        Dict with hourly dispatch schedule, fuel consumption, costs, emissions
    """
    
    hours = len(load_profile)
    
    # Initialize results
    results = {
        'load_mw': load_profile,
        'recip_dispatch_mw': np. zeros(hours),
        'turbine_dispatch_mw': np.zeros(hours),
        'bess_discharge_mw': np.zeros(hours),
        'bess_charge_mw': np.zeros(hours),
        'bess_soc_mwh': np.zeros(hours),
        'solar_generation_mw': np.zeros(hours),
        'grid_import_mw': np.zeros(hours),
        'unserved_energy_mw': np.zeros(hours),
        'fuel_consumption_mmbtu': np.zeros(hours),
        'fuel_cost_usd': np.zeros(hours),
        'emissions_nox_lb': np.zeros(hours),
        'emissions_co2_tons': np.zeros(hours)
    }
    
    # Extract equipment capacities
    recip_total = sum(e.get('capacity_mw', 0) for e in equipment_config.get('recip_engines', []))
    turbine_total = sum(e.get('capacity_mw', 0) for e in equipment_config.get('gas_turbines', []))
    bess_power = sum(e.get('power_mw', 0) for e in equipment_config.get('bess', []))
    bess_energy = sum(e.get('energy_mwh', 0) for e in equipment_config.get('bess', []))
    solar_capacity = equipment_config.get('solar_mw_dc', 0)
    solar_cf = equipment_config.get('solar_cf', 0.30)
    
    # BESS state tracking
    bess_soc = bess_energy * 0.5  # Start at 50% SOC
    
    # Fuel and emissions factors
    gas_price = 3.50  # $/MMBtu
    recip_heat_rate = 7700  # Btu/kWh average
    turbine_heat_rate = 8500  # Btu/kWh
    nox_factor = 0.099  # lb/MMBtu
    co2_factor = 117  # lb/MMBtu (natural gas)
    
    # Dispatch each hour
    for hour in range(hours):
        load = load_profile[hour]
        remaining_load = load
        
        # 1. Solar generation (if available)
        if solar_capacity > 0:
            # Improved solar profile with seasonal variation
            hour_of_day = hour % 24
            day_of_year = (hour // 24) % 365
            
            # Daily solar curve (sunrise to sunset)
            if 6 <= hour_of_day <= 18:
                # Cosine curve for daily variation
                solar_daily = np.cos((hour_of_day - 12) * np.pi / 12)
                solar_daily = max(0, solar_daily)
                
                # Seasonal variation (winter = 0.7x, summer = 1.3x of baseline)
                # Peak at summer solstice (day 172), minimum at winter solstice (day 355)
                seasonal_factor = 1.0 + 0.3 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
                
                # Apply capacity factor and seasonal adjustment
                solar_factor = solar_daily * solar_cf * seasonal_factor * 2
                solar_factor = max(0, solar_factor)
            else:
                # Night time: no solar
                solar_factor = 0
            
            solar_gen = solar_capacity * solar_factor
            results['solar_generation_mw'][hour] = solar_gen
            remaining_load -= solar_gen
        
        # 2. Reciprocating engines (baseload)
        if recip_total > 0 and remaining_load > 0:
            recip_dispatch = min(recip_total, remaining_load)
            results['recip_dispatch_mw'][hour] = recip_dispatch
            remaining_load -= recip_dispatch
            
            # Fuel consumption
            fuel_mmbtu = recip_dispatch * 1000 * recip_heat_rate / 1_000_000
            results['fuel_consumption_mmbtu'][hour] += fuel_mmbtu
            results['fuel_cost_usd'][hour] += fuel_mmbtu * gas_price
            results['emissions_nox_lb'][hour] += fuel_mmbtu * nox_factor
            results['emissions_co2_tons'][hour] += fuel_mmbtu * co2_factor / 2000
        
        # 3. Gas turbines (peaking/intermediate)
        if turbine_total > 0 and remaining_load > 0:
            turbine_dispatch = min(turbine_total, remaining_load)
            results['turbine_dispatch_mw'][hour] = turbine_dispatch
            remaining_load -= turbine_dispatch
            
            # Fuel consumption
            fuel_mmbtu = turbine_dispatch * 1000 * turbine_heat_rate / 1_000_000
            results['fuel_consumption_mmbtu'][hour] += fuel_mmbtu
            results['fuel_cost_usd'][hour] += fuel_mmbtu * gas_price
            results['emissions_nox_lb'][hour] += fuel_mmbtu * nox_factor
            results['emissions_co2_tons'][hour] += fuel_mmbtu * co2_factor / 2000
        
        # 4. BESS discharge (if needed and available)
        if bess_available and bess_power > 0 and remaining_load > 0:
            # Can discharge up to available SOC
            max_discharge = min(bess_power, bess_soc, remaining_load)
            results['bess_discharge_mw'][hour] = max_discharge
            remaining_load -= max_discharge
            bess_soc -= max_discharge
        
        # 5. Grid import (if available and needed)
        grid_capacity = equipment_config.get('grid_import_mw', 0)
        if grid_capacity > 0 and remaining_load > 0:
            grid_import = min(grid_capacity, remaining_load)
            results['grid_import_mw'][hour] = grid_import
            remaining_load -= grid_import
        
        # 6. BESS charging (if excess generation and room in battery)
        if bess_available and bess_power > 0 and remaining_load < 0:
            # We have excess, charge battery
            max_charge = min(bess_power, bess_energy - bess_soc, abs(remaining_load))
            results['bess_charge_mw'][hour] = max_charge
            bess_soc += max_charge * 0.85  # 85% round-trip efficiency
            remaining_load += max_charge
        
        # 7. Unserved energy (if any)
        if remaining_load > 0:
            results['unserved_energy_mw'][hour] = remaining_load
        
        # Update BESS SOC tracking
        results['bess_soc_mwh'][hour] = bess_soc
    
    # Calculate summary statistics
    total_load = np.sum(load_profile)
    total_unserved = np.sum(results['unserved_energy_mw'])
    
    # Add load profile to results for export
    results['load_profile_mw'] = load_profile
    
    results['summary'] = {
        'total_energy_served_gwh': total_load / 1000,
        'total_unserved_gwh': total_unserved / 1000,
        'reliability_pct': 100 * (1 - total_unserved / total_load) if total_load > 0 else 0,
        'total_fuel_cost_m': np.sum(results['fuel_cost_usd']) / 1_000_000,
        'total_fuel_mmbtu': np.sum(results['fuel_consumption_mmbtu']),
        'total_nox_tons': np.sum(results['emissions_nox_lb']) / 2000,
        'total_co2_tons': np.sum(results['emissions_co2_tons']),
        'avg_solar_cf': np.mean(results['solar_generation_mw']) / solar_capacity if solar_capacity > 0 else 0,
        'avg_bess_cycles_per_day': np.sum(results['bess_discharge_mw']) / bess_energy / 365 if bess_energy > 0 else 0,
        'recip_hours': np.sum(results['recip_dispatch_mw'] > 0),
        'turbine_hours': np.sum(results['turbine_dispatch_mw'] > 0),
        'grid_hours': np.sum(results['grid_import_mw'] > 0)
    }
    
    return results


def create_dispatch_summary_df(dispatch_results: Dict) -> pd.DataFrame:
    """Create summary dataframe from dispatch results"""
    
    summary = dispatch_results['summary']
    
    data = {
        'Metric': [
            'Total Energy Served',
            'Unserved Energy',
            'Reliability',
            'Total Fuel Cost',
            'Total Fuel Consumption',
            'Total NOx Emissions',
            'Total CO2 Emissions',
            'Recip Engine Hours',
            'Gas Turbine Hours',
            'Grid Import Hours',
            'Avg BESS Cycles/Day'
        ],
        'Value': [
            f"{summary['total_energy_served_gwh']:.1f} GWh",
            f"{summary['total_unserved_gwh']:.3f} GWh",
            f"{summary['reliability_pct']:.2f}%",
            f"${summary['total_fuel_cost_m']:.2f}M",
            f"{summary['total_fuel_mmbtu']:,.0f} MMBtu",
            f"{summary['total_nox_tons']:.1f} tons",
            f"{summary['total_co2_tons']:,.0f} tons",
            f"{summary['recip_hours']:,.0f} hrs",
            f"{summary['turbine_hours']:,.0f} hrs",
            f"{summary['grid_hours']:,.0f} hrs",
            f"{summary['avg_bess_cycles_per_day']:.2f}"
        ]
    }
    
    return pd.DataFrame(data)
