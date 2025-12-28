"""
Equipment Electrical and Reliability Specifications
===================================================

Complete electrical parameters, reliability data, and physical specifications
for generating equipment to support integration with external tools (ETAP, PSS/e, Windchill RAM).

Data Sources:
- IEEE Standards (IEEE 115, IEEE 399, IEEE 493)
- Equipment manufacturers (Wärtsilä, GE, Caterpillar, Siemens)
- Black & Veatch engineering estimates
- config/settings.py EQUIPMENT_DEFAULTS

⚠️ ASSUMPTIONS REQUIRING VALIDATION:
All parameters marked with "# ASSUMPTION:" require validation against actual equipment datasheets
or site-specific engineering studies before use in final design.
"""

from typing import Dict, List

# =============================================================================
# ELECTRICAL IMPEDANCES & GENERATOR PARAMETERS
# =============================================================================

ELECTRICAL_SPECS = {
    'recip': {
        # === VALIDATED VALUES (from settings.py) ===
        'unit_mw': 18.3,                    # Source: EQUIPMENT_DEFAULTS
        'power_factor': 0.85,                # Typical for standby generators
        'voltage_kv': 13.8,                  # Standard medium voltage
        
        # === GENERATOR IMPEDANCES (per-unit on machine base) ===
        # ASSUMPTION: Based on IEEE Std 115 for reciprocating engine generators
        # Typical range for salient-pole synchronous generators
        'Xd_pu': 1.80,                       # Direct-axis synchronous reactance
        'Xd_prime_pu': 0.25,                 # Direct-axis transient reactance
        'Xd_double_prime_pu': 0.18,          # Direct-axis subtransient reactance
        'Xq_pu': 0.90,                       # Quadrature-axis synchronous reactance (salient pole)
        'Xq_prime_pu': 0.40,                 # Quadrature-axis transient reactance
        'Xq_double_prime_pu': 0.18,          # Quadrature-axis subtransient reactance
        
        # === TIME CONSTANTS (seconds) ===
        # ASSUMPTION: Based on IEEE 399 typical values for diesel/gas reciprocating generators
        'Td_prime_s': 0.60,                  # Direct-axis transient open-circuit time constant
        'Td_double_prime_s': 0.035,          # Direct-axis subtransient open-circuit time constant
        'Tq_prime_s':0.40,                  # Quadrature-axis transient time constant
        'Tq_double_prime_s': 0.035,          # Quadrature-axis subtransient time constant
        
        # === INERTIA CONSTANT ===
        # ASSUMPTION: Reciprocating engines have lower inertia than turbines
        'H_inertia_sec': 1.5,                # Inertia constant (MJ/MVA)
        'D_damping': 2.0,                    # Damping coefficient
        
        # === SHORT CIRCUIT ===
        'Xd_sat': 1.60,                      # Saturated direct-axis reactance
        'transient_sc_ratio': 4.0,           # X/R ratio for transient SC
        'subtransient_sc_ratio': 15.0,       # X/R ratio for subtransient SC
        
        # === EXCITATION SYSTEM ===
        # ASSUMPTION: Static exciter typical for modern reciprocating generators
        'exciter_type': 'ST1A',              # IEEE ST1A static exciter
        'exciter_gain': 200.0,               # Exciter gain
        'exciter_time_constant': 0.05,       # Exciter time constant (s)
        
        # === VOLTAGE REGULATION ===
        'voltage_regulation_pct': 0.5,       # ±0.5% voltage regulation
        'voltage_response_s': 0.2,           # 200ms response time
    },
    
    'turbine': {
        # === VALIDATED VALUES ===
        'unit_mw': 50.0,                     # Source: EQUIPMENT_DEFAULTS  
        'power_factor': 0.85,
        'voltage_kv': 13.8,
        
        # === GENERATOR IMPEDANCES ===
        # ASSUMPTION: Based on IEEE Std 115 for aeroderivative gas turbines (LM6000-class)
        # Round-rotor machines have different characteristics than salient-pole
        'Xd_pu': 1.50,                       # Lower than recips (round rotor)
        'Xd_prime_pu': 0.22,
        'Xd_double_prime_pu': 0.15,
        'Xq_pu': 1.45,                       # Similar to Xd (round rotor)
        'Xq_prime_pu': 0.35,
        'Xq_double_prime_pu': 0.15,
        
        # === TIME CONSTANTS ===
        # ASSUMPTION: Gas turbines have faster response than recips
        'Td_prime_s': 0.80,
        'Td_double_prime_s': 0.025,
        'Tq_prime_s': 0.50,
        'Tq_double_prime_s': 0.025,
        
        # === INERTIA CONSTANT ===
        # ASSUMPTION: Higher inertia than recips due to turbine mass
        'H_inertia_sec': 3.0,               # Higher than recips
        'D_damping': 1.5,
        
        # === SHORT CIRCUIT ===
        'Xd_sat': 1.35,
        'transient_sc_ratio': 6.0,
        'subtransient_sc_ratio': 20.0,
        
        # === EXCITATION SYSTEM ===
        # ASSUMPTION: Brushless exciter typical for gas turbines
        'exciter_type': 'AC4A',              # IEEE AC4A brushless exciter
        'exciter_gain': 400.0,
        'exciter_time_constant': 0.02,
        
        # === VOLTAGE REGULATION ===
        'voltage_regulation_pct': 0.25,      # Tighter regulation
        'voltage_response_s': 0.1,           # Faster response
    },
    
    'bess': {
        # === VALIDATED VALUES ===
        'unit_mw': 30.0,                     # ASSUMPTION: Based on typical containerized BESS
        'unit_mwh': 120.0,                   # 4-hour duration
        'power_factor': 1.0,                 # Unity PF for inverter-based
        'voltage_kv': 13.8,
        
        # === INVERTER IMPEDANCES ===
        # ASSUMPTION: Grid-following inverter model (GFL)
        # Inverters don't have physical reactance, but control system creates equivalent
        'Xd_pu': 0.15,                       # Very low (inverter-based)
        'Xd_prime_pu': 0.15,                 # No distinction for inverters
        'Xd_double_prime_pu': 0.15,
        'Xq_pu': 0.15,
        'Xq_prime_pu': 0.15,
        'Xq_double_prime_pu': 0.15,
        
        # === CONTROL RESPONSE ===
        # ASSUMPTION: Fast control loops typical of modern grid-tied inverters
        'control_bandwidth_hz': 100,         # 100 Hz control bandwidth
        'response_time_ms': 2,               # 2ms (half cycle)
        
        # === INERTIA (VIRTUAL) ===
        'H_inertia_sec': 0.0,                # No physical inertia
        'virtual_inertia_sec': 0.5,          # Can emulate if programmed
        'D_damping': 0.0,                    # No mechanical damping
        
        # === SHORT CIRCUIT CONTRIBUTION ===
        # ASSUMPTION: Grid-following inverters limit to 1.2x rated current
        'sc_contribution_pu': 1.2,           # 1.2 pu max fault current
        'sc_duration_cycles': 0.5,           # Only for ~0.5 cycles
        
        # === GRID SUPPORT ===
        'grid_forming_capable': False,       # ASSUMPTION: GFL mode
        'black_start_capable': False,        # ASSUMPTION: Requires grid reference
        'voltage_ride_through': 'LVRT+HVRT', # Low/High voltage ride-through
    },
    
    'transformer': {
        # === MAIN TRANSFORMER SPECS ===
        # ASSUMPTION: Typical pad-mount transformer for datacenter service
        'rated_mva': 100.0,                  # ASSUMPTION: 100 MVA typical
        'voltage_primary_kv': 138.0,         # ASSUMPTION: Sub-transmission level
        'voltage_secondary_kv': 13.8,        # Medium voltage distribution
        'winding_config': 'Dyn11',           # Delta-wye grounded, 30° phase shift
        
        # === IMPEDANCES ===
        # ASSUMPTION: Based on IEEE C57.12.00 for power transformers
        'Z_pu': 0.10,                        # 10% impedance on transformer base
        'X_R_ratio': 15.0,                   # Typical X/R for power transformer
        'R_pu': 0.0067,                      # Calculated: Z / sqrt(1 + X/R^2)
        'X_pu': 0.0998,                      # Calculated: sqrt(Z^2 - R^2)
        
        # ===COOLING & Loading ===
        'cooling_type': 'ONAN',              # Oil natural, air natural
        'continuous_rating_mva': 100.0,
        'emergency_rating_mva': 133.0,       # 133% of nameplate (IEEE C57.91)
        
        # === TAP CHANGER ===
        # ASSUMPTION: LTC typical for utility-scale datacenter service
        'tap_changer': 'LTC',                # Load tap changer
        'tap_range_pct': 10.0,               # ±10% (±16 steps typical)
        'tap_step_pct': 0.625,               # 0.625% per step (32 steps)
    },
    
    'switchgear': {
        # === MAIN SWITCHGEAR SPECS ===
        # ASSUMPTION: Medium voltage metal-clad switchgear
        'rated_voltage_kv': 15.0,            # 15kV class
        'rated_current_a': 2000,             # 2000A continuous
        'rated_sc_ka': 50.0,                 # 50 kA short circuit rating
        'rated_sc_duration_s': 3.0,          # 3-second duration
        
        # === BREAKER SPECS ===
        # ASSUMPTION: Vacuum circuit breakers typical for 15kV class
        'breaker_type': 'VCB',               # Vacuum circuit breaker
        'interrupt_time_cycles': 3,          # 3 cycles (50ms @ 60Hz)
        'interrupt_rating_ka': 50.0,
        'momentary_rating_ka': 110.0,        # 2.2x symmetrical for asymmetric peak
        
        # === BUS CONFIGURATION ===
        'bus_config': 'main_tie_main',       # ASSUMPTION: Typical for datacenter
        'num_feeders': 8,                    # ASSUMPTION: 8 feeder positions
    }
}


