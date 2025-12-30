"""
Antigravity Energy Optimizer - Configuration Settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"

# =============================================================================
# Backend Configuration
# =============================================================================
# Options: "google_sheets", "sharepoint", "local"
BACKEND = os.getenv("BACKEND", "local")

# Google Sheets
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# SharePoint (future)
SHAREPOINT_SITE = os.getenv("SHAREPOINT_SITE", "")
SHAREPOINT_LIST_NAME = os.getenv("SHAREPOINT_LIST_NAME", "AntigravityProjects")

# =============================================================================
# App Settings
# =============================================================================
APP_NAME = "Antigravity Energy Optimizer"
APP_VERSION = "1.0.0"  # bvNexus Integration: 5 Problem Statements + Phase 1/2 Optimization
APP_ICON = "⚡"
APP_TAGLINE = "Co-located Power, Energy and Load Optimization for AI Datacenters"

# Theme colors (Black & Veatch inspired)
COLORS = {
    "primary": "#1a365d",      # Dark blue
    "secondary": "#2d4a6f",    # Medium blue
    "accent": "#f6ad55",       # Orange accent
    "success": "#48bb78",      # Green
    "warning": "#ecc94b",      # Yellow
    "danger": "#fc8181",       # Red
    "text": "#2d3748",         # Dark gray
    "text_light": "#718096",   # Light gray
    "background": "#f7fafc",   # Off-white
}

# =============================================================================
# Default Values
# =============================================================================
DEFAULT_IT_CAPACITY_MW = 160
DEFAULT_PUE = 1.25
DEFAULT_RACK_UPS_SECONDS = 30
DEFAULT_DESIGN_AMBIENT_F = 95

# Default workload mix (must sum to 1.0)
DEFAULT_WORKLOAD_MIX = {
    "pre_training": 0.40,
    "fine_tuning": 0.15,
    "batch_inference": 0.20,
    "realtime_inference": 0.10,
    "rl_training": 0.05,
    "cloud_hpc": 0.10,
}

# Workload characteristics (for reference)
WORKLOAD_CHARACTERISTICS = {
    "pre_training": {
        "name": "LLM Pre-Training",
        "description": "Sustained high load, checkpointing spikes",
        "utilization_range": (0.85, 0.95),
        "variability": "low",
        "transient_magnitude": (2, 3),
        "color": "#7B68EE",
    },
    "fine_tuning": {
        "name": "Fine-Tuning / Post-Training",
        "description": "Medium duration, moderate variability",
        "utilization_range": (0.60, 0.80),
        "variability": "medium",
        "transient_magnitude": (3, 5),
        "color": "#9370DB",
    },
    "batch_inference": {
        "name": "Inference (Batch)",
        "description": "Queue-based, smoothable, predictable",
        "utilization_range": (0.50, 0.70),
        "variability": "medium",
        "transient_magnitude": (4, 6),
        "color": "#20B2AA",
    },
    "realtime_inference": {
        "name": "Inference (Real-Time)",
        "description": "User-facing, highly variable, bursty",
        "utilization_range": (0.30, 0.60),
        "variability": "high",
        "transient_magnitude": (8, 12),
        "color": "#FF6B6B",
    },
    "rl_training": {
        "name": "Reinforcement Learning",
        "description": "Episodic, simulation bursts, very spiky",
        "utilization_range": (0.40, 0.90),
        "variability": "very_high",
        "transient_magnitude": (10, 15),
        "color": "#FFB347",
    },
    "cloud_hpc": {
        "name": "Traditional Cloud / HPC",
        "description": "Well-understood, lower transient magnitude",
        "utilization_range": (0.40, 0.70),
        "variability": "low",
        "transient_magnitude": (2, 3),
        "color": "#87CEEB",
    },
}

# =============================================================================
# Constraint Defaults
# =============================================================================
DEFAULT_CONSTRAINTS = {
    # Capacity
    "min_capacity_mw": 200,
    "reserve_margin_pct": 10,
    "n_minus_1": True,
    
    # Reliability
    "min_availability_pct": 99.9,
    
    # Performance
    "min_ramp_rate_mw_s": 1.0,  # After UPS smoothing
    "freq_tolerance_hz": 0.5,
    "voltage_tolerance_pct": 5,
    
    # Timeline
    "max_time_to_power_months": 24,
    
    # Environmental
    "max_nox_tpy": 99,  # Minor source threshold
    
    # Economic
    "max_lcoe_per_mwh": 85,
    "max_capex_million": 400,
}

# =============================================================================
# Optimization Settings
# =============================================================================
OPTIMIZER_SETTINGS = {
    "solver": "cbc",  # "gurobi", "cbc", "glpk"
    "solver_options": {
        "MIPGap": 0.001,
        "TimeLimit": 300,  # seconds
    },
    "n_scenarios": 100,
    "n_pareto_points": 15,
}

# =============================================================================
# RAM Analysis Defaults
# =============================================================================
# Equipment failure data (Forced Outage Rate, MTBF hours, MTTR hours)
RAM_DEFAULTS = {
    "recip_engine": {"for_pct": 2.5, "mtbf_hrs": 2500, "mttr_hrs": 24},
    "gas_turbine": {"for_pct": 3.0, "mtbf_hrs": 2000, "mttr_hrs": 48},
    "bess": {"for_pct": 0.5, "mtbf_hrs": 8760, "mttr_hrs": 4},
    "solar_pv": {"for_pct": 2.0, "mtbf_hrs": 4380, "mttr_hrs": 8},
    "grid_import": {"for_pct": 0.03, "mtbf_hrs": 35000, "mttr_hrs": 2},
    "transformer": {"for_pct": 0.1, "mtbf_hrs": 100000, "mttr_hrs": 72},
    "switchgear": {"for_pct": 0.05, "mtbf_hrs": 50000, "mttr_hrs": 8},
}

# =============================================================================
# PUE Seasonal Factors
# =============================================================================
PUE_SEASONAL = {
    "winter_low": 1.15,
    "spring_fall": 1.20,
    "summer_avg": 1.25,
    "summer_peak": 1.35,
}

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# bvNexus Integration: Problem Statements
# =============================================================================
PROBLEM_STATEMENTS = {
    1: {
        'name': 'Greenfield Datacenter',
        'short_name': 'Greenfield',
        'icon': '🏗️',
        'objective': 'Minimize LCOE',
        'question': "What's the cheapest way to reliably serve my known load trajectory?",
        'key_output': 'Equipment sizing + dispatch',
        'color': '#48bb78',  # Green
    },
    2: {
        'name': 'Brownfield Expansion',
        'short_name': 'Brownfield',
        'icon': '📈',
        'objective': 'Maximize Load',
        'question': "How much additional load can I add while keeping all-in power cost below $X/MWh?",
        'key_output': 'Expansion capacity',
        'color': '#4299e1',  # Blue
    },
    3: {
        'name': 'Land Development',
        'short_name': 'Land Dev',
        'icon': '🗺️',
        'objective': 'Maximize Firm Power',
        'question': "How much power can I develop on this site, and how does that change with customer flexibility?",
        'key_output': 'Power potential matrix',
        'color': '#9f7aea',  # Purple
    },
    4: {
        'name': 'Grid Services',
        'short_name': 'Grid Services',
        'icon': '🔌',
        'objective': 'Maximize DR Revenue',
        'question': "What grid services should I participate in, and what's the value?",
        'key_output': 'Service enrollment + revenue',
        'color': '#ed8936',  # Orange
    },
    5: {
        'name': 'Bridge Power Transition',
        'short_name': 'Bridge Power',
        'icon': '🌉',
        'objective': 'Minimize NPV',
        'question': "What's the optimal temporary generation strategy while waiting for grid interconnection?",
        'key_output': 'Transition timeline',
        'color': '#e53e3e',  # Red
    },
}

# =============================================================================
# bvNexus Integration: Optimization Tiers
# =============================================================================
OPTIMIZATION_TIERS = {
    1: {
        'name': 'Heuristic Screening',
        'runtime': '30-60 seconds',
        'accuracy': '±50% (Class 5)',
        'label': 'Indicative Only',
        'description': 'Quick feasibility check for rapid iteration',
    },
    2: {
        'name': 'MILP Design',
        'runtime': '5-60 minutes',
        'accuracy': '±20% (Class 3)',
        'label': 'Preliminary Design',
        'description': 'Full optimization with HiGHS solver',
    },
    3: {
        'name': 'LP Validation',
        'runtime': '15-30 minutes',
        'accuracy': '±15% (Class 3)',
        'label': 'Validated Design',
        'description': 'Full 8760 dispatch validation at 15-min resolution',
    },
}

# =============================================================================
# bvNexus Integration: Equipment Defaults
# =============================================================================
EQUIPMENT_DEFAULTS = {
    'recip': {
        'capacity_mw': 18.3,
        'heat_rate_btu_kwh': 7700,
        'nox_lb_mwh': 0.10,  # POST-SCR (Modern Tier 4F with SCR: 0.07-0.15 lb/MWh, using mid-range)
        'co_lb_mwh': 0.40,
        'capex_per_kw': 1650,
        'vom_per_mwh': 8.50,
        'fom_per_kw_yr': 18.50,
        'availability': 0.975,
        'lead_time_months': 18,
        'land_acres_per_mw': 0.5,  # Onsite generation land use
        'ramp_rate_mw_min': 3.0,
        # NEW fields for heuristic calculations
        'min_load_pct': 0.30,           # 30% minimum stable load
        'start_time_min': 5,            # 5-minute hot start
        'nox_lb_mmbtu': 0.065,          # NOx per fuel input (alternative calc)
        'gas_mcf_per_mwh': 7.42,        # Gas consumption rate
    },
    'turbine': {
        'capacity_mw': 50.0,
        'heat_rate_btu_kwh': 8500,  # Simple Cycle (higher than combined cycle 6500-7000)
        'nox_lb_mwh': 0.12,  # POST-SCR Simple Cycle (0.08-0.15 lb/MWh range, using mid-high)
        'co_lb_mwh': 0.15,
        'capex_per_kw': 1300,
        'vom_per_mwh': 6.50,
        'fom_per_kw_yr': 12.50,
        'availability': 0.95,
        'lead_time_months': 24,
        'land_acres_per_mw': 0.3,
        'ramp_rate_mw_min': 8.0,
        # NEW fields
        'min_load_pct': 0.50,           # 50% minimum stable load (simple cycle)
        'start_time_min': 15,           # 15-minute hot start
        'nox_lb_mmbtu': 0.029,          # NOx per fuel input
        'gas_mcf_per_mwh': 8.20,        # Gas consumption rate
    },
    'bess': {
        'power_mw': 50.0,
        'duration_hours': 4,
        'roundtrip_efficiency': 0.90,
        'capex_per_kwh': 236,
        'degradation_per_kwh': 0.03,
        'availability': 0.995,
        'lead_time_months': 12,
        'land_acres_per_mwh': 0.01,
        'ramp_rate_mw_min': 50.0,  # Very fast
        # NEW fields
        'max_soc': 0.95,                # Maximum state of charge
        'min_soc': 0.10,                # Minimum state of charge
        'calendar_life_years': 15,
        'cycle_life': 4000,             # Full equivalent cycles
        'c_rate_max': 0.5,              # Max C-rate (0.5 = 2-hour discharge)
    },
    'solar': {
        'capex_per_w_dc': 0.95,
        'capacity_factor': 0.25,
        'availability': 0.995,
        'lead_time_months': 12,
        'land_acres_per_mw': 5.0,
        # NEW fields
        'vom_per_mwh': 0.0,             # Minimal O&M
        'fom_per_kw_yr': 12.0,          # $12/kW-yr fixed O&M
        'degradation_pct_yr': 0.005,    # 0.5% annual degradation
        'dc_ac_ratio': 1.3,             # DC/AC ratio (inverter sizing)
    },
    'grid': {
        'availability': 0.9997,
        'lead_time_months': 60,  # 5 years typical (can bridge to full grid)
        # NEW fields
        'default_price_mwh': 65.0,      # Wholesale energy price
        'demand_charge_kw_mo': 15.0,    # $/kW-month demand charge
        'interconnection_cost_mw': 100_000,  # $/MW CIAC (Contribution in Aid of Construction)
        'max_ciac_threshold': 500_000_000,  # $500M max CIAC before cost prohibitive
        'lcoe_threshold': 180.0,  # $/MWh - cost prohibitive above this
        'capacity_charge_kw_yr': 180.0,  # $/kW-year capacity charge (for LCOE calc)
        'standby_charge_kw_mo': 5.0,  # $/kW-month standby/backup charge
    },
    'rental': {
        # NEW: Rental generator parameters for Problem 5 (Bridge Power)
        'capex_per_kw': 0,              # No CAPEX (rental)
        'rental_cost_kw_month': 50,     # $50/kW-month rental
        'fuel_included': False,         # Fuel separate
        'heat_rate_btu_kwh': 9500,      # Less efficient than owned
        'nox_lb_mwh': 0.80,             # Higher emissions (older units)
        'availability': 0.92,           # Lower availability
        'lead_time_months': 2,          # Fast deployment
        'mobilization_cost': 50000,     # Per-unit mobilization
    }
}

# Capacity Credits for Firm Capacity Calculation
# Conservative values for datacenter 24/7 load reliability
CAPACITY_CREDITS = {
    'solar': 0.10,      # 10% - Conservative for 24/7 load (vs 15-25% ISO peak)
    'bess': 0.50,       # 50% - Very conservative (vs 80-95% ISO duration-based)
    'recip': 1.00,      # 100% - Fully dispatchable thermal
    'turbine': 1.00,    # 100% - Fully dispatchable thermal
    'grid': 1.00,       # 100% - Fully firm import
}

# Rationale:
# - Solar: 10% accounts for some daytime contribution, but DC load is 24/7
# - BESS: 50% very conservative due to duration limits and cycling constraints
# - Thermal/Grid: 100% true firm capacity, dispatchable anytime

# =============================================================================
# bvNexus Integration: Economic Parameters
# =============================================================================
ECONOMIC_DEFAULTS = {
    'discount_rate': 0.08,           # 8%
    'project_life_years': 20,
    'fuel_price_mmbtu': 3.50,        # $/MMBtu
    'fuel_escalation_rate': 0.025,   # 2.5% annual
    'itc_rate': 0.30,                # 30% ITC for solar/BESS
    'crf_20yr_8pct': 0.1019,         # Capital recovery factor
    # NEW fields for improved calculations
    'inflation_rate': 0.025,            # General inflation
    'electricity_escalation': 0.02,     # Grid price escalation
    'residual_value_pct': 0.10,         # 10% residual at end of life
    'debt_fraction': 0.70,              # 70% debt financing
    'debt_interest_rate': 0.06,         # 6% interest on debt
    'equity_return': 0.12,              # 12% required equity return
}

# =============================================================================
# bvNexus Integration: Constraint Defaults
# =============================================================================
CONSTRAINT_DEFAULTS = {
    'nox_tpy_annual': 100,           # Minor source threshold
    'co_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 500,
    'grid_import_mw': 0,             # Until grid available
    'n_minus_1_required': True,
    'min_availability_pct': 99.5,
    # NEW fields for constraint tracking
    'title_v_threshold_tpy': 100,       # Title V permit threshold
    'psd_threshold_tpy': 250,           # PSD major source threshold
    'max_thermal_footprint_acres': 50,  # Max land for thermal plant
    'min_firm_capacity_mw': 0,          # Minimum firm capacity
    'max_unserved_energy_pct': 0.1,     # 0.1% max unserved energy
}

# =============================================================================
# bvNexus Integration: AI Workload Flexibility Parameters
# =============================================================================
WORKLOAD_FLEXIBILITY = {
    'pre_training': {
        'flexibility_pct': 0.30,     # 20-40%
        'response_time_min': 60,
        'checkpoint_overhead_pct': 0.05,
        'description': 'Batch-oriented, checkpoint-capable, hours to days',
        'typical_load_share': 0.40,     # NEW: Typical share of load
    },
    'fine_tuning': {
        'flexibility_pct': 0.50,     # 40-60%
        'response_time_min': 30,
        'checkpoint_overhead_pct': 0.03,
        'description': 'Shorter jobs, more interruptible',
        'typical_load_share': 0.15,
    },
    'batch_inference': {
        'flexibility_pct': 0.90,     # 80-100%
        'response_time_min': 15,
        'checkpoint_overhead_pct': 0.01,
        'description': 'Deferrable, queue-based',
        'typical_load_share': 0.20,
    },
    'real_time_inference': {
        'flexibility_pct': 0.05,     # 0-10%
        'response_time_min': 0,
        'checkpoint_overhead_pct': 0.0,
        'description': 'Latency-critical, minimal flexibility',
        'typical_load_share': 0.15,
    },
    'cloud_hpc': {
        'flexibility_pct': 0.70,
        'response_time_min': 15,
        'checkpoint_overhead_pct': 0.02,
        'description': 'General cloud compute, schedulable',
        'typical_load_share': 0.10,
    },
}

# =============================================================================
# bvNexus Integration: Demand Response Services
# =============================================================================
DR_SERVICES = {
    'ers_10': {
        'name': 'ERS-10 (10-minute response)',
        'response_time_min': 10,
        'payment_mw_hr': 15.0,          # $/MW-hr availability
        'activation_mwh': 100.0,        # $/MWh when called
        'expected_hours_yr': 100,       # Expected dispatch hours
        'min_capacity_mw': 1.0,
        'min_duration_hours': 1,
        'compatible_workloads': ['batch_inference'],
    },
    'ers_30': {
        'name': 'ERS-30 (30-minute response)',
        'response_time_min': 30,
        'payment_mw_hr': 8.0,
        'activation_mwh': 75.0,
        'expected_hours_yr': 150,
        'min_capacity_mw': 1.0,
        'min_duration_hours': 2,
        'compatible_workloads': ['fine_tuning', 'batch_inference'],
    },
    'economic_dr': {
        'name': 'Economic DR (Day-ahead)',
        'response_time_min': 1440,      # Day-ahead
        'payment_mw_hr': 0.0,           # No availability payment
        'activation_mwh': 150.0,        # $/MWh when called
        'expected_hours_yr': 50,
        'min_capacity_mw': 5.0,
        'min_duration_hours': 4,
        'compatible_workloads': ['pre_training', 'fine_tuning', 'batch_inference'],
    },
    'capacity': {
        'name': 'Capacity Market',
        'response_time_min': 60,
        'payment_kw_yr': 50.0,          # $/kW-year
        'activation_mwh': 0.0,          # No energy payment
        'expected_hours_yr': 0,
        'min_capacity_mw': 10.0,
        'min_duration_hours': 4,
        'compatible_workloads': ['pre_training', 'fine_tuning', 'batch_inference'],
    },
}

# =============================================================================
# Value of Lost Load (VOLL) and Battery Degradation
# =============================================================================
VOLL_PENALTY = 50000  # $/MWh - penalty for unserved energy (DO NOT blend into LCOE)
K_DEG = 0.03  # $/kWh throughput for battery degradation

# =============================================================================
# LCOE Sanity Checks
# =============================================================================
LCOE_SANITY_CHECKS = {
    'warning_threshold': 200,      # $/MWh - flag for review
    'error_threshold': 500,        # $/MWh - likely calculation error
    'min_realistic': 50,           # $/MWh - below this is suspicious
    'max_realistic': 300,          # $/MWh - BTM with rentals can be high
}

# =============================================================================
# Heuristic Configuration
# =============================================================================
HEURISTIC_CONFIG = {
    # Sizing parameters
    'n1_reserve_margin': 0.15,          # 15% reserve for N-1 redundancy
    'baseload_recip_fraction': 0.70,    # 70% of thermal from recips
    'peaker_turbine_fraction': 0.30,    # 30% from turbines (peaking)
    'bess_transient_coverage': 0.10,    # 10% of peak for AI transient coverage
    'bess_default_duration_hrs': 4,     # 4-hour BESS default
    
    # Dispatch parameters
    'recip_capacity_factor': 0.85,      # High CF for baseload recips
    'turbine_capacity_factor': 0.30,    # Low CF for peaking turbines
    'solar_capacity_factor': 0.25,      # Regional average
    'bess_daily_cycles': 1.0,           # 1 cycle/day for arbitrage
    
    # Land density factors (MW/acre or MWh/acre)
    'recip_land_acres_per_mw': 0.5,
    'turbine_land_acres_per_mw': 0.3,
    'solar_land_acres_per_mw': 5.0,     # Fixed-tilt utility scale
    'bess_land_acres_per_mwh': 0.01,
    
    # Merit order (lower = dispatched first)
    'merit_order': {
        'solar': 1,      # Must-take, zero marginal cost
        'bess_discharge': 2,  # Previously charged energy
        'grid_import': 3,     # If available and cheap
        'recip': 4,           # Baseload thermal
        'turbine': 5,         # Peaking thermal
    },
    
    # NOx calculation parameters
    'nox_lb_to_ton': 2000,              # lb/ton conversion
    'hours_per_year': 8760,
    
    # Gas conversion
    'gas_hhv_mmbtu_per_mcf': 1.037,     # Higher heating value
}