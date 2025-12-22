"""
Load Profile Data Models with Demand Response Capabilities
Facility parameters, workload composition, and DR flexibility
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import numpy as np


@dataclass
class WorkloadMix:
    """
    AI/HPC workload composition with demand response flexibility.
    
    Based on research findings:
    - Pre-training: 20-40% flexible, 5-30 min response
    - Fine-tuning: 40-60% flexible, 1-10 min response  
    - Batch inference: 80-100% flexible, <1 min response
    - Real-time inference: 0-10% flexible (SLA protected)
    """
    # Workload composition (fractions, must sum to 1.0)
    pre_training: float = 0.40
    fine_tuning: float = 0.15
    batch_inference: float = 0.20
    realtime_inference: float = 0.10
    rl_training: float = 0.05
    cloud_hpc: float = 0.10
    
    # Demand response flexibility parameters (research-based defaults)
    pre_training_flex: float = 0.30      # 30% of pre-training is flexible
    fine_tuning_flex: float = 0.50       # 50% of fine-tuning is flexible
    batch_inference_flex: float = 0.90   # 90% of batch is flexible
    realtime_inference_flex: float = 0.05  # 5% of realtime is flexible
    rl_training_flex: float = 0.40       # 40% of RL training is flexible
    cloud_hpc_flex: float = 0.25         # 25% of cloud HPC is flexible
    
    # Response time parameters (minutes)
    pre_training_response_min: float = 15.0
    fine_tuning_response_min: float = 5.0
    batch_inference_response_min: float = 1.0
    realtime_inference_response_min: float = float('inf')  # Cannot interrupt
    rl_training_response_min: float = 10.0
    cloud_hpc_response_min: float = 20.0
    
    # Minimum run durations (hours) - cannot interrupt more frequently
    pre_training_min_run_hrs: float = 3.0
    fine_tuning_min_run_hrs: float = 1.0
    batch_inference_min_run_hrs: float = 0.0
    realtime_inference_min_run_hrs: float = float('inf')
    rl_training_min_run_hrs: float = 2.0
    cloud_hpc_min_run_hrs: float = 4.0
    
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
    
    def calculate_total_flexibility(self) -> float:
        """
        Calculate total IT load flexibility percentage.
        
        Returns:
            Weighted average flexibility (0-1)
        """
        total_flex = (
            self.pre_training * self.pre_training_flex +
            self.fine_tuning * self.fine_tuning_flex +
            self.batch_inference * self.batch_inference_flex +
            self.realtime_inference * self.realtime_inference_flex +
            self.rl_training * self.rl_training_flex +
            self.cloud_hpc * self.cloud_hpc_flex
        )
        return total_flex
    
    def get_flexibility_by_response_time(self, max_response_minutes: float) -> float:
        """
        Calculate flexibility available within a given response time.
        
        Args:
            max_response_minutes: Maximum acceptable response time
        
        Returns:
            Flexibility percentage achievable within that response time
        """
        flex = 0.0
        
        if max_response_minutes >= self.realtime_inference_response_min:
            flex += self.realtime_inference * self.realtime_inference_flex
        
        if max_response_minutes >= self.batch_inference_response_min:
            flex += self.batch_inference * self.batch_inference_flex
        
        if max_response_minutes >= self.fine_tuning_response_min:
            flex += self.fine_tuning * self.fine_tuning_flex
        
        if max_response_minutes >= self.rl_training_response_min:
            flex += self.rl_training * self.rl_training_flex
        
        if max_response_minutes >= self.pre_training_response_min:
            flex += self.pre_training * self.pre_training_flex
        
        if max_response_minutes >= self.cloud_hpc_response_min:
            flex += self.cloud_hpc * self.cloud_hpc_flex
        
        return flex
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "pre_training": self.pre_training,
            "fine_tuning": self.fine_tuning,
            "batch_inference": self.batch_inference,
            "realtime_inference": self.realtime_inference,
            "rl_training": self.rl_training,
            "cloud_hpc": self.cloud_hpc,
            "flexibility": {
                "pre_training": self.pre_training_flex,
                "fine_tuning": self.fine_tuning_flex,
                "batch_inference": self.batch_inference_flex,
                "realtime_inference": self.realtime_inference_flex,
                "rl_training": self.rl_training_flex,
                "cloud_hpc": self.cloud_hpc_flex,
            },
            "total_it_flexibility": self.calculate_total_flexibility(),
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


@dataclass
class CoolingFlexibility:
    """
    Cooling system flexibility parameters for demand response.
    Based on research: 20-30% of cooling load is flexible.
    """
    
    # Thermal parameters
    thermal_time_constant_min: float = 30.0  # Minutes to reach new equilibrium
    max_setpoint_increase_c: float = 3.0     # Maximum temperature rise allowed
    power_reduction_per_degree_pct: float = 4.0  # % of cooling load per °C
    
    # Operational constraints
    min_chiller_on_time_min: float = 20.0    # Minimum run time before cycling
    min_chiller_off_time_min: float = 15.0   # Minimum off time before restart
    max_cooling_reduction_pct: float = 25.0  # Maximum cooling load reduction
    
    # Response characteristics
    response_time_min: float = 15.0          # Time to reduce cooling
    recovery_time_min: float = 30.0          # Time to restore full cooling
    
    def calculate_cooling_flexibility(self, pue: float) -> float:
        """
        Calculate cooling load flexibility as % of total facility load.
        
        Args:
            pue: Power Usage Effectiveness (typically 1.1-1.4)
        
        Returns:
            Flexibility as percentage of total facility load
        """
        # Cooling is (PUE - 1) / PUE of total load
        cooling_fraction = (pue - 1) / pue
        
        # Maximum reducible is max_cooling_reduction_pct of cooling load
        max_reducible = cooling_fraction * (self.max_cooling_reduction_pct / 100)
        
        return max_reducible
    
    def to_dict(self) -> dict:
        return {
            'thermal_time_constant_min': self.thermal_time_constant_min,
            'max_setpoint_increase_c': self.max_setpoint_increase_c,
            'power_reduction_per_degree_pct': self.power_reduction_per_degree_pct,
            'max_cooling_reduction_pct': self.max_cooling_reduction_pct,
            'response_time_min': self.response_time_min,
            'recovery_time_min': self.recovery_time_min,
        }


@dataclass
class DRProductConfig:
    """Configuration for a demand response product."""
    
    name: str
    response_time_min: float
    payment_per_mw_hr: float      # $/MW-hr capacity payment
    activation_per_mwh: float     # $/MWh when activated
    max_events_per_year: int
    min_duration_hrs: float
    compatible_workloads: List[str] = field(default_factory=list)
    
    def is_compatible(self, workload: str) -> bool:
        return workload in self.compatible_workloads


# Default DR Products (from research)
DR_PRODUCTS = {
    'spinning_reserve': DRProductConfig(
        name='Spinning Reserve',
        response_time_min=10,
        payment_per_mw_hr=15,
        activation_per_mwh=50,
        max_events_per_year=50,
        min_duration_hrs=1,
        compatible_workloads=['fine_tuning', 'batch_inference']
    ),
    'non_spinning_reserve': DRProductConfig(
        name='Non-Spinning Reserve',
        response_time_min=30,
        payment_per_mw_hr=8,
        activation_per_mwh=40,
        max_events_per_year=100,
        min_duration_hrs=1,
        compatible_workloads=['pre_training', 'fine_tuning', 'batch_inference']
    ),
    'economic_dr': DRProductConfig(
        name='Economic DR',
        response_time_min=60,
        payment_per_mw_hr=5,
        activation_per_mwh=100,
        max_events_per_year=200,
        min_duration_hrs=4,
        compatible_workloads=['pre_training', 'fine_tuning', 'batch_inference', 'cooling']
    ),
    'emergency_dr': DRProductConfig(
        name='Emergency DR',
        response_time_min=120,
        payment_per_mw_hr=3,
        activation_per_mwh=200,
        max_events_per_year=20,
        min_duration_hrs=2,
        compatible_workloads=['pre_training', 'fine_tuning', 'batch_inference', 'cooling']
    ),
}


@dataclass
class FacilityLoadProfile:
    """
    Complete facility load profile with workload mix and flexibility.
    Integrates IT loads, cooling, and demand response capabilities.
    """
    
    # Basic parameters
    peak_it_load_mw: float = 160.0           # Peak IT load (MW)
    pue: float = 1.25                         # Power Usage Effectiveness
    load_factor: float = 0.75                 # Average utilization
    
    # Workload composition
    workload_mix: WorkloadMix = field(default_factory=WorkloadMix)
    
    # Cooling flexibility
    cooling_flex: CoolingFlexibility = field(default_factory=CoolingFlexibility)
    
    # DR configuration
    annual_curtailment_budget_pct: float = 0.01  # 1% annual budget (research-based)
    enabled_dr_products: List[str] = field(default_factory=lambda: ['economic_dr'])
    
    # Time-of-day patterns
    daily_pattern_enabled: bool = True
    peak_hours: Tuple[int, int] = (9, 22)    # Peak usage hours
    off_peak_factor: float = 0.90            # Load factor during off-peak
    
    # Seasonal patterns
    seasonal_pattern_enabled: bool = True
    summer_peak_factor: float = 1.05         # Summer load multiplier
    winter_trough_factor: float = 0.95       # Winter load multiplier
    
    @property
    def peak_facility_load_mw(self) -> float:
        """Total facility load including cooling and overhead."""
        return self.peak_it_load_mw * self.pue
    
    def calculate_total_flexibility(self) -> dict:
        """
        Calculate total facility flexibility from all sources.
        
        Returns:
            Dict with flexibility breakdown and total
        """
        # IT load flexibility (weighted by workload mix)
        it_flex_pct = self.workload_mix.calculate_total_flexibility()
        it_load_fraction = 1 / self.pue
        it_flex_facility_pct = it_flex_pct * it_load_fraction
        
        # Cooling flexibility
        cooling_flex_facility_pct = self.cooling_flex.calculate_cooling_flexibility(self.pue)
        
        # Total facility flexibility
        total_flex_pct = it_flex_facility_pct + cooling_flex_facility_pct
        
        # Flexible MW
        flexible_mw = self.peak_facility_load_mw * total_flex_pct
        
        return {
            'it_flexibility_pct': it_flex_pct * 100,
            'it_contribution_to_facility_pct': it_flex_facility_pct * 100,
            'cooling_contribution_to_facility_pct': cooling_flex_facility_pct * 100,
            'total_facility_flexibility_pct': total_flex_pct * 100,
            'flexible_mw': flexible_mw,
            'firm_load_mw': self.peak_facility_load_mw - flexible_mw,
        }
    
    def generate_8760_profile(self, seed: int = 42) -> np.ndarray:
        """
        Generate hourly load profile for full year.
        
        Returns:
            Array of 8760 hourly load values (MW)
        """
        np.random.seed(seed)
        hours = 8760
        profile = np.zeros(hours)
        
        base_load = self.peak_facility_load_mw * self.load_factor
        
        for hour in range(hours):
            hour_of_day = hour % 24
            day_of_year = hour // 24
            
            # Daily pattern
            if self.daily_pattern_enabled:
                if self.peak_hours[0] <= hour_of_day <= self.peak_hours[1]:
                    daily_factor = 1.0
                else:
                    daily_factor = self.off_peak_factor
            else:
                daily_factor = 1.0
            
            # Seasonal pattern (sinusoidal, peaks in summer)
            if self.seasonal_pattern_enabled:
                # Day 172 = summer solstice, Day 355 = winter solstice
                seasonal_factor = 1.0 + 0.05 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
                seasonal_factor = np.clip(
                    seasonal_factor,
                    self.winter_trough_factor,
                    self.summer_peak_factor
                )
            else:
                seasonal_factor = 1.0
            
            # Random variation (±2%)
            random_factor = 1.0 + (np.random.random() - 0.5) * 0.04
            
            profile[hour] = base_load * daily_factor * seasonal_factor * random_factor
        
        # Clip to bounds
        profile = np.clip(profile, 
                         self.peak_facility_load_mw * 0.5,
                         self.peak_facility_load_mw)
        
        return profile
    
    def generate_flexibility_profiles(self, seed: int = 42) -> Dict[str, np.ndarray]:
        """
        Generate hourly flexibility profiles for all components.
        
        Returns:
            Dict with arrays for each flexibility component
        """
        load_profile = self.generate_8760_profile(seed)
        hours = len(load_profile)
        
        # IT load
        it_load = load_profile / self.pue
        
        # Cooling load
        cooling_load = load_profile - it_load
        
        # Flexibility by workload type
        wm = self.workload_mix
        
        pre_training_load = it_load * wm.pre_training
        pre_training_flex = pre_training_load * wm.pre_training_flex
        
        fine_tuning_load = it_load * wm.fine_tuning
        fine_tuning_flex = fine_tuning_load * wm.fine_tuning_flex
        
        batch_inference_load = it_load * wm.batch_inference
        batch_inference_flex = batch_inference_load * wm.batch_inference_flex
        
        realtime_inference_load = it_load * wm.realtime_inference
        realtime_inference_flex = realtime_inference_load * wm.realtime_inference_flex
        
        rl_training_load = it_load * wm.rl_training
        rl_training_flex = rl_training_load * wm.rl_training_flex
        
        cloud_hpc_load = it_load * wm.cloud_hpc
        cloud_hpc_flex = cloud_hpc_load * wm.cloud_hpc_flex
        
        # Total IT flexibility
        total_it_flex = (pre_training_flex + fine_tuning_flex + 
                        batch_inference_flex + realtime_inference_flex +
                        rl_training_flex + cloud_hpc_flex)
        
        # Cooling flexibility
        cooling_flex = cooling_load * (self.cooling_flex.max_cooling_reduction_pct / 100)
        
        # Total flexibility
        total_flex = total_it_flex + cooling_flex
        
        # Firm load
        firm_load = load_profile - total_flex
        
        return {
            'total_load_mw': load_profile,
            'it_load_mw': it_load,
            'cooling_load_mw': cooling_load,
            'pre_training_load_mw': pre_training_load,
            'fine_tuning_load_mw': fine_tuning_load,
            'batch_inference_load_mw': batch_inference_load,
            'realtime_inference_load_mw': realtime_inference_load,
            'rl_training_load_mw': rl_training_load,
            'cloud_hpc_load_mw': cloud_hpc_load,
            'pre_training_flex_mw': pre_training_flex,
            'fine_tuning_flex_mw': fine_tuning_flex,
            'batch_inference_flex_mw': batch_inference_flex,
            'realtime_inference_flex_mw': realtime_inference_flex,
            'rl_training_flex_mw': rl_training_flex,
            'cloud_hpc_flex_mw': cloud_hpc_flex,
            'total_it_flex_mw': total_it_flex,
            'cooling_flex_mw': cooling_flex,
            'total_flex_mw': total_flex,
            'firm_load_mw': firm_load,
        }
    
    def calculate_dr_potential(self) -> Dict[str, dict]:
        """
        Calculate DR potential for each enabled product.
        
        Returns:
            Dict with DR economics for each product
        """
        flex = self.calculate_total_flexibility()
        profiles = self.generate_flexibility_profiles()
        
        results = {}
        
        for product_id in self.enabled_dr_products:
            if product_id not in DR_PRODUCTS:
                continue
            
            product = DR_PRODUCTS[product_id]
            
            # Calculate compatible flexibility
            compatible_flex_mw = np.zeros(8760)
            wm = self.workload_mix
            
            for wl in product.compatible_workloads:
                key = f'{wl}_flex_mw'
                if key in profiles:
                    compatible_flex_mw += profiles[key]
                elif wl == 'cooling':
                    compatible_flex_mw += profiles['cooling_flex_mw']
            
            # Guaranteed capacity is minimum
            guaranteed_mw = np.min(compatible_flex_mw)
            avg_mw = np.mean(compatible_flex_mw)
            
            # Economics
            capacity_payment = guaranteed_mw * 8760 * product.payment_per_mw_hr
            
            # Assume 100 hours of activation per year
            activation_hours = min(100, product.max_events_per_year * 2)
            activation_payment = guaranteed_mw * activation_hours * product.activation_per_mwh
            
            total_revenue = capacity_payment + activation_payment
            
            results[product_id] = {
                'product_name': product.name,
                'response_time_min': product.response_time_min,
                'guaranteed_capacity_mw': guaranteed_mw,
                'average_capacity_mw': avg_mw,
                'capacity_payment_annual': capacity_payment,
                'activation_payment_annual': activation_payment,
                'total_annual_revenue': total_revenue,
                'revenue_per_mw_year': total_revenue / guaranteed_mw if guaranteed_mw > 0 else 0,
            }
        
        return results
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        flex = self.calculate_total_flexibility()
        return {
            'basic_params': {
                'peak_it_load_mw': self.peak_it_load_mw,
                'pue': self.pue,
                'peak_facility_load_mw': self.peak_facility_load_mw,
                'load_factor': self.load_factor,
            },
            'workload_mix': self.workload_mix.to_dict(),
            'cooling_flexibility': self.cooling_flex.to_dict(),
            'flexibility_summary': flex,
            'dr_config': {
                'annual_curtailment_budget_pct': self.annual_curtailment_budget_pct,
                'enabled_products': self.enabled_dr_products,
            },
            'patterns': {
                'daily_enabled': self.daily_pattern_enabled,
                'peak_hours': self.peak_hours,
                'seasonal_enabled': self.seasonal_pattern_enabled,
            },
        }
