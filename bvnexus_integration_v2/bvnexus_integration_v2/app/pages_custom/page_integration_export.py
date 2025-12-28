"""
bvNexus Integration Export Page (Enhanced)
==========================================

Enhanced export page with:
- Sample file previews
- Visual representations of equipment and scenarios
- Graphical diagrams (single-line, RBD)
- File format documentation
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from io import BytesIO
import json
import zipfile

# =============================================================================
# SAMPLE DATA GENERATORS
# =============================================================================

def generate_sample_equipment_config() -> Dict:
    """Generate a realistic sample equipment configuration."""
    return {
        'project_name': 'Dallas Hyperscale DC',
        'site_id': 'DAL-001',
        'peak_load_mw': 200.0,
        'n_recip': 8,
        'recip_mw': 146.4,  # 8 x 18.3 MW
        'recip_mw_each': 18.3,
        'n_turbine': 2,
        'turbine_mw': 100.0,  # 2 x 50 MW
        'turbine_mw_each': 50.0,
        'bess_mw': 30.0,
        'bess_mwh': 120.0,
        'bess_duration_hr': 4.0,
        'solar_mw': 0.0,
        'grid_connection_mw': 50.0,
        'redundancy': 'N+1',
        'voltage_kv': 13.8,
        'system_mva_base': 100.0,
    }


def generate_sample_etap_equipment_df(config: Dict) -> pd.DataFrame:
    """Generate sample ETAP equipment dataframe."""
    rows = []
    bus_id = 100
    
    # Reciprocating engines
    for i in range(config.get('n_recip', 0)):
        rows.append({
            'ID': f'GEN_RECIP_{i+1:02d}',
            'Name': f'Recip Engine {i+1}',
            'Type': 'Synchronous Generator',
            'Bus_ID': f'BUS_{bus_id + i}',
            'Rated_kV': 13.8,
            'Rated_MW': config.get('recip_mw_each', 18.3),
            'Rated_MVA': config.get('recip_mw_each', 18.3) / 0.85,
            'Rated_PF': 0.85,
            'Xd_pu': 1.80,
            'Xd_prime_pu': 0.25,
            'Xd_double_prime_pu': 0.18,
            'H_inertia_sec': 1.5,
            'Status': 'Online',
            'Redundancy_Group': 'THERMAL_GEN',
        })
    
    # Gas turbines
    for i in range(config.get('n_turbine', 0)):
        rows.append({
            'ID': f'GEN_GT_{i+1:02d}',
            'Name': f'Gas Turbine {i+1}',
            'Type': 'Synchronous Generator',
            'Bus_ID': f'BUS_{bus_id + 20 + i}',
            'Rated_kV': 13.8,
            'Rated_MW': config.get('turbine_mw_each', 50.0),
            'Rated_MVA': config.get('turbine_mw_each', 50.0) / 0.85,
            'Rated_PF': 0.85,
            'Xd_pu': 1.50,
            'Xd_prime_pu': 0.22,
            'Xd_double_prime_pu': 0.15,
            'H_inertia_sec': 3.0,
            'Status': 'Online',
            'Redundancy_Group': 'THERMAL_GEN',
        })
    
    # BESS
    if config.get('bess_mw', 0) > 0:
        rows.append({
            'ID': 'BESS_01',
            'Name': f"Battery Storage ({config.get('bess_mwh', 0):.0f} MWh)",
            'Type': 'Battery Energy Storage',
            'Bus_ID': 'BUS_140',
            'Rated_kV': 13.8,
            'Rated_MW': config.get('bess_mw', 0),
            'Rated_MVA': config.get('bess_mw', 0),
            'Rated_PF': 1.00,
            'Xd_pu': 0.0,
            'Xd_prime_pu': 0.0,
            'Xd_double_prime_pu': 0.05,
            'H_inertia_sec': 0.0,
            'Status': 'Online',
            'Redundancy_Group': 'STORAGE',
        })
    
    return pd.DataFrame(rows)


def generate_sample_etap_scenarios_df(config: Dict) -> pd.DataFrame:
    """Generate sample ETAP scenarios dataframe."""
    peak_load = config.get('peak_load_mw', 200)
    n_recip = config.get('n_recip', 8)
    n_turbine = config.get('n_turbine', 2)
    
    rows = [
        # Base cases
        {'Scenario_ID': 'BASE_100', 'Name': 'Base Case - 100% Load', 'Type': 'Normal',
         'Load_MW': peak_load, 'Load_PF': 0.95, 'Tripped_Equipment': '', 
         'Description': 'All equipment online, peak load'},
        {'Scenario_ID': 'BASE_75', 'Name': 'Base Case - 75% Load', 'Type': 'Normal',
         'Load_MW': peak_load * 0.75, 'Load_PF': 0.95, 'Tripped_Equipment': '',
         'Description': 'All equipment online, 75% load'},
        {'Scenario_ID': 'BASE_50', 'Name': 'Base Case - 50% Load', 'Type': 'Normal',
         'Load_MW': peak_load * 0.50, 'Load_PF': 0.95, 'Tripped_Equipment': '',
         'Description': 'All equipment online, 50% load'},
        {'Scenario_ID': 'BASE_25', 'Name': 'Base Case - 25% Load', 'Type': 'Normal',
         'Load_MW': peak_load * 0.25, 'Load_PF': 0.95, 'Tripped_Equipment': '',
         'Description': 'All equipment online, 25% load'},
    ]
    
    # N-1 contingencies for recips
    for i in range(n_recip):
        rows.append({
            'Scenario_ID': f'N1_RECIP_{i+1:02d}',
            'Name': f'N-1: Recip {i+1} Trip',
            'Type': 'N-1 Contingency',
            'Load_MW': peak_load,
            'Load_PF': 0.95,
            'Tripped_Equipment': f'GEN_RECIP_{i+1:02d}',
            'Description': f'Single contingency - Recip Engine {i+1} offline',
        })
    
    # N-1 contingencies for turbines
    for i in range(n_turbine):
        rows.append({
            'Scenario_ID': f'N1_GT_{i+1:02d}',
            'Name': f'N-1: GT {i+1} Trip',
            'Type': 'N-1 Contingency',
            'Load_MW': peak_load,
            'Load_PF': 0.95,
            'Tripped_Equipment': f'GEN_GT_{i+1:02d}',
            'Description': f'Single contingency - Gas Turbine {i+1} offline',
        })
    
    # N-2 contingencies (largest units)
    rows.append({
        'Scenario_ID': 'N2_GT_BOTH',
        'Name': 'N-2: Both GTs Trip',
        'Type': 'N-2 Contingency',
        'Load_MW': peak_load,
        'Load_PF': 0.95,
        'Tripped_Equipment': 'GEN_GT_01,GEN_GT_02',
        'Description': 'Double contingency - Both gas turbines offline',
    })
    
    return pd.DataFrame(rows)


def generate_sample_etap_loadflow_results_df() -> pd.DataFrame:
    """Generate sample ETAP load flow results (what would be imported)."""
    return pd.DataFrame([
        {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.012, 
         'Angle_deg': 2.3, 'P_MW': 18.3, 'Q_MVAR': 9.8, 'Loading_pct': 72.5},
        {'Bus_ID': 'BUS_101', 'Bus_Name': 'RECIP_2_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.010, 
         'Angle_deg': 2.1, 'P_MW': 18.3, 'Q_MVAR': 9.7, 'Loading_pct': 71.8},
        {'Bus_ID': 'BUS_102', 'Bus_Name': 'RECIP_3_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.008, 
         'Angle_deg': 1.9, 'P_MW': 18.3, 'Q_MVAR': 9.6, 'Loading_pct': 70.2},
        {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.025, 
         'Angle_deg': 0.0, 'P_MW': 50.0, 'Q_MVAR': 25.0, 'Loading_pct': 85.0},
        {'Bus_ID': 'BUS_121', 'Bus_Name': 'GT_2_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.020, 
         'Angle_deg': -0.5, 'P_MW': 50.0, 'Q_MVAR': 24.5, 'Loading_pct': 82.3},
        {'Bus_ID': 'BUS_140', 'Bus_Name': 'BESS_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.005, 
         'Angle_deg': 1.2, 'P_MW': 0.0, 'Q_MVAR': 5.0, 'Loading_pct': 0.0},
        {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.000, 
         'Angle_deg': 0.0, 'P_MW': -200.0, 'Q_MVAR': -65.0, 'Loading_pct': 95.2},
    ])


def generate_sample_etap_shortcircuit_results_df() -> pd.DataFrame:
    """Generate sample ETAP short circuit results."""
    return pd.DataFrame([
        {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Fault_Type': '3-Phase', 
         'Isc_kA': 28.5, 'Isc_MVA': 682, 'X_R_Ratio': 12.5, 'Breaker_Rating_kA': 40.0, 'Duty_pct': 71.3},
        {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Fault_Type': '3-Phase', 
         'Isc_kA': 35.2, 'Isc_MVA': 841, 'X_R_Ratio': 15.8, 'Breaker_Rating_kA': 40.0, 'Duty_pct': 88.0},
        {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Fault_Type': '3-Phase', 
         'Isc_kA': 42.8, 'Isc_MVA': 1022, 'X_R_Ratio': 18.2, 'Breaker_Rating_kA': 50.0, 'Duty_pct': 85.6},
        {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Fault_Type': 'L-G', 
         'Isc_kA': 38.5, 'Isc_MVA': 920, 'X_R_Ratio': 16.5, 'Breaker_Rating_kA': 50.0, 'Duty_pct': 77.0},
    ])


def generate_sample_psse_raw(config: Dict) -> str:
    """Generate sample PSS/e RAW format file content."""
    lines = []
    system_mva = config.get('system_mva_base', 100.0)
    
    # Header (3 lines required)
    lines.append(f"0,   {system_mva:.2f}     / PSS/E-35    {datetime.now().strftime('%a, %b %d %Y  %H:%M')}")
    lines.append(f"{config.get('project_name', 'bvNexus Export')} - Power Flow Base Case")
    lines.append("Behind-the-Meter Datacenter Generation System")
    
    # Bus data section
    lines.append("")
    lines.append("/ BUS DATA")
    lines.append("/ I, 'NAME', BASKV, IDE, AREA, ZONE, OWNER, VM, VA, NVHI, NVLO, EVHI, EVLO")
    
    bus_id = 100
    buses = []
    
    # Generator buses
    for i in range(config.get('n_recip', 0)):
        bus = bus_id + i
        buses.append(bus)
        lines.append(f"{bus},'RECIP_{i+1:02d}',  {config.get('voltage_kv', 13.8):.3f},1,   1,   1,   1,1.01000,   0.0000,1.10000,0.90000,1.10000,0.90000")
    
    for i in range(config.get('n_turbine', 0)):
        bus = bus_id + 20 + i
        buses.append(bus)
        lines.append(f"{bus},'GT_{i+1:02d}    ',  {config.get('voltage_kv', 13.8):.3f},1,   1,   1,   1,1.02500,   0.0000,1.10000,0.90000,1.10000,0.90000")
    
    # BESS bus
    if config.get('bess_mw', 0) > 0:
        bus = bus_id + 40
        buses.append(bus)
        lines.append(f"{bus},'BESS_01 ',  {config.get('voltage_kv', 13.8):.3f},1,   1,   1,   1,1.00500,   0.0000,1.10000,0.90000,1.10000,0.90000")
    
    # Main bus (swing)
    main_bus = 200
    buses.append(main_bus)
    lines.append(f"{main_bus},'MAIN_BUS',  {config.get('voltage_kv', 13.8):.3f},3,   1,   1,   1,1.00000,   0.0000,1.10000,0.90000,1.10000,0.90000")
    
    lines.append("0 / END OF BUS DATA")
    
    # Load data section
    lines.append("")
    lines.append("/ LOAD DATA")
    lines.append("/ I, ID, STATUS, AREA, ZONE, PL, QL, IP, IQ, YP, YQ, OWNER, SCALE, INTRPT, DESSION")
    peak_load = config.get('peak_load_mw', 200)
    lines.append(f"{main_bus},'1 ',1,   1,   1,   {peak_load:.2f},    {peak_load*0.33:.2f},   0.00,   0.00,   0.00,   0.00,   1,1,0,1")
    lines.append("0 / END OF LOAD DATA")
    
    # Fixed shunt data
    lines.append("")
    lines.append("/ FIXED SHUNT DATA")
    lines.append("0 / END OF FIXED SHUNT DATA")
    
    # Generator data section
    lines.append("")
    lines.append("/ GENERATOR DATA")
    lines.append("/ I, ID, PG, QG, QT, QB, VS, IREG, MBASE, ZR, ZX, RT, XT, GTAP, STAT, RMPCT, PT, PB")
    
    for i in range(config.get('n_recip', 0)):
        bus = bus_id + i
        mw = config.get('recip_mw_each', 18.3)
        mva = mw / 0.85
        lines.append(f"{bus},'1 ',   {mw:.2f},    0.00,  {mva*0.5:.2f}, {-mva*0.3:.2f},1.0100,     0,  {mva:.2f}, 0.00000, 1.00000, 0.00000, 0.00000,1.00000,1,  100.0,  {mw:.2f},    0.00,1,1.0000,0,1.0000,0,1.0000,0,1.0000,0")
    
    for i in range(config.get('n_turbine', 0)):
        bus = bus_id + 20 + i
        mw = config.get('turbine_mw_each', 50.0)
        mva = mw / 0.85
        lines.append(f"{bus},'1 ',   {mw:.2f},    0.00,  {mva*0.5:.2f}, {-mva*0.3:.2f},1.0250,     0,  {mva:.2f}, 0.00000, 1.00000, 0.00000, 0.00000,1.00000,1,  100.0,  {mw:.2f},    0.00,1,1.0000,0,1.0000,0,1.0000,0,1.0000,0")
    
    lines.append("0 / END OF GENERATOR DATA")
    
    # Branch data section
    lines.append("")
    lines.append("/ BRANCH DATA")
    lines.append("/ I, J, CKT, R, X, B, RATEA, RATEB, RATEC, GI, BI, GJ, BJ, ST, MET, LEN, O1, F1")
    
    # Connect all generators to main bus
    for i in range(config.get('n_recip', 0)):
        bus = bus_id + i
        lines.append(f"{bus},  {main_bus},'1 ', 0.00100, 0.01000, 0.00000,  100.0,  100.0,  100.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.10,1,1.0000")
    
    for i in range(config.get('n_turbine', 0)):
        bus = bus_id + 20 + i
        lines.append(f"{bus},  {main_bus},'1 ', 0.00050, 0.00800, 0.00000,  150.0,  150.0,  150.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.05,1,1.0000")
    
    if config.get('bess_mw', 0) > 0:
        bus = bus_id + 40
        lines.append(f"{bus},  {main_bus},'1 ', 0.00200, 0.01500, 0.00000,   50.0,   50.0,   50.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.02,1,1.0000")
    
    lines.append("0 / END OF BRANCH DATA")
    
    # System switching device data
    lines.append("")
    lines.append("/ SYSTEM SWITCHING DEVICE DATA")
    lines.append("0 / END OF SYSTEM SWITCHING DEVICE DATA")
    
    # Transformer data
    lines.append("")
    lines.append("/ TRANSFORMER DATA")
    lines.append("0 / END OF TRANSFORMER DATA")
    
    # Area data
    lines.append("")
    lines.append("/ AREA DATA")
    lines.append(f"   1,  {main_bus},   0.000,   10.00,'DATACENTER'")
    lines.append("0 / END OF AREA DATA")
    
    # Two-terminal DC data
    lines.append("")
    lines.append("/ TWO-TERMINAL DC DATA")
    lines.append("0 / END OF TWO-TERMINAL DC DATA")
    
    # VSC DC line data
    lines.append("")
    lines.append("/ VSC DC LINE DATA")
    lines.append("0 / END OF VSC DC LINE DATA")
    
    # Switched shunt data
    lines.append("")
    lines.append("/ SWITCHED SHUNT DATA")
    lines.append("0 / END OF SWITCHED SHUNT DATA")
    
    # Impedance correction data
    lines.append("")
    lines.append("/ IMPEDANCE CORRECTION DATA")
    lines.append("0 / END OF IMPEDANCE CORRECTION DATA")
    
    # Multi-terminal DC data
    lines.append("")
    lines.append("/ MULTI-TERMINAL DC DATA")
    lines.append("0 / END OF MULTI-TERMINAL DC DATA")
    
    # Multi-section line data
    lines.append("")
    lines.append("/ MULTI-SECTION LINE DATA")
    lines.append("0 / END OF MULTI-SECTION LINE DATA")
    
    # Zone data
    lines.append("")
    lines.append("/ ZONE DATA")
    lines.append("   1,'ZONE_1'")
    lines.append("0 / END OF ZONE DATA")
    
    # Inter-area transfer data
    lines.append("")
    lines.append("/ INTER-AREA TRANSFER DATA")
    lines.append("0 / END OF INTER-AREA TRANSFER DATA")
    
    # Owner data
    lines.append("")
    lines.append("/ OWNER DATA")
    lines.append("   1,'OWNER_1'")
    lines.append("0 / END OF OWNER DATA")
    
    # FACTS device data
    lines.append("")
    lines.append("/ FACTS DEVICE DATA")
    lines.append("0 / END OF FACTS DEVICE DATA")
    
    # End of file
    lines.append("")
    lines.append("Q")
    
    return '\n'.join(lines)


def generate_sample_psse_results_df() -> pd.DataFrame:
    """Generate sample PSS/e power flow results (what would be imported)."""
    return pd.DataFrame([
        {'BUS': 100, 'NAME': 'RECIP_01', 'BASKV': 13.8, 'VM_PU': 1.010, 'VA_DEG': 2.3, 
         'P_GEN_MW': 18.3, 'Q_GEN_MVAR': 9.8, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 101, 'NAME': 'RECIP_02', 'BASKV': 13.8, 'VM_PU': 1.008, 'VA_DEG': 2.1, 
         'P_GEN_MW': 18.3, 'Q_GEN_MVAR': 9.6, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 120, 'NAME': 'GT_01', 'BASKV': 13.8, 'VM_PU': 1.025, 'VA_DEG': 0.0, 
         'P_GEN_MW': 50.0, 'Q_GEN_MVAR': 25.0, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 121, 'NAME': 'GT_02', 'BASKV': 13.8, 'VM_PU': 1.020, 'VA_DEG': -0.5, 
         'P_GEN_MW': 50.0, 'Q_GEN_MVAR': 24.5, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 140, 'NAME': 'BESS_01', 'BASKV': 13.8, 'VM_PU': 1.005, 'VA_DEG': 1.2, 
         'P_GEN_MW': 0.0, 'Q_GEN_MVAR': 5.0, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 200, 'NAME': 'MAIN_BUS', 'BASKV': 13.8, 'VM_PU': 1.000, 'VA_DEG': 0.0, 
         'P_GEN_MW': 0.0, 'Q_GEN_MVAR': 0.0, 'P_LOAD_MW': 200.0, 'Q_LOAD_MVAR': 66.0},
    ])


def generate_sample_windchill_component_df(config: Dict) -> pd.DataFrame:
    """Generate sample Windchill RAM component dataframe."""
    rows = []
    
    # Reciprocating engines
    for i in range(config.get('n_recip', 0)):
        rows.append({
            'Component_ID': f'GEN_RECIP_{i+1:02d}',
            'Component_Name': f'Recip Engine {i+1}',
            'Component_Type': 'RECIPROCATING_ENGINE',
            'Subsystem': 'Power Generation',
            'Redundancy_Group': 'THERMAL_GEN',
            'Capacity_MW': config.get('recip_mw_each', 18.3),
            'MTBF_Hours': 8760,
            'MTTR_Hours': 24,
            'Failure_Rate_Per_Hour': 1.14e-4,
            'Availability': 0.9973,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 8760,
            'Operating_Hours_Per_Year': 8000,
            'PM_Interval_Hours': 2000,
        })
    
    # Gas turbines
    for i in range(config.get('n_turbine', 0)):
        rows.append({
            'Component_ID': f'GEN_GT_{i+1:02d}',
            'Component_Name': f'Gas Turbine {i+1}',
            'Component_Type': 'GAS_TURBINE',
            'Subsystem': 'Power Generation',
            'Redundancy_Group': 'THERMAL_GEN',
            'Capacity_MW': config.get('turbine_mw_each', 50.0),
            'MTBF_Hours': 17520,
            'MTTR_Hours': 48,
            'Failure_Rate_Per_Hour': 5.71e-5,
            'Availability': 0.9973,
            'Distribution': 'Weibull',
            'Weibull_Beta': 1.5,
            'Weibull_Eta': 20000,
            'Operating_Hours_Per_Year': 6000,
            'PM_Interval_Hours': 4000,
        })
    
    # BESS
    if config.get('bess_mw', 0) > 0:
        rows.append({
            'Component_ID': 'BESS_01',
            'Component_Name': f"Battery Storage ({config.get('bess_mwh', 0):.0f} MWh)",
            'Component_Type': 'BATTERY_STORAGE',
            'Subsystem': 'Energy Storage',
            'Redundancy_Group': 'STORAGE',
            'Capacity_MW': config.get('bess_mw', 0),
            'MTBF_Hours': 43800,
            'MTTR_Hours': 8,
            'Failure_Rate_Per_Hour': 2.28e-5,
            'Availability': 0.9998,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 43800,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 8760,
        })
    
    # Supporting equipment
    rows.append({
        'Component_ID': 'XFMR_MAIN',
        'Component_Name': 'Main Step-Up Transformer',
        'Component_Type': 'TRANSFORMER',
        'Subsystem': 'Electrical Distribution',
        'Redundancy_Group': 'ELECTRICAL',
        'Capacity_MW': 250,
        'MTBF_Hours': 175200,
        'MTTR_Hours': 168,
        'Failure_Rate_Per_Hour': 5.71e-6,
        'Availability': 0.9990,
        'Distribution': 'Exponential',
        'Weibull_Beta': 1.0,
        'Weibull_Eta': 175200,
        'Operating_Hours_Per_Year': 8760,
        'PM_Interval_Hours': 17520,
    })
    
    rows.append({
        'Component_ID': 'SWGR_MAIN',
        'Component_Name': 'Main Switchgear',
        'Component_Type': 'SWITCHGEAR',
        'Subsystem': 'Electrical Distribution',
        'Redundancy_Group': 'ELECTRICAL',
        'Capacity_MW': 300,
        'MTBF_Hours': 87600,
        'MTTR_Hours': 24,
        'Failure_Rate_Per_Hour': 1.14e-5,
        'Availability': 0.9997,
        'Distribution': 'Exponential',
        'Weibull_Beta': 1.0,
        'Weibull_Eta': 87600,
        'Operating_Hours_Per_Year': 8760,
        'PM_Interval_Hours': 8760,
    })
    
    return pd.DataFrame(rows)


def generate_sample_windchill_rbd_df(config: Dict) -> pd.DataFrame:
    """Generate sample Windchill RBD structure dataframe."""
    rows = []
    
    # Thermal generation block (parallel - N of M required)
    n_thermal = config.get('n_recip', 0) + config.get('n_turbine', 0)
    thermal_components = [f"GEN_RECIP_{i+1:02d}" for i in range(config.get('n_recip', 0))]
    thermal_components += [f"GEN_GT_{i+1:02d}" for i in range(config.get('n_turbine', 0))]
    
    rows.append({
        'Block_ID': 'THERMAL_GEN',
        'Block_Name': 'Thermal Generation Block',
        'Block_Type': 'PARALLEL_K_OF_N',
        'Parent_Block': 'SYSTEM',
        'Components': ','.join(thermal_components),
        'K_Required': max(1, n_thermal - 1),  # N-1 redundancy
        'N_Total': n_thermal,
        'Description': f'N-1 redundancy: {n_thermal-1} of {n_thermal} units required',
    })
    
    # Storage block (if present)
    if config.get('bess_mw', 0) > 0:
        rows.append({
            'Block_ID': 'STORAGE',
            'Block_Name': 'Energy Storage Block',
            'Block_Type': 'SERIES',
            'Parent_Block': 'SYSTEM',
            'Components': 'BESS_01',
            'K_Required': 1,
            'N_Total': 1,
            'Description': 'Single BESS unit - optional for availability',
        })
    
    # Electrical distribution (series)
    rows.append({
        'Block_ID': 'ELECTRICAL',
        'Block_Name': 'Electrical Distribution Block',
        'Block_Type': 'SERIES',
        'Parent_Block': 'SYSTEM',
        'Components': 'XFMR_MAIN,SWGR_MAIN',
        'K_Required': 2,
        'N_Total': 2,
        'Description': 'Series configuration - both required',
    })
    
    # System level
    rows.append({
        'Block_ID': 'SYSTEM',
        'Block_Name': 'Complete Power System',
        'Block_Type': 'SERIES',
        'Parent_Block': '',
        'Components': 'THERMAL_GEN,ELECTRICAL',
        'K_Required': 2,
        'N_Total': 2,
        'Description': 'Top-level system - requires generation AND distribution',
    })
    
    return pd.DataFrame(rows)


def generate_sample_windchill_results_df() -> pd.DataFrame:
    """Generate sample Windchill RAM analysis results (what would be imported)."""
    return pd.DataFrame([
        {'Block_ID': 'THERMAL_GEN', 'Block_Name': 'Thermal Generation Block', 
         'Availability': 0.99987, 'MTBF_Hours': 76923, 'MTTR_Hours': 10,
         'Annual_Downtime_Hours': 1.14, 'Failures_Per_Year': 0.114},
        {'Block_ID': 'STORAGE', 'Block_Name': 'Energy Storage Block', 
         'Availability': 0.99982, 'MTBF_Hours': 43800, 'MTTR_Hours': 8,
         'Annual_Downtime_Hours': 1.58, 'Failures_Per_Year': 0.200},
        {'Block_ID': 'ELECTRICAL', 'Block_Name': 'Electrical Distribution Block', 
         'Availability': 0.99870, 'MTBF_Hours': 67308, 'MTTR_Hours': 88,
         'Annual_Downtime_Hours': 11.39, 'Failures_Per_Year': 0.130},
        {'Block_ID': 'SYSTEM', 'Block_Name': 'Complete Power System', 
         'Availability': 0.99857, 'MTBF_Hours': 61224, 'MTTR_Hours': 88,
         'Annual_Downtime_Hours': 12.53, 'Failures_Per_Year': 0.143},
    ])


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_single_line_diagram_svg(config: Dict) -> str:
    """Generate a simple single-line diagram as SVG."""
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    has_bess = config.get('bess_mw', 0) > 0
    
    # SVG dimensions
    width = 800
    height = 500
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
    <style>
        .bus {{ stroke: #333; stroke-width: 3; }}
        .branch {{ stroke: #666; stroke-width: 2; }}
        .gen {{ fill: #4CAF50; stroke: #333; stroke-width: 2; }}
        .bess {{ fill: #2196F3; stroke: #333; stroke-width: 2; }}
        .load {{ fill: #f44336; stroke: #333; stroke-width: 2; }}
        .text {{ font-family: Arial; font-size: 12px; fill: #333; }}
        .title {{ font-family: Arial; font-size: 16px; font-weight: bold; fill: #333; }}
    </style>
    
    <!-- Title -->
    <text x="400" y="30" class="title" text-anchor="middle">{config.get('project_name', 'Single Line Diagram')}</text>
    <text x="400" y="50" class="text" text-anchor="middle">{config.get('peak_load_mw', 200):.0f} MW Peak Load | 13.8 kV</text>
    
    <!-- Main Bus -->
    <line x1="100" y1="250" x2="700" y2="250" class="bus"/>
    <text x="400" y="270" class="text" text-anchor="middle">MAIN BUS (13.8 kV)</text>
    '''
    
    # Recip engines (top left)
    recip_start_x = 120
    for i in range(min(n_recip, 8)):
        x = recip_start_x + i * 50
        svg += f'''
        <line x1="{x}" y1="250" x2="{x}" y2="150" class="branch"/>
        <circle cx="{x}" cy="130" r="20" class="gen"/>
        <text x="{x}" y="135" class="text" text-anchor="middle">G</text>
        <text x="{x}" y="100" class="text" text-anchor="middle">R{i+1}</text>
        '''
    
    # Gas turbines (top right)
    turbine_start_x = 550
    for i in range(min(n_turbine, 4)):
        x = turbine_start_x + i * 60
        svg += f'''
        <line x1="{x}" y1="250" x2="{x}" y2="150" class="branch"/>
        <circle cx="{x}" cy="130" r="25" class="gen"/>
        <text x="{x}" y="135" class="text" text-anchor="middle">G</text>
        <text x="{x}" y="95" class="text" text-anchor="middle">GT{i+1}</text>
        '''
    
    # BESS (bottom left)
    if has_bess:
        svg += f'''
        <line x1="200" y1="250" x2="200" y2="350" class="branch"/>
        <rect x="170" y="350" width="60" height="40" class="bess"/>
        <text x="200" y="375" class="text" text-anchor="middle">BESS</text>
        <text x="200" y="410" class="text" text-anchor="middle">{config.get('bess_mw', 0):.0f} MW</text>
        '''
    
    # Load (bottom right)
    svg += f'''
    <line x1="600" y1="250" x2="600" y2="350" class="branch"/>
    <polygon points="570,350 630,350 600,400" class="load"/>
    <text x="600" y="430" class="text" text-anchor="middle">DATACENTER</text>
    <text x="600" y="450" class="text" text-anchor="middle">{config.get('peak_load_mw', 200):.0f} MW</text>
    '''
    
    # Legend
    svg += f'''
    <rect x="50" y="430" width="20" height="20" class="gen"/>
    <text x="80" y="445" class="text">Generator</text>
    <rect x="180" y="430" width="20" height="20" class="bess"/>
    <text x="210" y="445" class="text">BESS</text>
    <polygon points="300,430 320,430 310,450" class="load"/>
    <text x="330" y="445" class="text">Load</text>
    '''
    
    svg += '</svg>'
    return svg


def create_rbd_diagram_svg(config: Dict) -> str:
    """Generate a reliability block diagram as SVG."""
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    has_bess = config.get('bess_mw', 0) > 0
    n_thermal = n_recip + n_turbine
    
    width = 900
    height = 400
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
    <style>
        .block {{ fill: #e3f2fd; stroke: #1976D2; stroke-width: 2; rx: 5; }}
        .parallel {{ fill: #e8f5e9; stroke: #388E3C; stroke-width: 2; rx: 5; }}
        .series {{ fill: #fff3e0; stroke: #F57C00; stroke-width: 2; rx: 5; }}
        .line {{ stroke: #333; stroke-width: 2; }}
        .arrow {{ fill: #333; }}
        .text {{ font-family: Arial; font-size: 11px; fill: #333; }}
        .title {{ font-family: Arial; font-size: 14px; font-weight: bold; fill: #333; }}
        .label {{ font-family: Arial; font-size: 10px; fill: #666; }}
    </style>
    
    <!-- Title -->
    <text x="450" y="25" class="title" text-anchor="middle">Reliability Block Diagram - {config.get('project_name', 'System')}</text>
    
    <!-- Input -->
    <text x="30" y="200" class="text">IN</text>
    <line x1="50" y1="195" x2="80" y2="195" class="line"/>
    <polygon points="80,190 90,195 80,200" class="arrow"/>
    '''
    
    # Thermal Generation Block (Parallel)
    svg += f'''
    <!-- Thermal Gen Block -->
    <rect x="100" y="80" width="300" height="230" class="parallel"/>
    <text x="250" y="100" class="title" text-anchor="middle">Thermal Generation</text>
    <text x="250" y="115" class="label" text-anchor="middle">(K of N Parallel: {n_thermal-1} of {n_thermal} required)</text>
    '''
    
    # Individual generators
    y_start = 130
    y_step = 30 if n_thermal <= 6 else 25
    
    for i in range(min(n_recip, 6)):
        y = y_start + i * y_step
        svg += f'''
        <rect x="120" y="{y}" width="120" height="22" class="block"/>
        <text x="180" y="{y+15}" class="text" text-anchor="middle">Recip {i+1} (18.3 MW)</text>
        '''
    
    for i in range(min(n_turbine, 3)):
        y = y_start + (n_recip + i) * y_step
        svg += f'''
        <rect x="120" y="{y}" width="120" height="22" class="block"/>
        <text x="180" y="{y+15}" class="text" text-anchor="middle">GT {i+1} (50 MW)</text>
        '''
    
    if n_thermal > 9:
        svg += f'''<text x="180" y="{y_start + 9 * y_step}" class="label" text-anchor="middle">... and {n_thermal - 9} more</text>'''
    
    # Connection from thermal block
    svg += '''
    <line x1="400" y1="195" x2="430" y2="195" class="line"/>
    <polygon points="430,190 440,195 430,200" class="arrow"/>
    '''
    
    # Electrical Distribution Block (Series)
    svg += f'''
    <!-- Electrical Block -->
    <rect x="450" y="120" width="200" height="150" class="series"/>
    <text x="550" y="145" class="title" text-anchor="middle">Electrical Distribution</text>
    <text x="550" y="160" class="label" text-anchor="middle">(Series: All Required)</text>
    
    <rect x="470" y="175" width="160" height="30" class="block"/>
    <text x="550" y="195" class="text" text-anchor="middle">Main Transformer</text>
    
    <line x1="550" y1="205" x2="550" y2="215" class="line"/>
    <polygon points="545,215 550,225 555,215" class="arrow"/>
    
    <rect x="470" y="225" width="160" height="30" class="block"/>
    <text x="550" y="245" class="text" text-anchor="middle">Main Switchgear</text>
    '''
    
    # Connection to output
    svg += '''
    <line x1="650" y1="195" x2="680" y2="195" class="line"/>
    <polygon points="680,190 690,195 680,200" class="arrow"/>
    '''
    
    # Output
    svg += f'''
    <!-- Output -->
    <rect x="700" y="165" width="100" height="60" class="block"/>
    <text x="750" y="190" class="text" text-anchor="middle">DATACENTER</text>
    <text x="750" y="210" class="text" text-anchor="middle">{config.get('peak_load_mw', 200):.0f} MW</text>
    
    <line x1="800" y1="195" x2="830" y2="195" class="line"/>
    <text x="850" y="200" class="text">OUT</text>
    '''
    
    # Legend
    svg += '''
    <!-- Legend -->
    <rect x="100" y="340" width="80" height="25" class="parallel"/>
    <text x="190" y="357" class="text">Parallel (K of N)</text>
    
    <rect x="300" y="340" width="80" height="25" class="series"/>
    <text x="390" y="357" class="text">Series (All Required)</text>
    
    <rect x="500" y="340" width="80" height="25" class="block"/>
    <text x="590" y="357" class="text">Component Block</text>
    '''
    
    svg += '</svg>'
    return svg


def create_scenario_matrix_chart(scenarios_df: pd.DataFrame) -> str:
    """Create an SVG visualization of scenario matrix."""
    width = 800
    height = 400
    
    # Count scenarios by type
    type_counts = scenarios_df['Type'].value_counts().to_dict()
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
    <style>
        .bar-normal {{ fill: #4CAF50; }}
        .bar-n1 {{ fill: #FFC107; }}
        .bar-n2 {{ fill: #f44336; }}
        .text {{ font-family: Arial; font-size: 12px; fill: #333; }}
        .title {{ font-family: Arial; font-size: 16px; font-weight: bold; fill: #333; }}
        .axis {{ stroke: #333; stroke-width: 1; }}
    </style>
    
    <text x="400" y="30" class="title" text-anchor="middle">Scenarios by Type</text>
    '''
    
    # Simple bar chart
    bar_width = 100
    bar_spacing = 150
    max_count = max(type_counts.values()) if type_counts else 1
    scale = 250 / max_count
    
    x = 150
    for scenario_type, count in type_counts.items():
        bar_height = count * scale
        bar_class = 'bar-normal' if 'Normal' in scenario_type else ('bar-n1' if 'N-1' in scenario_type else 'bar-n2')
        
        svg += f'''
        <rect x="{x}" y="{300 - bar_height}" width="{bar_width}" height="{bar_height}" class="{bar_class}"/>
        <text x="{x + bar_width/2}" y="320" class="text" text-anchor="middle">{scenario_type}</text>
        <text x="{x + bar_width/2}" y="{290 - bar_height}" class="text" text-anchor="middle">{count}</text>
        '''
        x += bar_spacing
    
    # Axis
    svg += f'''
    <line x1="100" y1="300" x2="700" y2="300" class="axis"/>
    '''
    
    svg += '</svg>'
    return svg


# =============================================================================
# EXCEL EXPORT FUNCTIONS
# =============================================================================

def export_full_etap_package(config: Dict) -> BytesIO:
    """Generate complete ETAP import package."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Equipment sheet
        equip_df = generate_sample_etap_equipment_df(config)
        equip_df.to_excel(writer, sheet_name='Equipment', index=False)
        
        # Scenarios sheet
        scenarios_df = generate_sample_etap_scenarios_df(config)
        scenarios_df.to_excel(writer, sheet_name='Scenarios', index=False)
        
        # Bus data sheet
        buses = equip_df['Bus_ID'].unique().tolist()
        bus_df = pd.DataFrame([{
            'Bus_ID': bus,
            'Bus_Name': bus,
            'Nominal_kV': 13.8,
            'Bus_Type': 'Generator' if 'RECIP' in bus or 'GT' in bus else 'Load',
        } for bus in buses])
        bus_df.to_excel(writer, sheet_name='Bus Data', index=False)
        
        # Instructions sheet
        instructions = pd.DataFrame([
            {'Step': 1, 'Instruction': 'Open ETAP and go to File → Import → DataX'},
            {'Step': 2, 'Instruction': 'Select the Equipment sheet and map columns'},
            {'Step': 3, 'Instruction': 'Import Bus Data sheet for bus definitions'},
            {'Step': 4, 'Instruction': 'Create study cases using Scenarios sheet as reference'},
            {'Step': 5, 'Instruction': 'Run Load Flow and Short Circuit studies'},
            {'Step': 6, 'Instruction': 'Export results via Results Analyzer → Excel'},
        ])
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    return output


