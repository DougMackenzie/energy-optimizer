"""
Greenfield Heuristic Optimizer v2.1.1
=====================================
Problem 1: Greenfield Datacenter - Minimize LCOE for known load trajectory

GOVERNANCE: This file is governed by GREENFIELD_HEURISTIC_RULES.md
- Core calculations are LOCKED and require user approval to modify
- See governance document for change control procedures

Author: bvNexus Team
Version: 2.1.1 (Merged Gemini QA/QC + Claude patches)
Last Updated: December 2025

CHANGELOG v2.1.1:
- Added gspread integration for Google Sheets backend
- Added dynamic ramp calculation based on workload mix
- Added BESS reliability charging (excess thermal/grid)
- Added grid CAPEX to total capital cost
- Fixed fuel annual calculation (divide by active years)
- PATCH: Fixed OPEX bug (was using missing recip_mw key)
- PATCH: Added recip_mw/turbine_mw storage in config
- PATCH: Added solar profile generation
- PATCH: Restored constraint checking logic
- PATCH: Added economic dispatch (compare grid vs thermal cost)

BACKEND SYNC:
- Equipment specs loaded from Google Sheets "Equipment" tab
- Global parameters loaded from Google Sheets "Global_Parameters" tab
- Uses gspread for backend connectivity
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
import time
import logging

# gspread integration
try:
    import gspread
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: BACKEND DATA LOADERS
# =============================================================================

class BackendDataLoader:
    """
    Loads equipment specs and global parameters from Google Sheets backend.
    Uses gspread library for Google Sheets connectivity.
    
    ANTIGRAVITY INSTRUCTIONS:
    -------------------------
    If columns are missing from backend, this class will use defaults and log warnings.
    See BACKEND_SCHEMA_UPDATES.md for required columns to add to Equipment and 
    Global_Parameters tabs.
    """
    
    # Default values used when backend columns are missing
    EQUIPMENT_DEFAULTS = {
        'recip_engine': {
            'capacity_mw': 10.0,
            'capex_per_mw': 1_800_000,
            'opex_annual_per_mw': 45_000,
            'heat_rate_btu_kwh': 8500,
            'nox_rate_lb_mmbtu': 0.15,
            'gas_consumption_mcf_mwh': 7.2,
            'efficiency': 0.42,
            'lifetime_years': 25,
            'lead_time_months': 24,  # 24 months per user spec
            'ramp_rate_pct_per_min': 100.0,
            'time_to_full_load_min': 5.0,
            'land_acres_per_mw': 0.5,
        },
        'gas_turbine': {
            'capacity_mw': 50.0,
            'capex_per_mw': 1_200_000,
            'opex_annual_per_mw': 35_000,
            'heat_rate_btu_kwh': 10500,
            'nox_rate_lb_mmbtu': 0.10,
            'gas_consumption_mcf_mwh': 8.5,
            'efficiency': 0.35,
            'lifetime_years': 25,
            'lead_time_months': 30,  # 30 months per user spec
            'ramp_rate_pct_per_min': 50.0,
            'time_to_full_load_min': 10.0,
            'land_acres_per_mw': 0.5,
        },
        'bess': {
            'capacity_mw': 1.0,
            'capacity_mwh': 4.0,
            'capex_per_mw': 250_000,
            'capex_per_mwh': 350_000,
            'opex_annual_per_mw': 5_000,
            'efficiency': 0.90,
            'lifetime_years': 15,
            'lead_time_months': 6,
            'ramp_rate_pct_per_min': 100.0,
            'time_to_full_load_min': 0.1,
            'land_acres_per_mw': 0.25,
        },
        'solar_pv': {
            'capacity_mw': 1.0,
            'capex_per_mw': 1_000_000,
            'opex_annual_per_mw': 12_000,
            'efficiency': 0.20,
            'lifetime_years': 30,
            'lead_time_months': 12,
            'land_acres_per_mw': 5.0,
            'capacity_factor': 0.25,
        },
        'grid': {
            'capacity_mw': 1.0,
            'capex_per_mw': 500_000,  # Interconnection cost
            'opex_annual_per_mw': 0,
            'efficiency': 1.0,
            'lifetime_years': 50,
            'lead_time_months': 60,
            'ramp_rate_pct_per_min': 100.0,
            'land_acres_per_mw': 0.1,
        },
    }
    
    GLOBAL_PARAM_DEFAULTS = {
        # Economic parameters
        'discount_rate': 0.08,
        'analysis_period_years': 15,  # 15 years per backend
        'electricity_price': 80.0,  # $/MWh
        'gas_price': 5.0,  # $/MCF
        'capacity_price': 150.0,  # $/kW-year
        
        # Constraint parameters
        'default_availability': 0.95,
        'n_minus_1_default': True,
        'emissions_limit_factor': 1.0,
        
        # Land allocation parameters
        'datacenter_mw_per_acre': 3.0,
        'solar_land_threshold_acres': 800.0,
        'thermal_land_per_mw': 0.5,
        'solar_land_per_mw': 5.0,
        'bess_land_per_mw': 0.25,
        
        # Lead time parameters
        'recip_lead_time_months': 24,
        'gt_lead_time_months': 30,
        'bess_lead_time_months': 6,
        'solar_lead_time_months': 12,
        'default_grid_lead_time_months': 60,
        
        # Capacity credit parameters
        'bess_capacity_credit_pct': 0.25,
        
        # Reliability parameters
        'voll_penalty': 50_000,
    }
    
    def __init__(self, sheets_client=None, spreadsheet_id: str = None):
        """
        Initialize data loader.
        
        Args:
            sheets_client: gspread.Client object (or None for defaults)
            spreadsheet_id: ID of the backend spreadsheet
        """
        self.sheets_client = sheets_client
        self.spreadsheet_id = spreadsheet_id
        self._equipment_cache = None
        self._global_params_cache = None
    
    def load_equipment_specs(self, force_reload: bool = False) -> Dict[str, Dict]:
        """Load equipment specifications from backend Equipment tab."""
        if self._equipment_cache is not None and not force_reload:
            return self._equipment_cache
        
        if self.sheets_client is None:
            logger.warning("No sheets client - using default equipment specs")
            self._equipment_cache = self.EQUIPMENT_DEFAULTS.copy()
            return self._equipment_cache
        
        try:
            equipment_df = self._read_sheet_range("Equipment")
            
            equipment_specs = {}
            for _, row in equipment_df.iterrows():
                equip_id = row.get('equipment_id', '')
                if not equip_id or pd.isna(equip_id):
                    continue
                
                # Get base type for defaults
                base_type = equip_id.rsplit('_', 1)[0] if '_' in equip_id else equip_id
                defaults = self.EQUIPMENT_DEFAULTS.get(base_type, {})
                
                equipment_specs[equip_id] = {
                    'name': row.get('name', equip_id),
                    'type': row.get('type', base_type),
                    'capacity_mw': self._safe_float(row.get('capacity_mw'), defaults.get('capacity_mw', 1.0)),
                    'capacity_mwh': self._safe_float(row.get('capacity_mwh'), defaults.get('capacity_mwh', 0)),
                    'capex_per_mw': self._safe_float(row.get('capex_per_mw'), defaults.get('capex_per_mw', 0)),
                    'capex_per_mwh': self._safe_float(row.get('capex_per_mwh'), defaults.get('capex_per_mwh', 0)),
                    'opex_annual_per_mw': self._safe_float(row.get('opex_annual_per_mw'), defaults.get('opex_annual_per_mw', 0)),
                    'efficiency': self._safe_float(row.get('efficiency'), defaults.get('efficiency', 1.0)),
                    'heat_rate_btu_kwh': self._safe_float(row.get('heat_rate_btu_kwh'), defaults.get('heat_rate_btu_kwh', 0)),
                    'nox_rate_lb_mmbtu': self._safe_float(row.get('nox_rate_lb_mmbtu'), defaults.get('nox_rate_lb_mmbtu', 0)),
                    'gas_consumption_mcf_mwh': self._safe_float(row.get('gas_consumption_mcf_mwh'), defaults.get('gas_consumption_mcf_mwh', 0)),
                    'lifetime_years': self._safe_int(row.get('lifetime_years'), defaults.get('lifetime_years', 25)),
                    'lead_time_months': self._safe_int(row.get('lead_time_months'), defaults.get('lead_time_months', 12)),
                    'ramp_rate_pct_per_min': self._safe_float(row.get('ramp_rate_pct_per_min'), defaults.get('ramp_rate_pct_per_min', 100.0)),
                    'time_to_full_load_min': self._safe_float(row.get('time_to_full_load_min'), defaults.get('time_to_full_load_min', 5.0)),
                    'land_acres_per_mw': self._safe_float(row.get('land_acres_per_mw'), defaults.get('land_acres_per_mw', 0.5)),
                }
            
            self._equipment_cache = equipment_specs
            logger.info(f"Loaded {len(equipment_specs)} equipment specs from backend")
            return equipment_specs
            
        except Exception as e:
            logger.error(f"Error loading equipment from backend: {e}")
            logger.warning("Falling back to default equipment specs")
            self._equipment_cache = self.EQUIPMENT_DEFAULTS.copy()
            return self._equipment_cache
    
    def load_global_parameters(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load global parameters from backend Global_Parameters tab."""
        if self._global_params_cache is not None and not force_reload:
            return self._global_params_cache
        
        if self.sheets_client is None:
            logger.warning("No sheets client - using default global parameters")
            self._global_params_cache = self.GLOBAL_PARAM_DEFAULTS.copy()
            return self._global_params_cache
        
        try:
            params_df = self._read_sheet_range("Global_Parameters")
            
            global_params = self.GLOBAL_PARAM_DEFAULTS.copy()
            for _, row in params_df.iterrows():
                param_name = row.get('parameter_name', '')
                if not param_name or pd.isna(param_name):
                    continue
                
                value = row.get('value')
                unit = row.get('unit', '')
                
                # Type conversion
                if unit == 'boolean' or param_name.endswith('_default'):
                    global_params[param_name] = str(value).lower() in ('true', '1', 'yes')
                elif unit in ('decimal', 'years', '$/MWh', '$/MCF', '$/kW-year', 'months', 'acres', 'MW/acre', 'acres/MW'):
                    global_params[param_name] = self._safe_float(value, global_params.get(param_name, 0))
                else:
                    global_params[param_name] = value
            
            self._global_params_cache = global_params
            logger.info(f"Loaded {len(global_params)} global parameters from backend")
            return global_params
            
        except Exception as e:
            logger.error(f"Error loading global parameters from backend: {e}")
            logger.warning("Falling back to default global parameters")
            self._global_params_cache = self.GLOBAL_PARAM_DEFAULTS.copy()
            return self._global_params_cache
    
    def get_equipment_by_type(self, equipment_type: str) -> Dict:
        """Get generic equipment spec by type (recip_engine, gas_turbine, etc.)"""
        specs = self.load_equipment_specs()
        if equipment_type in specs:
            return specs[equipment_type]
        return self.EQUIPMENT_DEFAULTS.get(equipment_type, {})
    
    def _read_sheet_range(self, tab_name: str) -> pd.DataFrame:
        """Read a tab from Google Sheets using gspread and return as DataFrame."""
        if not HAS_GSPREAD:
            raise ImportError("gspread library not installed. Install with: pip install gspread")
        
        if not self.sheets_client or not self.spreadsheet_id:
            raise ValueError("Sheets client and Spreadsheet ID required")

        try:
            sheet = self.sheets_client.open_by_key(self.spreadsheet_id)
            worksheet = sheet.worksheet(tab_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to read sheet tab {tab_name}: {e}")
            raise

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        """Safely convert value to float."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        try:
            if isinstance(value, str):
                value = value.replace('$', '').replace(',', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        """Safely convert value to int."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default


# =============================================================================
# SECTION 2: DATA CLASSES
# =============================================================================

@dataclass
class ConstraintResult:
    """Standardized constraint check result."""
    name: str
    value: float
    limit: float
    unit: str
    constraint_type: str  # 'hard' or 'soft'
    tolerance: float
    
    @property
    def utilization(self) -> float:
        if self.limit <= 0:
            return 0.0
        return self.value / self.limit
    
    @property
    def binding(self) -> bool:
        return self.utilization >= 0.95
    
    @property
    def violated(self) -> bool:
        effective_limit = self.limit * (1 + self.tolerance)
        return self.value > effective_limit
    
    @property
    def status(self) -> str:
        if self.violated:
            return "VIOLATED"
        elif self.binding:
            return "BINDING"
        elif self.utilization > 0.80:
            return "NEAR_BINDING"
        else:
            return "SLACK"
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name, 'value': self.value, 'limit': self.limit,
            'unit': self.unit, 'utilization': self.utilization,
            'binding': self.binding, 'violated': self.violated,
            'status': self.status, 'constraint_type': self.constraint_type,
        }