# =============================================================================
# RELIABILITY DATA (MTBF/MTTR)
# =============================================================================

RELIABILITY_SPECS = {
    'recip': {
        # === RELIABILITY PARAMETERS ===
        # Source: IEEE 493 "Gold Book" + B&V experience
        # ASSUMPTION: Values based on well-maintained standby/prime power generators
        'mtbf_hours': 8760,                  # 1 year MTBF (conservative for standby duty)
        'mttr_hours': 24,                    # 24 hours mean time to repair
        'failure_rate_per_hour': 1.14e-4,    # λ = 1/MTBF
        'availability': 0.9973,              # A = MTBF / (MTBF + MTTR)
        
        # === FAILURE MODES ===
        # ASSUMPTION: Distribution based on IEEE 493 Table 3-19
        'failure_mode_distribution': {
            'mechanical': 0.45,              # Bearings, pistons, valves
            'electrical': 0.20,              # Generator, exciter, controls
            'fuel_system': 0.15,             # Fuel pumps, injectors
            'cooling': 0.10,                 # Radiators, pumps
            'control_system': 0.10,          # PLC, sensors, breakers
        },
        
        # === WEIBULL PARAMETERS ===
        # ASSUMPTION: Weibull better models wear-out mechanisms
        'weibull_beta': 1.5,                 # Shape parameter (>1 = wear-out)
        'weibull_eta': 10000,                # Scale parameter (characteristic life)
        
        # === MAINTENANCE ===
        'scheduled_outage_hrs_yr': 80,       # ASSUMPTION: ~10 days/yr scheduled maintenance
        'forced_outage_rate': 0.025,         # 2.5% FOR
    },
    
    'turbine': {
        # === RELIABILITY PARAMETERS ===
        # Source: IEEE 493 + NERC GADS data for aeroderivative GTs
        # ASSUMPTION: Modern aeroderivative (LM6000-class) reliability
        'mtbf_hours': 17520,                 # 2 years MTBF
        'mttr_hours': 48,                    # 48 hours (longer than recips)
        'failure_rate_per_hour': 5.71e-5,
        'availability': 0.9973,
        
        # === FAILURE MODES ===
        'failure_mode_distribution': {
            'hot_section': 0.40,             # Turbine blades, combustor
            'compressor': 0.20,              # Compressor blades, seals
            'generator': 0.15,               # Generator windings
            'fuel_system': 0.15,             # Fuel nozzles, valves
            'controls': 0.10,                # FADEC, sensors
        },
        
        # === WEIBULL PARAMETERS ===
        'weibull_beta': 2.0,                 # Higher wear-out (hot section)
        'weibull_eta': 20000,
        
        # === MAINTENANCE ===
        'scheduled_outage_hrs_yr': 120,      # More intensive maintenance
        'forced_outage_rate': 0.030,         # 3.0% FOR
    },
    
    'bess': {
        # === RELIABILITY PARAMETERS ===
        # Source: DNV GL battery reliability studies + manufacturer data
        # ASSUMPTION: Modern lithium-ion BESS with BMS
        'mtbf_hours': 43800,                 # 5 years MTBF
        'mttr_hours': 8,                     # 8 hours (module swap)
        'failure_rate_per_hour': 2.28e-5,
        'availability': 0.9998,              # Very high availability
        
        # === FAILURE MODES ===
        'failure_mode_distribution': {
            'inverter': 0.35,                # PCS failures most common
            'bms': 0.25,                     # Battery management system
            'cooling': 0.20,                 # HVAC, thermal management
            'cell_module': 0.15,             # Battery cells/modules
            'auxiliary': 0.05,               # Transformers, switchgear
        },
        
        # === DEGRADATION ===
        # ASSUMPTION: Capacity fade separate from catastrophic failure
        'capacity_fade_pct_yr': 2.0,         # 2% annual capacity fade
        'eol_capacity_pct': 80,              # End of life at 80% capacity
        
        # === WEIBULL PARAMETERS ===
        'weibull_beta': 1.0,                 # Exponential (random failures)
        'weibull_eta': 43800,
        
        # === MAINTENANCE ===
        'scheduled_outage_hrs_yr': 24,       # Minimal scheduled maintenance
        'forced_outage_rate': 0.002,         # 0.2% FOR (very low)
    },
    
    'transformer': {
        # === RELIABILITY PARAMETERS ===
        # Source: IEEE 493 Table 3-12 (Power Transformers)
        # ASSUMPTION: Oil-filled power transformer, well-maintained
        'mtbf_hours': 175200,                # 20 years MTBF
        'mttr_hours': 168,                   # 7 days (major repair/replacement)
        'failure_rate_per_hour': 5.71e-6,
        'availability': 0.9990,
        
        # === FAILURE MODES ===
        'failure_mode_distribution': {
            'winding_insulation': 0.40,      # Most common failure
            'tap_changer': 0.25,             # LTC mechanism
            'cooling_system': 0.15,          # Fans, pumps, radiators
            'bushings': 0.10,                # External bushings
            'core': 0.10,                    # Core laminations, grounding
        },
        
        # === WEIBULL PARAMETERS ===
        'weibull_beta': 3.0,                 # Strong wear-out (insulation aging)
        'weibull_eta': 200000,
        
        # === MAINTENANCE ===
        'scheduled_outage_hrs_yr': 16,       # Annual inspection
        'forced_outage_rate': 0.001,         # 0.1% FOR
    },
    
    'switchgear': {
        # === RELIABILITY PARAMETERS ===
        # Source: IEEE 493 Table 3-17 (Metalclad Switchgear)
        # ASSUMPTION: Modern vacuum circuit breaker switchgear
        'mtbf_hours': 87600,                 # 10 years MTBF
        'mttr_hours': 8,                     # 8 hours (breaker replacement)
        'failure_rate_per_hour': 1.14e-5,
        'availability': 0.9999,
        
        # === FAILURE MODES ===
        'failure_mode_distribution': {
            'circuit_breaker': 0.50,         # VCB mechanism
            'control_power': 0.20,           # Control circuits, battery
            'protection_relays': 0.15,       # Protective relays
            'bus_connections': 0.10,         # Bus bars, connections
            'auxiliary': 0.05,               # Metering, indication
        },
        
        # === WEIBULL PARAMETERS ===
        'weibull_beta': 1.2,                 # Slight wear-out
        'weibull_eta': 100000,
        
        # === MAINTENANCE ===
        'scheduled_outage_hrs_yr': 8,        # Minimal maintenance
        'forced_outage_rate': 0.0005,        # 0.05% FOR
    }
}


