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
import plotly.graph_objects as go  # NEW: For interactive diagrams
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from io import BytesIO
import json
import zipfile

# Import custom diagram functions
from app.utils.plotly_diagram import create_interactive_single_line_diagram
from app.utils.plotly_rbd import create_interactive_rbd_diagram
# NEW: Comprehensive engineering drawings
from app.utils.plotly_engineering_drawings import (
    create_professional_single_line_diagram,
    create_site_plan_diagram,
    ELECTRICAL_SPECS,
    FOOTPRINT_LIBRARY
)

# =============================================================================
# SESSION STATE EXTRACTION (NEW - Pull Real Optimization Data)
# =============================================================================

def get_config_from_session_state() -> Optional[Dict]:
    """
    Extract equipment configuration from Streamlit session state optimization results.
    
    Checks multiple sources and builds integration export config with equipment counts.
    
    Returns:
        Dict with equipment configuration, or None if no optimization data found
        
    ⚠️ ASSUMPTIONS FLAGGED:
    - If equipment_details not in results, calculates counts using standard unit sizes  
    - Unit sizes: 18.3 MW recip (Wärtsilä 34SG), 50 MW turbine (GE LM6000)
    - BESS duration assumed 4 hours unless specified
    - Redundancy inferred from equipment count if not explicitly stated
    - Voltage assumed 13.8kV medium voltage if not in site data
    """
    # NEW: Try loading from Google Sheets FIRST for current site
    # This ensures we get the latest saved data, not stale session state
    
    site = None
    result = None
    
    # Get current site
    if 'current_site' in st.session_state and st.session_state.current_site:
        site_name = st.session_state.current_site
        
        # Load site object
        if 'sites_list' in st.session_state:
            for s in st.session_state.sites_list:
                if s.get('name') == site_name:
                    site = s
                    break
        
        # Load latest screening result from Google Sheets for this site
        try:
            from app.utils.site_backend import load_site_stage_result
            # Try screening first (most recent)
            result = load_site_stage_result(site_name, 'screening')
            if result:
                st.sidebar.caption(f"📊 **Data Source:** Google Sheets (screening) - {site_name}")
        except Exception as e:
            print(f"Error loading from Sheets: {e}")
    
    # Fallback: Try session state if Sheets load failed
    if not result:
        # Source 1: optimization_results dict (bvNexus multi-problem format)
        if 'optimization_results' in st.session_state and st.session_state.optimization_results:
            results_dict = st.session_state.optimization_results
            for problem_num in [1, 2, 3, 4, 5]:
                if problem_num in results_dict and results_dict[problem_num]:
                    result = results_dict[problem_num]
                    st.sidebar.caption(f"📊 **Data Source:** Session State (Problem {problem_num})")
                    break
        
        # Source 2: optimization_result (single result format)
        if not result and 'optimization_result' in st.session_state:
            result = st.session_state.optimization_result
            st.sidebar.caption(f"📊 **Data Source:** Session State (optimization_result)")
        
        # Source 3: current_config (MILP results)
        if not result and 'current_config' in st.session_state:
            config_st = st.session_state.current_config
            if 'results' in config_st:
                result = config_st['results']
                st.sidebar.caption(f"📊 **Data Source:** Session State (current_config)")
    
    # Fallback site if needed
    if not site:
        if 'current_site' in st.session_state and isinstance(st.session_state.current_site, dict):
            site = st.session_state.current_site
        elif 'sites_list' in st.session_state and st.session_state.sites_list:
            site = st.session_state.sites_list[0]
    
    # If no result found, return None (caller will use sample data)
    if not result:
        return None
    
    # Extract equipment data
    equipment = result.get('equipment', {})
    equipment_details = result.get('equipment_details', {})  # NEW from optimizer_backend
    
    # Build config dict
    config = {
        'data_source': 'session_state',  # Flag this is real data
        'project_name': site.get('name', 'Datacenter Project') if site else 'Datacenter Project',
        'site_id': site.get('geojson_prefix', 'SITE_001').upper() if site else 'SITE_001',
        'location': site.get('location', 'TBD') if site else 'TBD',
        'iso': site.get('iso', 'TBD') if site else 'TBD',
        
        'peak_load_mw': result.get('peak_load_mw', site.get('facility_mw', 200) if site else 200),
        'avg_load_mw': result.get('avg_load_mw', result.get('peak_load_mw', 200) * 0.8),
        
        # Reciprocating engines
        'recip_mw': equipment.get('recip_mw', 0),
    }
    
    if equipment_details and 'recip' in equipment_details:
        config['n_recip'] = equipment_details['recip'].get('count', 0)
        config['recip_mw_each'] = equipment_details['recip'].get('unit_mw', 18.3)
        config['recip_details'] = equipment_details['recip']  # Full specs
    else:
        # ASSUMPTION: Standard unit size
        config['recip_mw_each'] = 18.3  # ⚠️ ASSUMPTION: Wärtsilä 34SG
        config['n_recip'] = round(equipment.get('recip_mw', 0) / 18.3) if equipment.get('recip_mw', 0) > 0 else 0
    
    # Gas turbines
    config['turbine_mw'] = equipment.get('turbine_mw', 0)
    if equipment_details and 'turbine' in equipment_details:
        config['n_turbine'] = equipment_details['turbine'].get('count', 0)
        config['turbine_mw_each'] = equipment_details['turbine'].get('unit_mw', 50.0)
        config['turbine_details'] = equipment_details['turbine']
    else:
        config['turbine_mw_each'] = 50.0  # ⚠️ ASSUMPTION: GE LM6000PD
        config['n_turbine'] = round(equipment.get('turbine_mw', 0) / 50.0) if equipment.get('turbine_mw', 0) > 0 else 0
    
    # BESS
    config['bess_mwh'] = equipment.get('bess_mwh', 0)
    if equipment_details and 'bess' in equipment_details:
        config['bess_mw'] = equipment_details['bess'].get('total_mw', 0)
        config['bess_duration_hr'] = equipment_details['bess'].get('duration_hours', 4.0)
        config['bess_details'] = equipment_details['bess']
    else:
        config['bess_duration_hr'] = 4.0  # ⚠️ ASSUMPTION: 4-hour duration
        config['bess_mw'] = equipment.get('bess_mwh', 0) / 4.0
    
    #  Solar & Grid
    config['solar_mw'] = equipment.get('solar_mw', 0)
    config['grid_connection_mw'] = equipment.get('grid_mw', 0)
    
    # Site parameters
    config['voltage_kv'] = site.get('voltage_kv', 13.8) if site else 13.8  # ⚠️ ASSUMPTION: 13.8kV
    config['system_mva_base'] = 100.0
    config['pue'] = site.get('pue', 1.25) if site else 1.25
    
    # Site acreage from site data or GeoJSON
    config['site_acreage'] = site.get('acreage', 50) if site else 50
    if site and 'geojson' in site:
        try:
            import json
            geojson = json.loads(site['geojson']) if isinstance(site['geojson'], str) else site['geojson']
            if 'properties' in geojson:
                config['site_acreage'] = geojson['properties'].get('acres', config['site_acreage'])
        except:
            pass
    
    # Redundancy inference
    constraints = result.get('constraints', {})
    total_thermal = config['n_recip'] + config['n_turbine']
    if 'n_minus_1' in str(constraints).lower() or total_thermal > 10:
        config['redundancy'] = 'N+1'  #  ⚠️ ASSUMPTION: Inferred from count
    else:
        config['redundancy'] = 'N+0'
    
    # NEW: Load advanced load data from Google Sheets (bvNexus LoadComposition)
    if site:
        try:
            from app.utils.load_backend import load_load_configuration
            load_config = load_load_configuration(site.get('name'))
            
            # Check if advanced load data is available
            if load_config and load_config.get('cooling_type'):
                config['advanced_load'] = {
                    'cooling_type': load_config.get('cooling_type', ''),
                    'iso_region': load_config.get('iso_region', ''),
                    'psse_fractions': {
                        'electronic': load_config.get('psse_electronic_pct', 0.0),
                        'motor': load_config.get('psse_motor_pct', 0.0),
                        'static': load_config.get('psse_static_pct', 0.0),
                        'power_factor': load_config.get('psse_power_factor', 0.99)
                    },
                    'equipment': {
                        'ups': load_config.get('equipment_ups', 0),
                        'chillers': load_config.get('equipment_chillers', 0),
                        'crah': load_config.get('equipment_crah', 0),
                        'pumps': load_config.get('equipment_pumps', 0)
                    },
                    'dr_capacity': {
                        'total': load_config.get('dr_total_mw', 0.0),
                        'economic': load_config.get('dr_economic_mw', 0.0),
                        'ers30': load_config.get('dr_ers30_mw', 0.0),
                        'ers10': load_config.get('dr_ers10_mw', 0.0)
                    },
                    'harmonics': {
                        'thd_v': load_config.get('harmonics_thd_v', 0.0),
                        'thd_i': load_config.get('harmonics_thd_i', 0.0),
                        'ieee519_compliant': load_config.get('harmonics_ieee519_compliant', False)
                    },
                    'workload_mix': {
                        'pre_training': load_config.get('workload_pretraining_pct', 0.0),
                        'fine_tuning': load_config.get('workload_finetuning_pct', 0.0),
                        'batch_inference': load_config.get('workload_batch_inference_pct', 0.0),
                        'realtime_inference': load_config.get('workload_realtime_inference_pct', 0.0)
                    }
                }
                print(f"✓ Loaded advanced load data from Google Sheets for {site.get('name')}")
        except Exception as e:
            print(f"Note: Advanced load data not available ({e})")
    
    # NEW: Electrical configuration inference based on equipment and redundancy
    if config['redundancy'] == 'N+1' and total_thermal > 8:
        # Large, redundant facility → premium electrical configuration
        config['suggested_poi'] = 'ring_n1'
        config['suggested_gen'] = 'double_bus'
        config['suggested_dist'] = 'catcher'
    elif config['redundancy'] == 'N+1':
        # Standard redundant facility → mid-tier configuration
        config['suggested_poi'] = 'radial'
        config['suggested_gen'] = 'mtm'
        config['suggested_dist'] = 'n_topology'
    else:
        # No redundancy → simple configuration
        config['suggested_poi'] = 'radial'
        config['suggested_gen'] = 'radial'
        config['suggested_dist'] = 'distributed'
    
    return config


# =============================================================================
# SAMPLE DATA GENERATORS (Fallback if no session state data)
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
    
    # Solar PV (NEW)
    if config.get('solar_mw', 0) > 0:
        rows.append({
            'ID': 'SOLAR_01',
            'Name': f"Solar PV Array ({config.get('solar_mw', 0):.0f} MW)",
            'Type': 'Solar PV Inverter',
            'Bus_ID': 'BUS_150',
            'Rated_kV': 13.8,
            'Rated_MW': config.get('solar_mw', 0),
            'Rated_MVA': config.get('solar_mw', 0),
            'Rated_PF': 1.00,
            'Xd_pu': 0.0,
            'Xd_prime_pu': 0.0,
            'Xd_double_prime_pu': 0.10,
            'H_inertia_sec': 0.0,
            'Status': 'Online',
            'Redundancy_Group': 'RENEWABLE',
        })
    
    # Grid Connection (NEW)
    if config.get('grid_connection_mw', 0) > 0:
        rows.append({
            'ID': 'GRID_01',
            'Name': 'Grid Connection',
            'Type': 'External Grid',
            'Bus_ID': 'BUS_200',
            'Rated_kV': 13.8,
            'Rated_MW': config.get('grid_connection_mw', 0),
            'Rated_MVA': config.get('grid_connection_mw', 0) / 0.95,
            'Rated_PF': 0.95,
            'Xd_pu': 0.1,
            'Xd_prime_pu': 0.1,
            'Xd_double_prime_pu': 0.1,
            'H_inertia_sec': 999.0,  # Infinite bus
            'Status': 'Online',
            'Redundancy_Group': 'GRID',
        })
    
    return pd.DataFrame(rows)