@dataclass
class DispatchResult:
    """Results from 8760 hourly dispatch simulation."""
    year: int
    dispatch_df: pd.DataFrame
    energy_delivered_mwh: float
    energy_required_mwh: float
    unserved_energy_mwh: float
    generation_by_source: Dict[str, float]
    capacity_factors: Dict[str, float]
    peak_unserved_mw: float
    hours_with_unserved: int
    max_ramp_mw_per_min: float


@dataclass 
class HeuristicResultV2:
    """Container for Greenfield heuristic optimization results."""
    feasible: bool
    objective_value: float
    lcoe: float
    capex_total: float
    opex_annual: float
    fuel_annual: float
    npv_total_cost: float
    equipment_config: Dict[str, Any]
    equipment_by_year: Dict[int, Dict[str, Any]]
    dispatch_summary: Dict[str, Any]
    dispatch_by_year: Dict[int, DispatchResult]
    constraint_results: List[ConstraintResult]
    violations: List[str]
    warnings: List[str]
    timeline_months: int
    shadow_prices: Dict[str, float]
    solve_time_seconds: float
    total_energy_delivered_mwh: float
    total_unserved_energy_mwh: float
    unserved_energy_pct: float
    load_coverage_pct: float
    binding_constraints: List[str]
    primary_binding_constraint: str
    land_allocation: Dict[str, float]
    ramp_analysis: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            'feasible': self.feasible,
            'objective_value': self.objective_value,
            'lcoe': self.lcoe,
            'capex_total': self.capex_total,
            'opex_annual': self.opex_annual,
            'fuel_annual': self.fuel_annual,
            'npv_total_cost': self.npv_total_cost,
            'equipment_config': self.equipment_config,
            'equipment_by_year': {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, dict)} 
                                  for k, v in self.equipment_by_year.items()},
            'dispatch_summary': self.dispatch_summary,
            'constraint_status': {c.name: c.to_dict() for c in self.constraint_results},
            'violations': self.violations,
            'warnings': self.warnings,
            'timeline_months': self.timeline_months,
            'shadow_prices': self.shadow_prices,
            'solve_time_seconds': self.solve_time_seconds,
            'total_energy_delivered_mwh': self.total_energy_delivered_mwh,
            'total_unserved_energy_mwh': self.total_unserved_energy_mwh,
            'unserved_energy_pct': self.unserved_energy_pct,
            'load_coverage_pct': self.load_coverage_pct,
            'binding_constraints': self.binding_constraints,
            'primary_binding_constraint': self.primary_binding_constraint,
            'land_allocation': self.land_allocation,
            'ramp_analysis': self.ramp_analysis,
        }


# =============================================================================
# SECTION 3: LOCKED CALCULATION FUNCTIONS
# These formulas require user approval to modify per governance document
# =============================================================================

def calculate_nox_annual_tpy(
    generation_mwh: float,
    heat_rate_btu_kwh: float,
    nox_rate_lb_mmbtu: float,
) -> float:
    """
    LOCKED CALCULATION: Annual NOx emissions in tons per year
    
    Formula: NOx_tpy = generation_MWh × HR × nox_rate / 1,000,000 / 2000
    """
    mmbtu = generation_mwh * heat_rate_btu_kwh / 1000
    nox_lb = mmbtu * nox_rate_lb_mmbtu
    nox_tpy = nox_lb / 2000
    return nox_tpy


