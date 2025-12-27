"""
bvNexus Configuration Settings
Co-located Power, Energy and Load Optimization
"""

# Application Identity
APP_NAME = "bvNexus"
APP_VERSION = "2.0.0"
APP_ICON = "⚡"
APP_TAGLINE = "Co-located Power, Energy and Load Optimization"

# Color Scheme (Black & Veatch inspired)
COLORS = {
    'primary': '#1a365d',      # Dark blue
    'secondary': '#2d4a6f',    # Medium blue
    'accent': '#f6ad55',       # Orange accent
    'success': '#48bb78',      # Green
    'warning': '#ecc94b',      # Yellow
    'danger': '#fc8181',       # Red
    'text': '#2d3748',         # Dark gray
    'text_light': '#718096',   # Light gray
    'background': '#f7fafc',   # Off-white
}

# Problem Statement Definitions
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

# Optimization Tiers
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

# Economic Parameters
ECONOMIC_DEFAULTS = {
    'discount_rate': 0.08,           # 8%
    'project_life_years': 20,
    'fuel_price_mmbtu': 3.50,        # $/MMBtu
    'fuel_escalation_rate': 0.025,   # 2.5% annual
    'itc_rate': 0.30,                # 30% ITC for solar/BESS
    'crf_20yr_8pct': 0.1019,         # Capital recovery factor
}

# Equipment Defaults
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

# Constraint Defaults
CONSTRAINT_DEFAULTS = {
    'nox_tpy_annual': 100,           # Minor source threshold
    'co_tpy_annual': 100,
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 500,
    'grid_import_mw': 0,             # Until grid available
    'n_minus_1_required': True,
    'min_availability_pct': 99.5,
}

# AI Workload Flexibility Parameters
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

# Demand Response Services
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

# Value of Lost Load (VOLL)
VOLL_PENALTY = 50000  # $/MWh

# Battery Degradation
K_DEG = 0.03  # $/kWh cycled