# =============================================================================
# EQUIPMENT UNIT SIZES (for count calculation)
# =============================================================================

# VALIDATED from config/settings.py EQUIPMENT_DEFAULTS
UNIT_SIZES = {
    'recip': {
        'rated_mw': 18.3,                    # Wärtsilä 34SG typical
        'rated_mva': 21.5,                   # MW / PF
        'manufacturer': 'Wärtsilä',          # ASSUMPTION: Example manufacturer
        'model': '34SG',                     # ASSUMPTION: Example model
    },
    'turbine': {
        'rated_mw': 50.0,                    # GE LM6000 typical
        'rated_mva': 58.8,
        'manufacturer': 'GE',                # ASSUMPTION
        'model': 'LM6000PD',                 # ASSUMPTION
    },
    'bess': {
        'rated_mw': 30.0,                    # ASSUMPTION: Containerized unit
        'rated_mwh': 120.0,                  # 4-hour duration
        'rated_mva': 30.0,                   # Unity PF
        'manufacturer': 'Tesla/Fluence',     # ASSUMPTION
        'model': 'Megapack 2XL',             # ASSUMPTION
    }
}


# =============================================================================
# PHYSICAL LAYOUT PARAMETERS
# =============================================================================

PHYSICAL_SPECS = {
    'recip': {
        # ASSUMPTION: Based on typical engine-generator package dimensions
        'length_m': 12.0,
        'width_m': 4.0,
        'height_m': 5.0,
        'weight_kg': 85000,                  # ~85 tons
        'clearance_m': 3.0,                  # Service clearance
        'noise_db_at_10m': 85,               # Sound pressure level
    },
    'turbine': {
        # ASSUMPTION: Aeroderivative GT package
        'length_m': 15.0,
        'width_m': 6.0,
        'height_m': 6.0,
        'weight_kg': 150000,                 # ~150 tons
        'clearance_m': 5.0,
        'noise_db_at_10m': 90,
    },
    'bess': {
        # ASSUMPTION: 40-ft container
        'length_m': 12.2,                    # 40-ft container
        'width_m': 2.4,
        'height_m': 2.9,
        'weight_kg': 80000,                  # ~80 tons loaded
        'clearance_m': 2.0,
        'noise_db_at_10m': 65,               # Mainly cooling fans
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_equipment_count(equipment_mw: float, equipment_type: str) -> int:
    """
    Calculate equipment count from total MW.
    
    Args:
        equipment_mw: Total MW of equipment type
        equipment_type: 'recip', 'turbine', 'bess', etc.
    
    Returns:
        Integer count of units
    """
    if equipment_mw <= 0:
        return 0
    
    unit_size = UNIT_SIZES.get(equipment_type, {}).get('rated_mw', 1.0)
    return round(equipment_mw / unit_size)


def get_equipment_details(equipment_type: str, equipment_mw: float) -> Dict:
    """
    Get complete equipment details including electrical, reliability, and physical specs.
    
    Args:
        equipment_type: 'recip', 'turbine', 'bess', etc.
        equipment_mw: Total MW
    
    Returns:
        Dictionary with all specifications
    """
    count = get_equipment_count(equipment_mw, equipment_type)
    unit_size = UNIT_SIZES.get(equipment_type, {}).get('rated_mw', equipment_mw)
    
    return {
        # Sizing
        'count': count,
        'unit_mw': unit_size,
        'total_mw': equipment_mw,
        'unit_mva': UNIT_SIZES.get(equipment_type, {}).get('rated_mva', unit_size / 0.85),
        
        # Manufacturer (ASSUMPTIONS)
        'manufacturer': UNIT_SIZES.get(equipment_type, {}).get('manufacturer', 'TBD'),
        'model': UNIT_SIZES.get(equipment_type, {}).get('model', 'TBD'),
        
        # Electrical specs
        **ELECTRICAL_SPECS.get(equipment_type, {}),
        
        # Reliability specs
        **RELIABILITY_SPECS.get(equipment_type, {}),
        
        # Physical specs
        **PHYSICAL_SPECS.get(equipment_type, {}),
    }


# =============================================================================
# ASSUMPTIONS SUMMARY FOR VALIDATION
# =============================================================================

ASSUMPTIONS_REQUIRING_VALIDATION = [
    "Generator impedances (Xd, Xd', Xd'') based on IEEE 115 typical values, not actual equipment datasheets",
    "Time constants from IEEE 399 typical ranges for generic reciprocating/turbine generators",
    "Inertia constants estimated based on equipment class, not manufacturer data",
    "Reliability (MTBF/MTTR) from IEEE 493 'Gold Book' generic categories",
    "Exciter types assumed (ST1A for recips, AC4A for turbines) - actual may differ",
    "Transformer ratings (100 MVA, 138/13.8kV) are placeholder assumptions",
    "BESS assumed grid-following mode - actual project may use grid-forming",
    "Equipment manufacturers/models are examples only - actual vendor TBD",
    "Physical dimensions are typical values - verify with actual layout drawings",
    "Noise levels are estimates - require site-specific acoustic study",
    "Voltage levels (13.8kV) assumed - verify against utility interconnection requirements",
]
