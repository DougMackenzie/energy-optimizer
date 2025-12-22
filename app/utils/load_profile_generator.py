"""
AI Datacenter Load Profile Generator with Demand Response Capabilities

Standalone functions for generating load profiles with flexibility breakdown.
"""

import numpy as np
from typing import Dict, Optional


def generate_load_profile_with_flexibility(
    peak_it_load_mw: float,
    pue: float,
    load_factor: float,
    workload_mix: Dict[str, float],
    flexibility_params: Optional[Dict[str, float]] = None,
    cooling_flex_pct: float = 0.25,
    hours: int = 8760,
    include_patterns: bool = True,
    seed: int = 42
) -> Dict[str, np.ndarray]:
    """
    Generate complete load profile with flexibility breakdown.
    
    Args:
        peak_it_load_mw: Peak IT load in MW
        pue: Power Usage Effectiveness
        load_factor: Average capacity utilization (0-1)
        workload_mix: Dict with workload type percentages (sum to 100)
        flexibility_params: Optional overrides for flexibility percentages
        cooling_flex_pct: Cooling flexibility as fraction (default 0.25 = 25%)
        hours: Number of hours to generate (default 8760)
        include_patterns: Whether to include daily/seasonal patterns
        seed: Random seed for reproducibility
    
    Returns:
        Dict with arrays for all load and flexibility components
    """
    np.random.seed(seed)
    
    # Default flexibility parameters (from research)
    default_flex = {
        'pre_training': 0.30,
        'fine_tuning': 0.50,
        'batch_inference': 0.90,
        'realtime_inference': 0.05,
        'rl_training': 0.40,
        'cloud_hpc': 0.25,
    }
    
    if flexibility_params:
        default_flex.update(flexibility_params)
    
    # Calculate peak loads
    peak_facility_mw = peak_it_load_mw * pue
    
    # Generate base load profile
    base_load = peak_facility_mw * load_factor
    profile = np.full(hours, base_load)
    
    if include_patterns:
        for h in range(hours):
            hour_of_day = h % 24
            day_of_year = h // 24
            
            # Daily pattern: higher during 9am-10pm
            if 9 <= hour_of_day <= 22:
                daily_factor = 1.03
            else:
                daily_factor = 0.95
            
            # Seasonal pattern: ±5% (peak in summer)
            seasonal_factor = 1.0 + 0.05 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            
            # Random noise: ±2%
            random_factor = 1.0 + np.random.uniform(-0.02, 0.02)
            
            profile[h] = base_load * daily_factor * seasonal_factor * random_factor
    
    # Clip to reasonable bounds
    profile = np.clip(profile, peak_facility_mw * 0.5, peak_facility_mw)
    
    # Split into IT and cooling
    it_load = profile / pue
    cooling_load = profile - it_load
    
    # Calculate workload loads and flexibility
    workload_loads = {}
    workload_flex = {}
    
    workload_types = ['pre_training', 'fine_tuning', 'batch_inference', 
                     'realtime_inference', 'rl_training', 'cloud_hpc']
    
    for wl_type in workload_types:
        # Get percentage (handle both 'pre_training' and 'pre_training_pct' keys)
        pct = workload_mix.get(wl_type, workload_mix.get(f'{wl_type}_pct', 0))
        if isinstance(pct, (int, float)) and pct > 1:  # If percentage (0-100)
            pct = pct / 100
        
        wl_load = it_load * pct
        workload_loads[wl_type] = wl_load
        
        flex_pct = default_flex.get(wl_type, 0)
        workload_flex[wl_type] = wl_load * flex_pct
    
    # Calculate totals
    total_it_flex = sum(workload_flex.values())
    cooling_flex = cooling_load * cooling_flex_pct
    total_flex = total_it_flex + cooling_flex
    firm_load = profile - total_flex
    
    # Summary statistics
    summary = {
        'peak_facility_mw': peak_facility_mw,
        'avg_load_mw': np.mean(profile),
        'avg_flexibility_mw': np.mean(total_flex),
        'avg_flexibility_pct': np.mean(total_flex / profile) * 100,
        'min_flexibility_mw': np.min(total_flex),
        'max_flexibility_mw': np.max(total_flex),
    }
    
    return {
        # Total loads
        'total_load_mw': profile,
        'it_load_mw': it_load,
        'cooling_load_mw': cooling_load,
        
        # Workload breakdown
        'pre_training_load_mw': workload_loads['pre_training'],
        'fine_tuning_load_mw': workload_loads['fine_tuning'],
        'batch_inference_load_mw': workload_loads['batch_inference'],
        'realtime_inference_load_mw': workload_loads['realtime_inference'],
        'rl_training_load_mw': workload_loads['rl_training'],
        'cloud_hpc_load_mw': workload_loads['cloud_hpc'],
        
        # Flexibility by source
        'pre_training_flex_mw': workload_flex['pre_training'],
        'fine_tuning_flex_mw': workload_flex['fine_tuning'],
        'batch_inference_flex_mw': workload_flex['batch_inference'],
        'realtime_inference_flex_mw': workload_flex['realtime_inference'],
        'rl_training_flex_mw': workload_flex['rl_training'],
        'cloud_hpc_flex_mw': workload_flex['cloud_hpc'],
        'total_it_flex_mw': total_it_flex,
        'cooling_flex_mw': cooling_flex,
        
        # Totals
        'total_flex_mw': total_flex,
        'firm_load_mw': firm_load,
        
        # Summary statistics
        'summary': summary
    }