def export_full_windchill_package(config: Dict) -> BytesIO:
    """Generate complete Windchill RAM import package."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Component data
        comp_df = generate_sample_windchill_component_df(config)
        comp_df.to_excel(writer, sheet_name='Component Data', index=False)
        
        # RBD structure
        rbd_df = generate_sample_windchill_rbd_df(config)
        rbd_df.to_excel(writer, sheet_name='RBD Structure', index=False)
        
        # FMEA template
        fmea_rows = []
        for _, row in comp_df.iterrows():
            fmea_rows.extend([
                {
                    'Component_ID': row['Component_ID'],
                    'Component_Name': row['Component_Name'],
                    'Failure_Mode': 'Fails to Start',
                    'Failure_Cause': 'Control system failure',
                    'Local_Effect': 'Unit unavailable',
                    'System_Effect': 'Reduced capacity',
                    'Severity': 'Medium',
                    'Occurrence': 'Low',
                    'Detection': 'SCADA alarm',
                    'RPN': 12,
                    'Mitigation': 'Redundant controls',
                },
                {
                    'Component_ID': row['Component_ID'],
                    'Component_Name': row['Component_Name'],
                    'Failure_Mode': 'Fails During Operation',
                    'Failure_Cause': 'Mechanical wear',
                    'Local_Effect': 'Forced outage',
                    'System_Effect': 'Reduced capacity',
                    'Severity': 'High',
                    'Occurrence': 'Medium',
                    'Detection': 'Vibration monitoring',
                    'RPN': 36,
                    'Mitigation': 'Predictive maintenance',
                },
            ])
        fmea_df = pd.DataFrame(fmea_rows)
        fmea_df.to_excel(writer, sheet_name='FMEA', index=False)
        
        # Requirements
        req_df = pd.DataFrame([
            {'Req_ID': 'REQ-001', 'Requirement': 'System Availability', 'Target': '≥ 99.95%', 'Unit': '%', 'Priority': 'Critical'},
            {'Req_ID': 'REQ-002', 'Requirement': 'Annual Downtime', 'Target': '≤ 4.38 hours', 'Unit': 'hours/year', 'Priority': 'Critical'},
            {'Req_ID': 'REQ-003', 'Requirement': 'N-1 Redundancy', 'Target': 'Yes', 'Unit': 'Boolean', 'Priority': 'Critical'},
            {'Req_ID': 'REQ-004', 'Requirement': 'MTBF System', 'Target': '≥ 8760 hours', 'Unit': 'hours', 'Priority': 'High'},
        ])
        req_df.to_excel(writer, sheet_name='Requirements', index=False)
        
        # Instructions
        instructions = pd.DataFrame([
            {'Step': 1, 'Instruction': 'Open Windchill Prediction or BlockSim'},
            {'Step': 2, 'Instruction': 'File → Import → Excel to load Component Data'},
            {'Step': 3, 'Instruction': 'Create RBD using structure from RBD Structure sheet'},
            {'Step': 4, 'Instruction': 'Define block relationships per K_Required and N_Total'},
            {'Step': 5, 'Instruction': 'Run availability simulation (Monte Carlo or analytical)'},
            {'Step': 6, 'Instruction': 'Export results to Excel for import back to bvNexus'},
        ])
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    return output


# =============================================================================
# STREAMLIT PAGE
# =============================================================================

def render_integration_export_page():
    """Render the enhanced Integration Export page."""
    
    st.title("🔗 Integration Export Hub")
    st.markdown("""
    Generate input files for external validation tools with **visual previews** 
    and **sample file structures**. Export optimization results to ETAP, PSS/e, 
    and Windchill RAM for detailed engineering analysis.
    """)
    
    # Sidebar configuration
    st.sidebar.header("📋 Project Configuration")
    
    use_sample = st.sidebar.checkbox("Use Sample Configuration", value=True)
    
    if use_sample:
        config = generate_sample_equipment_config()
        st.sidebar.success("✅ Using Dallas Hyperscale DC sample")
    else:
        st.sidebar.subheader("Custom Configuration")
        config = {
            'project_name': st.sidebar.text_input("Project Name", "My Datacenter"),
            'peak_load_mw': st.sidebar.number_input("Peak Load (MW)", 10.0, 2000.0, 200.0),
            'n_recip': st.sidebar.number_input("Reciprocating Engines", 0, 50, 8),
            'recip_mw_each': st.sidebar.number_input("Recip Size (MW)", 1.0, 50.0, 18.3),
            'n_turbine': st.sidebar.number_input("Gas Turbines", 0, 20, 2),
            'turbine_mw_each': st.sidebar.number_input("GT Size (MW)", 10.0, 200.0, 50.0),
            'bess_mw': st.sidebar.number_input("BESS Power (MW)", 0.0, 500.0, 30.0),
            'bess_mwh': st.sidebar.number_input("BESS Energy (MWh)", 0.0, 2000.0, 120.0),
            'voltage_kv': 13.8,
            'system_mva_base': 100.0,
        }
        config['recip_mw'] = config['n_recip'] * config['recip_mw_each']
        config['turbine_mw'] = config['n_turbine'] * config['turbine_mw_each']
    
    # Main tabs
    tab_overview, tab_etap, tab_psse, tab_ram, tab_samples = st.tabs([
        "📊 System Overview", "⚡ ETAP Export", "🔌 PSS/e Export", 
        "📈 Windchill RAM", "📁 Sample Files"
    ])
    
    with tab_overview:
        render_system_overview(config)
    
    with tab_etap:
        render_etap_export(config)
    
    with tab_psse:
        render_psse_export(config)
    
    with tab_ram:
        render_ram_export(config)
    
    with tab_samples:
        render_sample_files(config)


def render_system_overview(config: Dict):
    """Render system overview with visual diagrams."""
    st.header("📊 System Overview")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Single Line Diagram")
        svg = create_single_line_diagram_svg(config)
        st.image(svg)
    
    with col2:
        st.subheader("Configuration Summary")
        st.metric("Peak Load", f"{config.get('peak_load_mw', 0):.0f} MW")
        
        total_gen = (config.get('n_recip', 0) * config.get('recip_mw_each', 0) + 
                    config.get('n_turbine', 0) * config.get('turbine_mw_each', 0))
        st.metric("Total Generation", f"{total_gen:.0f} MW")
        
        reserve = total_gen - config.get('peak_load_mw', 0)
        st.metric("Reserve Capacity", f"{reserve:.0f} MW", 
                 delta=f"{reserve/config.get('peak_load_mw', 1)*100:.1f}%")
        
        st.metric("BESS", f"{config.get('bess_mw', 0):.0f} MW / {config.get('bess_mwh', 0):.0f} MWh")
    
    st.divider()
    
    # Equipment summary table
    st.subheader("Equipment Summary")
    summary_df = pd.DataFrame([
        {'Equipment': 'Reciprocating Engines', 'Count': config.get('n_recip', 0), 
         'Unit Size (MW)': config.get('recip_mw_each', 0), 
         'Total (MW)': config.get('n_recip', 0) * config.get('recip_mw_each', 0)},
        {'Equipment': 'Gas Turbines', 'Count': config.get('n_turbine', 0), 
         'Unit Size (MW)': config.get('turbine_mw_each', 0), 
         'Total (MW)': config.get('n_turbine', 0) * config.get('turbine_mw_each', 0)},
        {'Equipment': 'BESS', 'Count': 1 if config.get('bess_mw', 0) > 0 else 0, 
         'Unit Size (MW)': config.get('bess_mw', 0), 
         'Total (MW)': config.get('bess_mw', 0)},
    ])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # Scenario overview
    st.subheader("Scenarios to Generate")
    scenarios_df = generate_sample_etap_scenarios_df(config)
    
    col1, col2 = st.columns(2)
    with col1:
        type_counts = scenarios_df['Type'].value_counts()
        st.bar_chart(type_counts)
    
    with col2:
        st.dataframe(
            scenarios_df[['Scenario_ID', 'Name', 'Type', 'Load_MW']].head(10),
            use_container_width=True,
            hide_index=True
        )


def render_etap_export(config: Dict):
    """Render ETAP export section with previews."""
    st.header("⚡ ETAP Export")
    
    st.markdown("""
    Generate Excel files for ETAP DataX import. These files can be directly 
    imported into ETAP for load flow, short circuit, and arc flash studies.
    """)
    
    # Preview tabs
    preview_tab, results_tab, download_tab = st.tabs([
        "📋 Preview Export Data", "📊 Expected Results Format", "⬇️ Download Files"
    ])
    
    with preview_tab:
        st.subheader("Equipment Data Preview")
        equip_df = generate_sample_etap_equipment_df(config)
        st.dataframe(equip_df, use_container_width=True, hide_index=True)
        
        st.subheader("Scenarios Preview")
        scenarios_df = generate_sample_etap_scenarios_df(config)
        st.dataframe(scenarios_df, use_container_width=True, hide_index=True)
    
    with results_tab:
        st.subheader("Load Flow Results Format")
        st.markdown("After running ETAP load flow, export results in this format:")
        lf_results = generate_sample_etap_loadflow_results_df()
        st.dataframe(lf_results, use_container_width=True, hide_index=True)
        
        st.subheader("Short Circuit Results Format")
        sc_results = generate_sample_etap_shortcircuit_results_df()
        st.dataframe(sc_results, use_container_width=True, hide_index=True)
        
        st.info("💡 Export these formats from ETAP Results Analyzer for import back to bvNexus")
    
    with download_tab:
        st.subheader("Download ETAP Package")
        
        if st.button("📦 Generate Complete ETAP Package", key="gen_etap"):
            excel_buffer = export_full_etap_package(config)
            st.download_button(
                label="⬇️ Download ETAP_Import_Package.xlsx",
                data=excel_buffer,
                file_name=f"bvNexus_ETAP_Package_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("✅ Package generated with Equipment, Scenarios, Bus Data, and Instructions!")


def render_psse_export(config: Dict):
    """Render PSS/e export section with previews."""
    st.header("🔌 PSS/e Export")
    
    st.markdown("""
    Generate RAW format files for PSS/e power flow and stability analysis.
    Use for grid interconnection studies and dynamic simulations.
    """)
    
    preview_tab, format_tab, download_tab = st.tabs([
        "📋 Preview RAW File", "📊 Results Format", "⬇️ Download Files"
    ])
    
    with preview_tab:
        st.subheader("PSS/e RAW File Preview")
        raw_content = generate_sample_psse_raw(config)
        
        # Show first ~50 lines
        lines = raw_content.split('\n')
        preview_lines = '\n'.join(lines[:60])
        st.code(preview_lines + "\n... (truncated)", language='text')
        
        st.subheader("File Structure Explanation")
        st.markdown("""
        | Section | Description |
        |---------|-------------|
        | Header (3 lines) | Case ID, system MVA base, title |
        | BUS DATA | Bus numbers, names, voltage levels, types |
        | LOAD DATA | Load MW/MVAR at each bus |
        | GENERATOR DATA | Generator ratings, setpoints, impedances |
        | BRANCH DATA | Lines connecting buses (R, X, ratings) |
        | AREA DATA | Control area definitions |
        """)
    
    with format_tab:
        st.subheader("Power Flow Results Format")
        st.markdown("After running PSS/e, export results via `dyntools.csvout()` or API extraction:")
        pf_results = generate_sample_psse_results_df()
        st.dataframe(pf_results, use_container_width=True, hide_index=True)
        
        st.code("""
