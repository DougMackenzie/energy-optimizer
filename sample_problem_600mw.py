#!/usr/bin/env python3
"""
bvNexus Sample Problem Definition
==================================

Standard 600 MW AI Data Center - Phased Deployment with Grid Bridging

This file defines a complete, realistic problem statement for testing
and demonstration. All values are preset to common industry parameters.

Scenario Summary:
-----------------
• 600 MW IT Load (750 MW facility at PUE 1.25)
• Phased deployment: 150 MW/year starting 2028
• Grid interconnection available Q1 2031
• 300 acres available land
• Sufficient gas supply for 300+ MW BTM generation
• 100 tpy NOx limit (minor source permit)

Usage:
------
    from sample_problem_600mw import get_sample_problem
    
    problem = get_sample_problem()
    
    site = problem['site']
    constraints = problem['constraints']
    load_profile = problem['load_profile']
    years = problem['years']
    scenarios = problem['scenarios']

Author: Claude AI
Date: December 2024
Version: 1.0
"""

import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# SITE PARAMETERS
# ============================================================================

SITE_CONFIG = {
    # Identification
    "site_id": "SAMPLE-DC-600MW",
    "site_name": "Sample AI Hyperscale Campus",
    "location": "Central US (Hypothetical)",
    "state": "TX",  # ERCOT region
    "iso_rto": "ERCOT",
    
    # Physical Characteristics
    "total_land_acres": 500,
    "available_land_acres": 300,  # For power island
    "zoning": "Industrial / Data Center",
    "elevation_ft": 800,
    "ambient_temp_design_f": 95,
    
    # Electrical Infrastructure
    "interconnection_voltage_kv": 345,
    "poi_capacity_mw": 600,
    "queue_position": 45,
    "queue_cluster": "2024-Q3",
    
    # Gas Infrastructure  
    "gas_pipeline": "Permian Highway Pipeline",
    "gas_pipeline_diameter_in": 16,
    "gas_pressure_psig": 800,
    "distance_to_tap_miles": 2.5,
    
    # Facility Design
    "pue": 1.25,
    "cooling_type": "Evaporative + DX backup",
    "tier_level": "Tier III+",
    "n_plus_1_required": True,
}


# ============================================================================
# CONSTRAINT PARAMETERS
# ============================================================================

CONSTRAINTS_CONFIG = {
    # === AIR PERMITTING ===
    "air_permit_type": "Minor Source (Synthetic)",
    "NOx_Limit_tpy": 100.0,         # Tons per year - HARD LIMIT (fixed)
    "CO_Limit_tpy": 250.0,          # Tons per year
    "VOC_Limit_tpy": 25.0,          # Tons per year
    "PM10_Limit_tpy": 50.0,         # Tons per year
    "CO2_Limit_tpy": 0.0,           # 0 = no limit (not regulated)
    "nonattainment_area": False,
    "permit_timeline_months": 12,
    
    # === GAS SUPPLY ===
    # 300 MW of recips @ 8,200 BTU/kWh, 85% CF:
    # 300 MW × 1000 kW/MW × 8200 BTU/kWh × 0.85 × 24 hr / 1,030,000 BTU/MCF ≈ 49,000 MCF/day
    # Adding margin for turbines and operational flexibility: 75,000 MCF/day
    "Gas_Supply_MCF_day": 75000.0,  # MCF per day - HARD LIMIT (fixed)
    "gas_cost_per_mmbtu": 3.50,     # $/MMBTU
    "gas_supply_firm": True,
    "gas_curtailment_days_year": 5, # Expected curtailment days
    
    # === LAND ===
    "Available_Land_Acres": 300.0,  # Acres - HARD LIMIT (fixed)
    "solar_land_acres_per_mw": 5.0, # Acres per MW DC
    "power_block_acres": 50.0,      # Reserved for gen equipment
    
    # === GRID INTERCONNECTION ===
    "Grid_Available_MW": 600.0,     # MW when connected (fixed)
    "grid_interconnection_year": 2031,  # Q1 2031
    "grid_interconnection_month": 3,
    "interconnection_cost_million": 45.0, # $M for 345kV, 600 MW
    "grid_wheeling_cost_mwh": 5.00, # $/MWh transmission
    
    # === RELIABILITY ===
    "N_Minus_1_Required": True,
    "min_availability_pct": 99.9,
    "max_single_contingency_mw": 50.0,
    "min_spinning_reserve_mw": 30.0,
    "max_ramp_rate_mw_min": 75.0,
    
    # === OPERATIONAL ===
    "max_transient_pct": 25.0,      # Max voltage/frequency transient
    "min_bess_duration_hrs": 4.0,   # Minimum BESS duration
    "max_bess_cycles_year": 365,    # Max annual cycles
}


