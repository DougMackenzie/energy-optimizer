"""
Project and Site Data Models
Top-level containers for project data
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from .load_profile import LoadProfile
from .equipment import Equipment, EquipmentSelection


@dataclass
class Site:
    """Site/location data"""
    
    id: str = ""
    name: str = ""
    
    # Location
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ""
    city: str = ""
    state: str = ""
    county: str = ""
    
    # Site characteristics
    acreage: float = 0.0
    zoning: str = ""
    
    # Grid/ISO
    iso: str = ""  # "SPP", "ERCOT", "MISO", "PJM", etc.
    utility: str = ""
    
    # Infrastructure
    water_available: bool = False
    gas_pipeline: bool = False
    fiber: bool = False
    
    # Interconnection
    nearest_substation: str = ""
    substation_voltage_kv: float = 0.0
    distance_to_sub_miles: float = 0.0
    available_capacity_mw: float = 0.0
    queue_position: Optional[int] = None
    study_status: str = ""
    estimated_energization: str = ""
    upgrade_cost_million: float = 0.0
    
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": {
                "lat": self.latitude,
                "lon": self.longitude,
                "address": self.address,
                "city": self.city,
                "state": self.state,
                "county": self.county,
            },
            "acreage": self.acreage,
            "zoning": self.zoning,
            "iso": self.iso,
            "interconnection": {
                "substation": self.nearest_substation,
                "voltage_kv": self.substation_voltage_kv,
                "distance_miles": self.distance_to_sub_miles,
                "available_mw": self.available_capacity_mw,
                "queue_position": self.queue_position,
                "study_status": self.study_status,
                "est_energization": self.estimated_energization,
            },
        }


@dataclass
class Constraints:
    """Optimization constraints"""
    
    # Capacity
    min_capacity_mw: float = 200.0
    reserve_margin_pct: float = 10.0
    n_minus_1: bool = True
    
    # Reliability
    min_availability_pct: float = 99.9
    
    # Performance
    min_ramp_rate_mw_s: float = 1.0
    freq_tolerance_hz: float = 0.5
    voltage_tolerance_pct: float = 5.0
    
    # Timeline
    max_time_to_power_months: int = 24
    
    # Environmental
    max_nox_tpy: float = 99.0  # Minor source
    
    # Economic
    max_lcoe_per_mwh: float = 85.0
    max_capex_million: float = 400.0
    
    # Site
    site_limit_mw: float = 300.0
    
    def to_dict(self) -> dict:
        return {
            "min_capacity_mw": self.min_capacity_mw,
            "reserve_margin_pct": self.reserve_margin_pct,
            "n_minus_1": self.n_minus_1,
            "min_availability_pct": self.min_availability_pct,
            "min_ramp_rate_mw_s": self.min_ramp_rate_mw_s,
            "max_time_to_power_months": self.max_time_to_power_months,
            "max_nox_tpy": self.max_nox_tpy,
            "max_lcoe_per_mwh": self.max_lcoe_per_mwh,
            "max_capex_million": self.max_capex_million,
        }


@dataclass
class Scenario:
    """An optimization scenario (equipment configuration)"""
    
    id: str = ""
    name: str = ""
    
    # Equipment selections
    equipment: List[EquipmentSelection] = field(default_factory=list)
    
    # Calculated metrics
    total_capacity_mw: float = 0.0
    firm_capacity_mw: float = 0.0  # N-1
    time_to_power_months: int = 0
    lcoe_per_mwh: float = 0.0
    capex_million: float = 0.0
    availability_pct: float = 0.0
    nox_tpy: float = 0.0
    carbon_kg_mwh: float = 0.0
    
    # Feasibility
    is_feasible: bool = False
    is_pareto_optimal: bool = False
    violations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "metrics": {
                "total_capacity_mw": self.total_capacity_mw,
                "firm_capacity_mw": self.firm_capacity_mw,
                "time_to_power_months": self.time_to_power_months,
                "lcoe_per_mwh": self.lcoe_per_mwh,
                "capex_million": self.capex_million,
                "availability_pct": self.availability_pct,
                "nox_tpy": self.nox_tpy,
                "carbon_kg_mwh": self.carbon_kg_mwh,
            },
            "feasible": self.is_feasible,
            "pareto_optimal": self.is_pareto_optimal,
            "violations": self.violations,
        }


@dataclass
class Project:
    """Top-level project container"""
    
    id: str = ""
    name: str = "New Project"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Project components
    site: Optional[Site] = None
    load_profile: Optional[LoadProfile] = None
    constraints: Constraints = field(default_factory=Constraints)
    
    # Equipment library (available for selection)
    equipment_library: List[Equipment] = field(default_factory=list)
    
    # Selected equipment for optimization
    selected_equipment: List[EquipmentSelection] = field(default_factory=list)
    
    # Optimization results
    scenarios: List[Scenario] = field(default_factory=list)
    recommended_scenario: Optional[Scenario] = None
    
    # Status
    status: str = "draft"  # "draft", "configured", "optimized", "complete"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "site": self.site.to_dict() if self.site else None,
            "load_profile": self.load_profile.to_dict() if self.load_profile else None,
            "constraints": self.constraints.to_dict(),
            "n_scenarios": len(self.scenarios),
            "n_feasible": sum(1 for s in self.scenarios if s.is_feasible),
        }
    
    def get_feasible_scenarios(self) -> List[Scenario]:
        return [s for s in self.scenarios if s.is_feasible]
    
    def get_pareto_scenarios(self) -> List[Scenario]:
        return [s for s in self.scenarios if s.is_pareto_optimal]
