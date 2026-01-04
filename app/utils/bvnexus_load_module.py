"""
bvNexus Load Module - AI HPC Data Center Load Modeling
=======================================================

This module provides comprehensive load modeling for AI HPC data centers,
translating Load Page configuration into:
- Pyomo optimization parameters
- PSS/e CMPLDW dynamic model fractions
- ETAP harmonic analysis data
- RAM reliability equipment counts

Critical Insight: AI HPC loads are 70-90% power electronic (GPU/TPU PSUs),
NOT motor-dominated like traditional industrial facilities.

Author: bvNexus Engineering Integration
Version: 4.1.0 (Corrected)
Date: 2026-01-03
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import math
import json


# =============================================================================
# SECTION 1: ENUMERATIONS AND CONSTANTS
# =============================================================================

class CoolingType(Enum):
    """Cooling technology options with associated characteristics."""
    AIR_COOLED = "air_cooled"
    REAR_DOOR_HEAT_EXCHANGER = "rear_door_heat_exchanger"
    DIRECT_LIQUID_COOLING = "direct_liquid_cooling"
    IMMERSION_SINGLE_PHASE = "immersion_single_phase"
    IMMERSION_TWO_PHASE = "immersion_two_phase"


class WorkloadType(Enum):
    """AI workload types with different flexibility characteristics."""
    PRE_TRAINING = "pre_training"
    FINE_TUNING = "fine_tuning"
    BATCH_INFERENCE = "batch_inference"
    REALTIME_INFERENCE = "realtime_inference"


class IsoRegion(Enum):
    """ISO/RTO regions with different interconnection requirements."""
    ERCOT = "ercot"
    SPP = "spp"
    PJM = "pjm"
    MISO = "miso"
    CAISO = "caiso"
    GENERIC = "generic"


# =============================================================================
# SECTION 2: CONFIGURATION DICTIONARIES
# =============================================================================

# Note: 'motor_load_pct' here is a reference baseline, but actual load
# will be calculated dynamically based on PUE.
COOLING_SPECS: Dict[str, Dict[str, Any]] = {
    "air_cooled": {
        "name": "Air-Cooled (Traditional)",
        "pue_range": (1.4, 1.8),
        "pue_typical": 1.5,
        "thd_i_cooling": 5.0,
        "vfd_penetration": 0.3,
        "chiller_type": "centrifugal",
        "motor_distribution": {
            "motor_a": 0.30,  # Small fans, pumps (5-15 HP)
            "motor_b": 0.40,  # Chillers (large, double-cage)
            "motor_c": 0.20,  # Compressors (constant torque)
            "motor_d": 0.10,  # VFD-driven
        },
    },
    "rear_door_heat_exchanger": {
        "name": "Rear-Door Heat Exchanger",
        "pue_range": (1.25, 1.4),
        "pue_typical": 1.3,
        "thd_i_cooling": 4.0,
        "vfd_penetration": 0.5,
        "chiller_type": "centrifugal",
        "motor_distribution": {
            "motor_a": 0.30,
            "motor_b": 0.40,
            "motor_c": 0.15,
            "motor_d": 0.15,
        },
    },
    "direct_liquid_cooling": {
        "name": "Direct-to-Chip Liquid",
        "pue_range": (1.1, 1.25),
        "pue_typical": 1.15,
        "thd_i_cooling": 3.0,
        "vfd_penetration": 0.7,
        "chiller_type": "screw",
        "motor_distribution": {
            "motor_a": 0.25,
            "motor_b": 0.35,
            "motor_c": 0.15,
            "motor_d": 0.25,
        },
    },
    "immersion_single_phase": {
        "name": "Single-Phase Immersion",
        "pue_range": (1.03, 1.1),
        "pue_typical": 1.05,
        "thd_i_cooling": 2.0,
        "vfd_penetration": 0.8,
        "chiller_type": "dry_cooler",
        "motor_distribution": {
            "motor_a": 0.20,
            "motor_b": 0.30,
            "motor_c": 0.10,
            "motor_d": 0.40,
        },
    },
    "immersion_two_phase": {
        "name": "Two-Phase Immersion",
        "pue_range": (1.01, 1.05),
        "pue_typical": 1.02,
        "thd_i_cooling": 1.5,
        "vfd_penetration": 0.9,
        "chiller_type": "dry_cooler",
        "motor_distribution": {
            "motor_a": 0.15,
            "motor_b": 0.25,
            "motor_c": 0.10,
            "motor_d": 0.50,
        },
    },
}


WORKLOAD_SPECS: Dict[str, Dict[str, Any]] = {
    "pre_training": {
        "name": "Pre-Training",
        "flexibility_pct": 30.0,
        "checkpoint_overhead_pct": 5.0,
        "restart_time_min": 15,
        "min_run_duration_hr": 2,
        "gang_scheduling": True,
        "dr_compatible": ["economic_dr", "ers_30"],
        "load_variability": "low",
        "power_profile_shape": "constant",
    },
    "fine_tuning": {
        "name": "Fine-Tuning",
        "flexibility_pct": 50.0,
        "checkpoint_overhead_pct": 3.0,
        "restart_time_min": 5,
        "min_run_duration_hr": 0.5,
        "gang_scheduling": False,
        "dr_compatible": ["economic_dr", "ers_30", "ers_10"],
        "load_variability": "medium",
        "power_profile_shape": "variable",
    },
    "batch_inference": {
        "name": "Batch Inference",
        "flexibility_pct": 90.0,
        "checkpoint_overhead_pct": 0.0,
        "restart_time_min": 1,
        "min_run_duration_hr": 0.0,
        "gang_scheduling": False,
        "dr_compatible": ["economic_dr", "ers_30", "ers_10", "frequency_response"],
        "load_variability": "high",
        "power_profile_shape": "queue_driven",
    },
    "realtime_inference": {
        "name": "Real-Time Inference",
        "flexibility_pct": 5.0,
        "checkpoint_overhead_pct": 0.0,
        "restart_time_min": 0,
        "min_run_duration_hr": 0.0,
        "gang_scheduling": False,
        "dr_compatible": [],
        "load_variability": "very_low",
        "power_profile_shape": "constant",
    },
}


ISO_PROFILES: Dict[str, Dict[str, Any]] = {
    "ercot": {
        "name": "ERCOT (Texas)",
        "large_load_threshold_mw": 75,
        "interconnection_process": "GINR",
        "lel_survey_required": True,
        "dynamic_model_required": True,
        "voltage_ride_through": {
            "required": True,
            "profile": "ercot_lel",
            "vtr": 0.0,   # No voltage trip
            "ttr": 999.0, # Long trip delay
        },
        "study_requirements": ["steady_state", "short_circuit", "dynamic"],
    },
    "spp": {
        "name": "SPP (Southwest Power Pool)",
        "large_load_threshold_mw": 50,
        "interconnection_process": "DISIS",
        "lel_survey_required": False,
        "dynamic_model_required": True,
        "voltage_ride_through": {
            "required": True,
            "profile": "ieee_1547",
            "vtr": 0.88,
            "ttr": 2.0,
        },
        "study_requirements": ["steady_state", "short_circuit", "dynamic"],
    },
    "pjm": {
        "name": "PJM Interconnection",
        "large_load_threshold_mw": 50,
        "interconnection_process": "DPP",
        "lel_survey_required": False,
        "dynamic_model_required": True,
        "voltage_ride_through": {
            "required": True,
            "profile": "pjm_standard",
            "vtr": 0.90,
            "ttr": 3.0,
        },
        "study_requirements": ["steady_state", "short_circuit", "dynamic", "sso"],
    },
    "miso": {
        "name": "MISO (Midcontinent ISO)",
        "large_load_threshold_mw": 50,
        "interconnection_process": "DPP",
        "lel_survey_required": False,
        "dynamic_model_required": True,
        "voltage_ride_through": {
            "required": True,
            "profile": "ieee_1547",
            "vtr": 0.88,
            "ttr": 2.0,
        },
        "study_requirements": ["steady_state", "short_circuit", "dynamic"],
    },
    "caiso": {
        "name": "CAISO (California)",
        "large_load_threshold_mw": 50,
        "interconnection_process": "LGIA",
        "lel_survey_required": False,
        "dynamic_model_required": True,
        "voltage_ride_through": {
            "required": True,
            "profile": "wecc",
            "vtr": 0.90,
            "ttr": 3.0,
        },
        "study_requirements": ["steady_state", "short_circuit", "dynamic", "emt"],
    },
    "generic": {
        "name": "Generic / Non-ISO",
        "large_load_threshold_mw": 100,
        "interconnection_process": "utility_specific",
        "lel_survey_required": False,
        "dynamic_model_required": False,
        "voltage_ride_through": {
            "required": False,
            "profile": "ieee_1547",
            "vtr": 0.88,
            "ttr": 2.0,
        },
        "study_requirements": ["steady_state"],
    },
}


# IEEE 493 Gold Book Reliability Data
IEEE_493_RELIABILITY: Dict[str, Dict[str, float]] = {
    "utility_single": {"lambda": 1.32, "mttr_hr": 1.5, "beta": 1.0},
    "utility_dual": {"lambda": 0.066, "mttr_hr": 1.5, "beta": 1.0},
    "transformer_power": {"lambda": 0.003, "mttr_hr": 720, "beta": 1.2},
    "transformer_dist": {"lambda": 0.005, "mttr_hr": 168, "beta": 1.1},
    "switchgear_mv": {"lambda": 0.0036, "mttr_hr": 24, "beta": 1.0},
    "switchgear_lv": {"lambda": 0.0011, "mttr_hr": 4, "beta": 1.0},
    "generator_recip": {"lambda": 0.012, "mttr_hr": 36, "beta": 0.9},
    "generator_turbine": {"lambda": 0.015, "mttr_hr": 48, "beta": 1.1},
    "ups_static": {"lambda": 0.0038, "mttr_hr": 8, "beta": 1.0},
    "sts": {"lambda": 0.0005, "mttr_hr": 2, "beta": 1.0},
    "pdu": {"lambda": 0.0012, "mttr_hr": 4, "beta": 1.0},
    "chiller_centrifugal": {"lambda": 0.15, "mttr_hr": 48, "beta": 1.3},
    "chiller_screw": {"lambda": 0.12, "mttr_hr": 24, "beta": 1.2},
    "crah": {"lambda": 0.08, "mttr_hr": 8, "beta": 1.0},
    "pump": {"lambda": 0.05, "mttr_hr": 8, "beta": 1.0},
}


# ETAP Harmonic Source Library
HARMONIC_SOURCES: Dict[str, Dict[str, Any]] = {
    "server_psu_active_pfc": {
        "description": "Server Power Supply (Active PFC)",
        "thd_i": 3.5,
        "input_pf": 0.99,
        "efficiency": 0.94,
        "spectrum": {
            3: {"mag": 1.5, "ang": -20},
            5: {"mag": 2.2, "ang": -35},
            7: {"mag": 1.8, "ang": -50},
            9: {"mag": 0.8, "ang": -65},
            11: {"mag": 0.5, "ang": -80},
            13: {"mag": 0.3, "ang": -95},
        },
    },
    "ups_double_conversion": {
        "description": "UPS Double Conversion Online",
        "thd_i": 5.5,
        "input_pf": 0.95,
        "efficiency": 0.96,
        "spectrum": {
            5: {"mag": 4.5, "ang": -30},
            7: {"mag": 2.8, "ang": -45},
            11: {"mag": 1.5, "ang": -60},
            13: {"mag": 1.2, "ang": -75},
            17: {"mag": 0.8, "ang": -90},
            19: {"mag": 0.6, "ang": -105},
        },
    },
    "vfd_6_pulse": {
        "description": "6-Pulse VFD",
        "thd_i": 28.0,
        "input_pf": 0.85,
        "spectrum": {
            5: {"mag": 20.0, "ang": -30},
            7: {"mag": 14.0, "ang": -50},
            11: {"mag": 9.0, "ang": -85},
            13: {"mag": 7.0, "ang": -110},
        },
    },
    "vfd_afe": {
        "description": "Active Front End VFD",
        "thd_i": 5.0,
        "input_pf": 0.98,
        "spectrum": {
            5: {"mag": 3.5, "ang": -30},
            7: {"mag": 2.5, "ang": -50},
            11: {"mag": 1.2, "ang": -85},
            13: {"mag": 0.8, "ang": -110},
        },
    },
    "chiller_vfd": {
        "description": "Chiller with VFD (12-Pulse)",
        "thd_i": 12.0,
        "input_pf": 0.92,
        "spectrum": {
            5: {"mag": 8.0, "ang": -30},
            7: {"mag": 6.0, "ang": -50},
            11: {"mag": 3.0, "ang": -85},
            13: {"mag": 2.0, "ang": -110},
        },
    },
}


# =============================================================================
# SECTION 3: DATA CLASSES
# =============================================================================

@dataclass
class WorkloadMix:
    """AI workload mix percentages (must sum to 1.0)."""
    pre_training: float = 0.3
    fine_tuning: float = 0.2
    batch_inference: float = 0.3
    realtime_inference: float = 0.2
    
    def __post_init__(self):
        total = self.pre_training + self.fine_tuning + self.batch_inference + self.realtime_inference
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Workload mix must sum to 1.0, got {total:.3f}")
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "pre_training": self.pre_training,
            "fine_tuning": self.fine_tuning,
            "batch_inference": self.batch_inference,
            "realtime_inference": self.realtime_inference,
        }


@dataclass
class LoadPageConfig:
    """Configuration from the Load Page UI."""
    peak_load_mw: float
    pue: float
    cooling_type: str = "rear_door_heat_exchanger"
    workload_mix: WorkloadMix = field(default_factory=WorkloadMix)
    iso_region: str = "generic"
    
    def __post_init__(self):
        if self.peak_load_mw <= 0:
            raise ValueError("Peak load must be positive")
        if self.pue < 1.0:
            raise ValueError("PUE must be >= 1.0")
        if self.cooling_type not in COOLING_SPECS:
            raise ValueError(f"Unknown cooling type: {self.cooling_type}")
        if self.iso_region not in ISO_PROFILES:
            raise ValueError(f"Unknown ISO region: {self.iso_region}")


@dataclass
class PsseFractions:
    """PSS/e CMPLDW composite load model fractions."""
    fma: float  # Motor A fraction (small commercial)
    fmb: float  # Motor B fraction (large industrial)
    fmc: float  # Motor C fraction (compressors)
    fmd: float  # Motor D fraction (VFD-driven)
    fel: float  # Electronic load fraction (GPU/TPU)
    pfs: float  # Static load fraction
    
    def __post_init__(self):
        total = self.fma + self.fmb + self.fmc + self.fmd + self.fel + self.pfs
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"CMPLDW fractions must sum to 1.0, got {total:.4f}")
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "fma": self.fma,
            "fmb": self.fmb,
            "fmc": self.fmc,
            "fmd": self.fmd,
            "fel": self.fel,
            "pfs": self.pfs,
        }


@dataclass
class EquipmentCounts:
    """Equipment counts for ETAP and RAM analysis."""
    ups_count: int
    ups_rating_kva: float
    chiller_count: int
    chiller_rating_mw: float
    chiller_vfd_equipped: bool
    crah_count: int
    crah_rating_kw: float
    pump_count: int
    pump_rating_kw: float


@dataclass
class HarmonicData:
    """Harmonic analysis data for ETAP."""
    thd_v: float
    thd_i: float
    dominant_orders: List[int]
    ieee_519_compliant: bool
    sources: List[Dict[str, Any]]
    assumed_scr: float


@dataclass
class FlexibilityData:
    """Demand response flexibility data."""
    weighted_flexibility_pct: float
    dr_capacity_mw: float
    economic_dr_mw: float
    ers_30_mw: float
    ers_10_mw: float
    checkpoint_overhead_pct: float
    min_curtailment_duration_hr: float
    notes: str


@dataclass
class LoadComposition:
    """Complete load composition result."""
    # Basic breakdown
    total_mw: float
    it_load_mw: float
    cooling_load_mw: float
    other_load_mw: float
    pue_actual: float
    
    # Power characteristics
    power_factor: float
    power_factor_type: str  # "lagging" or "leading"
    
    # PSS/e model data
    psse_fractions: PsseFractions
    
    # Equipment counts for ETAP/RAM
    equipment: EquipmentCounts
    
    # Harmonics
    harmonics: HarmonicData
    
    # Flexibility
    flexibility: FlexibilityData
    
    # ISO compliance
    iso_region: str
    requires_llis: bool
    voltage_ride_through: Dict[str, Any]


# =============================================================================
# SECTION 4: CORE CALCULATION FUNCTIONS
# =============================================================================

def calculate_load_breakdown(config: LoadPageConfig) -> Tuple[float, float, float]:
    """
    Calculate IT, cooling, and other load breakdown from PUE.
    
    Args:
        config: Load page configuration
        
    Returns:
        Tuple of (it_load_mw, cooling_load_mw, other_load_mw)
    """
    total_mw = config.peak_load_mw
    pue = config.pue
    
    # IT load = Total / PUE
    it_load_mw = total_mw / pue
    
    # Other losses (UPS, PDU, lighting) ~2% of total
    other_load_mw = total_mw * 0.02
    
    # Cooling = remainder
    cooling_load_mw = total_mw - it_load_mw - other_load_mw
    
    return it_load_mw, cooling_load_mw, other_load_mw


def calculate_psse_fractions(config: LoadPageConfig) -> PsseFractions:
    """
    Calculate PSS/e CMPLDW load model fractions.
    
    CORRECTED LOGIC v4.1:
    Now calculates motor fractions dynamically based on actual Cooling Load (PUE),
    rather than using hardcoded percentages. This prevents "missing" motor inertia
    in the dynamic model.
    
    Args:
        config: Load page configuration
        
    Returns:
        PsseFractions with motor/electronic/static breakdown
    """
    # 1. Get the actual component breakdown from PUE
    it_load_mw, cooling_load_mw, other_load_mw = calculate_load_breakdown(config)
    total_mw = config.peak_load_mw
    
    # 2. Calculate actual fraction of total load that is cooling (Motor load)
    actual_cooling_pct = cooling_load_mw / total_mw
    
    # 3. Get motor distribution mix for the cooling type
    cooling_spec = COOLING_SPECS[config.cooling_type]
    motor_dist = cooling_spec["motor_distribution"]
    
    # Normalize distribution just in case
    dist_sum = sum(motor_dist.values())
    
    # 4. Distribute the ACTUAL cooling load across motor types
    fma = actual_cooling_pct * (motor_dist["motor_a"] / dist_sum)
    fmb = actual_cooling_pct * (motor_dist["motor_b"] / dist_sum)
    fmc = actual_cooling_pct * (motor_dist["motor_c"] / dist_sum)
    fmd = actual_cooling_pct * (motor_dist["motor_d"] / dist_sum)
    
    # 5. Electronic Fraction (IT Load)
    # 95% of IT load is server PSUs (Electronic)
    it_fraction = it_load_mw / total_mw
    fel = it_fraction * 0.95
    
    # 6. Static Fraction (Remainder)
    # Includes:
    # - 2% Facility/Other (Lighting, etc.)
    # - 5% of IT Load (Fans inside server chassis, etc.)
    # - Any rounding residuals
    total_motor = fma + fmb + fmc + fmd
    pfs = 1.0 - (total_motor + fel)
    
    # Safety clamp to prevent negative float errors
    pfs = max(0.0, pfs)
    
    # Renormalize to ensure exact 1.0 sum
    total = fma + fmb + fmc + fmd + fel + pfs
    if total > 0:
        fma /= total
        fmb /= total
        fmc /= total
        fmd /= total
        fel /= total
        pfs /= total
    
    return PsseFractions(fma=fma, fmb=fmb, fmc=fmc, fmd=fmd, fel=fel, pfs=pfs)


def calculate_equipment_counts(config: LoadPageConfig) -> EquipmentCounts:
    """
    Calculate equipment counts for ETAP and RAM analysis.
    
    CORRECTED LOGIC v4.1:
    Updated equipment ratings to reflect standard MEP sizing conventions
    (Ton vs kW/Ton) rather than arbitrary MW ratings.
    
    Args:
        config: Load page configuration
        
    Returns:
        EquipmentCounts with UPS, chiller, CRAH, pump counts
    """
    it_load_mw, cooling_load_mw, _ = calculate_load_breakdown(config)
    cooling_spec = COOLING_SPECS[config.cooling_type]
    
    # UPS sizing: Standard 2.5 MVA / 2.5 MW blocks
    ups_rating_kva = 2500
    ups_count = max(1, math.ceil(it_load_mw * 1000 / ups_rating_kva))
    
    # Chiller sizing: 
    # Standard 1250 Ton Centrifugal Chiller
    # Efficiency ~0.55 kW/Ton -> ~690 kW electrical input
    # Rounded to 0.75 MW electrical for conservative breaker sizing
    chiller_rating_mw = 0.75 
    chiller_load_mw = cooling_load_mw * 0.6 # Chillers take ~60% of cooling energy
    chiller_count = max(1, math.ceil(chiller_load_mw / chiller_rating_mw))
    
    chiller_vfd_equipped = cooling_spec["vfd_penetration"] > 0.5
    
    # CRAH sizing: 150 kW sensible cooling units (typical)
    crah_rating_kw = 150
    crah_load_mw = cooling_load_mw * 0.3
    crah_count = max(1, math.ceil(crah_load_mw * 1000 / crah_rating_kw))
    
    # Pump sizing: 75 kW (100 HP) pumps typical for large loops
    pump_rating_kw = 75
    pump_load_mw = cooling_load_mw * 0.1
    pump_count = max(1, math.ceil(pump_load_mw * 1000 / pump_rating_kw))
    
    return EquipmentCounts(
        ups_count=ups_count,
        ups_rating_kva=ups_rating_kva,
        chiller_count=chiller_count,
        chiller_rating_mw=chiller_rating_mw,
        chiller_vfd_equipped=chiller_vfd_equipped,
        crah_count=crah_count,
        crah_rating_kw=crah_rating_kw,
        pump_count=pump_count,
        pump_rating_kw=pump_rating_kw,
    )


def calculate_harmonics(config: LoadPageConfig, equipment: EquipmentCounts) -> HarmonicData:
    """
    Calculate harmonic characteristics for ETAP analysis.
    
    CORRECTED LOGIC v4.1:
    Corrected Voltage THD calculation to use a realistic System Impedance (Z_sys)
    based on Short Circuit Ratio (SCR) = 20, rather than arbitrary 0.5 multiplier.
    
    Args:
        config: Load page configuration
        equipment: Equipment counts
        
    Returns:
        HarmonicData with THD and spectrum information
    """
    it_load_mw, cooling_load_mw, _ = calculate_load_breakdown(config)
    total_mw = config.peak_load_mw
    cooling_spec = COOLING_SPECS[config.cooling_type]
    
    # IT load THD (server PSUs with Active PFC)
    it_thd_i = HARMONIC_SOURCES["server_psu_active_pfc"]["thd_i"]
    
    # Cooling load THD
    cooling_thd_i = cooling_spec["thd_i_cooling"]
    
    # UPS contribution
    ups_thd_i = HARMONIC_SOURCES["ups_double_conversion"]["thd_i"]
    
    # Composite Current THD (RSS combination)
    it_weight = it_load_mw / total_mw
    cooling_weight = cooling_load_mw / total_mw
    ups_weight = 0.02  # UPS losses
    
    composite_thd_i = math.sqrt(
        (it_weight * it_thd_i) ** 2 +
        (cooling_weight * cooling_thd_i) ** 2 +
        (ups_weight * ups_thd_i) ** 2
    )
    
    # Voltage THD Calculation
    # Assumption: PCC SCR (Short Circuit Ratio) = 20 (Standard utility requirement)
    # Z_sys (p.u.) = 1 / SCR
    assumed_scr = 20.0
    z_sys = 1.0 / assumed_scr
    
    # V_THD approx I_THD * Z_sys (Linear approximation valid for low harmonic orders)
    composite_thd_v = composite_thd_i * z_sys
    
    # IEEE 519-2022 compliance check
    # For 1-69 kV: V_THD <= 5.0%, I_THD <= 8.0% (assuming Isc/IL >= 20)
    ieee_519_compliant = composite_thd_v <= 5.0 and composite_thd_i <= 8.0
    
    # Build source list
    sources = [
        {
            "id": "IT_LOAD",
            "type": "server_psu_active_pfc",
            "fraction": it_weight,
            **HARMONIC_SOURCES["server_psu_active_pfc"],
        },
        {
            "id": "UPS_SYSTEM",
            "type": "ups_double_conversion",
            "fraction": ups_weight,
            **HARMONIC_SOURCES["ups_double_conversion"],
        },
    ]
    
    if equipment.chiller_vfd_equipped:
        sources.append({
            "id": "CHILLER_VFD",
            "type": "vfd_afe",
            "fraction": cooling_weight * 0.6,
            **HARMONIC_SOURCES["vfd_afe"],
        })
    
    return HarmonicData(
        thd_v=composite_thd_v,
        thd_i=composite_thd_i,
        dominant_orders=[5, 7, 11, 13],
        ieee_519_compliant=ieee_519_compliant,
        sources=sources,
        assumed_scr=assumed_scr
    )


def calculate_flexibility(config: LoadPageConfig) -> FlexibilityData:
    """
    Calculate demand response flexibility parameters.
    
    Args:
        config: Load page configuration
        
    Returns:
        FlexibilityData with DR capacity and compatibility
    """
    workload_mix = config.workload_mix.to_dict()
    
    # Weighted average flexibility
    weighted_flex = sum(
        frac * WORKLOAD_SPECS[wtype]["flexibility_pct"]
        for wtype, frac in workload_mix.items()
        if frac > 0
    )
    
    # Weighted checkpoint overhead
    weighted_checkpoint = sum(
        frac * WORKLOAD_SPECS[wtype]["checkpoint_overhead_pct"]
        for wtype, frac in workload_mix.items()
        if frac > 0
    )
    
    # Total DR capacity
    dr_capacity_mw = config.peak_load_mw * (weighted_flex / 100.0)
    
    # DR product allocations
    # NOTE: These are ELIGIBILITY calculations, not additive capacity.
    # A single MW cannot typically be sold into multiple simultaneous programs.
    
    # Economic DR: all flexible capacity
    economic_dr_mw = dr_capacity_mw
    
    # ERS-30: pre-training + fine-tuning + batch inference
    ers_30_eligible = (
        workload_mix["pre_training"] * WORKLOAD_SPECS["pre_training"]["flexibility_pct"] +
        workload_mix["fine_tuning"] * WORKLOAD_SPECS["fine_tuning"]["flexibility_pct"] +
        workload_mix["batch_inference"] * WORKLOAD_SPECS["batch_inference"]["flexibility_pct"]
    ) / 100.0
    ers_30_mw = config.peak_load_mw * ers_30_eligible
    
    # ERS-10: fine-tuning + batch inference only
    ers_10_eligible = (
        workload_mix["fine_tuning"] * WORKLOAD_SPECS["fine_tuning"]["flexibility_pct"] +
        workload_mix["batch_inference"] * WORKLOAD_SPECS["batch_inference"]["flexibility_pct"]
    ) / 100.0
    ers_10_mw = config.peak_load_mw * ers_10_eligible
    
    # Minimum curtailment duration (weighted)
    min_duration = max(
        frac * WORKLOAD_SPECS[wtype]["min_run_duration_hr"]
        for wtype, frac in workload_mix.items()
        if frac > 0.1
    )
    
    return FlexibilityData(
        weighted_flexibility_pct=weighted_flex,
        dr_capacity_mw=dr_capacity_mw,
        economic_dr_mw=economic_dr_mw,
        ers_30_mw=ers_30_mw,
        ers_10_mw=ers_10_mw,
        checkpoint_overhead_pct=weighted_checkpoint,
        min_curtailment_duration_hr=min_duration,
        notes="WARNING: Program capacities are based on technical eligibility and are mutually exclusive (non-additive)."
    )


def get_iso_compliance(config: LoadPageConfig) -> Tuple[bool, Dict[str, Any]]:
    """
    Get ISO/RTO compliance requirements.
    
    Args:
        config: Load page configuration
        
    Returns:
        Tuple of (requires_llis, voltage_ride_through_settings)
    """
    iso_profile = ISO_PROFILES[config.iso_region]
    threshold = iso_profile["large_load_threshold_mw"]
    
    requires_llis = config.peak_load_mw >= threshold
    vrt = iso_profile["voltage_ride_through"]
    
    return requires_llis, vrt


# =============================================================================
# SECTION 5: MAIN CALCULATION FUNCTION
# =============================================================================

def calculate_load_composition(config: LoadPageConfig) -> LoadComposition:
    """
    Master function to calculate complete load composition.
    
    This is the main entry point that should be called from the optimizer
    and integration modules.
    
    Args:
        config: Load page configuration
        
    Returns:
        Complete LoadComposition with all parameters for PSS/e, ETAP, RAM
    """
    # Calculate load breakdown
    it_load_mw, cooling_load_mw, other_load_mw = calculate_load_breakdown(config)
    
    # Calculate PSS/e fractions
    psse_fractions = calculate_psse_fractions(config)
    
    # Calculate equipment counts
    equipment = calculate_equipment_counts(config)
    
    # Calculate harmonics
    harmonics = calculate_harmonics(config, equipment)
    
    # Calculate flexibility
    flexibility = calculate_flexibility(config)
    
    # Get ISO compliance
    requires_llis, voltage_ride_through = get_iso_compliance(config)
    
    return LoadComposition(
        total_mw=config.peak_load_mw,
        it_load_mw=it_load_mw,
        cooling_load_mw=cooling_load_mw,
        other_load_mw=other_load_mw,
        pue_actual=config.pue,
        power_factor=0.99,  # Corrected: AI Hardware is Unity PF
        power_factor_type="leading", # often slightly capacitive due to filters
        psse_fractions=psse_fractions,
        equipment=equipment,
        harmonics=harmonics,
        flexibility=flexibility,
        iso_region=config.iso_region,
        requires_llis=requires_llis,
        voltage_ride_through=voltage_ride_through,
    )


# =============================================================================
# SECTION 6: EXPORT GENERATORS
# =============================================================================

def generate_psse_dyr_parameters(
    composition: LoadComposition,
    bus_number: int = 401001,
    load_id: str = "1"
) -> str:
    """
    Generate PSS/e DYR file content for CMLDALU2 composite load model.
    
    Args:
        composition: Calculated load composition
        bus_number: PSS/e bus number
        load_id: Load ID string
        
    Returns:
        DYR file content as string
    """
    f = composition.psse_fractions
    vrt = composition.voltage_ride_through
    vtr = vrt.get("vtr", 0.88)
    ttr = vrt.get("ttr", 2.0)
    
    dyr = f"""/ PSS/e CMLDALU2 Composite Load Model