def generate_etap_bus_data(config: Dict) -> pd.DataFrame:
    """Generate ETAP bus data matching engineering drawing topology.
    
    Includes proper voltage levels and bus configurations:
    - 345 kV: POI (utility interconnection)
    - 34.5 kV: Main/Facility bus
    - 13.8 kV: Generation bus and generator terminals
    - 13.8 kV or 34.5 kV: Data hall buses
    """
    rows = []
    
    # Get electrical configurations
    poi_config = config.get('suggested_poi', 'radial')
    gen_config = config.get('suggested_gen', 'mtm')
    dist_config = config.get('suggested_dist', 'catcher')
    
    poi_type = ELECTRICAL_SPECS['poi'][poi_config]['type']
    gen_type = ELECTRICAL_SPECS['generation'][gen_config]['type']
    dist_type = ELECTRICAL_SPECS['distribution'][dist_config]['type']
    
    # === 1. POI BUSES (345 kV) ===
    if poi_type == 'ring':
        rows.append({
            "Bus_ID": "BUS_POI_RING",
            "Bus_Name": "345kV_RING_BUS",
            "Nominal_kV": 345.0,
            "Bus_Type": "Swing",
            "Area": 1,
            "Zone": 1,
            "Notes": "POI Ring Bus - N-1 configuration"
        })
    elif poi_type == 'bah':
        rows.append({
            "Bus_ID": "BUS_POI_RAIL_A",
            "Bus_Name": "345kV_RAIL_A",
            "Nominal_kV": 345.0,
            "Bus_Type": "Swing",
            "Area": 1,
            "Zone": 1,
            "Notes": "Breaker-and-a-Half - Rail A"
        })
        rows.append({
            "Bus_ID": "BUS_POI_RAIL_B",
            "Bus_Name": "345kV_RAIL_B",
            "Nominal_kV": 345.0,
            "Bus_Type": "Swing",
            "Area": 1,
            "Zone": 1,
            "Notes": "Breaker-and-a-Half - Rail B"
        })
    else:  # radial
        rows.append({
            "Bus_ID": "BUS_POI_RADIAL",
            "Bus_Name": "345kV_RADIAL_BUS",
            "Nominal_kV": 345.0,
            "Bus_Type": "Swing",
            "Area": 1,
            "Zone": 1,
            "Notes": "POI Radial Feed"
        })
    
    # === 2. MAIN BUS (34.5 kV) ===
    if gen_type in ['mtm', 'double']:
        rows.append({
            "Bus_ID": "BUS_MAIN_A",
            "Bus_Name": "MAIN_BUS_A_34_5kV",
            "Nominal_kV": 34.5,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Main Facility Bus A"
        })
        rows.append({
            "Bus_ID": "BUS_MAIN_B",
            "Bus_Name": "MAIN_BUS_B_34_5kV",
            "Nominal_kV": 34.5,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Main Facility Bus B"
        })
    else:
        rows.append({
            "Bus_ID": "BUS_MAIN",
            "Bus_Name": "MAIN_BUS_34_5kV",
            "Nominal_kV": 34.5,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Main Facility Bus"
        })
    
    # === 3. GENERATION BUS (13.8 kV) ===
    if gen_type in ['mtm', 'double']:
        rows.append({
            "Bus_ID": "BUS_GEN_A",
            "Bus_Name": "GEN_BUS_A_13_8kV",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Generation Bus A - connects to generators"
        })
        rows.append({
            "Bus_ID": "BUS_GEN_B",
            "Bus_Name": "GEN_BUS_B_13_8kV",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Generation Bus B - connects to generators"
        })
    elif gen_type == 'ring':
        rows.append({
            "Bus_ID": "BUS_GEN_RING",
            "Bus_Name": "GEN_RING_13_8kV",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Generation Ring Bus - generators tap from ring"
        })
    else:  # radial
        rows.append({
            "Bus_ID": "BUS_GEN",
            "Bus_Name": "GEN_BUS_13_8kV",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Generation Bus - single radial"
        })
    
    # === 4. GENERATOR TERMINAL BUSES (13.8 kV) ===
    for i in range(config.get("n_recip", 0)):
        rows.append({
            "Bus_ID": f"BUS_RECIP_{i+1:02d}",
            "Bus_Name": f"RECIP_{i+1:02d}_TERM",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": f"Reciprocating Engine {i+1} Terminal"
        })
    
    for i in range(config.get("n_turbine", 0)):
        rows.append({
            "Bus_ID": f"BUS_GT_{i+1:02d}",
            "Bus_Name": f"GT_{i+1:02d}_TERM",
            "Nominal_kV": 13.8,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": f"Gas Turbine {i+1} Terminal"
        })
    
    # === 5. DISTRIBUTION BUSES ===
    if dist_type == 'catcher':
        # Reserve bus at 34.5kV for catcher topology
        rows.append({
            "Bus_ID": "BUS_RESERVE",
            "Bus_Name": "RESERVE_BUS_34_5kV",
            "Nominal_kV": 34.5,
            "Bus_Type": "PV",
            "Area": 1,
            "Zone": 1,
            "Notes": "Reserve Bus for N+1 Catcher topology"
        })
    
    # === 6. DATA HALL BUSES (13.8 kV after distribution transformers) ===
    n_halls = 4
    for i in range(n_halls):
        rows.append({
            "Bus_ID": f"BUS_HALL_{i+1}",
            "Bus_Name": f"HALL_{i+1}_13_8kV",
            "Nominal_kV": 13.8,
            "Bus_Type": "PQ",
            "Area": 1,
            "Zone": 1,
            "Notes": f"Data Hall {i+1} Load Bus"
        })
    
    return pd.DataFrame(rows)