def calculate_gas_consumption_mcf_day(
    generation_mwh_annual: float,
    gas_consumption_mcf_mwh: float,
) -> float:
    """
    LOCKED CALCULATION: Daily gas consumption in MCF/day
    """
    annual_mcf = generation_mwh_annual * gas_consumption_mcf_mwh
    daily_mcf = annual_mcf / 365
    return daily_mcf


def calculate_capital_recovery_factor(
    discount_rate: float,
    project_life_years: int
) -> float:
    """
    LOCKED CALCULATION: Capital Recovery Factor for annualizing CAPEX
    
    Formula: CRF = r(1+r)^n / ((1+r)^n - 1)
    """
    r = discount_rate
    n = project_life_years
    if n <= 0:
        return 1.0
    crf = (r * (1 + r)**n) / ((1 + r)**n - 1)
    return crf


def calculate_lcoe(
    capex_total: float,
    opex_annual: float,
    fuel_annual: float,
    energy_delivered_mwh_annual: float,
    discount_rate: float,
    project_life_years: int,
    bess_degradation_cost: float = 0.0,
) -> float:
    """
    LOCKED CALCULATION: Levelized Cost of Energy
    
    Formula: LCOE = (CAPEX × CRF + OPEX + Fuel + BESS_deg) / Energy_delivered
    
    Note: This is CLEAN LCOE without VOLL penalty.
    """
    if energy_delivered_mwh_annual <= 0:
        return float('inf')
    
    crf = calculate_capital_recovery_factor(discount_rate, project_life_years)
    annualized_capex = capex_total * crf
    total_annual_cost = annualized_capex + opex_annual + fuel_annual + bess_degradation_cost
    
    return total_annual_cost / energy_delivered_mwh_annual


def calculate_firm_capacity(
    equipment_config: Dict,
    equipment_specs: Dict,
    bess_capacity_credit_pct: float,
) -> float:
    """
    LOCKED CALCULATION: Firm capacity (BTM only, not grid)
    
    Firm capacity = Thermal + (BESS × credit_pct)
    Solar is NOT firm (intermittent)
    """
    recip_spec = equipment_specs.get('recip_engine', {})
    turbine_spec = equipment_specs.get('gas_turbine', {})
    
    recip_mw = equipment_config.get('n_recips', 0) * recip_spec.get('capacity_mw', 10)
    turbine_mw = equipment_config.get('n_turbines', 0) * turbine_spec.get('capacity_mw', 50)
    bess_mw = equipment_config.get('bess_mw', 0)
    
    bess_firm_mw = bess_mw * bess_capacity_credit_pct
    
    return recip_mw + turbine_mw + bess_firm_mw


def calculate_ramp_capacity(
    equipment_config: Dict,
    equipment_specs: Dict,
) -> float:
    """
    LOCKED CALCULATION: Total ramp rate capacity in MW/min
    
    Formula: Sum of (capacity_mw × ramp_rate_pct_per_min / 100) for each equipment
    """
    recip_spec = equipment_specs.get('recip_engine', {})
    turbine_spec = equipment_specs.get('gas_turbine', {})
    bess_spec = equipment_specs.get('bess', {})
    
    recip_mw = equipment_config.get('n_recips', 0) * recip_spec.get('capacity_mw', 10)
    turbine_mw = equipment_config.get('n_turbines', 0) * turbine_spec.get('capacity_mw', 50)
    bess_mw = equipment_config.get('bess_mw', 0)
    
    recip_ramp = recip_mw * recip_spec.get('ramp_rate_pct_per_min', 100) / 100
    turbine_ramp = turbine_mw * turbine_spec.get('ramp_rate_pct_per_min', 50) / 100
    bess_ramp = bess_mw * bess_spec.get('ramp_rate_pct_per_min', 100) / 100
    
    return recip_ramp + turbine_ramp + bess_ramp


def calculate_thermal_marginal_cost(
    gas_price: float,
    heat_rate_btu_kwh: float,
    var_om_per_mwh: float = 5.0,
) -> float:
    """
    Calculate marginal cost of thermal generation in $/MWh.
    
    Formula: Gas_cost/MWh + Var_O&M
    """
    # heat_rate_btu_kwh * 1000 / 1,037,000 BTU per MCF = MCF/MWh
    gas_mcf_per_mwh = heat_rate_btu_kwh * 1000 / 1_037_000
    fuel_cost = gas_mcf_per_mwh * gas_price
    return fuel_cost + var_om_per_mwh


# =============================================================================
# SECTION 4: LAND ALLOCATION
# =============================================================================

class LandAllocator:
    """
    Manages land allocation with proper priority:
    1. Datacenter footprint (RESERVED FIRST)
    2. Substation/switchyard
    3. Infrastructure (roads, setbacks)
    4. Thermal equipment (high priority - high MW density)
    5. BESS (compact)
    6. Solar (ONLY if remaining > threshold)
    """
    
    def __init__(self, global_params: Dict, equipment_specs: Dict):
        self.params = global_params
        self.specs = equipment_specs
        
        self.dc_mw_per_acre = global_params.get('datacenter_mw_per_acre', 3.0)
        self.solar_threshold = global_params.get('solar_land_threshold_acres', 800.0)
        self.thermal_land_per_mw = global_params.get('thermal_land_per_mw', 0.5)
        self.solar_land_per_mw = global_params.get('solar_land_per_mw', 5.0)
        self.bess_land_per_mw = global_params.get('bess_land_per_mw', 0.25)
    
    def allocate(
        self,
        total_land_acres: float,
        peak_load_mw: float,
        thermal_mw: float = 0,
        bess_mw: float = 0,
    ) -> Dict[str, float]:
        """Allocate land with proper priority."""
        allocation = {}
        
        # Step 1: Datacenter footprint (FIRST PRIORITY)
        allocation['datacenter_acres'] = peak_load_mw / self.dc_mw_per_acre
        
        # Step 2: Substation/switchyard (fixed estimate)
        allocation['substation_acres'] = 10.0
        
        # Step 3: Infrastructure (roads, setbacks, buffers) - 10% of total
        allocation['infrastructure_acres'] = total_land_acres * 0.10
        
        # Calculate remaining after reserved allocations
        reserved = (allocation['datacenter_acres'] + 
                   allocation['substation_acres'] + 
                   allocation['infrastructure_acres'])
        remaining = total_land_acres - reserved
        
        # Step 4: Thermal equipment (HIGH PRIORITY)
        allocation['thermal_acres'] = thermal_mw * self.thermal_land_per_mw
        remaining -= allocation['thermal_acres']
        
        # Step 5: BESS (compact, low land use)
        allocation['bess_acres'] = bess_mw * self.bess_land_per_mw
        remaining -= allocation['bess_acres']
        
        # Step 6: Solar ONLY if remaining > threshold
        if remaining >= self.solar_threshold:
            allocation['solar_available_acres'] = remaining
        else:
            allocation['solar_available_acres'] = 0.0
            if remaining > 0:
                logger.info(f"Solar not enabled: {remaining:.1f} acres < {self.solar_threshold} acre threshold")
        
        allocation['total_used_acres'] = (
            allocation['datacenter_acres'] +
            allocation['substation_acres'] +
            allocation['infrastructure_acres'] +
            allocation['thermal_acres'] +
            allocation['bess_acres']
        )
        allocation['remaining_acres'] = max(0, total_land_acres - allocation['total_used_acres'])
        
        return allocation
    
    def get_max_solar_mw(self, available_solar_acres: float) -> float:
        """Calculate max solar MW from available acres."""
        if available_solar_acres <= 0:
            return 0.0
        return available_solar_acres / self.solar_land_per_mw
    
    def get_max_thermal_mw(self, available_acres: float) -> float:
        """Calculate max thermal MW from available acres."""
        if available_acres <= 0:
            return 0.0
        return available_acres / self.thermal_land_per_mw


# =============================================================================
# SECTION 5: EQUIPMENT SIZING (WITH DYNAMIC RAMP)
# =============================================================================