/ Generated by bvNexus Load Module v4.1 (Corrected)
/ Load Composition: {f.fel*100:.1f}% Electronic, {(f.fma+f.fmb+f.fmc+f.fmd)*100:.1f}% Motor
/ ISO Region: {composition.iso_region.upper()}
/
{bus_number}  'CMLDALU2'  {load_id}  /
/ Record 1: Distribution equivalent
  0.0000, 0.0400, 0.0400, 0.7500, 0.0800, 1.0000, 1.0000, 0,
  0.9000, 1.1000, 0.00625, 1.0000, 1.0000, 30.0, 5.0, 0.0000, 0.0000 /
/ Record 2: Load composition fractions
  {f.fma:.4f}, {f.fmb:.4f}, {f.fmc:.4f}, {f.fmd:.4f}, {f.fel:.4f}, {f.pfs:.4f} /
/ Record 3: Motor A (small fans, pumps)
  0.7500, 0.0400, 0.0400, 3.5000, 0.0400, 0.1200, 0.0000, 0.0000,
  0.4000, 0.0000, 0.8000, 0.0200, 10.0, 0.0000, 0.0250, 15.0,
  1.3000, 4.3000, 0.0500, 0.2000, 0.9000, 1.0000, 1.0000 /
/ Record 4: Motor B (chillers)
  0.7500, 0.0300, 0.0300, 4.0000, 0.0300, 0.0800, 0.0200, 0.1700,
  1.0000, 0.0000, 0.7500, 0.0200, 15.0, 0.0000, 0.0250, 30.0,
  1.3000, 4.3000, 0.0500, 0.2000, 0.8500, 1.0000, 1.0000 /