def generate_etap_transformer_data(config: Dict) -> pd.DataFrame:
    """Generate transformer data matching engineering drawing topology.
    
    Includes:
    - POI Transformers: T1, T2 (345kV → 34.5kV)
    - Step-Up Transformers: TR1-TR6 (13.8kV → 34.5kV)
    - Distribution Transformers: T-1 to T-4 (34.5kV → 13.8kV)
    """
    rows = []
    
    # Get electrical configurations
    poi_config = config.get('suggested_poi', 'radial')
    gen_config = config.get('suggested_gen', 'mtm')
    dist_config = config.get('suggested_dist', 'catcher')
    
    poi_type = ELECTRICAL_SPECS['poi'][poi_config]['type']
    gen_type = ELECTRICAL_SPECS['generation'][gen_config]['type']
    dist_type = ELECTRICAL_SPECS['distribution'][dist_config]['type']
    
    # === 1. POI TRANSFORMERS (345kV → 34.5kV) ===
    n_poi_xfmrs = 2 if poi_type in ['ring', 'bah'] else 1
    
    for i in range(n_poi_xfmrs):
        if poi_type == 'ring':
            from_bus = "BUS_POI_RING"
        elif poi_type == 'bah':
            from_bus = f"BUS_POI_RAIL_{'A' if i == 0 else 'B'}"
        else:
            from_bus = "BUS_POI_RADIAL"
        
        to_bus = f"BUS_MAIN_{'A' if i == 0 else 'B'}" if gen_type in ['mtm', 'double'] else "BUS_MAIN"
        
        rows.append({
            'Transformer_ID': f'T{i+1}',
            'From_Bus': from_bus,
            'To_Bus': to_bus,
            'MVA_Rating': 300,
            'Primary_kV': 345.0,
            'Secondary_kV': 34.5,
            'Connection': 'Delta-Wye',
            'Z_percent': 12.5,
            'R_percent': 0.5,
            'X_percent': 12.49,
            'Tap_Position': 0,
            'Notes': f'POI Transformer {i+1} - 345kV to 34.5kV step-down'
        })
    
    # === 2. STEP-UP TRANSFORMERS (13.8kV → 34.5kV) ===
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    n_step_up = min(6, max(2, (n_recip + n_turbine) // 3))  # N-1 redundancy
    
    for i in range(n_step_up):
        # Determine which gen bus (A or B for MTM/double, single for others)
        if gen_type in ['mtm', 'double']:
            from_bus = f"BUS_GEN_{'A' if i < n_step_up//2 else 'B'}"
            to_bus = f"BUS_MAIN_{'A' if i < n_step_up//2 else 'B'}"
        elif gen_type == 'ring':
            from_bus = "BUS_GEN_RING"
            to_bus = "BUS_MAIN"
        else:
            from_bus = "BUS_GEN"
            to_bus = "BUS_MAIN"
        
        # Size based on generators
        total_gen_mw = n_recip * config.get('recip_mw_each', 18.3) + n_turbine * config.get('turbine_mw_each', 50.0)
        xfmr_mva = max(50, total_gen_mw / n_step_up * 1.25)  # 25% margin
        
        rows.append({
            'Transformer_ID': f'TR{i+1}',
            'From_Bus': from_bus,
            'To_Bus': to_bus,
            'MVA_Rating': round(xfmr_mva, 1),
            'Primary_kV': 13.8,
            'Secondary_kV': 34.5,
            'Connection': 'Delta-Wye',
            'Z_percent': 6.5,
            'R_percent': 0.4,
            'X_percent': 6.49,
            'Tap_Position': 0,
            'Notes': f'Step-Up Transformer {i+1} - 13.8kV gen bus to 34.5kV main bus'
        })
    
    # === 3. DISTRIBUTION TRANSFORMERS (34.5kV → 13.8kV) ===
    n_halls = 4
    peak_load = config.get('peak_load_mw', 200)
    
    for i in range(n_halls):
        from_bus = "BUS_MAIN_A" if gen_type in ['mtm', 'double'] and i < 2 else \
                   ("BUS_MAIN_B" if gen_type in ['mtm', 'double'] else "BUS_MAIN")
        to_bus = f"BUS_HALL_{i+1}"
        
        # Size for per-hall load + margin
        dist_mva = (peak_load / n_halls) * 1.2
        
        rows.append({
            'Transformer_ID': f'T-{i+1}',
            'From_Bus': from_bus,
            'To_Bus': to_bus,
            'MVA_Rating': round(dist_mva, 1),
            'Primary_kV': 34.5,
            'Secondary_kV': 13.8,
            'Connection': 'Delta-Wye',
            'Z_percent': 5.75,
            'R_percent': 0.35,
            'X_percent': 5.74,
            'Tap_Position': 0,
            'Notes': f'Distribution Transformer to Hall {i+1}'
        })
    
    # === 4. RESERVE TRANSFORMER (if catcher topology) ===
    if dist_type == 'catcher':
        from_bus = "BUS_MAIN_B" if gen_type in ['mtm', 'double'] else "BUS_MAIN"
        
        rows.append({
            'Transformer_ID': 'T-Res',
            'From_Bus': from_bus,
            'To_Bus': 'BUS_RESERVE',
            'MVA_Rating': round(peak_load * 0.3, 1),  # 30% capacity for reserve
            'Primary_kV': 34.5,
            'Secondary_kV': 34.5,
            'Connection': 'Delta-Delta',
            'Z_percent': 5.0,
            'R_percent': 0.3,
            'X_percent': 4.99,
            'Tap_Position': 0,
            'Notes': 'Reserve Bus Transformer for N+1 Catcher topology'
        })
    
    return pd.DataFrame(rows)


def generate_etap_breaker_data(config: Dict) -> pd.DataFrame:
    """Generate breaker/switch data matching engineering drawing topology."""
    rows = []
    
    # Get electrical configurations
    poi_config = config.get('suggested_poi', 'radial')
    gen_config = config.get('suggested_gen', 'mtm')
    dist_config = config.get('suggested_dist', 'catcher')
    
    poi_type = ELECTRICAL_SPECS['poi'][poi_config]['type']
    gen_type = ELECTRICAL_SPECS['generation'][gen_config]['type']
    dist_type = ELECTRICAL_SPECS['distribution'][dist_config]['type']
    
    # === 1. POI BREAKERS ===
    if poi_type == 'ring':
        # Ring bus has breakers at corners
        for i in range(4):
            rows.append({
                'Breaker_ID': f'BKR_POI_RING_{i+1}',
                'Bus': 'BUS_POI_RING',
                'Voltage_kV': 345.0,
                'BIL_kV': 1550,
                'Interrupting_MVA': 40000,
                'Type': 'Circuit Breaker',
                'Status': 'Closed',
                'Notes': f'POI Ring Bus Breaker {i+1}'
            })
    elif poi_type == 'bah':
        # Breaker-and-a-half has 3 breakers per bay
        for bay in range(3):
            for pos in range(3):
                rows.append({
                    'Breaker_ID': f'BKR_POI_BAY{bay+1}_{pos+1}',
                    'Bus': f'BUS_POI_RAIL_{"AB"[pos%2]}',
                    'Voltage_kV': 345.0,
                    'BIL_kV': 1550,
                    'Interrupting_MVA': 40000,
                    'Type': 'Circuit Breaker',
                    'Status': 'Closed',
                    'Notes': f'Breaker-and-a-Half Bay {bay+1} Position {pos+1}'
                })
    
    # === 2. MAIN BUS BREAKERS ===
    if gen_type == 'mtm':
        # Tie breaker (normally open)
        rows.append({
            'Breaker_ID': 'BKR_MAIN_TIE',
            'Bus': 'BUS_MAIN_A',
            'Voltage_kV': 34.5,
            'BIL_kV': 200,
            'Interrupting_MVA': 1500,
            'Type': 'Circuit Breaker',
            'Status': 'Open',
            'Notes': 'Main Bus Tie Breaker (Normally Open for MTM)'
        })
    
    # === 3. GENERATION BUS BREAKERS ===
    if gen_type == 'mtm':
        rows.append({
            'Breaker_ID': 'BKR_GEN_TIE',
            'Bus': 'BUS_GEN_A',
            'Voltage_kV': 13.8,
            'BIL_kV': 95,
            'Interrupting_MVA': 500,
            'Type': 'Circuit Breaker',
            'Status': 'Open',
            'Notes': 'Generation Bus Tie Breaker (Normally Open for MTM)'
        })
    
    # Generator breakers
    for i in range(config.get('n_recip', 0)):
        rows.append({
            'Breaker_ID': f'BKR_RECIP_{i+1:02d}',
            'Bus': 'BUS_GEN_A' if gen_type in ['mtm', 'double'] and i < config.get('n_recip', 0)//2 else 'BUS_GEN_B' if gen_type in ['mtm', 'double'] else 'BUS_GEN',
            'Voltage_kV': 13.8,
            'BIL_kV': 95,
            'Interrupting_MVA': 500,
            'Type': 'Circuit Breaker',
            'Status': 'Closed',
            'Notes': f'Recip {i+1} Main Breaker'
        })
    
    for i in range(config.get('n_turbine', 0)):
        rows.append({
            'Breaker_ID': f'BKR_GT_{i+1:02d}',
            'Bus': 'BUS_GEN_B' if gen_type in ['mtm', 'double'] else 'BUS_GEN',
            'Voltage_kV': 13.8,
            'BIL_kV': 95,
            'Interrupting_MVA': 500,
            'Type': 'Circuit Breaker',
            'Status': 'Closed',
            'Notes': f'Gas Turbine {i+1} Main Breaker'
        })
    
    # === 4. STS SWITCHES (if catcher topology) ===
    if dist_type == 'catcher':
        for i in range(4):
            rows.append({
                'Breaker_ID': f'STS_{i+1}',
                'Bus': f'BUS_HALL_{i+1}',
                'Voltage_kV': 13.8,
                'BIL_kV': 95,
                'Interrupting_MVA': 250,
                'Type': 'Static Transfer Switch',
                'Status': 'Normal->Primary',
                'Transfer_Time_ms': 4,
                'Notes': f'STS for Hall {i+1} - Switches between primary and reserve'
            })
    
    return pd.DataFrame(rows)



def generate_etap_load_data(config: Dict) -> pd.DataFrame:
    """Generate ETAP load data for datacenter halls using advanced load composition."""
    import math
    
    peak_load = config.get("peak_load_mw", 200)
    n_halls = 4
    
    # Check if advanced load data available
    if 'advanced_load' in config:
        adv = config['advanced_load']
        psse_frac = adv.get('psse_fractions', {})
        
        # Get fractions (stored as percentages in JSON)
        electronic_frac = psse_frac.get('electronic', 0.73) / 100
        motor_frac = psse_frac.get('motor', 0.21) / 100
        static_frac = psse_frac.get('static', 0.06) / 100
        pf = psse_frac.get('power_factor', 0.99)
        
        # Get harmonics
        harm = adv.get('harmonics', {})
        thd_v = harm.get('thd_v', 0.0)
        thd_i = harm.get('thd_i', 0.0)
        ieee519 = 'Compliant' if harm.get('ieee519_compliant', True) else 'Non-Compliant'
        
        # Get equipment counts
        eq = adv.get('equipment', {})
        
        # Calculate load breakdown
        electronic_mw = peak_load * electronic_frac
        motor_mw = peak_load * motor_frac
        static_mw = peak_load * static_frac
        
        rows = []
        for i in range(n_halls):
            hall_num = i + 1
            
            # Electronic load (GPU/TPU) - Constant Power model
            if electronic_mw > 0:
                q_mvar = (electronic_mw / n_halls) * math.tan(math.acos(pf))
                rows.append({
                    "Load_ID": f"LOAD_HALL_{hall_num}_GPU",
                    "Load_Name": f"Hall {hall_num} GPU/TPU Load",
                    "Bus_ID": f"BUS_HALL_{hall_num}",
                    "Nominal_kV": 13.8,
                    "P_MW": round(electronic_mw / n_halls, 2),
                    "Q_MVAR": round(q_mvar, 2),
                    "Load_Model": "Constant Power",
                    "Status": "Online",
                    "Category": "Critical",
                    "Notes": f"Electronic load {electronic_frac*100:.1f}%, THD-V:{thd_v:.2f}%, THD-I:{thd_i:.2f}%, {ieee519}"
                })
            
            # Motor load (Cooling equipment) - Induction Motor model
            if motor_mw > 0:
                motor_pf = 0.85  # Typical motor power factor
                q_mvar = (motor_mw / n_halls) * math.tan(math.acos(motor_pf))
                rows.append({
                    "Load_ID": f"LOAD_HALL_{hall_num}_COOLING",
                    "Load_Name": f"Hall {hall_num} Cooling",
                    "Bus_ID": f"BUS_HALL_{hall_num}",
                    "Nominal_kV": 13.8,
                    "P_MW": round(motor_mw / n_halls, 2),
                    "Q_MVAR": round(q_mvar, 2),
                    "Load_Model": "Induction Motor",
                    "Status": "Online",
                    "Category": "Critical",
                    "Notes": f"Motor load {motor_frac*100:.1f}%, {eq.get('chillers', 0)//n_halls} chillers, {eq.get('crah', 0)//n_halls} CRAH"
                })
            
            # Static load (Lighting, controls) - Constant Impedance model
            if static_mw > 0:
                static_pf = 0.95
                q_mvar = (static_mw / n_halls) * math.tan(math.acos(static_pf))
                rows.append({
                    "Load_ID": f"LOAD_HALL_{hall_num}_STATIC",
                    "Load_Name": f"Hall {hall_num} Static Load",
                    "Bus_ID": f"BUS_HALL_{hall_num}",
                    "Nominal_kV": 13.8,
                    "P_MW": round(static_mw / n_halls, 2),
                    "Q_MVAR": round(q_mvar, 2),
                    "Load_Model": "Constant Impedance",
                    "Status": "Online",
                    "Category": "Normal",
                    "Notes": f"Static load {static_frac*100:.1f}% (lighting, controls)"
                })
    else:
        # Fallback to generic load if no advanced data
        load_per_hall = peak_load / n_halls
        rows = []
        for i in range(n_halls):
            rows.append({
                "Load_ID": f"LOAD_HALL_{i+1}",
                "Load_Name": f"Hall {i+1} Load",
                "Bus_ID": f"BUS_HALL_{i+1}",
                "Nominal_kV": 13.8,
                "P_MW": round(load_per_hall, 2),
                "Q_MVAR": round(load_per_hall * 0.33, 2),
                "Load_Model": "Constant Power",
                "Status": "Online",
                "Category": "Critical",
                "Notes": f"Data Hall {i+1} critical IT load (generic - no advanced data)"
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
    """Generate PSS/e RAW format file with full multi-voltage topology.
    
    Matches engineering drawing architecture:
    - 345 kV: POI (Utility Interconnection)
    - 34.5 kV: Main Facility Bus
    - 13.8 kV: Generation Bus + Generator Terminals + Data Halls
    """
    lines = []
    system_mva = config.get('system_mva_base', 100.0)
    
    # Get electrical configurations
    poi_config = config.get('suggested_poi', 'radial')
    gen_config = config.get('suggested_gen', 'mtm')
    dist_config = config.get('suggested_dist', 'catcher')
    
    poi_type = ELECTRICAL_SPECS['poi'][poi_config]['type']
    gen_type = ELECTRICAL_SPECS['generation'][gen_config]['type']
    dist_type = ELECTRICAL_SPECS['distribution'][dist_config]['type']
    
    # Header (3 lines required)
    lines.append(f"0,   {system_mva:.2f}     / PSS/E-35    {datetime.now().strftime('%a, %b %d %Y  %H:%M')}")
    lines.append(f"{config.get('project_name', 'bvNexus Export')} - {ELECTRICAL_SPECS['poi'][poi_config]['label']} / {ELECTRICAL_SPECS['generation'][gen_config]['label']}")
    lines.append(f"Multi-Voltage Topology: 345kV→34.5kV→13.8kV - Generated by bvNexus")
    
    # Bus data section
    lines.append("")
    lines.append("/ BUS DATA - Voltage Levels: 345kV (POI), 34.5kV (Main), 13.8kV (Gen/Halls)")
    lines.append("/ I, 'NAME', BASKV, IDE, AREA, ZONE, OWNER, VM, VA, NVHI, NVLO, EVHI, EVLO")
    
    bus_counter = 1
    bus_mapping = {}
    
    # === 1. POI BUSES (345 kV) - Swing Bus ===
    if poi_type == 'ring':
        poi_bus = bus_counter
        bus_mapping['POI'] = poi_bus
        lines.append(f"{poi_bus},'POI_RING ',345.000,3,   1,   1,   1,1.01000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    else:  # radial or bah - use single swing for simplicity
        poi_bus = bus_counter
        bus_mapping['POI'] = poi_bus
        lines.append(f"{poi_bus},'POI_UTIL ',345.000,3,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    # === 2. MAIN BUS (34.5 kV) - PV Buses ===
    if gen_type in ['mtm', 'double']:
        main_bus_a = bus_counter
        bus_mapping['MAIN_A'] = main_bus_a
        lines.append(f"{main_bus_a},'MAIN_A  ', 34.500,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
        
        main_bus_b = bus_counter
        bus_mapping['MAIN_B'] = main_bus_b
        lines.append(f"{main_bus_b},'MAIN_B  ', 34.500,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
        bus_mapping['MAIN'] = main_bus_a  # Default to A for single connections
    else:
        main_bus = bus_counter
        bus_mapping['MAIN'] = main_bus
        lines.append(f"{main_bus},'MAIN_BUS', 34.500,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    # === 3. GENERATION BUS (13.8 kV) - PV Buses ===
    if gen_type in ['mtm', 'double']:
        gen_bus_a = bus_counter
        bus_mapping['GEN_A'] = gen_bus_a
        lines.append(f"{gen_bus_a},'GEN_A   ', 13.800,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
        
        gen_bus_b = bus_counter
        bus_mapping['GEN_B'] = gen_bus_b
        lines.append(f"{gen_bus_b},'GEN_B   ', 13.800,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
        bus_mapping['GEN'] = gen_bus_a
    else:
        gen_bus = bus_counter
        bus_mapping['GEN'] = gen_bus
        lines.append(f"{gen_bus},'GEN_BUS ', 13.800,2,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    # === 4. GENERATOR TERMINAL BUSES (13.8 kV) - PV Buses ===
    bus_mapping['RECIP'] = []
    for i in range(config.get('n_recip', 0)):
        recip_bus = bus_counter
        bus_mapping['RECIP'].append(recip_bus)
        lines.append(f"{recip_bus},'RECIP{i+1:02d} ', 13.800,2,   1,   1,   1,1.01000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    bus_mapping['GT'] = []
    for i in range(config.get('n_turbine', 0)):
        gt_bus = bus_counter
        bus_mapping['GT'].append(gt_bus)
        lines.append(f"{gt_bus},'GT{i+1:02d}    ', 13.800,2,   1,   1,   1,1.02000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    # === 5. DATA HALL BUSES (13.8 kV) - PQ Load Buses ===
    bus_mapping['HALL'] = []
    for i in range(4):
        hall_bus = bus_counter
        bus_mapping['HALL'].append(hall_bus)
        lines.append(f"{hall_bus},'HALL_{i+1}  ', 13.800,1,   1,   1,   1,1.00000,   0.0000,1.05000,0.95000,1.05000,0.95000")
        bus_counter += 1
    
    lines.append("0 / END OF BUS DATA")
    
    # === LOAD DATA ===
    lines.append("")
    lines.append("/ LOAD DATA - Distributed across data halls with composition detail")
    lines.append("/ I, ID, STATUS, AREA, ZONE, PL, QL, IP, IQ, YP, YQ, OWNER, SCALE, INTRPT, DGENON")
    
    peak_load = config.get('peak_load_mw', 200)
    load_per_hall = peak_load / 4
    
    # Use advanced load data if available - DETAILED BREAKDOWN
    if 'advanced_load' in config:
        import math
        adv = config['advanced_load']
        psse_frac = adv.get('psse_fractions', {})
        
        # Get fractions (as percentages, convert to per-unit)
        electronic_frac = psse_frac.get('electronic', 73) / 100
        motor_frac = psse_frac.get('motor', 21) / 100
        static_frac = psse_frac.get('static', 6) / 100
        pf = psse_frac.get('power_factor', 0.99)
        
        # Calculate MW per load type per hall
        gpu_mw = load_per_hall * electronic_frac
        cooling_mw = load_per_hall * motor_frac
        static_mw = load_per_hall * static_frac
        
        # Calculate Q for each type
        gpu_q = gpu_mw * math.tan(math.acos(pf))  # GPU power electronics
        cooling_q = cooling_mw * math.tan(math.acos(0.85))  # Motor PF
        static_q = static_mw * math.tan(math.acos(0.95))  # Static load PF
        
        comment = f"! bvNexus detailed composition: {electronic_frac*100:.1f}% GPU/TPU, {motor_frac*100:.1f}% Cooling, {static_frac*100:.1f}% Static"
        lines.append(comment)
        
        for i, hall_bus in enumerate(bus_mapping['HALL']):
            # ID '1' = GPU/TPU load (electronic)
            lines.append(f"{hall_bus},'1 ',1,   1,   1,   {gpu_mw:.2f},    {gpu_q:.2f},   0.00,   0.00,   0.00,   0.00,   1,1,0,1  ! Hall {i+1} GPU")
            # ID '2' = Cooling load (motor)
            lines.append(f"{hall_bus},'2 ',1,   1,   1,   {cooling_mw:.2f},    {cooling_q:.2f},   0.00,   0.00,   0.00,   0.00,   1,1,0,1  ! Hall {i+1} Cooling")
            # ID '3' = Static load (lighting, controls)
            lines.append(f"{hall_bus},'3 ',1,   1,   1,   {static_mw:.2f},    {static_q:.2f},   0.00,   0.00,   0.00,   0.00,   1,1,0,1  ! Hall {i+1} Static")
    else:
        # Generic aggregate load if no advanced data
        for hall_bus in bus_mapping['HALL']:
            lines.append(f"{hall_bus},'1 ',1,   1,   1,   {load_per_hall:.2f},    {load_per_hall*0.33:.2f},   0.00,   0.00,   0.00,   0.00,   1,1,0,1")
    
    lines.append("0 / END OF LOAD DATA")
    
    # === FIXED SHUNT DATA ===
    lines.append("")
    lines.append("/ FIXED SHUNT DATA")
    lines.append("0 / END OF FIXED SHUNT DATA")
    
    # === GENERATOR DATA ===
    lines.append("")
    lines.append("/ GENERATOR DATA - 13.8kV terminals")
    lines.append("/ I, ID, PG, QG, QT, QB, VS, IREG, MBASE, ZR, ZX, RT, XT, GTAP, STAT, RMPCT, PT, PB")
    
    # Reciprocating engines
    for i, recip_bus in enumerate(bus_mapping['RECIP']):
        mw = config.get('recip_mw_each', 18.3)
        mva = mw / 0.85
        lines.append(f"{recip_bus},'1 ',   {mw:.2f},    0.00,  {mva*0.5:.2f}, {-mva*0.3:.2f},1.0100,     0,  {mva:.2f}, 0.00000, 1.00000, 0.00000, 0.00000,1.00000,1,  100.0,  {mw:.2f},    0.00,1,1.0000,0,1.0000,0,1.0000,0,1.0000,0")
    
    # Gas turbines
    for i, gt_bus in enumerate(bus_mapping['GT']):
        mw = config.get('turbine_mw_each', 50.0)
        mva = mw / 0.85
        lines.append(f"{gt_bus},'1 ',   {mw:.2f},    0.00,  {mva*0.5:.2f}, {-mva*0.3:.2f},1.0200,     0,  {mva:.2f}, 0.00000, 1.00000, 0.00000, 0.00000,1.00000,1,  100.0,  {mw:.2f},    0.00,1,1.0000,0,1.0000,0,1.0000,0,1.0000,0")
    
    lines.append("0 / END OF GENERATOR DATA")
    
    # === BRANCH DATA (Cable connections) ===
    lines.append("")
    lines.append("/ BRANCH DATA - Cable connections between buses")
    lines.append("/ I, J, CKT, R, X, B, RATEA, RATEB, RATEC, GI, BI, GJ, BJ, ST, MET, LEN, O1, F1")
    
    # Generators to gen bus
    if gen_type in ['mtm', 'double']:
        n_per_bus = len(bus_mapping['RECIP']) // 2
        for i, recip_bus in enumerate(bus_mapping['RECIP']):
            gen_bus = bus_mapping['GEN_A'] if i < n_per_bus else bus_mapping['GEN_B']
            lines.append(f"{recip_bus},  {gen_bus},'1 ', 0.00100, 0.01000, 0.00000,   25.0,   25.0,   25.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.10,1,1.0000")
        
        for i, gt_bus in enumerate(bus_mapping['GT']):
            gen_bus = bus_mapping['GEN_B']  # Turbines on Bus B
            lines.append(f"{gt_bus},  {gen_bus},'1 ', 0.00050, 0.00800, 0.00000,   60.0,   60.0,   60.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.05,1,1.0000")
    else:
        for recip_bus in bus_mapping['RECIP']:
            lines.append(f"{recip_bus},  {bus_mapping['GEN']},'1 ', 0.00100, 0.01000, 0.00000,   25.0,   25.0,   25.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.10,1,1.0000")
        
        for gt_bus in bus_mapping['GT']:
            lines.append(f"{gt_bus},  {bus_mapping['GEN']},'1 ', 0.00050, 0.00800, 0.00000,   60.0,   60.0,   60.0, 0.00000, 0.00000, 0.00000, 0.00000,1,1,   0.05,1,1.0000")
    
    lines.append("0 / END OF BRANCH DATA")
    
    # === TRANSFORMER DATA ===
    lines.append("")
    lines.append("/ TRANSFORMER DATA - Multi-voltage transformers")
    
    # POI Transformers (345kV → 34.5kV)
    if gen_type in ['mtm', 'double']:
        # T1: POI → MAIN_A
        lines.append(f"{bus_mapping['POI']}, {bus_mapping['MAIN_A']},'1 ',1,1,1,'T1_POI  ',   1,   1,   1,'            ',1,1, 1.00000")
        lines.append(f" 0.00500, 0.12500,  300.00")
        lines.append(f"1.00000,     0,1.00000,     0,1.10000,0.90000,1.10000,0.90000,   0,   0,   0.00000,   0.00000,  10,1,0.00000,1.00000,0.00000,'            '")
        lines.append(f"1.00000,   0.0000")
        
        # T2: POI → MAIN_B
        lines.append(f"{bus_mapping['POI']}, {bus_mapping['MAIN_B']},'1 ',1,1,1,'T2_POI  ',   1,   1,   1,'            ',1,1, 1.00000")
        lines.append(f" 0.00500, 0.12500,  300.00")
        lines.append(f"1.00000,     0,1.00000,     0,1.10000,0.90000,1.10000,0.90000,   0,   0,   0.00000,   0.00000,  10,1,0.00000,1.00000,0.00000,'            '")
        lines.append(f"1.00000,   0.0000")
    else:
        # T1: POI → MAIN
        lines.append(f"{bus_mapping['POI']}, {bus_mapping['MAIN']},'1 ',1,1,1,'T1_POI  ',   1,   1,   1,'            ',1,1, 1.00000")
        lines.append(f" 0.00500, 0.12500,  300.00")
        lines.append(f"1.00000,     0,1.00000,     0,1.10000,0.90000,1.10000,0.90000,   0,   0,   0.00000,   0.00000,  10,1,0.00000,1.00000,0.00000,'            '")
        lines.append(f"1.00000,   0.0000")
    
    # Step-Up Transformers (13.8kV → 34.5kV)
    n_step_up = min(6, max(2, (len(bus_mapping['RECIP']) + len(bus_mapping['GT'])) // 3))
    for i in range(n_step_up):
        if gen_type in ['mtm', 'double']:
            from_bus = bus_mapping['GEN_A'] if i < n_step_up//2 else bus_mapping['GEN_B']
            to_bus = bus_mapping['MAIN_A'] if i < n_step_up//2 else bus_mapping['MAIN_B']
        else:
            from_bus = bus_mapping['GEN']
            to_bus = bus_mapping['MAIN']
        
        lines.append(f"{from_bus}, {to_bus},'{i+1} ',1,1,1,'TR{i+1}_UP ',   1,   1,   1,'            ',1,1, 1.00000")
        lines.append(f" 0.00400, 0.06500,   70.00")
        lines.append(f"1.00000,     0,1.00000,     0,1.10000,0.90000,1.10000,0.90000,   0,   0,   0.00000,   0.00000,  10,1,0.00000,1.00000,0.00000,'            '")
        lines.append(f"1.00000,   0.0000")
    
    # Distribution Transformers (34.5kV → 13.8kV to halls)
    for i, hall_bus in enumerate(bus_mapping['HALL']):
        if gen_type in ['mtm', 'double']:
            from_bus = bus_mapping['MAIN_A'] if i < 2 else bus_mapping['MAIN_B']
        else:
            from_bus = bus_mapping['MAIN']
        
        lines.append(f"{from_bus}, {hall_bus},'{i+1} ',1,1,1,'T{i+1}_DIST',   1,   1,   1,'            ',1,1, 1.00000")
        lines.append(f" 0.00350, 0.05750,   65.00")
        lines.append(f"1.00000,     0,1.00000,     0,1.10000,0.90000,1.10000,0.90000,   0,   0,   0.00000,   0.00000,  10,1,0.00000,1.00000,0.00000,'            '")
        lines.append(f"1.00000,   0.0000")
    
    lines.append("0 / END OF TRANSFORMER DATA")
    
    # === Remaining sections (empty but required) ===
    lines.append("")
    lines.append("/ AREA DATA")
    lines.append(f"   1,  {bus_mapping['POI']},   0.000,   10.00,'DATACENTER'")
    lines.append("0 / END OF AREA DATA")
    
    for section in [
        "TWO-TERMINAL DC DATA", "VSC DC LINE DATA", "SWITCHED SHUNT DATA",
        "IMPEDANCE CORRECTION DATA", "MULTI-TERMINAL DC DATA", "MULTI-SECTION LINE DATA",
        "ZONE DATA", "INTER-AREA TRANSFER DATA", "OWNER DATA", "FACTS DEVICE DATA"
    ]:
        lines.append("")
        lines.append(f"/ {section}")
        if section == "ZONE DATA":
            lines.append("   1,'ZONE_1'")
        elif section == "OWNER DATA":
            lines.append("   1,'OWNER_1'")
        lines.append(f"0 / END OF {section}")
    
    # End of file
    lines.append("")
    lines.append("Q")
    
    return '\n'.join(lines)


def generate_psse_dyr(config: Dict) -> str:
    """Generate PSS/e DYR file with CMPLDW composite load model."""
    if 'advanced_load' not in config:
        return "! No advanced load data - CMPLDW requires bvNexus calculation\n"
    
    adv = config['advanced_load']
    psse_frac = adv.get('psse_fractions', {})
    
    # Get fractions (percentages, convert to per-unit)
    fel = psse_frac.get('electronic', 73.0) / 100
    motor_total = psse_frac.get('motor', 21.0) / 100
    pfs = psse_frac.get('static', 6.0) / 100
    pf = psse_frac.get('power_factor', 0.99)
    
    # Distribute motor across CMPLDW types
    fma, fmb, fmc, fmd = motor_total * 0.3, motor_total * 0.4, motor_total * 0.2, motor_total * 0.1
    
    cooling = adv.get('cooling_type', '').replace('_', ' ').title()
    iso = adv.get('iso_region', '').upper()
    eq = adv.get('equipment', {})
    
    dyr = []
    dyr.append("! PSS/e CMPLDW Composite Load Model - bvNexus Generated")
    dyr.append(f"! Site: {config.get('project_name', 'Datacenter')}")
    dyr.append(f"! Cooling: {cooling}, ISO: {iso}")
    dyr.append("!")
    dyr.append(f"! FEL (Electronic):  {fel:.6f} ({fel*100:.1f}%) - GPU/TPU")
    dyr.append(f"! FMA (Motor A):     {fma:.6f} ({fma*100:.1f}%) - Fans/Pumps")
    dyr.append(f"! FMB (Motor B):     {fmb:.6f} ({fmb*100:.1f}%) - Chillers")
    dyr.append(f"! FMC (Motor C):     {fmc:.6f} ({fmc*100:.1f}%) - Compressors")
    dyr.append(f"! FMD (Motor D):     {fmd:.6f} ({fmd*100:.1f}%) - VFD Equipment")
    dyr.append(f"! PFS (Static):      {pfs:.6f} ({pfs*100:.1f}%) - Lighting")
    dyr.append(f"! Power Factor:      {pf:.4f}")
    dyr.append(f"! Equipment: {eq.get('ups',0)} UPS, {eq.get('chillers',0)} Chillers, {eq.get('crah',0)} CRAH, {eq.get('pumps',0)} Pumps")
    dyr.append("!")
    
    for hall in range(1, 5):
        bus_num = 5 + hall  # Bus 6-9
        dyr.append(f"! Hall {hall}")
        dyr.append(f"{bus_num} 'CMPLDW' 1 {fel:.6f} {fma:.6f} {fmb:.6f} {fmc:.6f} {fmd:.6f} {pfs:.6f} {pf:.4f} /")
    
    return "\n".join(dyr)


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
        {'BUS': 150, 'NAME': 'SOLAR_01', 'BASKV': 13.8, 'VM_PU': 1.000, 'VA_DEG': 0.8, 
         'P_GEN_MW': 58.0, 'Q_GEN_MVAR': 0.0, 'P_LOAD_MW': 0.0, 'Q_LOAD_MVAR': 0.0},
        {'BUS': 200, 'NAME': 'MAIN_BUS', 'BASKV': 13.8, 'VM_PU': 1.000, 'VA_DEG': 0.0, 
         'P_GEN_MW': 0.0, 'Q_GEN_MVAR': 0.0, 'P_LOAD_MW': 200.0, 'Q_LOAD_MVAR': 66.0},
    ])


def generate_sample_windchill_component_df(config: Dict) -> pd.DataFrame:
    """Generate sample Windchill RAM component dataframe with actual equipment counts."""
    rows = []
    
    # === COOLING & ELECTRICAL EQUIPMENT (from bvNexus Advanced Load Data) ===
    if 'advanced_load' in config:
        adv = config['advanced_load']
        eq = adv.get('equipment', {})
        cooling = adv.get('cooling_type', 'air_cooled').replace('_', ' ').title()
        
        # UPS Systems
        n_ups = eq.get('ups', 0)
        if n_ups > 0:
            rows.append({
                'Component_ID': 'UPS_SYSTEM',
                'Component_Name': f'UPS Modules (N+1 Configuration)',
                'Component_Type': 'UPS_MODULE',
                'Subsystem': 'Electrical Distribution',
                'Redundancy_Group': 'UPS',
                'Capacity_MW': 2.5,  # Typical UPS module size
                'Quantity': n_ups,
                'MTBF_Hours': 50000,
                'MTTR_Hours': 24,
                'Failure_Rate_Per_Hour': 2.0e-5,
                'Availability': 0.9995,
                'Distribution': 'Exponential',
                'Weibull_Beta': 1.0,
                'Weibull_Eta': 50000,
                'Operating_Hours_Per_Year': 8760,
                'PM_Interval_Hours': 2190,  # Quarterly
                'Notes': f'bvNexus calculated: {n_ups} units required for {config.get("peak_load_mw", 200)} MW'
            })
        
        # Chillers
        n_chillers = eq.get('chillers', 0)
        if n_chillers > 0:
            rows.append({
                'Component_ID': 'CHILLER',
                'Component_Name': f'{cooling} Chiller',
                'Component_Type': 'CHILLER',
                'Subsystem': 'Cooling System',
                'Redundancy_Group': 'COOLING_PRIMARY',
                'Capacity_MW': 5.0,  # Typical chiller capacity
                'Quantity': n_chillers,
                'MTBF_Hours': 30000,
                'MTTR_Hours': 48,
                'Failure_Rate_Per_Hour': 3.33e-5,
                'Availability': 0.9984,
                'Distribution': 'Weibull',
                'Weibull_Beta': 1.5,
                'Weibull_Eta': 35000,
                'Operating_Hours_Per_Year': 8760,
                'PM_Interval_Hours': 4380,  # Semi-annual
                'Notes': f'bvNexus calculated: {n_chillers} units for {cooling} cooling'
            })
        
        # CRAH Units
        n_crah = eq.get('crah', 0)
        if n_crah > 0:
            rows.append({
                'Component_ID': 'CRAH',
                'Component_Name': 'CRAH Units (Computer Room Air Handler)',
                'Component_Type': 'CRAH_UNIT',
                'Subsystem': 'Cooling System',
                'Redundancy_Group': 'COOLING_DISTRIBUTION',
                'Capacity_MW': 0.2,  # Typical CRAH capacity
                'Quantity': n_crah,
                'MTBF_Hours': 40000,
                'MTTR_Hours': 12,
                'Failure_Rate_Per_Hour': 2.5e-5,
                'Availability': 0.9997,
                'Distribution': 'Exponential',
                'Weibull_Beta': 1.0,
                'Weibull_Eta': 40000,
                'Operating_Hours_Per_Year': 8760,
                'PM_Interval_Hours': 2190,  # Quarterly
                'Notes': f'bvNexus calculated: {n_crah} units required'
            })
        
        # Pumps
        n_pumps = eq.get('pumps', 0)
        if n_pumps > 0:
            rows.append({
                'Component_ID': 'PUMP',
                'Component_Name': 'Chilled Water Pumps',
                'Component_Type': 'PUMP',
                'Subsystem': 'Cooling System',
                'Redundancy_Group': 'PUMPS',
                'Capacity_MW': 0.5,  # Typical pump power
                'Quantity': n_pumps,
                'MTBF_Hours': 60000,
                'MTTR_Hours': 8,
                'Failure_Rate_Per_Hour': 1.67e-5,
                'Availability': 0.9999,
                'Distribution': 'Exponential',
                'Weibull_Beta': 1.0,
                'Weibull_Eta': 60000,
                'Operating_Hours_Per_Year': 8760,
                'PM_Interval_Hours': 4380,  # Semi-annual
                'Notes': f'bvNexus calculated: {n_pumps} units with N+2 redundancy'
            })
    
    # === GENERATION EQUIPMENT ===
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
    
    # Solar PV (NEW)
    if config.get('solar_mw', 0) > 0:
        rows.append({
            'Component_ID': 'SOLAR_01',
            'Component_Name': f"Solar PV Array ({config.get('solar_mw', 0):.0f} MW)",
            'Component_Type': 'SOLAR_PV',
            'Subsystem': 'Renewable Generation',
            'Redundancy_Group': 'RENEWABLE',
            'Capacity_MW': config.get('solar_mw', 0),
            'MTBF_Hours': 175200,
            'MTTR_Hours': 168,
            'Failure_Rate_Per_Hour': 5.71e-6,
            'Availability': 0.9990,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 175200,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 8760,
        })
    
    # === ELECTRICAL COMPONENTS (Based on Topology) ===
    # Get electrical configurations
    poi_config = config.get('suggested_poi', 'radial')
    gen_config = config.get('suggested_gen', 'mtm')
    dist_config = config.get('suggested_dist', 'catcher')
    
    poi_type = ELECTRICAL_SPECS['poi'][poi_config]['type']
    gen_type = ELECTRICAL_SPECS['generation'][gen_config]['type']
    dist_type = ELECTRICAL_SPECS['distribution'][dist_config]['type']
    
    # POI Transformers (345kV → 34.5kV)
    n_poi_xfmrs = 2 if poi_type in ['ring', 'bah'] else 1
    for i in range(n_poi_xfmrs):
        rows.append({
            'Component_ID': f'XFMR_POI_T{i+1}',
            'Component_Name': f'POI Transformer {i+1} (345kV→34.5kV)',
            'Component_Type': 'TRANSFORMER_HV',
            'Subsystem': 'POI / Utility Interconnection',
            'Redundancy_Group': 'POI_TRANSFORMERS',
            'Capacity_MW': 300,
            'MTBF_Hours': 175200,  # 20 years
            'MTTR_Hours': 720,  # 30 days (critical replacement)
            'Failure_Rate_Per_Hour': 5.71e-6,
            'Availability': 0.9959,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 175200,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 17520,  # 2 years
            'Notes': 'Critical HV transformer - extended outage on failure'
        })
    
    # Step-Up Transformers (13.8kV → 34.5kV)
    n_recip = config.get('n_recip', 0)
    n_turbine = config.get('n_turbine', 0)
    n_step_up = min(6, max(2, (n_recip + n_turbine) // 3))
    
    for i in range(n_step_up):
        rows.append({
            'Component_ID': f'XFMR_TR{i+1}',
            'Component_Name': f'Step-Up Transformer TR{i+1} (13.8kV→34.5kV)',
            'Component_Type': 'TRANSFORMER_MV',
            'Subsystem': 'Generation Step-Up',
            'Redundancy_Group': 'STEP_UP_TRANSFORMERS',
            'Capacity_MW': 70,
            'MTBF_Hours': 87600,  # 10 years
            'MTTR_Hours': 168,  # 1 week
            'Failure_Rate_Per_Hour': 1.14e-5,
            'Availability': 0.9981,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 87600,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 8760,  # 1 year
            'Notes': 'N-1 redundant - connects gen bus to main bus'
        })
    
    # Distribution Transformers (34.5kV → 13.8kV to halls)
    for i in range(4):
        rows.append({
            'Component_ID': f'XFMR_DIST_T{i+1}',
            'Component_Name': f'Distribution Transformer T-{i+1} (Hall {i+1})',
            'Component_Type': 'TRANSFORMER_MV',
            'Subsystem': 'Distribution to Data Halls',
            'Redundancy_Group': f'HALL_{i+1}_ELECTRICAL',
            'Capacity_MW': 65,
            'MTBF_Hours': 87600,
            'MTTR_Hours': 120,  # 5 days
            'Failure_Rate_Per_Hour': 1.14e-5,
            'Availability': 0.9986,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 87600,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 8760,
            'Notes': f'Primary feed to Hall {i+1}'
        })
    
    # Circuit Breakers (Topology-dependent)
    # Main bus breakers
    if gen_type == 'mtm':
        rows.append({
            'Component_ID': 'BKR_MAIN_TIE',
            'Component_Name': 'Main Bus Tie Breaker (34.5kV)',
            'Component_Type': 'CIRCUIT_BREAKER_MV',
            'Subsystem': 'Main Bus Protection',
            'Redundancy_Group': 'MAIN_BUS',
            'Capacity_MW': 300,
            'MTBF_Hours': 175200,
            'MTTR_Hours': 24,
            'Failure_Rate_Per_Hour': 5.71e-6,
            'Availability': 0.9999,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 175200,
            'Operating_Hours_Per_Year': 0,  # Normally open
            'PM_Interval_Hours': 8760,
            'Notes': 'Normally open - MTM topology tie breaker'
        })
    
    # STS Switches (if catcher topology)
    if dist_type == 'catcher':
        # Reserve transformer
        rows.append({
            'Component_ID': 'XFMR_RESERVE',
            'Component_Name': 'Reserve Bus Transformer (34.5kV→34.5kV)',
            'Component_Type': 'TRANSFORMER_MV',
            'Subsystem': 'Reserve/Redundant Path',
            'Redundancy_Group': 'RESERVE_BUS',
            'Capacity_MW': 60,
            'MTBF_Hours': 87600,
            'MTTR_Hours': 168,
            'Failure_Rate_Per_Hour': 1.14e-5,
            'Availability': 0.9981,
            'Distribution': 'Exponential',
            'Weibull_Beta': 1.0,
            'Weibull_Eta': 87600,
            'Operating_Hours_Per_Year': 8760,
            'PM_Interval_Hours': 8760,
            'Notes': 'Reserve/backup transformer for catcher topology'
        })
        
        for i in range(4):
            rows.append({
                'Component_ID': f'STS_{i+1}',
                'Component_Name': f'Static Transfer Switch - Hall {i+1}',
                'Component_Type': 'STS',
                'Subsystem': 'Distribution to Data Halls',
                'Redundancy_Group': f'HALL_{i+1}_ELECTRICAL',
                'Capacity_MW': 50,
                'MTBF_Hours': 100000,  # Very reliable
                'MTTR_Hours': 4,  # Quick replacement
                'Failure_Rate_Per_Hour': 1.0e-5,
                'Availability': 0.9999,
                'Distribution': 'Exponential',
                'Weibull_Beta': 1.0,
                'Weibull_Eta': 100000,
                'Operating_Hours_Per_Year': 8760,
                'PM_Interval_Hours': 4380,  # 6 months
                'Transfer_Time_ms': 4,
                'Notes': f'Auto-transfer to reserve on primary failure - Hall {i+1}'
            })
    
    # Switchgear / Bus Infrastructure
    rows.append({
        'Component_ID': 'BUS_MAIN_345KV',
        'Component_Name': '345kV POI Bus Infrastructure',
        'Component_Type': 'BUS_INFRASTRUCTURE',
        'Subsystem': 'POI / Utility Interconnection',
        'Redundancy_Group': 'POI_BUS',
        'Capacity_MW': 600,
        'MTBF_Hours': 262800,  # 30 years
        'MTTR_Hours': 48,
        'Failure_Rate_Per_Hour': 3.80e-6,
        'Availability': 0.9998,
        'Distribution': 'Exponential',
        'Weibull_Beta': 1.0,
        'Weibull_Eta': 262800,
        'Operating_Hours_Per_Year': 8760,
        'PM_Interval_Hours': 17520,
        'Notes': 'High voltage bus and associated protection/metering'
    })
    
    rows.append({
        'Component_ID': 'BUS_MAIN_34_5KV',
        'Component_Name': '34.5kV Main Facility Bus',
        'Component_Type': 'BUS_INFRASTRUCTURE',
        'Subsystem': 'Main Bus Protection',
        'Redundancy_Group': 'MAIN_BUS',
        'Capacity_MW': 400,
        'MTBF_Hours': 175200,
        'MTTR_Hours': 36,
        'Failure_Rate_Per_Hour': 5.71e-6,
        'Availability': 0.9998,
        'Distribution': 'Exponential',
        'Weibull_Beta': 1.0,
        'Weibull_Eta': 175200,
        'Operating_Hours_Per_Year': 8760,
        'PM_Interval_Hours': 8760,
        'Notes': 'Medium voltage distribution bus'
    })
    
    rows.append({
        'Component_ID': 'BUS_GEN_13_8KV',
        'Component_Name': '13.8kV Generation Bus',
        'Component_Type': 'BUS_INFRASTRUCTURE',
        'Subsystem': 'Generation Step-Up',
        'Redundancy_Group': 'GEN_BUS',
        'Capacity_MW': 250,
        'MTBF_Hours': 87600,
        'MTTR_Hours': 24,
        'Failure_Rate_Per_Hour': 1.14e-5,
        'Availability': 0.9997,
        'Distribution': 'Exponential',
        'Weibull_Beta': 1.0,
        'Weibull_Eta': 87600,
        'Operating_Hours_Per_Year': 8760,
        'PM_Interval_Hours': 8760,
        'Notes': 'Generator collection bus'
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

# INTERACTIVE PLOT LY DIAGRAM
from app.utils.plotly_diagram import create_interactive_single_line_diagram

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
    
    # Solar PV (top center-left) - NEW
    solar_mw = config.get('solar_mw', 0)
    if solar_mw > 0:
        svg += f'''
        <line x1="350" y1="250" x2="350" y2="150" class="branch"/>
        <rect x="325" y="120" width="50" height="30" style="fill: #FFA726; stroke: #333; stroke-width: 2;"/>
        <text x="350" y="138" class="text" text-anchor="middle" style="fill: white; font-weight: bold;">☀</text>
        <text x="350" y="95" class="text" text-anchor="middle">SOLAR</text>
        <text x="350" y="110" class="text" text-anchor="middle">{solar_mw:.0f} MW</text>
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
    """Generate complete ETAP import package matching engineering drawing topology."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # === 1. ELECTRICAL ARCHITECTURE (Configuration Summary) ===
        poi_config = config.get('suggested_poi', 'radial')
        gen_config = config.get('suggested_gen', 'mtm')
        dist_config = config.get('suggested_dist', 'catcher')
        
        n_recip = config.get('n_recip', 0)
        n_turbine = config.get('n_turbine', 0)
        n_transformers = min(6, max(2, (n_recip + n_turbine) // 3))
        
        arch_data = {
            'Parameter': [
                'POI Configuration',
                'POI Voltage',
                'POI Transformer Count',
                'Main Bus Voltage',
                'Generation Bus Configuration',
                'Generation Voltage',
                'Step-Up Transformer Count',
                'Distribution Configuration', 
                'Distribution Voltage',
                'Data Hall Count',
                'Total Generators',
                'Redundancy Level',
                'Peak Load (MW)'
            ],
            'Value': [
                ELECTRICAL_SPECS['poi'][poi_config]['label'],
                '345 kV',
                '2' if ELECTRICAL_SPECS['poi'][poi_config]['type'] in ['ring', 'bah'] else '1',
                '34.5 kV',
                ELECTRICAL_SPECS['generation'][gen_config]['label'],
                '13.8 kV',
                f'{n_transformers} (TR1-TR{n_transformers})',
                ELECTRICAL_SPECS['distribution'][dist_config]['label'],
                '13.8 kV to data halls',
                '4',
                f'{n_recip + n_turbine} ({n_recip} recip + {n_turbine} turbines)',
                config.get('redundancy', 'N+0'),
                f"{config.get('peak_load_mw', 200):.1f}"
            ],
            'Notes': [
                'See Single Line Diagram tab in System Overview',
                'Utility interconnection voltage',
                'T1, T2 step down 345kV to 34.5kV',
                'Facility distribution voltage',
                'Affects bus and breaker topology',
                'Generators output at 13.8kV',
                'Step up from 13.8kV gen bus to 34.5kV main bus',
                'Determines STS and reserve requirements',
                'Final distribution to IT equipment',
                'Standard 4-hall datacenter configuration',
                'Total thermal + renewable generation',
                'Equipment and path redundancy',
                'Critical IT load demand'
            ]
        }
        arch_df = pd.DataFrame(arch_data)
        arch_df.to_excel(writer, sheet_name='Electrical_Architecture', index=False)
        
        # === 2. BUS DATA ===
        bus_df = generate_etap_bus_data(config)
        bus_df.to_excel(writer, sheet_name='Bus_Data', index=False)
        
        # === 3. TRANSFORMER DATA ===
        xfmr_df = generate_etap_transformer_data(config)
        xfmr_df.to_excel(writer, sheet_name='Transformer_Data', index=False)
        
        # === 4. BREAKER/SWITCH DATA ===
        breaker_df = generate_etap_breaker_data(config)
        breaker_df.to_excel(writer, sheet_name='Breaker_Data', index=False)
        
        # === 5. EQUIPMENT DATA ===
        equip_df = generate_sample_etap_equipment_df(config)
        equip_df.to_excel(writer, sheet_name='Equipment', index=False)
        
        # === 6. LOAD DATA ===
        load_df = generate_etap_load_data(config)
        load_df.to_excel(writer, sheet_name='Load_Data', index=False)
        
        # === 7. SCENARIOS ===
        scenarios_df = generate_sample_etap_scenarios_df(config)
        scenarios_df.to_excel(writer, sheet_name='Scenarios', index=False)
        
        # === 8. IMPORT INSTRUCTIONS ===
        instructions = pd.DataFrame([
            {'Step': 1, 'Instruction': 'Review Electrical_Architecture sheet for system topology'},
            {'Step': 2, 'Instruction': 'Open ETAP and create new project'},
            {'Step': 3, 'Instruction': 'Import Bus_Data: Go to Study → DataX Import → Buses'},
            {'Step': 4, 'Instruction': 'Import Transformer_Data: DataX Import → Transformers'},
            {'Step': 5, 'Instruction': 'Import Breaker_Data: DataX Import → Circuit Breakers'},
            {'Step': 6, 'Instruction': 'Import Equipment: DataX Import → Generators/Motors'},
            {'Step': 7, 'Instruction': 'Import Load_Data: DataX Import → Loads'},
            {'Step': 8, 'Instruction': 'Create study cases using Scenarios sheet reference'},
            {'Step': 9, 'Instruction': 'Build one-line diagram matching System Overview'},
            {'Step': 10, 'Instruction': 'Run Load Flow, Short Circuit, and Arc Flash studies'},
            {'Step': 11, 'Instruction': 'Export results via Results Analyzer → Excel for import back to bvNexus'},
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
    
    # SITE SELECTOR at top of page
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        # Load available sites
        if 'sites_list' not in st.session_state or not st.session_state.sites_list:
            from app.utils.site_backend import load_sites_from_google_sheets
            try:
                st.session_state.sites_list = load_sites_from_google_sheets()
            except:
                st.session_state.sites_list = []
        
        if st.session_state.sites_list:
            site_names = [s.get('name', 'Unnamed') for s in st.session_state.sites_list]
            
            # Get current selection
            current_idx = 0
            if 'current_site' in st.session_state and st.session_state.current_site:
                try:
                    current_idx = site_names.index(st.session_state.current_site)
                except ValueError:
                    pass
            
            selected_site = st.selectbox(
                "📍 Select Site for Export",
                options=site_names,
                index=current_idx,
                key="integration_export_site_selector"
            )
            
            # Update session state
            if selected_site != st.session_state.get('current_site'):
                st.session_state.current_site = selected_site
                st.rerun()
        else:
            st.warning("⚠️ No sites loaded. Go to Sites page to create a site first.")
    
    with col2:
        if st.button("🔄 Refresh Data", help="Reload site data from Google Sheets"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Sidebar configuration
    st.sidebar.header("📋 Project Configuration")
    
    # NEW: Try to load from session state first
    session_config = get_config_from_session_state()
    
    if session_config:
        # Real optimization data available
        use_sample = st.sidebar.checkbox("Use Sample Data Instead", value=False, 
                                        help="Real optimization data found. Uncheck to use sample data.")
        
        if not use_sample:
            config = session_config
            st.sidebar.success(f"✅ Using: {config['project_name']}")
            st.sidebar.info(f"📊 **Data Source:** Session State\n**Location:** {config.get('location', 'TBD')}\n**ISO:** {config.get('iso', 'TBD')}")
            
            # Show assumptions being used
            with st.sidebar.expander("⚠️ View Assumptions"):
                st.caption("**Assumptions in use:**")
                if 'recip_details' not in config:
                    st.caption("• Recip unit: 18.3 MW (Wärtsilä 34SG)")
                if 'turbine_details' not in config:
                    st.caption("• Turbine unit: 50 MW (GE LM6000)")
                if 'bess_details' not in config:
                    st.caption("• BESS duration: 4 hours")
                st.caption(f"• Voltage: {config['voltage_kv']} kV")
                st.caption(f"• Redundancy: {config['redundancy']}")
        else:
            config = generate_sample_equipment_config()
            st.sidebar.success("✅ Using Dallas Hyperscale DC sample")
    else:
        # No optimization data - use sample or custom
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
    """Render system overview with comprehensive engineering diagrams."""
    st.header("📊 System Overview")
    
    st.markdown("""
    Professional electrical single-line diagrams and site plans synchronized with optimization results.
    Select electrical configurations below to customize the diagrams.
    """)
    
    # Configuration Selectors
    st.subheader("Electrical Configuration")
    col_poi, col_gen, col_dist = st.columns(3)
    
    with col_poi:
        poi_options = list(ELECTRICAL_SPECS['poi'].keys())
        poi_default = config.get('suggested_poi', 'radial')
        # Ensure default is in options
        if poi_default not in poi_options:
            poi_default = poi_options[0]
        
        poi_config = st.selectbox(
            "POI Substation",
            options=poi_options,
            index=poi_options.index(poi_default),
            format_func=lambda x: ELECTRICAL_SPECS['poi'][x]['label'],
            help="Point of Interconnection configuration"
        )
        st.caption(f"**Tier:** {ELECTRICAL_SPECS['poi'][poi_config]['tier']}")
    
    with col_gen:
        gen_options = list(ELECTRICAL_SPECS['generation'].keys())
        gen_default = config.get('suggested_gen', 'mtm')
        if gen_default not in gen_options:
            gen_default = gen_options[0]
        
        gen_config = st.selectbox(
            "Generation Bus",
            options=gen_options,
            index=gen_options.index(gen_default),
            format_func=lambda x: ELECTRICAL_SPECS['generation'][x]['label'],
            help="Medium voltage generation bus topology"
        )
        st.caption(f"**Type:** {ELECTRICAL_SPECS['generation'][gen_config]['desc']}")
    
    with col_dist:
        dist_options = list(ELECTRICAL_SPECS['distribution'].keys())
        dist_default = config.get('suggested_dist', 'catcher')
        if dist_default not in dist_options:
            dist_default = dist_options[0]
        
        dist_config = st.selectbox(
            "Distribution",
            options=dist_options,
            index=dist_options.index(dist_default),
            format_func=lambda x: ELECTRICAL_SPECS['distribution'][x]['label'],
            help="Low voltage distribution architecture"
        )
        st.caption(f"**Type:** {ELECTRICAL_SPECS['distribution'][dist_config]['desc']}")
    
    st.divider()
    
    # Engineering Drawings Tabs
    tab_sld, tab_site, tab_summary = st.tabs([
        "⚡ Single Line Diagram", 
        "🗺️ Site Plan",
        "📋 Equipment Summary"
    ])
    
    with tab_sld:
        st.subheader("Professional Single Line Diagram")
        
        # Create electrical config dict
        electrical_config = {
            'poi_config': poi_config,
            'gen_config': gen_config,
            'dist_config': dist_config
        }
        
        try:
            # Generate comprehensive diagram
            fig = create_professional_single_line_diagram(config, electrical_config)
            st.plotly_chart(fig, use_container_width=True)
            
            # Configuration notes
            st.info(f"""
            **Configuration:** {ELECTRICAL_SPECS['poi'][poi_config]['label']} | 
            {ELECTRICAL_SPECS['generation'][gen_config]['label']} | 
            {ELECTRICAL_SPECS['distribution'][dist_config]['label']}
            """)
            
        except Exception as e:
            st.error(f"Error generating single-line diagram: {e}")
            st.warning("Falling back to simple diagram...")
            # Fallback to simple diagram
            fig = create_interactive_single_line_diagram(config)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab_site:
        st.subheader("Site Plan / Equipment Layout")
        
        # Prepare site data
        site_data = {
            'acreage': config.get('site_acreage', 50),
            'name': config.get('project_name', 'Datacenter Project')
        }
        
        # Add POI config to config dict for site plan
        config['suggested_poi'] = poi_config
        
        try:
            # Generate site plan
            fig = create_site_plan_diagram(config, site_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Site details
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Site Acreage", f"{site_data['acreage']:.1f} acres")
            with col2:
                n_buildings = (1 if config.get('n_recip', 0) > 0 else 0) + config.get('n_turbine', 0) + (1 if config.get('bess_mw', 0) > 0 else 0)
                st.metric("Major Structures", n_buildings)
            with col3:
                st.metric("POI Footprint", f"{FOOTPRINT_LIBRARY.get('substation_345kv_bah' if poi_config == 'breaker_half' else 'substation_345kv_ring', {}).get('acres', 6)} acres")
        
        except Exception as e:
            st.error(f"Error generating site plan: {e}")
            st.info("Site plan could not be generated. Check equipment configuration.")
    
    with tab_summary:
        st.subheader("Configuration Summary")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.metric("Peak Load", f"{config.get('peak_load_mw', 0):.0f} MW")
            
            total_gen = (config.get('n_recip', 0) * config.get('recip_mw_each', 0) + 
                        config.get('n_turbine', 0) * config.get('turbine_mw_each', 0))
            st.metric("Total Generation", f"{total_gen:.0f} MW")
            
            reserve = total_gen - config.get('peak_load_mw', 0)
            st.metric("Reserve Capacity", f"{reserve:.0f} MW", 
                     delta=f"{reserve/config.get('peak_load_mw', 1)*100:.1f}%")
            
            st.metric("BESS", f"{config.get('bess_mw', 0):.0f} MW / {config.get('bess_mwh', 0):.0f} MWh")
        
        with col2:
            if config.get('solar_mw', 0) > 0:
                st.metric("Solar PV", f"{config.get('solar_mw', 0):.0f} MW")
            if config.get('grid_connection_mw', 0) > 0:
                st.metric("Grid Connection", f"{config.get('grid_connection_mw', 0):.0f} MW")
            st.metric("Redundancy", config.get('redundancy', 'N+0'))
            st.metric("Voltage Level", f"{config.get('voltage_kv', 13.8)} kV")
        
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
            {'Equipment': 'Solar PV', 'Count': 1 if config.get('solar_mw', 0) > 0 else 0,
             'Unit Size (MW)': config.get('solar_mw', 0),
             'Total (MW)': config.get('solar_mw', 0)},
            {'Equipment': 'Grid Connection', 'Count': 1 if config.get('grid_connection_mw', 0) > 0 else 0,
             'Unit Size (MW)': config.get('grid_connection_mw', 0),
             'Total (MW)': config.get('grid_connection_mw', 0)},
        ])
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # Equipment specifications (if detailed data available)
        if 'recip_details' in config or 'turbine_details' in config or 'bess_details' in config:
            st.subheader("Detailed Equipment Specifications")
            
            if 'recip_details' in config:
                with st.expander("🔧 Reciprocating Engine Details"):
                    st.json(config['recip_details'])
            
            if 'turbine_details' in config:
                with st.expander("⚙️ Gas Turbine Details"):
                    st.json(config['turbine_details'])
            
            if 'bess_details' in config:
                with st.expander("🔋 BESS Details"):
                    st.json(config['bess_details'])



def render_etap_export(config: Dict):
    """Render ETAP export section with previews."""
    st.header("⚡ ETAP Export")
    
    st.markdown("""
    Generate Excel files for ETAP DataX import. These files can be directly 
    imported into ETAP for load flow, short circuit, and arc flash studies.
    """)
    
    # Check if advanced load data is available
    if 'advanced_load' in config:
        adv = config['advanced_load']
        
        st.success(f"✅ Advanced load model loaded: **{adv['cooling_type'].replace('_', ' ').title()}** cooling @ **{adv['iso_region'].upper()}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Load Composition:**")
            st.write(f"- Electronic (GPU/TPU): {adv['psse_fractions']['electronic']:.1f}%")
            st.write(f"- Motor Load: {adv['psse_fractions']['motor']:.1f}%")
            st.write(f"- Static Load: {adv['psse_fractions']['static']:.1f}%")
            st.write(f"- Power Factor: {adv['psse_fractions']['power_factor']:.3f}")
        
        with col2:
            st.markdown("**Harmonics (IEEE 519):**")
            st.write(f"- THD-V: {adv['harmonics']['thd_v']:.2f}%")
            st.write(f"- THD-I: {adv['harmonics']['thd_i']:.2f}%")
            compliance = "✅ Compliant" if adv['harmonics']['ieee519_compliant'] else "❌ Non-Compliant"
            st.write(f"- IEEE 519: {compliance}")
        
        with col3:
            st.markdown("**Equipment Counts:**")
            st.write(f"- UPS Units: {adv['equipment']['ups']}")
            st.write(f"- Chillers: {adv['equipment']['chillers']}")
            st.write(f"- CRAH Units: {adv['equipment']['crah']}")
            st.write(f"- Pumps: {adv['equipment']['pumps']}")
        
        st.markdown("---")
    else:
        st.warning("⚠️ No advanced load model found. Go to **Load Composer** → Calculate Advanced Model → Save to Google Sheets")
        st.info("💡 Advanced load data includes PSS/e fractions, harmonics, equipment counts, and DR capacity")
        st.markdown("---")
    
    
    # Preview tabs
    preview_tab, results_tab, download_tab = st.tabs([
        "📋 Preview Export Data", "📊 Expected Results Format", "⬇️ Download Files"
    ])
    
    with preview_tab:
        st.info("✅ Export now includes full electrical topology matching System Overview diagrams")
        
        st.subheader("Bus Data Preview")
        bus_df = generate_etap_bus_data(config)
        st.dataframe(bus_df, use_container_width=True, hide_index=True)
        st.caption(f"📊 {len(bus_df)} buses across 3 voltage levels: 345kV (POI) → 34.5kV (Main) → 13.8kV (Gen/Halls)")
        
        st.subheader("Transformer Data Preview")
        xfmr_df = generate_etap_transformer_data(config)
        st.dataframe(xfmr_df, use_container_width=True, hide_index=True)
        st.caption(f"⚡ {len(xfmr_df)} transformers: POI (345→34.5kV), Step-Up (13.8→34.5kV), Distribution (34.5→13.8kV)")
        
        st.subheader("Breaker/Switch Data Preview")
        breaker_df = generate_etap_breaker_data(config)
        st.dataframe(breaker_df, use_container_width=True, hide_index=True)
        st.caption(f"🔌 {len(breaker_df)} breakers/switches including POI, main bus, generation, and STS (if applicable)")
        
        st.subheader("Equipment Data Preview")
        equip_df = generate_sample_etap_equipment_df(config)
        st.dataframe(equip_df, use_container_width=True, hide_index=True)
        
        st.subheader("Load Data Preview")
        load_df = generate_etap_load_data(config)
        st.dataframe(load_df, use_container_width=True, hide_index=True)
        st.caption("📍 Loads distributed across 4 data halls")
        
       
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
    
    # Check if advanced load data is available
    if 'advanced_load' in config:
        adv = config['advanced_load']
        
        st.success(f"✅ PSS/e CMPLDW load model ready: **{adv['cooling_type'].replace('_', ' ').title()}** @ **{adv['iso_region'].upper()}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**CMPLDW Load Fractions:**")
            st.write(f"- Electronic (GPU/TPU): {adv['psse_fractions']['electronic']:.1f}%")
            st.write(f"- Motor Load (Cooling): {adv['psse_fractions']['motor']:.1f}%")
            st.write(f"- Static Load: {adv['psse_fractions']['static']:.1f}%")
            st.write(f"- Power Factor: {adv['psse_fractions']['power_factor']:.3f}")
        
        with col2:
            st.markdown("**ISO Compliance:**")
            st.write(f"- Region: {adv['iso_region'].upper()}")
            st.write(f"- Cooling Type: {adv['cooling_type'].replace('_', ' ').title()}")
            # Show dynamic model requirement based on load size
            peak_mw = config.get('peak_load_mw', 0)
            if peak_mw > 75:
                st.write(f"- Dynamic Model: ✅ Required (>75 MW)")
            else:
                st.write(f"- Dynamic Model: Optional (<75 MW)")
        
        with col3:
            st.markdown("**Equipment for Motor Model:**")
            st.write(f"- Chillers: {adv['equipment']['chillers']}")
            st.write(f"- CRAH Units: {adv['equipment']['crah']}")
            st.write(f"- Pumps: {adv['equipment']['pumps']}")
            st.write(f"- UPS Units: {adv['equipment']['ups']}")
        
        st.markdown("---")
    else:
        st.warning("⚠️ No advanced load model found. Go to **Load Composer** → Calculate Advanced Model → Save to Google Sheets")
        st.info("💡 PSS/e CMPLDW model requires load fractions from bvNexus Load Module")
        st.markdown("---")
    
    
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
        
        col1, col2, col3 = st.columns(3)
        
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
            # Direct DYR download (no generate button needed)
            try:
                dyr_content = generate_psse_dyr(config)
                st.download_button(
                    label="⚡ Download DYR File",
                    data=dyr_content,
                    file_name=f"bvNexus_CMPLDW_{datetime.now().strftime('%Y%m%d_%H%M')}.dyr",
                    mime="text/plain",
                    help="PSS/e CMPLDW composite load model with bvNexus fractions",
                    key="download_dyr_direct"
                )
                # Show status below button
                if 'advanced_load' in config:
                    st.caption("✅ Using bvNexus load composition")
                else:
                    st.caption("⚠️ Using generic defaults")
            except Exception as e:
                st.error(f"❌ DYR Error: {str(e)[:100]}")
                if st.checkbox("Show full error", key="show_dyr_error"):
                    import traceback
                    st.code(traceback.format_exc())
        
        with col3:
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
    
    # Check if advanced load data is available
    if 'advanced_load' in config:
        adv = config['advanced_load']
        
        st.success(f"✅ Equipment reliability data from bvNexus: **{adv['cooling_type'].replace('_', ' ').title()}** cooling system")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Cooling Equipment:**")
            st.write(f"- Chillers: {adv['equipment']['chillers']} units (N+1)")
            st.write(f"- CRAH Units: {adv['equipment']['crah']} units (N+1)")
            st.write(f"- Pumps: {adv['equipment']['pumps']} units (N+2)")
            st.caption("Component counts from load calculation")
        
        with col2:
            st.markdown("**Electrical Equipment:**")
            st.write(f"- UPS Units: {adv['equipment']['ups']} units")
            num_gen = config.get('n_recip', 0) + config.get('n_turbine', 0)
            num_xfmr = max(2, num_gen // 4)  # Estimate transformers
            st.write(f"- Generators: {num_gen} units")
            st.write(f"- Transformers: {num_xfmr} units")
            st.caption("From configuration")
        
        with col3:
            st.markdown("**Reliability Targets:**")
            # Calculate system availability estimate
            # Simplified: assuming series components
            chiller_avail = 0.9998  # Commercial chiller
            ups_avail = 0.9999  # N+1 UPS
            # Simplified calculation
            est_avail = chiller_avail * ups_avail
            st.write(f"- Estimated Availability: {est_avail:.5f}")
            st.write(f"- Annual Downtime: {(1-est_avail)*8760:.1f} hrs")
            st.caption("Preliminary estimate only")
        
        st.markdown("---")
    else:
        st.warning("⚠️ No advanced load model found. Generic equipment counts will be used.")
        st.info("💡 Go to **Load Composer** → Calculate Advanced Model → Save to get actual equipment counts")
        st.markdown("---")
    
    
    # Show RBD diagram
    st.subheader("Reliability Block Diagram")
    # NEW: Interactive Plotly RBD (updates from session state)
    fig_rbd = create_interactive_rbd_diagram(config)
    st.plotly_chart(fig_rbd, use_container_width=True)
    
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
| SOLAR_01     | Solar PV Array | BUS_150 | 13.8     | 58       | 58        | 1.0      | N/A   | N/A    | N/A     | N/A   |

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
| SOLAR_01      | Solar PV Array (58 MW) | SOLAR_PV        | 175200     | 168        | 5.71E-06     | Exponential  | 1.0          |
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
