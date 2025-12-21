"""
Equipment Data Models
Defines equipment types for BTM power solutions
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum


class EquipmentType(Enum):
    RECIP = "recip"
    GAS_TURBINE = "gas_turbine"
    BESS = "bess"
    SOLAR_PV = "solar_pv"
    GRID = "grid"


@dataclass
class Equipment:
    """Base class for all equipment types"""
    id: str
    name: str
    type: EquipmentType
    capacity_mw: float
    availability_pct: float = 97.0
    lead_time_months: Tuple[int, int] = (12, 24)
    capex_per_kw: float = 0.0
    fixed_om_per_kw_yr: float = 0.0
    variable_om_per_mwh: float = 0.0
    footprint_sqft: float = 0.0
    notes: str = ""
    
    @property
    def lead_time_min(self) -> int:
        return self.lead_time_months[0]
    
    @property
    def lead_time_max(self) -> int:
        return self.lead_time_months[1]
    
    @property
    def capex_total(self) -> float:
        """Total CAPEX in $"""
        return self.capacity_mw * 1000 * self.capex_per_kw


@dataclass
class RecipEngine(Equipment):
    """Reciprocating engine (natural gas)"""
    type: EquipmentType = field(default=EquipmentType.RECIP, init=False)
    
    manufacturer: str = ""
    model: str = ""
    fuel: str = "natural_gas"
    
    efficiency_pct: float = 45.0
    heat_rate_btu_kwh: float = 7500
    min_load_pct: float = 40
    
    start_time_cold_min: float = 2.0
    start_time_hot_min: float = 0.5
    ramp_rate_mw_min: float = 3.0
    ramp_rate_pct_min: float = 15
    
    nox_g_hphr: float = 0.5
    nox_lb_mwh: float = 0.5
    co2_lb_mwh: float = 900
    
    mtbf_hrs: float = 2500
    mttr_hrs: float = 24
    
    @property
    def ramp_rate_mw_s(self) -> float:
        """Ramp rate in MW/second"""
        return self.ramp_rate_mw_min / 60
    
    def nox_annual_tons(self, mwh_annual: float) -> float:
        """Calculate annual NOx emissions in tons"""
        return (self.nox_lb_mwh * mwh_annual) / 2000


@dataclass
class GasTurbine(Equipment):
    """Aeroderivative or industrial gas turbine"""
    type: EquipmentType = field(default=EquipmentType.GAS_TURBINE, init=False)
    
    manufacturer: str = ""
    model: str = ""
    turbine_type: str = "aeroderivative"  # or "industrial"
    fuel: str = "natural_gas"
    
    capacity_range_mw: Tuple[float, float] = (0, 0)
    efficiency_pct: float = 40.0
    heat_rate_btu_kwh: float = 8500
    min_load_pct: float = 50
    
    start_time_cold_min: float = 10.0
    start_time_hot_min: float = 5.0
    ramp_rate_mw_min: float = 10.0
    ramp_rate_pct_min: float = 15
    
    nox_ppm_15o2: float = 25
    nox_lb_mwh: float = 0.5
    co2_lb_mwh: float = 1050
    
    mtbf_hrs: float = 2000
    mttr_hrs: float = 48


@dataclass
class BESS(Equipment):
    """Battery Energy Storage System"""
    type: EquipmentType = field(default=EquipmentType.BESS, init=False)
    
    chemistry: str = "LFP"
    duration_hrs: float = 4.0
    energy_mwh: float = 100.0
    power_mw: float = 25.0
    
    roundtrip_efficiency_pct: float = 88.0
    response_time_ms: float = 50
    dod_pct: float = 80
    
    cycle_life: int = 6000
    calendar_life_yrs: int = 15
    augmentation_yr: int = 10
    
    capex_per_kwh: float = 350
    
    mtbf_hrs: float = 8760
    mttr_hrs: float = 4
    
    @property
    def capacity_mw(self) -> float:
        return self.power_mw
    
    @property
    def usable_energy_mwh(self) -> float:
        """Usable energy considering depth of discharge"""
        return self.energy_mwh * (self.dod_pct / 100)
    
    @property
    def ramp_rate_mw_s(self) -> float:
        """Effectively instant for BESS"""
        return self.power_mw  # Can go from 0 to full in <1 second


@dataclass
class SolarPV(Equipment):
    """Utility-scale solar PV"""
    type: EquipmentType = field(default=EquipmentType.SOLAR_PV, init=False)
    
    tracking: str = "single_axis"  # or "fixed"
    capacity_factor_pct: float = 25.0
    dc_ac_ratio: float = 1.3
    degradation_pct_yr: float = 0.5
    
    land_acres_per_mw: float = 5.0
    itc_eligible: bool = True
    
    capex_per_kw_dc: float = 1000
    
    def annual_generation_mwh(self) -> float:
        """Expected annual generation"""
        return self.capacity_mw * 8760 * (self.capacity_factor_pct / 100)


@dataclass 
class GridConnection(Equipment):
    """Grid interconnection"""
    type: EquipmentType = field(default=EquipmentType.GRID, init=False)
    
    substation: str = ""
    voltage_kv: float = 345
    distance_miles: float = 0.0
    
    queue_position: Optional[int] = None
    study_status: str = ""  # "System Impact", "Facilities", "IA Negotiation"
    estimated_energization: str = ""
    upgrade_cost_million: float = 0.0
    
    wheeling_cost_per_mwh: float = 5.0
    demand_charge_per_kw_mo: float = 10.0
    energy_cost_per_mwh: float = 45.0
    
    co2_lb_mwh: float = 850  # Grid average
    
    availability_pct: float = 99.97
    mtbf_hrs: float = 35000
    mttr_hrs: float = 2


@dataclass
class EquipmentSelection:
    """A selected equipment with quantity"""
    equipment: Equipment
    quantity: int = 1
    
    @property
    def total_capacity_mw(self) -> float:
        return self.equipment.capacity_mw * self.quantity
    
    @property
    def total_capex(self) -> float:
        return self.equipment.capex_total * self.quantity
