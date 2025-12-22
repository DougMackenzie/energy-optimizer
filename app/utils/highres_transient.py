"""
High-Resolution Transient Simulation
Second-level granularity for detailed power quality analysis
"""

import numpy as np
from typing import Dict, Tuple


def generate_high_res_transient(
    base_load_mw: float,
    event_type: str = 'step_change',
    duration_seconds: int = 300,
    event_magnitude_pct: float = 20
) -> Dict:
    """
    Generate high-resolution (1-second) transient simulation
    
    Args:
        base_load_mw: Base load in MW
        event_type: 'step_change', 'ramp_up', 'ramp_down', or 'oscillation'
        duration_seconds: Total simulation duration (default 300s = 5 min)
        event_magnitude_pct: Size of transient event as % of base load
    
    Returns:
        Dict with time series data at 1-second resolution
    """
    
    # Time array (1-second resolution)
    time = np.arange(0, duration_seconds, 1)
    num_points = len(time)
    
    # Initialize load profile
    load_profile = np.ones(num_points) * base_load_mw
    
    # Event parameters
    event_mw = base_load_mw * (event_magnitude_pct / 100)
    event_start = int(num_points * 0.2)  # Start at 20% of timeline
    
    if event_type == 'step_change':
        # Sudden step up
        step_duration = 60  # 60 seconds
        load_profile[event_start:event_start+step_duration] += event_mw
        
    elif event_type == 'ramp_up':
        # Gradual ramp over 60 seconds
        ramp_duration = 60
        ramp = np.linspace(0, event_mw, ramp_duration)
        load_profile[event_start:event_start+ramp_duration] += ramp
        # Hold
        load_profile[event_start+ramp_duration:event_start+ramp_duration+60] += event_mw
        
    elif event_type == 'ramp_down':
        # Start high, ramp down
        load_profile[:event_start] += event_mw
        ramp_duration = 60
        ramp = np.linspace(event_mw, 0, ramp_duration)
        load_profile[event_start:event_start+ramp_duration] += ramp
        
    elif event_type == 'oscillation':
        # Sinusoidal oscillation (load breathing)
        freq = 0.05  # 0.05 Hz = 20 second period
        oscillation = event_mw * np.sin(2 * np.pi * freq * time)
        load_profile += oscillation
    
    # Simulate BESS response (instant)
    bess_response = np.zeros(num_points)
    load_delta = np.diff(load_profile, prepend=load_profile[0])
    
    # BESS responds to changes > 1 MW/s
    for i in range(num_points):
        if abs(load_delta[i]) > 1.0:  # > 1 MW/s change
            bess_response[i] = -load_delta[i]  # BESS counteracts the change
    
    # Generator response (slower, 5-second ramp)
    gen_response = np.zeros(num_points)
    for i in range(5, num_points):
        # Generator tracks load with 5-second lag
        gen_target = load_profile[i] - bess_response[i]
        gen_response[i] = gen_response[i-1] + (gen_target - gen_response[i-1]) * 0.2
    
    # Calculate net load (what grid sees)
    net_load = load_profile - bess_response - gen_response
    
    # Frequency deviation using Swing Equation (physics-based)
    # df/dt = (f0 / 2H) * (P_imbalance / P_base)
    # where H = inertia constant (seconds), f0 = nominal frequency
    
    # System parameters
    f0 = 60.0  # Hz
    H = 4.0    # Inertia constant (typical for grid-connected system = 2-6 seconds)
    dt = 1.0   # Time step (1 second)
    
    # Initialize frequency array
    frequency = np.zeros(num_points)
    frequency[0] = f0
    
    # Guard against division by zero
    if base_load_mw > 0:
        # Integrate frequency deviation over time
        for i in range(1, num_points):
            # Power imbalance (MW)
            p_imbalance = net_load[i] - base_load_mw
            
            # Rate of frequency change (Hz/s)
            df_dt = (f0 / (2 * H)) * (p_imbalance / base_load_mw)
            
            # Integrate: f[i] = f[i-1] + df_dt * dt
            frequency[i] = frequency[i-1] + df_dt * dt
    else:
        # If no base load, frequency stays constant
        frequency[:] = f0
    
    # Clip to realistic bounds (± 0.5 Hz from nominal)
    frequency = np.clip(frequency, 59.5, 60.5)
    
    return {
        'time': time,
        'load_mw': load_profile,
        'bess_response_mw': bess_response,
        'generator_response_mw': gen_response,
        'net_load_mw': net_load,
        'frequency_hz': frequency,
        'load_delta_mw_s': load_delta,
        'event_type': event_type,
        'event_magnitude_mw': event_mw
    }


def calculate_power_quality_metrics(transient_data: Dict) -> Dict:
    """
    Calculate power quality metrics from high-res data
    """
    
    frequency = transient_data['frequency_hz']
    load_delta = transient_data['load_delta_mw_s']
    bess_response = transient_data['bess_response_mw']
    
    metrics = {
        'max_frequency_deviation_hz': max(abs(frequency - 60.0)),
        'max_ramp_rate_mw_s': np.max(np.abs(load_delta)),
        'avg_ramp_rate_mw_s': np.mean(np.abs(load_delta)),
        'bess_max_response_mw': np.max(np.abs(bess_response)),
        'bess_total_energy_mwh': np.sum(np.abs(bess_response)) / 3600,  # Convert to MWh
        'frequency_nadir_hz': np.min(frequency),
        'frequency_zenith_hz': np.max(frequency),
        'time_to_stabilize_s': calculate_stabilization_time(transient_data),
        'transient_severity': classify_transient_severity(transient_data)
    }
    
    return metrics


def calculate_stabilization_time(transient_data: Dict) -> float:
    """
    Calculate time for system to stabilize after transient
    """
    
    frequency = transient_data['frequency_hz']
    
    # Find when frequency returns to within 0.1 Hz of nominal and stays there
    stable_threshold = 0.1  # Hz
    stable_duration = 10  # Must be stable for 10 seconds
    
    for i in range(len(frequency) - stable_duration):
        window = frequency[i:i+stable_duration]
        if np.all(np.abs(window - 60.0) < stable_threshold):
            return transient_data['time'][i]
    
    return transient_data['time'][-1]  # Didn't stabilize


def classify_transient_severity(transient_data: Dict) -> str:
    """
    Classify transient severity based on IEEE standards
    """
    
    max_freq_dev = max(abs(transient_data['frequency_hz'] - 60.0))
    max_ramp = np.max(np.abs(transient_data['load_delta_mw_s']))
    
    if max_freq_dev > 0.5 or max_ramp > 50:
        return "Severe"
    elif max_freq_dev > 0.3 or max_ramp > 20:
        return "Moderate"
    elif max_freq_dev > 0.1 or max_ramp > 5:
        return "Minor"
    else:
        return "Negligible"