class EquipmentSizer:
    """
    Equipment sizing with proper sequencing:
    1. Check lead time feasibility
    2. Size FIRM power first (thermal) to meet firm load
    3. Check ramp rate requirements (DYNAMIC based on workload mix)
    4. Add BESS for ramp support (partial firm credit)
    5. Add solar ONLY if land threshold met
    6. Add grid when available
    """
    
    # Engineering ramp factors based on workload characteristics
    RAMP_FACTORS = {
        'pre_training': 0.00,        # Stable, days-long jobs
        'fine_tuning': 0.05,         # Moderate cycling
        'batch_inference': 0.00,     # Deferrable/queued
        'real_time_inference': 0.50, # High volatility (SLA protected)
        'rl_training': 0.10,         # Moderate
        'cloud_hpc': 0.02,           # Batch-like
        'cooling': 0.02,             # Thermal inertia
    }
    
    def __init__(
        self,
        equipment_specs: Dict,
        global_params: Dict,
        constraints: Dict,
    ):
        self.specs = equipment_specs
        self.params = global_params
        self.constraints = constraints
        
        self.nox_limit_tpy = constraints.get('nox_tpy_annual', 100)
        self.gas_limit_mcf_day = constraints.get('gas_supply_mcf_day', 50000)
        self.land_limit_acres = constraints.get('land_area_acres', 500)
        self.n1_required = constraints.get('n_minus_1_required', 
                                          global_params.get('n_minus_1_default', True))
        
        self.bess_capacity_credit = global_params.get('bess_capacity_credit_pct', 0.25)
        self.solar_threshold = global_params.get('solar_land_threshold_acres', 800)
        
        self.lead_times = {
            'recip': global_params.get('recip_lead_time_months', 24),
            'turbine': global_params.get('gt_lead_time_months', 30),
            'bess': global_params.get('bess_lead_time_months', 6),
            'solar': global_params.get('solar_lead_time_months', 12),
            'grid': constraints.get('grid_lead_time_months', 
                                   global_params.get('default_grid_lead_time_months', 60)),
        }
        
        self.grid_available_year = constraints.get('grid_available_year')
        self.grid_capacity_mw = constraints.get('grid_capacity_mw', 0)
        
        self.land_allocator = LandAllocator(global_params, equipment_specs)
    
    def get_equipment_availability(
        self,
        year: int,
        project_start_year: int,
    ) -> Dict[str, bool]:
        """Determine what equipment can be deployed by a given year."""
        months_available = (year - project_start_year) * 12
        
        availability = {}
        for equip, lead_time in self.lead_times.items():
            availability[equip] = months_available >= lead_time
        
        availability['grid'] = (
            self.grid_available_year is not None and
            year >= self.grid_available_year and
            self.grid_capacity_mw > 0
        )
        
        return availability
    
    def calculate_nox_limited_thermal(self, capacity_factor: float = 0.85) -> float:
        """Calculate max thermal MW limited by NOx constraint."""
        recip_spec = self.specs.get('recip_engine', {})
        hr = recip_spec.get('heat_rate_btu_kwh', 8500)
        nox_rate = recip_spec.get('nox_rate_lb_mmbtu', 0.15)
        
        if nox_rate <= 0 or hr <= 0:
            return float('inf')
        
        max_mw = (self.nox_limit_tpy * 2000 * 1000) / (8760 * capacity_factor * hr * nox_rate)
        return max_mw
    
    def calculate_gas_limited_thermal(self, capacity_factor: float = 0.85) -> float:
        """Calculate max thermal MW limited by gas supply."""
        recip_spec = self.specs.get('recip_engine', {})
        gas_rate = recip_spec.get('gas_consumption_mcf_mwh', 7.2)
        
        if gas_rate <= 0:
            return float('inf')
        
        max_mw = (self.gas_limit_mcf_day * 365) / (gas_rate * 8760 * capacity_factor)
        return max_mw
    
    def calculate_ramp_requirement(
        self,
        peak_load_mw: float,
        workload_mix: Dict[str, float] = None,
    ) -> float:
        """
        DYNAMIC RAMP CALCULATION based on workload mix.
        
        Returns MW/min required based on workload physics.
        """
        if not workload_mix:
            # Default mix (45/20/15/20 from DR Economics screenshot)
            workload_mix = {
                'pre_training': 45.0,
                'fine_tuning': 20.0,
                'batch_inference': 15.0,
                'real_time_inference': 20.0,
            }
        
        total_ramp_mw_min = 0.0
        
        for w_type, pct in workload_mix.items():
            # Normalize key names
            key = w_type.lower().replace('-', '_').replace(' ', '_')
            
            # Map to ramp factors
            factor = 0.1  # Default safety margin
            if 'pre_train' in key:
                factor = self.RAMP_FACTORS['pre_training']
            elif 'fine_tun' in key:
                factor = self.RAMP_FACTORS['fine_tuning']
            elif 'batch' in key:
                factor = self.RAMP_FACTORS['batch_inference']
            elif 'real' in key or 'live' in key:
                factor = self.RAMP_FACTORS['real_time_inference']
            elif 'rl' in key or 'reinforce' in key:
                factor = self.RAMP_FACTORS['rl_training']
            elif 'cloud' in key or 'hpc' in key:
                factor = self.RAMP_FACTORS['cloud_hpc']
            elif 'cool' in key:
                factor = self.RAMP_FACTORS['cooling']
            
            load_mw = peak_load_mw * (pct / 100.0)
            total_ramp_mw_min += load_mw * factor
        
        return total_ramp_mw_min
    
    def size_for_year(
        self,
        target_load_mw: float,
        firm_load_mw: float,
        year: int,
        project_start_year: int,
        existing_equipment: Dict = None,
        workload_mix: Dict = None,
    ) -> Dict:
        """Size equipment for a specific year with proper priority."""
        existing = existing_equipment or {}
        availability = self.get_equipment_availability(year, project_start_year)
        
        recip_spec = self.specs.get('recip_engine', {})
        turbine_spec = self.specs.get('gas_turbine', {})
        
        recip_unit_mw = recip_spec.get('capacity_mw', 10)
        turbine_unit_mw = turbine_spec.get('capacity_mw', 50)
        
        # Start with existing equipment
        config = {
            'n_recips': existing.get('n_recips', 0),
            'n_turbines': existing.get('n_turbines', 0),
            'solar_mw': existing.get('solar_mw', 0),
            'bess_mw': existing.get('bess_mw', 0),
            'bess_mwh': existing.get('bess_mwh', 0),
            'grid_mw': 0,
            'year': year,
        }
        
        # Calculate existing firm capacity
        existing_firm_mw = calculate_firm_capacity(config, self.specs, self.bess_capacity_credit)
        
        # Calculate constraint-limited thermal capacity
        max_thermal_nox = self.calculate_nox_limited_thermal()
        max_thermal_gas = self.calculate_gas_limited_thermal()
        max_thermal_constraint = min(max_thermal_nox, max_thermal_gas)
        
        # Calculate existing thermal
        existing_thermal_mw = (
            config['n_recips'] * recip_unit_mw +
            config['n_turbines'] * turbine_unit_mw
        )
        
        remaining_thermal_budget = max_thermal_constraint - existing_thermal_mw
        
        # STEP 1: Size FIRM thermal power to meet firm load
        firm_deficit = firm_load_mw - existing_firm_mw
        
        if firm_deficit > 0 and remaining_thermal_budget > 0:
            thermal_to_add = min(firm_deficit, remaining_thermal_budget)
            
            if availability.get('recip', False):
                n_new_recips = int(np.ceil(thermal_to_add / recip_unit_mw))
                if self.n1_required and not availability.get('grid', False):
                    n_new_recips += 1
                config['n_recips'] += n_new_recips
            
            elif availability.get('turbine', False):
                n_new_turbines = int(np.ceil(thermal_to_add / turbine_unit_mw))
                if self.n1_required and not availability.get('grid', False):
                    n_new_turbines += 1
                config['n_turbines'] += n_new_turbines
        
        # STEP 2: Check RAMP RATE requirements (DYNAMIC)
        required_ramp_mw_min = self.calculate_ramp_requirement(target_load_mw, workload_mix)
        current_ramp_capacity = calculate_ramp_capacity(config, self.specs)
        ramp_deficit = required_ramp_mw_min - current_ramp_capacity
        
        if ramp_deficit > 0:
            if availability.get('bess', False):
                bess_ramp_rate = self.specs.get('bess', {}).get('ramp_rate_pct_per_min', 100) / 100
                bess_needed_mw = ramp_deficit / bess_ramp_rate if bess_ramp_rate > 0 else 0
                
                if bess_needed_mw > config['bess_mw']:
                    config['bess_mw'] = bess_needed_mw
                    config['bess_mwh'] = bess_needed_mw * 4
            
            current_ramp_capacity = calculate_ramp_capacity(config, self.specs)
            ramp_deficit = required_ramp_mw_min - current_ramp_capacity
            
            if ramp_deficit > 0 and availability.get('recip', False):
                recip_ramp_rate = recip_spec.get('ramp_rate_pct_per_min', 100) / 100
                recips_needed_mw = ramp_deficit / recip_ramp_rate if recip_ramp_rate > 0 else 0
                n_recips_for_ramp = int(np.ceil(recips_needed_mw / recip_unit_mw))
                config['n_recips'] += n_recips_for_ramp
        
        # STEP 3: STORE MW VALUES (PATCH: Fix OPEX calculation)
        config['recip_mw'] = config['n_recips'] * recip_unit_mw
        config['turbine_mw'] = config['n_turbines'] * turbine_unit_mw
        thermal_mw = config['recip_mw'] + config['turbine_mw']
        
        # STEP 4: Land allocation and solar check
        land_allocation = self.land_allocator.allocate(
            total_land_acres=self.land_limit_acres,
            peak_load_mw=target_load_mw,
            thermal_mw=thermal_mw,
            bess_mw=config['bess_mw'],
        )
        
        if availability.get('solar', False) and land_allocation['solar_available_acres'] > 0:
            max_solar_mw = self.land_allocator.get_max_solar_mw(
                land_allocation['solar_available_acres']
            )
            current_firm = calculate_firm_capacity(config, self.specs, self.bess_capacity_credit)
            remaining_gap = target_load_mw - current_firm - config.get('grid_mw', 0)
            config['solar_mw'] = min(max_solar_mw, max(0, remaining_gap))
        
        # STEP 5: Add grid when available
        if availability.get('grid', False):
            current_btm = calculate_firm_capacity(config, self.specs, self.bess_capacity_credit)
            remaining_gap = target_load_mw - current_btm
            config['grid_mw'] = min(self.grid_capacity_mw, max(0, remaining_gap))
        
        # FINAL: Calculate totals
        config['total_btm_mw'] = (
            config['recip_mw'] + 
            config['turbine_mw'] + 
            config['solar_mw'] +
            config['bess_mw'] * self.bess_capacity_credit
        )
        config['total_firm_mw'] = calculate_firm_capacity(config, self.specs, self.bess_capacity_credit)
        config['total_capacity_mw'] = config['total_btm_mw'] + config['grid_mw']
        config['land_allocation'] = land_allocation
        config['ramp_required_mw_min'] = required_ramp_mw_min
        config['ramp_available_mw_min'] = calculate_ramp_capacity(config, self.specs)
        
        if config['total_capacity_mw'] < target_load_mw:
            config['power_gap_mw'] = target_load_mw - config['total_capacity_mw']
            config['constraint_limited'] = True
        else:
            config['power_gap_mw'] = 0
            config['constraint_limited'] = False
        
        return config


