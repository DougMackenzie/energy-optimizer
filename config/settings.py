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
        'nox_lb_mwh': 0.50,
        'co_lb_mwh': 0.40,
        'capex_per_kw': 1650,
        'vom_per_mwh': 8.50,
        'fom_per_kw_yr': 18.50,
        'availability': 0.975,
        'lead_time_months': 18,
        'land_acres_per_mw': 0.5,
        'ramp_rate_mw_min': 3.0,
    },
    'turbine': {
        'capacity_mw': 50.0,
        'heat_rate_btu_kwh': 8500,
        'nox_lb_mwh': 0.25,
        'co_lb_mwh': 0.15,
        'capex_per_kw': 1300,
        'vom_per_mwh': 6.50,
        'fom_per_kw_yr': 12.50,
        'availability': 0.95,
        'lead_time_months': 24,
        'land_acres_per_mw': 0.3,
        'ramp_rate_mw_min': 8.0,
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
    },
    'solar': {
        'capex_per_w_dc': 0.95,
        'capacity_factor': 0.25,
        'availability': 0.995,
        'lead_time_months': 12,
        'land_acres_per_mw': 5.0,
    },
    'grid': {
        'availability': 0.9997,
        'lead_time_months': 60,  # 5 years typical
    },
}

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
    },
    'fine_tuning': {
        'flexibility_pct': 0.50,     # 40-60%
        'response_time_min': 30,
        'checkpoint_overhead_pct': 0.03,
        'description': 'Shorter jobs, more interruptible',
    },
    'batch_inference': {
        'flexibility_pct': 0.90,     # 80-100%
        'response_time_min': 15,
        'checkpoint_overhead_pct': 0.01,
        'description': 'Deferrable, queue-based',
    },
    'real_time_inference': {
        'flexibility_pct': 0.05,     # 0-10%
        'response_time_min': 0,
        'checkpoint_overhead_pct': 0.0,
        'description': 'Latency-critical, minimal flexibility',
    },
}

# =============================================================================
# bvNexus Integration: Demand Response Services
# =============================================================================
DR_SERVICES = {
    'econ_dr': {
        'name': 'Economic DR',
        'response_time_min': 60,
        'min_duration_hours': 4,
        'price_per_mw_hr': 50,
        'compatible_workloads': ['pre_training', 'fine_tuning', 'batch_inference'],
    },
    'ers_10': {
        'name': 'ERS-10',
        'response_time_min': 10,
        'min_duration_hours': 1,
        'price_per_mw_hr': 75,
        'compatible_workloads': ['batch_inference'],
    },
    'ers_30': {
        'name': 'ERS-30',
        'response_time_min': 30,
        'min_duration_hours': 2,
        'price_per_mw_hr': 60,
        'compatible_workloads': ['fine_tuning', 'batch_inference'],
    },
    'capacity': {
        'name': 'Capacity Market',
        'response_time_min': 120,
        'min_duration_hours': 4,
        'price_per_mw_month': 5000,
        'compatible_workloads': ['pre_training', 'fine_tuning', 'batch_inference'],
    },
}

# Value of Lost Load (VOLL) and Battery Degradation
VOLL_PENALTY = 50000  # $/MWh
K_DEG = 0.03  # $/kWh cycled