# Python code to extract PSS/e results
import psspy
import csv

# After running power flow
ierr, bus_data = psspy.abusreal(-1, 1, ['PU', 'ANGLED'])
ierr, gen_data = psspy.agenbusreal(-1, 1, ['PGEN', 'QGEN'])

# Export to CSV
with open('psse_results.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['BUS', 'VM_PU', 'VA_DEG', 'P_GEN', 'Q_GEN'])
    # ... write data
        """, language='python')
    
    with download_tab:
        st.subheader("Download PSS/e Files")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generate RAW File", key="gen_raw"):
                raw_content = generate_sample_psse_raw(config)
                st.download_button(
                    label="⬇️ Download Network.raw",
                    data=raw_content,
                    file_name=f"bvNexus_PSSe_{datetime.now().strftime('%Y%m%d_%H%M')}.raw",
                    mime="text/plain",
                )
        
        with col2:
            if st.button("📋 Generate Scenarios CSV", key="gen_psse_scen"):
                scenarios_df = generate_sample_etap_scenarios_df(config)
                csv_content = scenarios_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Scenarios.csv",
                    data=csv_content,
                    file_name=f"bvNexus_PSSe_Scenarios_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                )


def render_ram_export(config: Dict):
    """Render Windchill RAM export section with previews."""
    st.header("📈 Windchill RAM Export")
    
    st.markdown("""
    Generate Excel files for Windchill (ReliaSoft) reliability analysis.
    Includes component data, RBD structure, FMEA templates, and requirements.
    """)
    
    # Show RBD diagram
    st.subheader("Reliability Block Diagram")
    rbd_svg = create_rbd_diagram_svg(config)
    st.image(rbd_svg)
    
    preview_tab, results_tab, download_tab = st.tabs([
        "📋 Preview Export Data", "📊 Results Format", "⬇️ Download Files"
    ])
    
    with preview_tab:
        st.subheader("Component Data")
        comp_df = generate_sample_windchill_component_df(config)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        
        st.subheader("RBD Structure")
        rbd_df = generate_sample_windchill_rbd_df(config)
        st.dataframe(rbd_df, use_container_width=True, hide_index=True)
    
    with results_tab:
        st.subheader("RAM Analysis Results Format")
        st.markdown("After running Windchill simulation, export results in this format:")
        ram_results = generate_sample_windchill_results_df()
        st.dataframe(ram_results, use_container_width=True, hide_index=True)
        
        st.subheader("Key Metrics to Extract")
        st.markdown("""
        | Metric | Target | Unit |
        |--------|--------|------|
        | System Availability | ≥ 99.95% | % |
        | Annual Downtime | ≤ 4.38 hours | hours/year |
        | System MTBF | ≥ 8,760 hours | hours |
        | System MTTR | ≤ 24 hours | hours |
        """)
    
    with download_tab:
        st.subheader("Download Windchill Package")
        
        target_avail = st.slider("Target Availability", 0.990, 0.99999, 0.9995, format="%.5f")
        st.metric("Max Annual Downtime", f"{(1-target_avail)*8760:.2f} hours")
        
        if st.button("📦 Generate Complete RAM Package", key="gen_ram"):
            excel_buffer = export_full_windchill_package(config)
            st.download_button(
                label="⬇️ Download Windchill_RAM_Package.xlsx",
                data=excel_buffer,
                file_name=f"bvNexus_Windchill_RAM_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.success("✅ Package generated with Component Data, RBD, FMEA, Requirements!")


def render_sample_files(config: Dict):
    """Render sample file structures for reference."""
    st.header("📁 Sample File Structures")
    
    st.markdown("""
    Reference file structures showing the expected format for each integration tool.
    Use these as templates when preparing manual exports or validating automated outputs.
    """)
    
    tool_tab = st.selectbox(
        "Select Tool",
        ["ETAP", "PSS/e", "Windchill RAM"]
    )
    
    if tool_tab == "ETAP":
        st.subheader("ETAP File Structure")
        
        st.markdown("### Equipment Import (Excel → DataX)")
        st.code("""
# ETAP Equipment Import Structure
# File: ETAP_Equipment.xlsx

Sheet: "Synchronous Generators"
| ID           | Name           | Bus_ID  | Rated_kV | Rated_MW | Rated_MVA | Rated_PF | Xd_pu | Xd'_pu | Xd''_pu | H_sec |
|--------------|----------------|---------|----------|----------|-----------|----------|-------|--------|---------|-------|
| GEN_RECIP_01 | Recip Engine 1 | BUS_100 | 13.8     | 18.3     | 21.5      | 0.85     | 1.80  | 0.25   | 0.18    | 1.5   |
| GEN_GT_01    | Gas Turbine 1  | BUS_120 | 13.8     | 50.0     | 58.8      | 0.85     | 1.50  | 0.22   | 0.15    | 3.0   |

Sheet: "Load Data"
| ID      | Name       | Bus_ID  | Rated_kV | P_MW  | Q_MVAR | PF   | Type     |
|---------|------------|---------|----------|-------|--------|------|----------|
| LOAD_DC | Datacenter | BUS_200 | 13.8     | 200.0 | 66.0   | 0.95 | Constant |
        """, language='text')
        
        st.markdown("### Study Results Export (Results Analyzer → Excel)")
        st.code("""
# ETAP Load Flow Results Export
# File: LF_Results.xlsx

| Bus_ID  | Bus_Name    | Voltage_kV | Voltage_pu | Angle_deg | P_MW   | Q_MVAR | Loading_pct |
|---------|-------------|------------|------------|-----------|--------|--------|-------------|
| BUS_100 | RECIP_1_BUS | 13.8       | 1.012      | 2.3       | 18.3   | 9.8    | 72.5        |
| BUS_120 | GT_1_BUS    | 13.8       | 1.025      | 0.0       | 50.0   | 25.0   | 85.0        |
| BUS_200 | MAIN_BUS    | 13.8       | 1.000      | 0.0       | -200.0 | -65.0  | 95.2        |
        """, language='text')
    
    elif tool_tab == "PSS/e":
        st.subheader("PSS/e File Structure")
        
        st.markdown("### RAW File Format (v33/34/35)")
        st.code("""
0,   100.00     / PSS/E-35    Fri, Dec 27 2024  12:00
Dallas Hyperscale DC - Power Flow Base Case
Behind-the-Meter Datacenter Generation System

/ BUS DATA
/ I, 'NAME', BASKV, IDE, AREA, ZONE, OWNER, VM, VA
100,'RECIP_01',  13.800,1,   1,   1,   1,1.01000,   0.0000
120,'GT_01   ',  13.800,1,   1,   1,   1,1.02500,   0.0000
200,'MAIN_BUS',  13.800,3,   1,   1,   1,1.00000,   0.0000
0 / END OF BUS DATA

/ LOAD DATA
/ I, ID, STATUS, AREA, ZONE, PL, QL
200,'1 ',1,   1,   1,   200.00,    66.00
0 / END OF LOAD DATA

/ GENERATOR DATA
/ I, ID, PG, QG, QT, QB, VS, IREG, MBASE
100,'1 ',   18.30,    0.00,  10.75, -6.45,1.0100,     0,  21.53
120,'1 ',   50.00,    0.00,  29.41,-17.65,1.0250,     0,  58.82
0 / END OF GENERATOR DATA

/ BRANCH DATA
/ I, J, CKT, R, X, B, RATEA, RATEB, RATEC
100,  200,'1 ', 0.00100, 0.01000, 0.00000,  100.0,  100.0,  100.0
120,  200,'1 ', 0.00050, 0.00800, 0.00000,  150.0,  150.0,  150.0
0 / END OF BRANCH DATA

Q
        """, language='text')
        
        st.markdown("### Results CSV Format")
        st.code("""
# PSS/e Power Flow Results (extracted via dyntools or API)
# File: PSSE_Results.csv

BUS,NAME,BASKV,VM_PU,VA_DEG,P_GEN_MW,Q_GEN_MVAR,P_LOAD_MW,Q_LOAD_MVAR
100,RECIP_01,13.8,1.010,2.3,18.3,9.8,0.0,0.0
101,RECIP_02,13.8,1.008,2.1,18.3,9.6,0.0,0.0
120,GT_01,13.8,1.025,0.0,50.0,25.0,0.0,0.0
200,MAIN_BUS,13.8,1.000,0.0,0.0,0.0,200.0,66.0
        """, language='text')
    
    else:  # Windchill RAM
        st.subheader("Windchill RAM File Structure")
        
        st.markdown("### Component Data (Excel Import)")
        st.code("""
# Windchill Component Data Import
# File: RAM_Component_Data.xlsx

Sheet: "Component Data"
| Component_ID  | Component_Name   | Type              | MTBF_Hours | MTTR_Hours | Failure_Rate | Distribution | Weibull_Beta |
|---------------|------------------|-------------------|------------|------------|--------------|--------------|--------------|
| GEN_RECIP_01  | Recip Engine 1   | RECIPROCATING_ENG | 8760       | 24         | 1.14E-04     | Exponential  | 1.0          |
| GEN_GT_01     | Gas Turbine 1    | GAS_TURBINE       | 17520      | 48         | 5.71E-05     | Weibull      | 1.5          |
| BESS_01       | Battery Storage  | BATTERY_STORAGE   | 43800      | 8          | 2.28E-05     | Exponential  | 1.0          |
| XFMR_MAIN     | Main Transformer | TRANSFORMER       | 175200     | 168        | 5.71E-06     | Exponential  | 1.0          |
        """, language='text')
        
        st.markdown("### RBD Structure (Excel Import)")
        st.code("""
# Windchill RBD Structure
# File: RAM_RBD_Structure.xlsx

Sheet: "RBD Structure"
| Block_ID     | Block_Name              | Block_Type      | Components                        | K_Required | N_Total |
|--------------|-------------------------|-----------------|-----------------------------------|------------|---------|
| THERMAL_GEN  | Thermal Generation      | PARALLEL_K_OF_N | GEN_RECIP_01,...,GEN_GT_02        | 9          | 10      |
| ELECTRICAL   | Electrical Distribution | SERIES          | XFMR_MAIN,SWGR_MAIN               | 2          | 2       |
| SYSTEM       | Complete Power System   | SERIES          | THERMAL_GEN,ELECTRICAL            | 2          | 2       |
        """, language='text')
        
        st.markdown("### Analysis Results (Excel Export)")
        st.code("""
# Windchill RAM Analysis Results
# File: RAM_Results.xlsx

Sheet: "Block Results"
| Block_ID     | Block_Name              | Availability | MTBF_Hours | MTTR_Hours | Annual_Downtime_Hrs |
|--------------|-------------------------|--------------|------------|------------|---------------------|
| THERMAL_GEN  | Thermal Generation      | 0.99987      | 76923      | 10         | 1.14                |
| ELECTRICAL   | Electrical Distribution | 0.99870      | 67308      | 88         | 11.39               |
| SYSTEM       | Complete Power System   | 0.99857      | 61224      | 88         | 12.53               |

Sheet: "Summary"
| Metric              | Value    | Target   | Status |
|---------------------|----------|----------|--------|
| System Availability | 99.857%  | 99.950%  | FAIL   |
| Annual Downtime     | 12.53 hr | 4.38 hr  | FAIL   |
| System MTBF         | 61224 hr | 8760 hr  | PASS   |
        """, language='text')
    
    st.divider()
    
    # Download all samples as a ZIP
    st.subheader("📦 Download All Sample Files")
    
    if st.button("Generate Sample Files Package"):
        # Create ZIP with all samples
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # ETAP files
            etap_buffer = export_full_etap_package(config)
            zf.writestr('ETAP/bvNexus_ETAP_Package.xlsx', etap_buffer.getvalue())
            
            # PSS/e files
            raw_content = generate_sample_psse_raw(config)
            zf.writestr('PSSe/bvNexus_Network.raw', raw_content)
            
            scenarios_csv = generate_sample_etap_scenarios_df(config).to_csv(index=False)
            zf.writestr('PSSe/bvNexus_Scenarios.csv', scenarios_csv)
            
            psse_results_csv = generate_sample_psse_results_df().to_csv(index=False)
            zf.writestr('PSSe/Sample_Results.csv', psse_results_csv)
            
            # Windchill files
            ram_buffer = export_full_windchill_package(config)
            zf.writestr('Windchill_RAM/bvNexus_RAM_Package.xlsx', ram_buffer.getvalue())
            
            ram_results_csv = generate_sample_windchill_results_df().to_csv(index=False)
            zf.writestr('Windchill_RAM/Sample_Results.csv', ram_results_csv)
            
            # README
            readme = """# bvNexus Integration Sample Files

## Contents

### ETAP/
- bvNexus_ETAP_Package.xlsx - Equipment, scenarios, bus data for DataX import

### PSSe/
- bvNexus_Network.raw - RAW format network model
- bvNexus_Scenarios.csv - Study scenarios
- Sample_Results.csv - Example results format for import

### Windchill_RAM/
- bvNexus_RAM_Package.xlsx - Component data, RBD, FMEA, requirements
- Sample_Results.csv - Example results format for import

## Usage

1. Review sample files to understand expected formats
2. Use Export Hub in bvNexus to generate files for your project
3. Import files into respective tools
4. Run studies and export results
5. Use Import Hub in bvNexus to parse results and update constraints

## Questions?

Contact: [Your Team]
"""
            zf.writestr('README.md', readme)
        
        zip_buffer.seek(0)
        st.download_button(
            label="⬇️ Download All Samples (ZIP)",
            data=zip_buffer,
            file_name=f"bvNexus_Integration_Samples_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip",
        )
        st.success("✅ Sample files package generated!")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="bvNexus - Integration Export",
        page_icon="🔗",
        layout="wide"
    )
    render_integration_export_page()