# =============================================================================
# SECTION 6: 8760 DISPATCH SIMULATION (WITH ECONOMIC DISPATCH & BESS CHARGING)
# =============================================================================

class DispatchSimulator:
    """
    Full 8760 hourly dispatch with:
    - Economic merit order (compare grid vs thermal cost)
    - BESS reliability charging (from excess thermal/grid, not just solar)
    - Ramp tracking
    """
    
    def __init__(
        self,
        equipment_specs: Dict,
        global_params: Dict,
    ):
        self.specs = equipment_specs
        self.params = global_params
        
        self.gas_price = global_params.get('gas_price', 5.0)
        self.grid_price = global_params.get('electricity_price', 80.0)
        
        recip_spec = equipment_specs.get('recip_engine', {})
        turbine_spec = equipment_specs.get('gas_turbine', {})
        
        self.recip_marginal_cost = calculate_thermal_marginal_cost(
            self.gas_price,
            recip_spec.get('heat_rate_btu_kwh', 8500),
        )
        self.turbine_marginal_cost = calculate_thermal_marginal_cost(
            self.gas_price,
            turbine_spec.get('heat_rate_btu_kwh', 10500),
        )
    
    def run_dispatch(
        self,
        equipment_config: Dict,
        load_profile: np.ndarray,
        firm_load_profile: np.ndarray,
        solar_profile: np.ndarray,
        grid_available: bool = False,
        grid_capacity_mw: float = 0,
    ) -> DispatchResult:
        """Run economic merit-order dispatch for 8760 hours."""
        n_hours = len(load_profile)
        
        recip_cap = equipment_config.get('recip_mw', 0)
        turbine_cap = equipment_config.get('turbine_mw', 0)
        solar_cap = equipment_config.get('solar_mw', 0)
        bess_mw = equipment_config.get('bess_mw', 0)
        bess_mwh = equipment_config.get('bess_mwh', 0)
        grid_cap = grid_capacity_mw if grid_available else 0
        
        recip_gen = np.zeros(n_hours)
        turbine_gen = np.zeros(n_hours)
        solar_gen = np.zeros(n_hours)
        bess_discharge = np.zeros(n_hours)
        bess_charge = np.zeros(n_hours)
        grid_import = np.zeros(n_hours)
        unserved = np.zeros(n_hours)
        bess_soc = np.zeros(n_hours)
        
        bess_eff = self.specs.get('bess', {}).get('efficiency', 0.90)
        bess_soc_current = bess_mwh * 0.5
        
        ramp_events = []
        grid_cheaper_than_recip = self.grid_price < self.recip_marginal_cost
        
        for h in range(n_hours):
            load = load_profile[h]
            remaining = load
            
            if h > 0:
                ramp_mw = abs(load_profile[h] - load_profile[h-1])
                ramp_events.append(ramp_mw)
            
            # Step 1: Solar (must-take)
            solar_avail = solar_profile[h] if solar_cap > 0 else 0
            solar_gen[h] = min(solar_avail, remaining)
            remaining -= solar_gen[h]
            excess_solar = solar_avail - solar_gen[h]
            
            # Step 2: BESS discharge
            if remaining > 0 and bess_soc_current > 0:
                discharge_avail = min(bess_mw, bess_soc_current * np.sqrt(bess_eff))
                bess_discharge[h] = min(discharge_avail, remaining)
                bess_soc_current -= bess_discharge[h] / np.sqrt(bess_eff)
                remaining -= bess_discharge[h]
            
            # Step 3: Economic Dispatch (Grid vs Thermal)
            if remaining > 0:
                if grid_cheaper_than_recip and grid_cap > 0:
                    grid_import[h] = min(grid_cap, remaining)
                    remaining -= grid_import[h]
                    
                    if remaining > 0 and recip_cap > 0:
                        recip_gen[h] = min(recip_cap, remaining)
                        remaining -= recip_gen[h]
                    
                    if remaining > 0 and turbine_cap > 0:
                        turbine_gen[h] = min(turbine_cap, remaining)
                        remaining -= turbine_gen[h]
                else:
                    if recip_cap > 0:
                        recip_gen[h] = min(recip_cap, remaining)
                        remaining -= recip_gen[h]
                    
                    if remaining > 0 and turbine_cap > 0:
                        turbine_gen[h] = min(turbine_cap, remaining)
                        remaining -= turbine_gen[h]
                    
                    if remaining > 0 and grid_cap > 0:
                        grid_import[h] = min(grid_cap, remaining)
                        remaining -= grid_import[h]
            
            # Step 4: Unserved
            if remaining > 0:
                unserved[h] = remaining
            
            # Step 5: BESS Charging (Reliability Mode)
            if bess_soc_current < bess_mwh:
                charge_room = min(bess_mw, (bess_mwh - bess_soc_current) / np.sqrt(bess_eff))
                
                unused_recip = max(0, recip_cap - recip_gen[h])
                unused_turbine = max(0, turbine_cap - turbine_gen[h])
                unused_grid = max(0, grid_cap - grid_import[h])
                
                total_avail_for_charge = excess_solar + unused_recip + unused_turbine + unused_grid
                
                charge_amount = min(charge_room, total_avail_for_charge)
                bess_charge[h] = charge_amount
                bess_soc_current += charge_amount * np.sqrt(bess_eff)
                
                needed_from_firm = max(0, charge_amount - excess_solar)
                if needed_from_firm > 0:
                    take_grid = min(needed_from_firm, unused_grid)
                    grid_import[h] += take_grid
                    needed_from_firm -= take_grid
                    
                    take_recip = min(needed_from_firm, unused_recip)
                    recip_gen[h] += take_recip
                    needed_from_firm -= take_recip
                    
                    take_turbine = min(needed_from_firm, unused_turbine)
                    turbine_gen[h] += take_turbine
            
            bess_soc[h] = bess_soc_current
        
        dispatch_df = pd.DataFrame({
            'hour': range(n_hours),
            'load_mw': load_profile,
            'firm_load_mw': firm_load_profile,
            'solar_mw': solar_gen,
            'bess_discharge_mw': bess_discharge,
            'bess_charge_mw': bess_charge,
            'bess_soc_mwh': bess_soc,
            'recip_mw': recip_gen,
            'turbine_mw': turbine_gen,
            'grid_mw': grid_import,
            'unserved_mw': unserved,
        })
        
        energy_delivered = (solar_gen + bess_discharge + recip_gen + turbine_gen + grid_import).sum()
        energy_required = load_profile.sum()
        
        generation_by_source = {
            'solar_mwh': solar_gen.sum(),
            'bess_mwh': bess_discharge.sum(),
            'recip_mwh': recip_gen.sum(),
            'turbine_mwh': turbine_gen.sum(),
            'grid_mwh': grid_import.sum(),
        }
        
        capacity_factors = {
            'solar': solar_gen.sum() / (solar_cap * n_hours) if solar_cap > 0 else 0,
            'recip': recip_gen.sum() / (recip_cap * n_hours) if recip_cap > 0 else 0,
            'turbine': turbine_gen.sum() / (turbine_cap * n_hours) if turbine_cap > 0 else 0,
            'grid': grid_import.sum() / (grid_cap * n_hours) if grid_cap > 0 else 0,
        }
        
        max_ramp_mw_per_hour = max(ramp_events) if ramp_events else 0
        max_ramp_mw_per_min = max_ramp_mw_per_hour / 5
        
        return DispatchResult(
            year=0,
            dispatch_df=dispatch_df,
            energy_delivered_mwh=energy_delivered,
            energy_required_mwh=energy_required,
            unserved_energy_mwh=unserved.sum(),
            generation_by_source=generation_by_source,
            capacity_factors=capacity_factors,
            peak_unserved_mw=unserved.max(),
            hours_with_unserved=int((unserved > 0).sum()),
            max_ramp_mw_per_min=max_ramp_mw_per_min,
        )


