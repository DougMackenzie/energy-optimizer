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
APP_VERSION = "0.2.1"
APP_ICON = "⚡"

# Theme colors (matching UI mockup)
COLORS = {
    "primary": "#1E3A5F",
    "secondary": "#2E86AB", 
    "accent": "#F18F01",
    "success": "#28A745",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "text": "#333333",
    "text_light": "#666666",
    "bg_light": "#F8F9FA",
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