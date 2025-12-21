"""
Calculation Utilities
Core engineering calculations for the optimizer
"""

from typing import List, Dict, Tuple
import numpy as np


def calculate_lcoe(
    capex: float,
    fixed_om_annual: float,
    variable_om_per_mwh: float,
    fuel_cost_per_mwh: float,
    annual_generation_mwh: float,
    lifetime_years: int = 20,
    discount_rate: float = 0.08,
) -> float:
    """
    Calculate Levelized Cost of Electricity (LCOE)
    
    Args:
        capex: Total capital cost ($)
        fixed_om_annual: Annual fixed O&M cost ($)
        variable_om_per_mwh: Variable O&M ($/MWh)
        fuel_cost_per_mwh: Fuel cost ($/MWh)
        annual_generation_mwh: Expected annual generation (MWh)
        lifetime_years: Project lifetime
        discount_rate: Discount rate (default 8%)
    
    Returns:
        LCOE in $/MWh
    """
    if annual_generation_mwh <= 0:
        return float('inf')
    
    # Calculate NPV of costs
    years = np.arange(1, lifetime_years + 1)
    discount_factors = 1 / (1 + discount_rate) ** years
    
    # Annual costs
    annual_variable = (variable_om_per_mwh + fuel_cost_per_mwh) * annual_generation_mwh
    annual_total = fixed_om_annual + annual_variable
    
    # NPV
    npv_costs = capex + np.sum(annual_total * discount_factors)
    npv_generation = np.sum(annual_generation_mwh * discount_factors)
    
    return npv_costs / npv_generation


def calculate_nox(
    equipment_list: List[Dict],
    annual_mwh_by_equipment: Dict[str, float],
) -> float:
    """
    Calculate total annual NOx emissions in tons per year
    
    Args:
        equipment_list: List of equipment with nox_lb_mwh attribute
        annual_mwh_by_equipment: Dict mapping equipment_id to annual MWh
    
    Returns:
        Total NOx in tons per year
    """
    total_nox_lb = 0
    
    for equip in equipment_list:
        equip_id = equip.get('id', '')
        nox_lb_mwh = equip.get('nox_lb_mwh', 0)
        annual_mwh = annual_mwh_by_equipment.get(equip_id, 0)
        total_nox_lb += nox_lb_mwh * annual_mwh
    
    return total_nox_lb / 2000  # Convert to tons


def calculate_availability(
    equipment_availabilities: List[float],
    configuration: str = "parallel",
    k_of_n: Tuple[int, int] = None,
) -> float:
    """
    Calculate system availability
    
    Args:
        equipment_availabilities: List of individual equipment availabilities (0-1)
        configuration: "series", "parallel", or "k_of_n"
        k_of_n: Tuple of (k, n) for k-of-n redundancy
    
    Returns:
        System availability (0-1)
    """
    if not equipment_availabilities:
        return 0.0
    
    if configuration == "series":
        # All must work
        return np.prod(equipment_availabilities)
    
    elif configuration == "parallel":
        # At least one must work
        return 1 - np.prod([1 - a for a in equipment_availabilities])
    
    elif configuration == "k_of_n" and k_of_n:
        k, n = k_of_n
        if len(equipment_availabilities) != n:
            raise ValueError(f"Expected {n} availabilities, got {len(equipment_availabilities)}")
        
        # Assume all units have same availability
        p = equipment_availabilities[0]
        
        # Sum probability of k or more working
        from math import comb
        availability = 0
        for i in range(k, n + 1):
            availability += comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
        return availability
    
    else:
        raise ValueError(f"Unknown configuration: {configuration}")


def calculate_ramp_rate(
    equipment_list: List[Dict],
    quantities: Dict[str, int],
) -> Tuple[float, float]:
    """
    Calculate combined ramp rate capability
    
    Returns:
        Tuple of (instant_mw, sustained_mw_per_sec)
    """
    instant_mw = 0  # BESS contribution
    sustained_mw_s = 0  # Engine/turbine contribution
    
    for equip in equipment_list:
        equip_id = equip.get('id', '')
        qty = quantities.get(equip_id, 0)
        
        if equip.get('type') == 'bess':
            # BESS provides instant response
            instant_mw += equip.get('power_mw', 0) * qty
        else:
            # Thermal units provide sustained ramp
            ramp_mw_min = equip.get('ramp_rate_mw_min', 0)
            sustained_mw_s += (ramp_mw_min / 60) * qty
    
    return instant_mw, sustained_mw_s


def calculate_time_to_power(
    equipment_list: List[Dict],
    quantities: Dict[str, int],
) -> int:
    """
    Calculate time to power (months) based on longest lead time
    
    Returns:
        Time to power in months
    """
    max_time = 0
    
    for equip in equipment_list:
        equip_id = equip.get('id', '')
        qty = quantities.get(equip_id, 0)
        
        if qty > 0:
            lead_time_max = equip.get('lead_time_months_max', 
                                      equip.get('lead_time_months', [0, 0])[1] if isinstance(equip.get('lead_time_months'), list) else 0)
            max_time = max(max_time, lead_time_max)
    
    # Add installation/commissioning buffer
    return max_time + 2


def calculate_capacity(
    equipment_list: List[Dict],
    quantities: Dict[str, int],
) -> Tuple[float, float]:
    """
    Calculate total and N-1 capacity
    
    Returns:
        Tuple of (total_mw, n_minus_1_mw)
    """
    total_mw = 0
    largest_unit = 0
    
    for equip in equipment_list:
        equip_id = equip.get('id', '')
        qty = quantities.get(equip_id, 0)
        capacity = equip.get('capacity_mw', equip.get('power_mw', 0))
        
        total_mw += capacity * qty
        if capacity > largest_unit:
            largest_unit = capacity
    
    n_minus_1 = total_mw - largest_unit
    
    return total_mw, n_minus_1


def calculate_capex(
    equipment_list: List[Dict],
    quantities: Dict[str, int],
) -> float:
    """
    Calculate total CAPEX in millions
    
    Returns:
        Total CAPEX in $M
    """
    total = 0
    
    for equip in equipment_list:
        equip_id = equip.get('id', '')
        qty = quantities.get(equip_id, 0)
        
        capacity_kw = equip.get('capacity_mw', equip.get('power_mw', 0)) * 1000
        capex_per_kw = equip.get('capex_per_kw', 0)
        
        # BESS uses per-kWh pricing
        if equip.get('type') == 'bess':
            energy_kwh = equip.get('energy_mwh', 0) * 1000
            capex_per_kwh = equip.get('capex_per_kwh', 0)
            total += (capex_per_kwh * energy_kwh * qty) / 1e6
        else:
            total += (capex_per_kw * capacity_kw * qty) / 1e6
    
    return total