# =============================================================================
# SECTION 7: MAIN OPTIMIZER CLASS
# =============================================================================

class GreenfieldHeuristicV2:
    """Greenfield Datacenter Heuristic Optimizer v2.1.1"""
    
    def __init__(
        self,
        site: Dict,
        load_trajectory: Dict[int, float],
        constraints: Dict,
        sheets_client=None,
        spreadsheet_id: str = None,
        load_profile_data: Dict = None,
    ):
        self.site = site
        self.load_trajectory = load_trajectory
        self.constraints = constraints
        self.load_profile_data = load_profile_data or {}
        
        self.data_loader = BackendDataLoader(sheets_client, spreadsheet_id)
        self.equipment_specs = self.data_loader.load_equipment_specs()
        self.global_params = self.data_loader.load_global_parameters()
        
        if 'grid_lead_time_months' in constraints:
            self.global_params['default_grid_lead_time_months'] = constraints['grid_lead_time_months']
        
        self.years = sorted(load_trajectory.keys())
        self.start_year = min(self.years)
        self.end_year = max(self.years)
        self.peak_load = max(load_trajectory.values())
        
        self.flexibility_pct = self.load_profile_data.get('flexibility_pct', 30.0) / 100
        self.firm_load_factor = 1.0 - self.flexibility_pct
        self.workload_mix = self.load_profile_data.get('workload_mix', None)
        
        self.sizer = EquipmentSizer(self.equipment_specs, self.global_params, constraints)
        self.dispatcher = DispatchSimulator(self.equipment_specs, self.global_params)
    
    def _generate_load_profile(self, peak_load_mw: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generate 8760 load profiles for total and firm load."""
        if 'hourly_profile' in self.load_profile_data:
            total_load = np.array(self.load_profile_data['hourly_profile'])
            if len(total_load) != 8760:
                total_load = np.resize(total_load, 8760)
            firm_load = total_load * self.firm_load_factor
        else:
            hours = np.arange(8760)
            np.random.seed(42)
            
            base = peak_load_mw * 0.85
            hour_of_day = hours % 24
            daily = 1.0 + 0.05 * np.sin(2 * np.pi * (hour_of_day - 14) / 24)
            random_var = 1.0 + 0.10 * (np.random.random(8760) - 0.5)
            
            total_load = np.clip(base * daily * random_var, 0, peak_load_mw)
            firm_load = total_load * self.firm_load_factor
        
        return total_load, firm_load
    
    def _generate_solar_profile(self, capacity_mw: float) -> np.ndarray:
        """Generate 8760 solar profile."""
        if capacity_mw <= 0:
            return np.zeros(8760)
        
        hours = np.arange(8760)
        hour_of_day = hours % 24
        day_of_year = hours // 24
        
        solar_cf = np.zeros(8760)
        np.random.seed(43)
        
        for h in range(8760):
            hod = hour_of_day[h]
            doy = day_of_year[h]
            
            if 6 <= hod <= 18:
                hour_factor = np.exp(-((hod - 12) ** 2) / 8)
                seasonal = 0.7 + 0.3 * np.sin(2 * np.pi * (doy - 80) / 365)
                weather = 0.85 + 0.15 * np.random.random()
                solar_cf[h] = hour_factor * seasonal * weather * 0.9
        
        return solar_cf * capacity_mw
    
    def optimize(self) -> HeuristicResultV2:
        """Run hierarchical optimization."""
        print("\n" + "🔷"*40)
        print("🚀 GreenfieldHeuristicV2.optimize() STARTED")
        print(f"📍 Site: {self.site}")
        print(f"📅 Years to optimize: {self.years}")
        print(f"📊 Load trajectory: {self.load_trajectory}")
        print(f"⚡ Equipment specs loaded: {len(self.equipment_specs)} types")
        print(f"⚙️  Global params loaded: {len(self.global_params)} parameters")
        print("🔷"*40 + "\n")
        
        start_time = time.time()
        warnings = []
        
        discount_rate = self.global_params.get('discount_rate', 0.08)
        analysis_years = self.global_params.get('analysis_period_years', 15)
        voll = self.global_params.get('voll_penalty', 50000)
        
        # PHASE 1: Year-by-year equipment sizing
        equipment_by_year = {}
        dispatch_by_year = {}
        existing_equipment = {}
        
        for year in self.years:
            peak_load_mw = self.load_trajectory[year]
            if peak_load_mw <= 0:
                equipment_by_year[year] = existing_equipment.copy()
                continue
            
            firm_load_mw = peak_load_mw * self.firm_load_factor
            
            config = self.sizer.size_for_year(
                target_load_mw=peak_load_mw,
                firm_load_mw=firm_load_mw,
                year=year,
                project_start_year=self.start_year,
                existing_equipment=existing_equipment,
                workload_mix=self.workload_mix,
            )
            
            equipment_by_year[year] = config
            
            existing_equipment = {
                'n_recips': config['n_recips'],
                'n_turbines': config['n_turbines'],
                'solar_mw': config.get('solar_mw', 0),
                'bess_mw': config.get('bess_mw', 0),
                'bess_mwh': config.get('bess_mwh', 0),
            }
        
        # PHASE 2: 8760 dispatch simulation
        total_energy_delivered = 0
        total_energy_required = 0
        total_unserved = 0
        total_gen_by_source = {k: 0 for k in ['solar_mwh', 'bess_mwh', 'recip_mwh', 'turbine_mwh', 'grid_mwh']}
        
        active_years = [y for y in self.years if self.load_trajectory[y] > 0]
        n_active_years = len(active_years)
        
        for year in self.years:
            peak_load_mw = self.load_trajectory[year]
            if peak_load_mw <= 0:
                continue
            
            config = equipment_by_year[year]
            
            total_load, firm_load = self._generate_load_profile(peak_load_mw)
            solar_profile = self._generate_solar_profile(config.get('solar_mw', 0))
            
            grid_year = self.constraints.get('grid_available_year')
            grid_available = grid_year is not None and year >= grid_year
            grid_cap = self.constraints.get('grid_capacity_mw', 0) if grid_available else 0
            
            print(f"  📅 Year {year}: Running dispatch for {len(total_load)} hours...")
            dispatch_start = time.time()
            
            dispatch = self.dispatcher.run_dispatch(
                equipment_config=config,
                load_profile=total_load,
                firm_load_profile=firm_load,
                solar_profile=solar_profile,
                grid_available=grid_available,
                grid_capacity_mw=grid_cap,
            )
            
            dispatch_time = time.time() - dispatch_start
            print(f"     ⏱  Dispatch completed in {dispatch_time:.2f}s")
            
            dispatch.year = year
            dispatch_by_year[year] = dispatch
            
            total_energy_delivered += dispatch.energy_delivered_mwh
            total_energy_required += dispatch.energy_required_mwh
            total_unserved += dispatch.unserved_energy_mwh
            
            for source, mwh in dispatch.generation_by_source.items():
                total_gen_by_source[source] += mwh
        
        # PHASE 3: Check constraints
        final_config = equipment_by_year[self.end_year]
        constraint_results = self._check_constraints(final_config, dispatch_by_year)
        
        violations = [c.name for c in constraint_results if c.violated and c.constraint_type == 'hard']
        for c in constraint_results:
            if c.status == "NEAR_BINDING":
                warnings.append(f"{c.name}: {c.utilization*100:.1f}% utilization")
        
        # PHASE 4: Calculate economics
        capex = self._calculate_capex(equipment_by_year)
        
        if final_config.get('grid_mw', 0) > 0:
            grid_capex = final_config['grid_mw'] * self.equipment_specs.get('grid', {}).get('capex_per_mw', 500_000)
            capex += grid_capex
        
        opex = self._calculate_opex(final_config)
        fuel_total = self._calculate_fuel_cost(total_gen_by_source)
        fuel_annual = fuel_total / max(n_active_years, 1)
        avg_energy = total_energy_delivered / max(n_active_years, 1)
        
        crf = calculate_capital_recovery_factor(discount_rate, analysis_years)
        npv = capex + (opex + fuel_annual) / crf
        
        lcoe = calculate_lcoe(capex, opex, fuel_annual, avg_energy, discount_rate, analysis_years)
        
        avg_unserved = total_unserved / max(n_active_years, 1)
        voll_cost = avg_unserved * voll
        objective = lcoe + (voll_cost / avg_energy if avg_energy > 0 else 0)
        
        # PHASE 5: Compile results
        feasible = len(violations) == 0
        binding = [c.name for c in constraint_results if c.binding]
        
        unserved_pct = (total_unserved / total_energy_required * 100) if total_energy_required > 0 else 0
        coverage = 100 - unserved_pct
        
        land_allocation = final_config.get('land_allocation', {})
        
        max_ramp_observed = max(d.max_ramp_mw_per_min for d in dispatch_by_year.values()) if dispatch_by_year else 0
        ramp_capacity = calculate_ramp_capacity(final_config, self.equipment_specs)
        ramp_required = final_config.get('ramp_required_mw_min', 0)
        
        return HeuristicResultV2(
            feasible=feasible,
            objective_value=objective,
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            fuel_annual=fuel_annual,
            npv_total_cost=npv,
            equipment_config=final_config,
            equipment_by_year=equipment_by_year,
            dispatch_summary={
                'total_energy_delivered_mwh': total_energy_delivered,
                'total_energy_required_mwh': total_energy_required,
                'total_unserved_mwh': total_unserved,
                'generation_by_source': total_gen_by_source,
            },
            dispatch_by_year=dispatch_by_year,
            constraint_results=constraint_results,
            violations=violations,
            warnings=warnings,
            timeline_months=self._get_timeline(final_config),
            shadow_prices=self._estimate_shadow_prices(constraint_results, lcoe),
            solve_time_seconds=time.time() - start_time,
            total_energy_delivered_mwh=total_energy_delivered,
            total_unserved_energy_mwh=total_unserved,
            unserved_energy_pct=unserved_pct,
            load_coverage_pct=coverage,
            binding_constraints=binding,
            primary_binding_constraint=binding[0] if binding else 'none',
            land_allocation=land_allocation,
            ramp_analysis={
                'max_ramp_observed_mw_min': max_ramp_observed,
                'ramp_required_mw_min': ramp_required,
                'ramp_capacity_mw_min': ramp_capacity,
                'ramp_margin_mw_min': ramp_capacity - ramp_required,
            },
        )
    
    def _check_constraints(self, config: Dict, dispatch_by_year: Dict) -> List[ConstraintResult]:
        """Check all constraints."""
        results = []
        
        recip_mwh = sum(d.generation_by_source['recip_mwh'] for d in dispatch_by_year.values())
        turbine_mwh = sum(d.generation_by_source['turbine_mwh'] for d in dispatch_by_year.values())
        n_years = len([y for y in dispatch_by_year if dispatch_by_year[y].energy_required_mwh > 0])
        
        avg_recip = recip_mwh / max(n_years, 1)
        avg_turbine = turbine_mwh / max(n_years, 1)
        
        recip_spec = self.equipment_specs.get('recip_engine', {})
        turbine_spec = self.equipment_specs.get('gas_turbine', {})
        
        recip_nox = calculate_nox_annual_tpy(
            avg_recip,
            recip_spec.get('heat_rate_btu_kwh', 8500),
            recip_spec.get('nox_rate_lb_mmbtu', 0.15)
        )
        turbine_nox = calculate_nox_annual_tpy(
            avg_turbine,
            turbine_spec.get('heat_rate_btu_kwh', 10500),
            turbine_spec.get('nox_rate_lb_mmbtu', 0.10)
        )
        
        results.append(ConstraintResult(
            name='nox_annual',
            value=recip_nox + turbine_nox,
            limit=self.constraints.get('nox_tpy_annual', 100),
            unit='tpy',
            constraint_type='hard',
            tolerance=0.0001,
        ))
        
        recip_gas = avg_recip * recip_spec.get('gas_consumption_mcf_mwh', 7.2) / 365
        turbine_gas = avg_turbine * turbine_spec.get('gas_consumption_mcf_mwh', 8.5) / 365
        
        results.append(ConstraintResult(
            name='gas_supply',
            value=recip_gas + turbine_gas,
            limit=self.constraints.get('gas_supply_mcf_day', 50000),
            unit='MCF/day',
            constraint_type='soft',
            tolerance=0.10,
        ))
        
        land_used = config.get('land_allocation', {}).get('total_used_acres', 0)
        results.append(ConstraintResult(
            name='land_area',
            value=land_used,
            limit=self.constraints.get('land_area_acres', 500),
            unit='acres',
            constraint_type='soft',
            tolerance=0.10,
        ))
        
        return results
    
    def _calculate_capex(self, equipment_by_year: Dict) -> float:
        """Calculate total CAPEX (excluding grid - added separately)."""
        total = 0
        prev = {}
        
        for year in sorted(equipment_by_year.keys()):
            config = equipment_by_year[year]
            
            recip_spec = self.equipment_specs.get('recip_engine', {})
            turbine_spec = self.equipment_specs.get('gas_turbine', {})
            solar_spec = self.equipment_specs.get('solar_pv', {})
            bess_spec = self.equipment_specs.get('bess', {})
            
            new_recips = config.get('n_recips', 0) - prev.get('n_recips', 0)
            if new_recips > 0:
                total += new_recips * recip_spec.get('capacity_mw', 10) * recip_spec.get('capex_per_mw', 1_800_000)
            
            new_turbines = config.get('n_turbines', 0) - prev.get('n_turbines', 0)
            if new_turbines > 0:
                total += new_turbines * turbine_spec.get('capacity_mw', 50) * turbine_spec.get('capex_per_mw', 1_200_000)
            
            new_solar = config.get('solar_mw', 0) - prev.get('solar_mw', 0)
            if new_solar > 0:
                total += new_solar * solar_spec.get('capex_per_mw', 1_000_000)
            
            new_bess = config.get('bess_mwh', 0) - prev.get('bess_mwh', 0)
            if new_bess > 0:
                total += new_bess * bess_spec.get('capex_per_mwh', 350_000)
            
            prev = config
        
        return total
    
    def _calculate_opex(self, config: Dict) -> float:
        """Calculate annual OPEX (PATCHED: use stored MW values)."""
        recip_spec = self.equipment_specs.get('recip_engine', {})
        turbine_spec = self.equipment_specs.get('gas_turbine', {})
        solar_spec = self.equipment_specs.get('solar_pv', {})
        bess_spec = self.equipment_specs.get('bess', {})
        
        recip_mw = config.get('recip_mw', 
                             config.get('n_recips', 0) * recip_spec.get('capacity_mw', 10))
        turbine_mw = config.get('turbine_mw',
                               config.get('n_turbines', 0) * turbine_spec.get('capacity_mw', 50))
        
        opex = 0
        opex += recip_mw * recip_spec.get('opex_annual_per_mw', 45_000)
        opex += turbine_mw * turbine_spec.get('opex_annual_per_mw', 35_000)
        opex += config.get('solar_mw', 0) * solar_spec.get('opex_annual_per_mw', 12_000)
        opex += config.get('bess_mw', 0) * bess_spec.get('opex_annual_per_mw', 5_000)
        
        return opex
    
    def _calculate_fuel_cost(self, gen_by_source: Dict) -> float:
        """Calculate TOTAL fuel cost (over all years)."""
        gas_price = self.global_params.get('gas_price', 5.0)
        grid_price = self.global_params.get('electricity_price', 80.0)
        
        recip_spec = self.equipment_specs.get('recip_engine', {})
        turbine_spec = self.equipment_specs.get('gas_turbine', {})
        
        recip_mcf = gen_by_source.get('recip_mwh', 0) * recip_spec.get('gas_consumption_mcf_mwh', 7.2)
        turbine_mcf = gen_by_source.get('turbine_mwh', 0) * turbine_spec.get('gas_consumption_mcf_mwh', 8.5)
        grid_cost = gen_by_source.get('grid_mwh', 0) * grid_price
        
        return (recip_mcf + turbine_mcf) * gas_price + grid_cost
    
    def _get_timeline(self, config: Dict) -> int:
        """Get deployment timeline in months."""
        timelines = []
        if config.get('n_recips', 0) > 0:
            timelines.append(self.global_params.get('recip_lead_time_months', 24))
        if config.get('n_turbines', 0) > 0:
            timelines.append(self.global_params.get('gt_lead_time_months', 30))
        if config.get('solar_mw', 0) > 0:
            timelines.append(self.global_params.get('solar_lead_time_months', 12))
        if config.get('bess_mw', 0) > 0:
            timelines.append(self.global_params.get('bess_lead_time_months', 6))
        return max(timelines) if timelines else 0
    
    def _estimate_shadow_prices(self, constraints: List[ConstraintResult], lcoe: float) -> Dict:
        """Estimate shadow prices for binding constraints."""
        prices = {}
        for c in constraints:
            if c.binding:
                if c.name == 'nox_annual':
                    prices['nox_tpy'] = 3.0 * lcoe * 8760 * 0.85 / 1000
                elif c.name == 'gas_supply':
                    prices['gas_mcf_day'] = 0.005 * lcoe * 8760 * 0.85 / 1000
        return prices


# Backward compatibility
class GreenFieldHeuristic(GreenfieldHeuristicV2):
    """Backward-compatible wrapper."""
    def __init__(self, site: Dict, load_trajectory: Dict[int, float], constraints: Dict, 
                 equipment_options: Dict = None, economic_params: Dict = None):
        super().__init__(site=site, load_trajectory=load_trajectory, constraints=constraints)


# =============================================================================
# VALIDATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Greenfield Heuristic v2.1.1 - Validation Test")
    print("=" * 70)
    
    site = {'name': 'Dallas Brownfield Exp', 'location': 'Dallas, TX'}
    
    load_trajectory = {
        2028: 187.5,
        2029: 375.0,
        2030: 562.5,
        2031: 750.0,
        2032: 750.0,
    }
    
    constraints = {
        'nox_tpy_annual': 100,
        'gas_supply_mcf_day': 100000,
        'land_area_acres': 500,
        'grid_available_year': 2030,
        'grid_capacity_mw': 500,
    }
    
    load_profile_data = {
        'flexibility_pct': 30.6,
        'workload_mix': {
            'pre_training': 45.0,
            'fine_tuning': 20.0,
            'batch_inference': 15.0,
            'real_time_inference': 20.0,
        }
    }
    
    optimizer = GreenfieldHeuristicV2(
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints,
        load_profile_data=load_profile_data,
    )
    
    print("\nRunning optimization...")
    result = optimizer.optimize()
    
    print(f"\n{'RESULTS':=^70}")
    print(f"Feasible: {result.feasible}")
    print(f"LCOE: ${result.lcoe:.2f}/MWh")
    print(f"Objective (w/VOLL): ${result.objective_value:.2f}/MWh")
    print(f"Load Coverage: {result.load_coverage_pct:.1f}%")
    print(f"Analysis Period: {optimizer.global_params.get('analysis_period_years')} years")
    print(f"Solve Time: {result.solve_time_seconds:.2f}s")
    
    print(f"\n{'EQUIPMENT':=^70}")
    cfg = result.equipment_config
    print(f"  Recips: {cfg.get('n_recips', 0)} units ({cfg.get('recip_mw', 0):.1f} MW)")
    print(f"  Turbines: {cfg.get('n_turbines', 0)} units ({cfg.get('turbine_mw', 0):.1f} MW)")
    print(f"  Solar: {cfg.get('solar_mw', 0):.1f} MW")
    print(f"  BESS: {cfg.get('bess_mw', 0):.1f} MW / {cfg.get('bess_mwh', 0):.1f} MWh")
    print(f"  Grid: {cfg.get('grid_mw', 0):.1f} MW")
    print(f"  Total Capacity: {cfg.get('total_capacity_mw', 0):.1f} MW")
    
    print(f"\n{'ECONOMICS':=^70}")
    print(f"  CAPEX: ${result.capex_total/1e6:.1f}M")
    print(f"  OPEX (annual): ${result.opex_annual/1e6:.2f}M")
    print(f"  Fuel (annual): ${result.fuel_annual/1e6:.2f}M")
    
    print(f"\n{'LAND ALLOCATION':=^70}")
    for k, v in result.land_allocation.items():
        print(f"  {k}: {v:.1f} acres")
    
    print(f"\n{'RAMP ANALYSIS':=^70}")
    for k, v in result.ramp_analysis.items():
        print(f"  {k}: {v:.2f} MW/min")
    
    print(f"\n{'CONSTRAINTS':=^70}")
    for c in result.constraint_results:
        print(f"  {c.name}: {c.value:.1f}/{c.limit:.1f} {c.unit} [{c.status}]")
    
    if result.violations:
        print(f"\n⚠️  VIOLATIONS: {', '.join(result.violations)}")
    
    if result.warnings:
        print(f"\n⚠️  WARNINGS:")
        for w in result.warnings:
            print(f"    - {w}")
    
    print("\n" + "=" * 70)
    print("✅ Validation complete")
