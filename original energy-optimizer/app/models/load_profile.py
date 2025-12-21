"""
Load Profile Data Models
Facility parameters and workload composition
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np


@dataclass
class WorkloadMix:
    """AI/HPC workload composition"""
    pre_training: float = 0.40
    fine_tuning: float = 0.15
    batch_inference: float = 0.20
    realtime_inference: float = 0.10
    rl_training: float = 0.05
    cloud_hpc: float = 0.10
    
    def __post_init__(self):
        self.validate()
    
    def validate(self) -> bool:
        """Ensure workload mix sums to 1.0"""
        total = sum([
            self.pre_training,
            self.fine_tuning,
            self.batch_inference,
            self.realtime_inference,
            self.rl_training,
            self.cloud_hpc,
        ])
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Workload mix must sum to 1.0, got {total}")
        return True
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "pre_training": self.pre_training,
            "fine_tuning": self.fine_tuning,
            "batch_inference": self.batch_inference,
            "realtime_inference": self.realtime_inference,
            "rl_training": self.rl_training,
            "cloud_hpc": self.cloud_hpc,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "WorkloadMix":
        return cls(**data)
    
    @classmethod
    def training_focused(cls) -> "WorkloadMix":
        """Pre-defined training-heavy mix"""
        return cls(
            pre_training=0.70,
            fine_tuning=0.15,
            batch_inference=0.05,
            realtime_inference=0.05,
            rl_training=0.03,
            cloud_hpc=0.02,
        )
    
    @classmethod
    def inference_focused(cls) -> "WorkloadMix":
        """Pre-defined inference-heavy mix"""
        return cls(
            pre_training=0.15,
            fine_tuning=0.05,
            batch_inference=0.35,
            realtime_inference=0.25,
            rl_training=0.05,
            cloud_hpc=0.15,
        )
    
    @classmethod
    def balanced(cls) -> "WorkloadMix":
        """Pre-defined balanced mix"""
        return cls()  # Use defaults
    
    @classmethod
    def traditional_cloud(cls) -> "WorkloadMix":
        """Pre-defined traditional cloud/HPC mix"""
        return cls(
            pre_training=0.05,
            fine_tuning=0.05,
            batch_inference=0.05,
            realtime_inference=0.05,
            rl_training=0.0,
            cloud_hpc=0.80,
        )


# Workload characteristics for calculations
WORKLOAD_PARAMS = {
    "pre_training": {
        "utilization_avg": 0.90,
        "variability": "low",
        "transient_magnitude": 2.5,
    },
    "fine_tuning": {
        "utilization_avg": 0.70,
        "variability": "medium",
        "transient_magnitude": 4.0,
    },
    "batch_inference": {
        "utilization_avg": 0.60,
        "variability": "medium",
        "transient_magnitude": 5.0,
    },
    "realtime_inference": {
        "utilization_avg": 0.45,
        "variability": "high",
        "transient_magnitude": 10.0,
    },
    "rl_training": {
        "utilization_avg": 0.65,
        "variability": "very_high",
        "transient_magnitude": 12.5,
    },
    "cloud_hpc": {
        "utilization_avg": 0.55,
        "variability": "low",
        "transient_magnitude": 2.5,
    },
}


@dataclass
class LoadProfile:
    """Complete facility load profile"""
    
    # Facility parameters
    it_capacity_mw: float = 160.0
    design_pue: float = 1.25
    cooling_type: str = "DLC"  # "Air", "DLC", "Immersion"
    rack_ups_seconds: int = 30  # 0, 30, 60, 300
    design_ambient_f: float = 95.0
    
    # Workload composition
    workload_mix: WorkloadMix = field(default_factory=WorkloadMix)
    
    # Seasonal PUE variation
    pue_winter: float = 1.15
    pue_spring_fall: float = 1.20
    pue_summer: float = 1.25
    pue_peak: float = 1.35
    
    @property
    def total_facility_mw(self) -> float:
        """Total facility load at design PUE"""
        return self.it_capacity_mw * self.design_pue
    
    @property
    def peak_facility_mw(self) -> float:
        """Peak facility load (summer peak PUE)"""
        return self.it_capacity_mw * self.pue_peak
    
    @property
    def min_facility_mw(self) -> float:
        """Minimum facility load (winter low PUE, low utilization)"""
        return self.it_capacity_mw * self.pue_winter * 0.5
    
    @property
    def cooling_load_mw(self) -> float:
        """Cooling load at design conditions"""
        return self.total_facility_mw - self.it_capacity_mw
    
    def weighted_utilization(self) -> float:
        """Calculate weighted average utilization"""
        mix = self.workload_mix.to_dict()
        return sum(
            mix[k] * WORKLOAD_PARAMS[k]["utilization_avg"]
            for k in mix
        )
    
    def effective_transient_magnitude(self) -> float:
        """Calculate weighted transient magnitude"""
        mix = self.workload_mix.to_dict()
        return sum(
            mix[k] * WORKLOAD_PARAMS[k]["transient_magnitude"]
            for k in mix
        )
    
    def raw_transient_mw(self) -> float:
        """Raw transient swing in MW (before UPS smoothing)"""
        return self.it_capacity_mw * (self.effective_transient_magnitude() / 10)
    
    def smoothed_transient_mw(self) -> float:
        """Transient swing after UPS smoothing"""
        # UPS reduces transient magnitude significantly
        reduction_factor = 0.35 if self.rack_ups_seconds >= 30 else 0.7
        return self.raw_transient_mw() * reduction_factor
    
    def generate_8760(self) -> np.ndarray:
        """Generate synthetic 8760 hourly load profile"""
        hours = np.arange(8760)
        
        # Base load (weighted utilization)
        base = self.it_capacity_mw * self.weighted_utilization()
        
        # Seasonal variation (PUE effect on cooling)
        seasonal = np.zeros(8760)
        for h in hours:
            day_of_year = h // 24
            # Simple sinusoidal seasonal pattern
            pue_factor = 0.5 * (1 + np.sin(2 * np.pi * day_of_year / 365 - np.pi/2))
            pue = self.pue_winter + pue_factor * (self.pue_summer - self.pue_winter)
            seasonal[h] = base * (pue - 1)  # Cooling contribution
        
        # Daily variation
        daily = 0.1 * base * np.sin(2 * np.pi * hours / 24 - np.pi/3)
        
        # Random noise
        noise = 0.02 * base * np.random.randn(8760)
        
        load = base + seasonal + daily + noise
        return np.maximum(load, 0.3 * base)  # Minimum load floor
    
    def to_dict(self) -> dict:
        return {
            "it_capacity_mw": self.it_capacity_mw,
            "design_pue": self.design_pue,
            "cooling_type": self.cooling_type,
            "rack_ups_seconds": self.rack_ups_seconds,
            "design_ambient_f": self.design_ambient_f,
            "workload_mix": self.workload_mix.to_dict(),
            "total_facility_mw": self.total_facility_mw,
        }