def calculate_dr_economics(
    load_data: Dict[str, np.ndarray],
    dr_product: str,
    event_hours: int = 100
) -> Dict:
    """
    Calculate demand response economics for a given product.
    
    Args:
        load_data: Output from generate_load_profile_with_flexibility()
        dr_product: One of 'spinning_reserve', 'non_spinning_reserve', 
                    'economic_dr', 'emergency_dr'
        event_hours: Expected annual hours of DR activation
    
    Returns:
        Dict with DR capacity and economics
    """
    # DR product parameters
    products = {
        'spinning_reserve': {
            'response_min': 10,
            'capacity_payment': 15,  # $/MW-hr
            'activation_payment': 50,  # $/MWh
            'compatible': ['fine_tuning_flex_mw', 'batch_inference_flex_mw'],
        },
        'non_spinning_reserve': {
            'response_min': 30,
            'capacity_payment': 8,
            'activation_payment': 40,
            'compatible': ['pre_training_flex_mw', 'fine_tuning_flex_mw', 'batch_inference_flex_mw'],
        },
        'economic_dr': {
            'response_min': 60,
            'capacity_payment': 5,
            'activation_payment': 100,
            'compatible': ['pre_training_flex_mw', 'fine_tuning_flex_mw', 
                          'batch_inference_flex_mw', 'cooling_flex_mw'],
        },
        'emergency_dr': {
            'response_min': 120,
            'capacity_payment': 3,
            'activation_payment': 200,
            'compatible': ['pre_training_flex_mw', 'fine_tuning_flex_mw', 
                          'batch_inference_flex_mw', 'cooling_flex_mw'],
        },
    }
    
    if dr_product not in products:
        raise ValueError(f"Unknown DR product: {dr_product}")
    
    params = products[dr_product]
    
    # Calculate available flexibility
    compatible_flex = np.zeros(len(load_data['total_load_mw']))
    for key in params['compatible']:
        if key in load_data:
            compatible_flex += load_data[key]
    
    guaranteed_mw = np.min(compatible_flex)
    avg_mw = np.mean(compatible_flex)
    
    # Economics
    capacity_payment = guaranteed_mw * 8760 * params['capacity_payment']
    activation_payment = guaranteed_mw * event_hours * params['activation_payment']
    total_revenue = capacity_payment + activation_payment
    
    return {
        'product': dr_product,
        'response_time_min': params['response_min'],
        'guaranteed_capacity_mw': guaranteed_mw,
        'average_capacity_mw': avg_mw,
        'capacity_payment_annual': capacity_payment,
        'activation_payment_annual': activation_payment,
        'total_annual_revenue': total_revenue,
        'revenue_per_mw_year': total_revenue / guaranteed_mw if guaranteed_mw > 0 else 0,
    }