/ Record 5: Motor C (compressors)
  0.7500, 0.0400, 0.0400, 3.5000, 0.0500, 0.1200, 0.0000, 0.0000,
  0.1500, 0.0000, 0.5500, 0.0200, 20.0, 0.0000, 0.0250, 10.0,
  2.0000, 4.3000, 0.1000, 0.2500, 0.6500, 1.0000, 1.0000 /
/ Record 6: Motor D (VFD-driven)
  0.7500, 0.0400, 0.0400, 3.5000, 0.0400, 0.1000, 0.0000, 0.0000,
  0.5000, 0.0000, 0.7000, 0.0300, 10.0, 0.0000, 0.0250, 20.0,
  1.5000, 4.3000, 0.0800, 0.3000, 0.8000, 1.0000, 1.0000 /
/ Record 7: Electronic load (GPU/TPU) - Unity PF assumed
  0.7000, 0.5000, 0.3000, 0.9900, 0.9900, {vtr:.4f}, {ttr:.1f},
  0.5000, 0.4000, 0.6000, 0.5000, 15.0, 1.5000, 4.0000 /
/ Record 8: Static load
  0.0000, 0.0000, 1.0000, 1.0000, 0.0000, 0.0000, 1.0000, 2.0000 /
/
"""
    return dyr


def generate_etap_data(composition: LoadComposition, site_id: str = "SITE") -> Dict[str, Any]:
    """
    Generate ETAP DataX-compatible data structure.
    
    Args:
        composition: Calculated load composition
        site_id: Site identifier
        
    Returns:
        Dictionary ready for JSON serialization
    """
    eq = composition.equipment
    
    return {
        "metadata": {
            "format": "ETAP_DataX",
            "version": "22.0",
            "generated_by": "bvNexus Load Module v4.1",
        },
        "loads": [
            {
                "Load_ID": f"{site_id}_LOAD_DC",
                "Rated_kVA": composition.total_mw * 1000 / composition.power_factor,
                "PF": composition.power_factor,
                "Load_Model": "CONSTANT_POWER",
                "Harmonic_Enabled": True,
                "THD_I": composition.harmonics.thd_i,
                "Ref_SCR": composition.harmonics.assumed_scr
            }
        ],
        "ups_systems": [
            {
                "UPS_ID": f"{site_id}_UPS_{i+1:03d}",
                "Rated_kVA": eq.ups_rating_kva,
                "Topology": "DOUBLE_CONVERSION",
                "Efficiency": 0.96,
                "THD_I": HARMONIC_SOURCES["ups_double_conversion"]["thd_i"],
            }
            for i in range(eq.ups_count)
        ],
        "motors": [
            {
                "Motor_ID": f"{site_id}_MTR_CHILLER_{i+1:03d}",
                "Rated_HP": 2000,
                "Rated_kV": 4.16,
                "Starting_Method": "VFD" if eq.chiller_vfd_equipped else "ACROSS_LINE",
                "VFD_Equipped": eq.chiller_vfd_equipped,
            }
            for i in range(eq.chiller_count)
        ],
        "harmonic_sources": composition.harmonics.sources,
    }


def generate_ram_data(composition: LoadComposition, site_id: str = "SITE") -> Dict[str, Any]:
    """
    Generate RAM reliability data structure.
    
    Args:
        composition: Calculated load composition
        site_id: Site identifier
        
    Returns:
        Dictionary with reliability blocks and parameters
    """
    eq = composition.equipment
    blocks = []
    
    # UPS blocks
    for i in range(eq.ups_count):
        rel_data = IEEE_493_RELIABILITY["ups_static"]
        blocks.append({
            "block_id": f"{site_id}_BLK_UPS_{i+1:03d}",
            "type": "UPS",
            "lambda": rel_data["lambda"],
            "mtbf_hr": 1 / rel_data["lambda"],
            "mttr_hr": rel_data["mttr_hr"],
            "distribution": "exponential",
            "beta": rel_data["beta"],
        })
    
    # Chiller blocks
    chiller_type = "chiller_centrifugal" if eq.chiller_vfd_equipped else "chiller_screw"
    for i in range(eq.chiller_count):
        rel_data = IEEE_493_RELIABILITY[chiller_type]
        blocks.append({
            "block_id": f"{site_id}_BLK_CHILLER_{i+1:03d}",
            "type": "CHILLER",
            "lambda": rel_data["lambda"],
            "mtbf_hr": 1 / rel_data["lambda"],
            "mttr_hr": rel_data["mttr_hr"],
            "distribution": "weibull",
            "beta": rel_data["beta"],
        })
    
    # Calculate simple availability
    ups_mtbf = 1 / IEEE_493_RELIABILITY["ups_static"]["lambda"]
    ups_mttr = IEEE_493_RELIABILITY["ups_static"]["mttr_hr"]
    ups_avail = ups_mtbf / (ups_mtbf + ups_mttr)
    
    chiller_mtbf = 1 / IEEE_493_RELIABILITY[chiller_type]["lambda"]
    chiller_mttr = IEEE_493_RELIABILITY[chiller_type]["mttr_hr"]
    chiller_avail = chiller_mtbf / (chiller_mtbf + chiller_mttr)
    
    # Assume 2N UPS and N+1 chillers
    power_avail = 1 - (1 - ups_avail) ** 2
    cooling_avail = sum(
        math.comb(eq.chiller_count, i) * chiller_avail ** i * (1 - chiller_avail) ** (eq.chiller_count - i)
        for i in range(eq.chiller_count - 1, eq.chiller_count + 1)
    )
    
    overall_avail = power_avail * cooling_avail
    
    return {
        "metadata": {
            "standard": "IEEE 493-2007",
            "mission_time_hr": 8760,
        },
        "blocks": blocks,
        "availability": {
            "power_path": power_avail,
            "cooling": cooling_avail,
            "overall": overall_avail,
            "downtime_hr_yr": (1 - overall_avail) * 8760,
        },
    }


# =============================================================================
# SECTION 7: PYOMO INTEGRATION HELPERS
# =============================================================================

def get_pyomo_load_parameters(composition: LoadComposition) -> Dict[str, Any]:
    """
    Get parameters formatted for Pyomo optimization model.
    
    Args:
        composition: Calculated load composition
        
    Returns:
        Dictionary of parameters for Pyomo model
    """
    return {
        # Basic load parameters
        "peak_load_mw": composition.total_mw,
        "it_load_mw": composition.it_load_mw,
        "cooling_load_mw": composition.cooling_load_mw,
        "pue": composition.pue_actual,
        "power_factor": composition.power_factor,
        
        # Flexibility parameters (for DR optimization)
        "flexibility_pct": composition.flexibility.weighted_flexibility_pct,
        "dr_capacity_mw": composition.flexibility.dr_capacity_mw,
        "economic_dr_mw": composition.flexibility.economic_dr_mw,
        "ers_30_mw": composition.flexibility.ers_30_mw,
        "ers_10_mw": composition.flexibility.ers_10_mw,
        "min_curtailment_hr": composition.flexibility.min_curtailment_duration_hr,
        
        # Equipment counts (for reliability constraints)
        "ups_count": composition.equipment.ups_count,
        "chiller_count": composition.equipment.chiller_count,
        
        # ISO compliance
        "requires_llis": composition.requires_llis,
        "iso_region": composition.iso_region,
    }


def get_load_profile_multipliers(
    workload_mix: WorkloadMix,
    hours: int = 8760
) -> List[float]:
    """
    Generate hourly load profile multipliers based on workload mix.
    
    Args:
        workload_mix: Workload mix percentages
        hours: Number of hours (default 8760 for one year)
        
    Returns:
        List of hourly multipliers (0.7 - 1.0 range typical)
    """
    import random
    random.seed(42)  # Reproducible results
    
    mix = workload_mix.to_dict()
    
    # Base profile (weighted average of variability)
    variability_map = {
        "pre_training": 0.05,      # Very stable
        "fine_tuning": 0.15,       # Moderate variation
        "batch_inference": 0.30,   # High variation
        "realtime_inference": 0.02, # Almost constant
    }
    
    weighted_variability = sum(
        frac * variability_map[wtype]
        for wtype, frac in mix.items()
    )
    
    multipliers = []
    for h in range(hours):
        # Base load (high for data centers)
        base = 0.85
        
        # Add time-of-day pattern (slight)
        hour_of_day = h % 24
        tod_factor = 1.0 + 0.05 * math.sin(2 * math.pi * (hour_of_day - 6) / 24)
        
        # Add random variation based on workload mix
        random_factor = 1.0 + random.gauss(0, weighted_variability)
        random_factor = max(0.7, min(1.1, random_factor))
        
        multiplier = base * tod_factor * random_factor
        multiplier = max(0.5, min(1.0, multiplier))
        
        multipliers.append(multiplier)
    
    return multipliers


# =============================================================================
# SECTION 8: MAIN FUNCTION AND CLI
# =============================================================================

def main():
    """Example usage of the load module."""
    
    # Create configuration
    config = LoadPageConfig(
        peak_load_mw=200,
        pue=1.3,
        cooling_type="rear_door_heat_exchanger",
        workload_mix=WorkloadMix(
            pre_training=0.30,
            fine_tuning=0.20,
            batch_inference=0.30,
            realtime_inference=0.20,
        ),
        iso_region="ercot",
    )
    
    # Calculate composition
    composition = calculate_load_composition(config)
    
    # Print summary
    print("=" * 60)
    print("bvNexus Load Composition Analysis (v4.1 Corrected)")
    print("=" * 60)
    print(f"\nTotal Load: {composition.total_mw:.1f} MW")
    print(f"  IT Load:      {composition.it_load_mw:.1f} MW ({composition.it_load_mw/composition.total_mw*100:.1f}%)")
    print(f"  Cooling Load: {composition.cooling_load_mw:.1f} MW ({composition.cooling_load_mw/composition.total_mw*100:.1f}%)")
    print(f"  PUE:          {composition.pue_actual:.2f}")
    
    print(f"\nPSS/e CMPLDW Fractions (Dynamic Calculation):")
    f = composition.psse_fractions
    print(f"  Motor A (small fans):  {f.fma*100:.1f}%")
    print(f"  Motor B (chillers):    {f.fmb*100:.1f}%")
    print(f"  Motor C (compressors): {f.fmc*100:.1f}%")
    print(f"  Motor D (VFD-driven):  {f.fmd*100:.1f}%")
    print(f"  Electronic (GPU/TPU):  {f.fel*100:.1f}%  ← DOMINANT")
    print(f"  Static:                {f.pfs*100:.1f}%")
    
    print(f"\nEquipment Counts (Corrected Sizing):")
    eq = composition.equipment
    print(f"  UPS Modules:    {eq.ups_count} × {eq.ups_rating_kva} kVA")
    print(f"  Chillers:       {eq.chiller_count} × {eq.chiller_rating_mw} MW (Electrical)")
    print(f"  CRAH Units:     {eq.crah_count} × {eq.crah_rating_kw} kW")
    
    print(f"\nFlexibility:")
    flex = composition.flexibility
    print(f"  Weighted Flexibility: {flex.weighted_flexibility_pct:.1f}%")
    print(f"  DR Capacity:          {flex.dr_capacity_mw:.1f} MW")
    print(f"  NOTE: {flex.notes}")
    
    print(f"\nISO Compliance ({composition.iso_region.upper()}):")
    print(f"  LLIS Required:        {composition.requires_llis}")
    vrt = composition.voltage_ride_through
    print(f"  VRT Profile:          {vrt['profile']}")
    
    print(f"\nHarmonics (Calculated with SCR=20):")
    print(f"  THD-V: {composition.harmonics.thd_v:.2f}% (Limit: 5.0%)")
    print(f"  THD-I: {composition.harmonics.thd_i:.2f}% (Limit: 8.0%)")
    print(f"  Status: {'COMPLIANT' if composition.harmonics.ieee_519_compliant else 'NON-COMPLIANT'}")
    
    # Generate and print DYR content
    print("\n" + "=" * 60)
    print("PSS/e DYR File Content (excerpt):")
    print("=" * 60)
    dyr_content = generate_psse_dyr_parameters(composition)
    print(dyr_content[:1500] + "...")
    
    return composition


if __name__ == "__main__":
    main()
