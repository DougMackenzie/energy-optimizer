"""
Additional Transient Analysis Charts
Generates charts from actual transient simulation data
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict
from datetime import datetime
import os


def create_transient_response_chart(transient_data: Dict, save_path: str = None) -> str:
    """
    Generate transient response chart showing Load, Generator, and BESS response
    Uses ACTUAL data from highres_transient simulation
    """
    if not transient_data:
        return None
    
    time = transient_data.get('time', [])
    load = transient_data.get('load_mw', [])
    gen_response = transient_data.get('generator_response_mw', [])
    bess_response = transient_data.get('bess_response_mw', [])
    
    if len(time) == 0:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot load, generator, and BESS
    ax.plot(time, load, 'b-', linewidth=2, label='Load', color='#4169E1')
    ax.plot(time, gen_response, 'g-', linewidth=2, label='Generator', color='#32CD32')
    ax.plot(time, bess_response, '-', linewidth=2, label='BESS', color='#FF8C00')
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Power (MW)', fontsize=12)
    ax.set_title('Transient Response (1-second resolution)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    if save_path is None:
        save_path = f'/tmp/transient_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_load_rate_of_change_chart(transient_data: Dict, save_path: str = None) -> str:
    """
    Generate load rate of change chart (dP/dt)
    Shows ramp rates during transient events
    """
    if not transient_data:
        return None
    
    time = transient_data.get('time', [])
    load_delta = transient_data.get('load_delta_mw_s', [])
    
    if len(time) == 0:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Plot load rate of change
    ax.plot(time, load_delta, linewidth=2, color='#FF8C00')
    ax.fill_between(time, 0, load_delta, alpha=0.3, color='#FF8C00')
    ax.axhline(0, color='gray', linestyle='-', linewidth=0.5)
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('dP/dt (MW/s)', fontsize=12)
    ax.set_title('Load Rate of Change', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    if save_path is None:
        save_path = f'/tmp/load_rate_change_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_frequency_deviation_chart(transient_data: Dict, save_path: str = None) -> str:
    """
    Generate frequency deviation chart
    Shows how frequency varies during transient event
    """
    if not transient_data:
        return None
    
    time = transient_data.get('time', [])
    frequency = transient_data.get('frequency_hz', [])
    
    if len(time) == 0:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Plot frequency
    ax.plot(time, frequency, linewidth=2, color='#DC143C')
    ax.fill_between(time, 59.5, frequency, where=(frequency >= 59.5), alpha=0.3, color='#DC143C', label='Deviation')
    ax.fill_between(time, frequency, 60.5, where=(frequency <= 60.5), alpha=0.3, color='#DC143C')
    
    # Reference lines
    ax.axhline(60.0, color='green', linestyle='--', linewidth=2, label='Nominal (60 Hz)')
    ax.axhline(59.5, color='red', linestyle=':', linewidth=1, alpha=0.7, label='Limits (±0.5 Hz)')
    ax.axhline(60.5, color='red', linestyle=':', linewidth=1, alpha=0.7)
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title('Frequency Deviation During Transient', fontsize=14, fontweight='bold')
    ax.set_ylim(59.4, 60.6)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    if save_path is None:
        save_path = f'/tmp/frequency_deviation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path


def create_workload_step_change_chart(transient_data: Dict, save_path: str = None) -> str:
    """
    Generate workload step change event chart
    Shows the load profile during the transient event
    """
    if not transient_data:
        return None
    
    time = transient_data.get('time', [])
    load = transient_data.get('load_mw', [])
    
    if len(time) == 0:
        return None
    
    # Get event parameters
    event_magnitude = transient_data.get('event_magnitude_mw', 0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot load as step function
    ax.plot(time, load, linewidth=3, color='#4169E1', drawstyle='steps-post')
    ax.fill_between(time, 0, load, alpha=0.2, color='#4169E1', step='post')
    
    # Add peak capacity reference line if available
    if len(load) > 0:
        peak = max(load)
        ax.axhline(peak, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'Peak Capacity')
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Load (MW)', fontsize=12)
    ax.set_title('Transient Event: Workload Step Change', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    
    if save_path is None:
        save_path = f'/tmp/workload_step_change_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return save_path