# ============================================================================
# LOAD PROFILE PARAMETERS
# ============================================================================

def generate_load_trajectory() -> Dict[int, float]:
    """
    Generate phased load trajectory.
    
    Load Growth:
    - 2028: 150 MW IT → 187.5 MW facility
    - 2029: 300 MW IT → 375 MW facility
    - 2030: 450 MW IT → 562.5 MW facility
    - 2031+: 600 MW IT → 750 MW facility (grid arrives)
    """
    pue = SITE_CONFIG['pue']
    
    return {
        2028: 150 * pue,   # 187.5 MW
        2029: 300 * pue,   # 375.0 MW
        2030: 450 * pue,   # 562.5 MW
        2031: 600 * pue,   # 750.0 MW
        2032: 600 * pue,   # 750.0 MW (steady state)
        2033: 600 * pue,   # 750.0 MW
        2034: 600 * pue,   # 750.0 MW
        2035: 600 * pue,   # 750.0 MW
    }


def generate_8760_profile(peak_mw: float, seed: int = 42) -> np.ndarray:
    """
    Generate realistic 8760 hourly load profile.
    
    Incorporates:
    - Daily pattern (GPU training cycles)
    - Weekly pattern (batch jobs on weekends)
    - Seasonal cooling variation
    - Random variability (AI workload stochasticity)
    
    Args:
        peak_mw: Peak facility load (MW)
        seed: Random seed for reproducibility
        
    Returns:
        8760-element numpy array of hourly loads (MW)
    """
    np.random.seed(seed)
    hours = np.arange(8760)
    
    # Base load factor (AI DCs run hot)
    base_load_factor = 0.85
    base_load = peak_mw * base_load_factor
    
    # Daily pattern: slight dip overnight (batch processing vs real-time)
    hour_of_day = hours % 24
    daily_pattern = 0.05 * np.sin((hour_of_day - 14) / 24 * 2 * np.pi)
    
    # Weekly pattern: slightly lower on weekends (reduced interactive load)
    day_of_week = (hours // 24) % 7
    weekly_pattern = np.where(day_of_week >= 5, -0.03, 0.0)
    
    # Seasonal cooling variation (summer peak)
    day_of_year = hours // 24
    seasonal_pattern = 0.08 * np.sin((day_of_year - 172) / 365 * 2 * np.pi)
    
    # Random GPU cluster variability
    random_variability = 0.02 * np.random.randn(8760)
    
    # Combine patterns
    load_factor = base_load_factor + daily_pattern + weekly_pattern + seasonal_pattern + random_variability
    
    # Clip to reasonable bounds
    load_factor = np.clip(load_factor, 0.75, 1.0)
    
    # Scale to MW
    load_profile = peak_mw * load_factor
    
    return load_profile


def generate_workload_mix() -> Dict[str, float]:
    """
    Generate typical AI workload mix percentages.
    
    Based on hyperscale AI training facility profile.
    """
    return {
        "pre_training": 0.45,       # Large model training - most flexible
        "fine_tuning": 0.20,        # Model customization - moderately flexible
        "batch_inference": 0.15,    # Offline predictions - very flexible
        "realtime_inference": 0.20, # Live API serving - inflexible
    }


LOAD_PROFILE_CONFIG = {
    # IT Load Parameters
    "peak_it_mw": 600,
    "pue": 1.25,
    "peak_facility_mw": 750,  # 600 × 1.25
    
    # Load Growth
    "load_trajectory": generate_load_trajectory(),
    "load_start_year": 2028,
    "load_ramp_mw_per_year": 150,
    
    # Workload Composition
    "workload_mix": generate_workload_mix(),
    
    # Flexibility Parameters (from DCFlex research)
    "workload_flexibility": {
        "pre_training": 0.30,      # 30% interruptible
        "fine_tuning": 0.50,       # 50% interruptible
        "batch_inference": 0.90,   # 90% deferrable
        "realtime_inference": 0.05,# 5% curtailable (emergency only)
    },
    
    # Cooling Flexibility
    "cooling_flexibility_pct": 25,  # 25% of cooling load deferrable
    "thermal_time_constant_min": 30,
    
    # Total Facility Flexibility
    "total_flexibility_pct": 18,   # ~18% of facility load is flexible
    
    # Profile Characteristics
    "load_factor": 0.85,
    "peak_to_average_ratio": 1.15,
    "daily_variation_pct": 5,
    "seasonal_variation_pct": 8,
}


# ============================================================================
# EQUIPMENT LIBRARY
# ============================================================================

EQUIPMENT_LIBRARY = {
    "recip": {
        "name": "18 MW Reciprocating Engine (Wärtsilä 18V50SG)",
        "capacity_mw": 18,
        "heat_rate_btu_kwh": 8200,
        "efficiency_pct": 41.6,
        "nox_lb_mmbtu": 0.05,       # With SCR
        "co_lb_mmbtu": 0.08,
        "capex_per_kw": 1200,
        "fixed_om_per_kw_yr": 12,
        "variable_om_per_mwh": 8,
        "availability_pct": 97.5,
        "mtbf_hours": 8000,
        "mttr_hours": 24,
        "lead_time_months": 18,
        "ramp_rate_mw_min": 3.6,    # 20%/min
        "min_load_pct": 30,
        "start_time_minutes": 5,
        "fuel_type": "natural_gas",
        "emissions_tier": "Tier 4",
    },
    
    "turbine_aeroderivative": {
        "name": "25 MW Aeroderivative GT (GE LM2500)",
        "capacity_mw": 25,
        "heat_rate_btu_kwh": 9500,
        "efficiency_pct": 36.0,
        "nox_lb_mmbtu": 0.04,       # Dry low NOx
        "co_lb_mmbtu": 0.02,
        "capex_per_kw": 950,
        "fixed_om_per_kw_yr": 10,
        "variable_om_per_mwh": 5,
        "availability_pct": 96.0,
        "mtbf_hours": 6000,
        "mttr_hours": 48,
        "lead_time_months": 24,
        "ramp_rate_mw_min": 12.5,   # 50%/min
        "min_load_pct": 50,
        "start_time_minutes": 10,
        "fuel_type": "natural_gas",
    },
    
    "turbine_frame": {
        "name": "85 MW Frame GT (GE 7E.03)",
        "capacity_mw": 85,
        "heat_rate_btu_kwh": 10200,
        "efficiency_pct": 33.5,
        "nox_lb_mmbtu": 0.035,
        "co_lb_mmbtu": 0.015,
        "capex_per_kw": 700,
        "fixed_om_per_kw_yr": 8,
        "variable_om_per_mwh": 4,
        "availability_pct": 95.0,
        "mtbf_hours": 5000,
        "mttr_hours": 72,
        "lead_time_months": 30,
        "ramp_rate_mw_min": 8.5,
        "min_load_pct": 60,
        "start_time_minutes": 30,
        "fuel_type": "natural_gas",
    },
    
    "bess": {
        "name": "4-hour Li-ion BESS",
        "duration_hours": 4,
        "round_trip_efficiency": 0.88,
        "capex_per_kwh": 350,
        "fixed_om_per_kw_yr": 5,
        "availability_pct": 99.5,
        "calendar_life_years": 15,
        "cycle_life": 4000,
        "depth_of_discharge_pct": 90,
        "lead_time_months": 12,
        "ramp_rate_pct_sec": 100,   # Full power in <1 second
        "aux_load_pct": 2,
    },
    
    "solar": {
        "name": "Utility-Scale Solar PV",
        "capex_per_kw_dc": 950,
        "capacity_factor_pct": 24,  # Central TX
        "land_acres_per_mw": 5,
        "degradation_pct_yr": 0.5,
        "availability_pct": 99.0,
        "lead_time_months": 12,
        "fixed_om_per_kw_yr": 10,
    },
    
    "grid": {
        "name": "345 kV Grid Interconnection",
        "interconnection_year": 2031,
        "capacity_mw": 600,
        "capex_total_million": 45,
        "wheeling_cost_mwh": 5.00,
        "energy_cost_mwh": 45,      # Average wholesale
        "availability_pct": 99.97,
        "lead_time_months": 36,
    },
}


# ============================================================================
# SCENARIO DEFINITIONS
# ============================================================================

SCENARIOS = [
    {
        "scenario_id": "S1-BTM-RECIP",
        "name": "All Recips (Behind-the-Meter Only)",
        "description": "Maximum recip deployment within NOx limits, BESS for stability",
        "grid_enabled": False,
        "solar_enabled": False,
        "equipment_preference": ["recip", "bess"],
        "priority": "time_to_power",
    },
    {
        "scenario_id": "S2-BTM-HYBRID",
        "name": "Hybrid BTM (Recips + Turbines + BESS)",
        "description": "Mixed generation for diversity, grid bridging until 2031",
        "grid_enabled": True,
        "solar_enabled": True,
        "equipment_preference": ["recip", "turbine_aeroderivative", "bess", "solar"],
        "priority": "balanced",
    },
    {
        "scenario_id": "S3-GRID-FORWARD",
        "name": "Grid-Forward (Minimize BTM)",
        "description": "Minimum BTM for bridging, maximize grid post-2031",
        "grid_enabled": True,
        "solar_enabled": True,
        "equipment_preference": ["bess", "solar", "grid"],
        "priority": "cost",
    },
    {
        "scenario_id": "S4-MAX-RENEWABLE",
        "name": "Maximum Renewable + Storage",
        "description": "Prioritize solar + BESS, gas backup only",
        "grid_enabled": True,
        "solar_enabled": True,
        "equipment_preference": ["solar", "bess", "recip"],
        "priority": "emissions",
    },
    {
        "scenario_id": "S5-PREDEFINED-300MW",
        "name": "Pre-defined 300 MW Stack",
        "description": "Fixed configuration: 12 recips (216 MW) + 2 turbines (50 MW) + 100 MWh BESS",
        "grid_enabled": True,
        "solar_enabled": False,
        "fixed_equipment": {
            "n_recip": 12,
            "n_turbine": 2,
            "bess_mwh": 100,
            "solar_mw": 0,
        },
        "priority": "fixed",
    },
]


# ============================================================================
# ECONOMIC PARAMETERS
# ============================================================================

ECONOMIC_CONFIG = {
    # Discount rate and project life
    "discount_rate": 0.08,
    "project_life_years": 20,
    "analysis_start_year": 2028,
    "analysis_end_year": 2035,
    
    # Fuel prices
    "ng_price_mmbtu": 3.50,
    "ng_escalation_pct_yr": 2.0,
    
    # Electricity prices
    "grid_energy_mwh": 45.00,
    "grid_demand_kw_mo": 12.00,
    "grid_escalation_pct_yr": 2.5,
    
    # Demand Response Revenue (ERCOT)
    "dr_spinning_reserve_mw_hr": 15.00,
    "dr_non_spinning_mw_hr": 8.00,
    "dr_emergency_mw_hr": 25.00,
    "dr_economic_mw_hr": 5.00,
    "dr_capacity_credit_pct": 50,  # % of flexible capacity eligible
    
    # Tax and incentives
    "itc_pct": 0,                # No ITC for gas
    "itc_bess_pct": 30,          # 30% ITC for standalone storage (IRA)
    "itc_solar_pct": 30,         # 30% ITC for solar (IRA)
    "depreciation_years": 7,     # MACRS
    "tax_rate_pct": 25,
    
    # Insurance and other
    "insurance_pct_capex": 0.5,
    "property_tax_pct_capex": 1.0,
}


# ============================================================================
# OPTIMIZATION PARAMETERS
# ============================================================================

OPTIMIZATION_CONFIG = {
    # Solver settings
    "solver": "cbc",             # cbc, glpk, or gurobi
    "time_limit_seconds": 300,
    "mip_gap_pct": 1.0,          # 1% optimality gap
    
    # Representative periods
    "use_representative_periods": True,
    "n_representative_weeks": 6,  # 6 weeks × 168 hours = 1008 hours
    "representative_week_indices": [0, 10, 20, 30, 40, 50],
    
    # Hierarchical objective weights
    "unserved_penalty_mwh": 50000,  # $/MWh - ensures power > cost
    
    # Capacity planning
    "planning_reserve_margin_pct": 15,
    "contingency_reserve_pct": 10,
    
    # Convergence
    "max_iterations": 1000,
    "feasibility_tolerance": 1e-6,
}


# ============================================================================
# MAIN INTERFACE
# ============================================================================

def get_sample_problem() -> Dict[str, Any]:
    """
    Get complete sample problem definition.
    
    Returns:
        Dictionary with all problem parameters ready for optimization.
    """
    
    # Generate load profiles for each year
    load_trajectory = generate_load_trajectory()
    
    load_profiles_by_year = {}
    for year, peak_mw in load_trajectory.items():
        load_profiles_by_year[year] = generate_8760_profile(peak_mw, seed=42 + year)
    
    # Build complete load profile structure
    load_profile = {
        **LOAD_PROFILE_CONFIG,
        "load_profiles_by_year": load_profiles_by_year,
        "load_trajectory": load_trajectory,
        "load_data": {
            # Use 2030 (450 MW phase) as representative
            "total_load_mw": list(load_profiles_by_year[2030]),
            "peak_load_mw": float(max(load_profiles_by_year[2030])),
            "min_load_mw": float(min(load_profiles_by_year[2030])),
            "avg_load_mw": float(np.mean(load_profiles_by_year[2030])),
        },
    }
    
    return {
        "site": SITE_CONFIG,
        "constraints": CONSTRAINTS_CONFIG,
        "load_profile": load_profile,
        "equipment_library": EQUIPMENT_LIBRARY,
        "scenarios": SCENARIOS,
        "economics": ECONOMIC_CONFIG,
        "optimization": OPTIMIZATION_CONFIG,
        "years": list(range(2028, 2036)),
        "metadata": {
            "problem_name": "600 MW AI Hyperscale Campus",
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "author": "bvNexus Sample Problem Generator",
        },
    }


def print_problem_summary():
    """Print a human-readable summary of the problem."""
    
    problem = get_sample_problem()
    
    print("\n" + "=" * 70)
    print("bvNexus SAMPLE PROBLEM: 600 MW AI DATA CENTER")
    print("=" * 70)
    
    print("\n📍 SITE")
    print("-" * 40)
    print(f"  Location:        {problem['site']['location']}")
    print(f"  ISO/RTO:         {problem['site']['iso_rto']}")
    print(f"  Available Land:  {problem['constraints']['Available_Land_Acres']} acres")
    print(f"  Gas Supply:      {problem['constraints']['Gas_Supply_MCF_day']:,} MCF/day")
    
    print("\n⚡ LOAD")
    print("-" * 40)
    print(f"  Peak IT Load:    {problem['load_profile']['peak_it_mw']} MW")
    print(f"  PUE:             {problem['load_profile']['pue']}")
    print(f"  Peak Facility:   {problem['load_profile']['peak_facility_mw']} MW")
    print("\n  Load Trajectory:")
    for year, mw in problem['load_profile']['load_trajectory'].items():
        grid_note = " ← Grid arrives" if year == 2031 else ""
        print(f"    {year}: {mw:.0f} MW facility ({mw/problem['load_profile']['pue']:.0f} MW IT){grid_note}")
    
    print("\n🚧 CONSTRAINTS")
    print("-" * 40)
    print(f"  NOx Limit:       {problem['constraints']['NOx_Limit_tpy']} tpy")
    print(f"  Gas Supply:      {problem['constraints']['Gas_Supply_MCF_day']:,} MCF/day")
    print(f"  Land Available:  {problem['constraints']['Available_Land_Acres']} acres")
    print(f"  Grid Available:  {problem['constraints']['grid_interconnection_year']} ({problem['constraints']['Grid_Available_MW']} MW)")
    print(f"  N-1 Required:    {problem['constraints']['N_Minus_1_Required']}")
    
    print("\n🔧 EQUIPMENT OPTIONS")
    print("-" * 40)
    for eq_type, specs in problem['equipment_library'].items():
        if 'capacity_mw' in specs:
            print(f"  {specs['name'][:40]:40} {specs['capacity_mw']:>6} MW")
    
    print("\n📊 SCENARIOS")
    print("-" * 40)
    for scenario in problem['scenarios']:
        print(f"  {scenario['scenario_id']}: {scenario['name']}")
    
    print("\n" + "=" * 70)
    print("Use get_sample_problem() to load all parameters for optimization")
    print("=" * 70 + "\n")


# ============================================================================
# QUICK ACCESS FUNCTIONS
# ============================================================================

def get_site() -> Dict:
    """Get site configuration only."""
    return SITE_CONFIG.copy()

def get_constraints() -> Dict:
    """Get constraints configuration only."""
    return CONSTRAINTS_CONFIG.copy()

def get_load_profile(year: int = 2030) -> Dict:
    """Get load profile for a specific year."""
    problem = get_sample_problem()
    peak_mw = problem['load_profile']['load_trajectory'].get(year, 750)
    
    return {
        "peak_load_mw": peak_mw,
        "pue": LOAD_PROFILE_CONFIG['pue'],
        "load_factor": LOAD_PROFILE_CONFIG['load_factor'],
        "workload_mix": generate_workload_mix(),
        "total_load_mw": list(generate_8760_profile(peak_mw)),
    }

def get_years() -> List[int]:
    """Get analysis years."""
    return list(range(2028, 2036))

def get_scenarios() -> List[Dict]:
    """Get scenario definitions."""
    return SCENARIOS.copy()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print_problem_summary()
    
    # Optionally run quick validation
    problem = get_sample_problem()
    
    print("\n🧪 VALIDATION")
    print("-" * 40)
    
    # Check gas supply is sufficient
    # 300 MW recips @ 8200 BTU/kWh, 85% CF, 24 hours
    # = 300 × 1000 × 8200 × 0.85 × 24 / 1,030,000 = ~49,000 MCF/day
    max_gas_gen_mw = (
        problem['constraints']['Gas_Supply_MCF_day'] * 1_030_000 /  # BTU/day
        (problem['equipment_library']['recip']['heat_rate_btu_kwh'] * 1000 * 0.85 * 24)
    )
    print(f"  Gas supply supports: {max_gas_gen_mw:.0f} MW of recips at 85% CF")
    
    # Check land supports solar target
    max_solar_mw = problem['constraints']['Available_Land_Acres'] / 5
    print(f"  Land supports:       {max_solar_mw:.0f} MW of solar (@ 5 acres/MW)")
    
    # Check NOx allows equipment
    nox_per_recip = 8  # Approximate tpy per recip at 80% CF
    max_recips = problem['constraints']['NOx_Limit_tpy'] // nox_per_recip
    print(f"  NOx limit allows:    ~{max_recips} recips ({max_recips * 18} MW)")
    
    print("\n✅ Sample problem ready for optimization\n")
