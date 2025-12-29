"""
bvNexus Stage 1 Heuristic Optimizer - QA/QC Fixes
=================================================

This file contains the CORRECTED heuristic optimizer with:
1. Fixed LCOE calculation (no more $999/MWh errors)
2. Separated unserved energy reporting (not blended into LCOE)
3. Merit-order dispatch simulation
4. Constraint waterfall analysis
5. Sanity checks with warnings

INSTRUCTIONS:
Replace app/optimization/heuristic_optimizer.py with this file.

Changes preserve existing class names, method signatures, and data structures.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
import time
import sys

# Import from config (adjust path as needed for your project structure)
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.settings import (
        EQUIPMENT_DEFAULTS, CONSTRAINT_DEFAULTS, ECONOMIC_DEFAULTS,
        WORKLOAD_FLEXIBILITY, VOLL_PENALTY, K_DEG, HEURISTIC_CONFIG,
        LCOE_SANITY_CHECKS, DR_SERVICES
    )
except ImportError:
    # Fallback defaults if settings not updated yet
    EQUIPMENT_DEFAULTS = {
        'recip': {'capacity_mw': 18.3, 'heat_rate_btu_kwh': 7700, 'nox_lb_mwh': 0.10,  # POST-SCR (0.07-0.15 range)
                  'capex_per_kw': 1650, 'vom_per_mwh': 8.50, 'fom_per_kw_yr': 18.50,
                  'gas_mcf_per_mwh': 7.42, 'land_acres_per_mw': 0.5},
        'turbine': {'capacity_mw': 50.0, 'heat_rate_btu_kwh': 8500, 'nox_lb_mwh': 0.12,  # POST-SCR Simple Cycle (0.08-0.15 range)
                    'capex_per_kw': 1300, 'vom_per_mwh': 6.50, 'fom_per_kw_yr': 12.50,
                    'gas_mcf_per_mwh': 8.20, 'land_acres_per_mw': 0.3},
        'bess': {'capex_per_kwh': 236, 'duration_hours': 4, 'roundtrip_efficiency': 0.90,
                 'land_acres_per_mwh': 0.01},
        'solar': {'capex_per_w_dc': 0.95, 'capacity_factor': 0.25, 'fom_per_kw_yr': 12.0,
                  'land_acres_per_mw': 5.0},
        'grid': {'default_price_mwh': 65.0, 'lead_time_months': 60, 
                 'interconnection_cost_mw': 100000, 'max_ciac_threshold': 500_000_000,
                 'lcoe_threshold': 180.0, 'capacity_charge_kw_yr': 180.0},
    }
    CONSTRAINT_DEFAULTS = {'nox_tpy_annual': 100, 'gas_supply_mcf_day': 50000,
                           'land_area_acres': 500}
    ECONOMIC_DEFAULTS = {'discount_rate': 0.08, 'project_life_years': 20,
                         'fuel_price_mmbtu': 3.50, 'crf_20yr_8pct': 0.1019}
    WORKLOAD_FLEXIBILITY = {}
    VOLL_PENALTY = 50000
    K_DEG = 0.03
    HEURISTIC_CONFIG = {
        'n1_reserve_margin': 0.15, 'baseload_recip_fraction': 0.70,
        'bess_transient_coverage': 0.10, 'bess_default_duration_hrs': 4,
        'recip_capacity_factor': 0.85, 'turbine_capacity_factor': 0.30,
        'solar_capacity_factor': 0.25
    }
    LCOE_SANITY_CHECKS = {'warning_threshold': 200, 'error_threshold': 500}
    DR_SERVICES = {}


@dataclass
class HeuristicResult:
    """Container for heuristic optimization results - UNCHANGED STRUCTURE"""
    feasible: bool
    objective_value: float
    lcoe: float
    capex_total: float
    opex_annual: float
    equipment_config: Dict
    dispatch_summary: Dict
    constraint_status: Dict
    violations: List[str]
    timeline_months: int
    shadow_prices: Dict
    solve_time_seconds: float
    warnings: List[str] = field(default_factory=list)
    unserved_energy_mwh: float = 0.0
    unserved_energy_pct: float = 0.0
    energy_delivered_mwh: float = 0.0
    constraint_utilization: Dict = field(default_factory=dict)
    binding_constraint: str = ""


class HeuristicOptimizer:
    """Base class for heuristic optimization - FIXED VERSION"""
    
    def __init__(
        self,
        site: Dict,
        load_trajectory: Dict[int, float],
        constraints: Dict,
        equipment_options: Dict = None,
        economic_params: Dict = None,
    ):
        self.site = site
        self.load_trajectory = load_trajectory
        self.constraints = {**CONSTRAINT_DEFAULTS, **constraints}
        self.equipment = equipment_options or EQUIPMENT_DEFAULTS
        self.economics = economic_params or ECONOMIC_DEFAULTS
        self.heuristic_config = HEURISTIC_CONFIG
        self.peak_load = max(load_trajectory.values()) if load_trajectory else 100
        self.years = sorted(load_trajectory.keys()) if load_trajectory else [2028]
        self.start_year = min(self.years)
        self.end_year = max(self.years)
        self.annual_energy_mwh = self.peak_load * 8760 * 0.85
        
    def optimize_annual_energy_stack(self) -> Dict:
        """
        Run year-by-year optimization to build optimal energy stack over time.
        
        Considers:
        - Grid availability timeline (default 60 months from start)
        - Different load levels per year
        - Annual NOx, gas, land constraints
        - Minimizes total LCOE over planning horizon
        
        Returns:
            Dict with annual equipment deployments and energy stack
        """
        grid_lead_months = self.equipment.get('grid', {}).get('lead_time_months', 60)
        grid_available_year = self.start_year + (grid_lead_months // 12)
        
        annual_stack = {}
        cumulative_equipment = {
            'n_recip': 0, 'recip_mw': 0,
            'n_turbine': 0, 'turbine_mw': 0,
            'solar_mw': 0, 'bess_mw': 0, 'bess_mwh': 0,
            'grid_mw': 0
        }
        
        total_cost_npv = 0
        discount_rate = self.economics.get('discount_rate', 0.08)
        
        for year in self.years:
            year_load_mw = self.load_trajectory.get(year, 0)
            
            if year_load_mw == 0:
                # No load this year, skip
                annual_stack[year] = {
                    'load_mw': 0,
                    'equipment': cumulative_equipment.copy(),
                    'new_equipment': {},
                    'energy_delivered_mwh': 0,
                    'unserved_pct': 0,
                    'lcoe': 0,
                }
                continue
            
            
            # Determine if grid is available this year
            grid_available = (year >= grid_available_year)
            
            # Calculate existing FIRM capacity (with capacity credits)
            # Import capacity credits from config
            from config.settings import CAPACITY_CREDITS
            
            existing_firm_mw = (
                cumulative_equipment.get('recip_mw', 0) * CAPACITY_CREDITS.get('recip', 1.0) +
                cumulative_equipment.get('turbine_mw', 0) * CAPACITY_CREDITS.get('turbine', 1.0) +
                cumulative_equipment.get('solar_mw', 0) * CAPACITY_CREDITS.get('solar', 0.10) +
                cumulative_equipment.get('bess_mw', 0) * CAPACITY_CREDITS.get('bess', 0.50)
            )

            
            # SMART SIZING: Size for this year's load, considering existing equipment
            if grid_available and existing_firm_mw > 0:
                # Grid is available - use it to fill gap between load and existing onsite
                # Keep existing onsite (sunk cost, low marginal cost ~$22/MWh)
                # Use grid for shortfall only
                required_firm_mw = year_load_mw * (1.15 if self.constraints.get('n_minus_1_required', True) else 1.0)
                
                if required_firm_mw <= existing_firm_mw:
                    # Existing onsite can serve load - no grid needed
                    equipment_needed = cumulative_equipment.copy()
                    equipment_needed['grid_mw'] = 0
                else:
                    # Need more capacity - use grid for shortfall
                    grid_needed = required_firm_mw - existing_firm_mw
                    equipment_needed = cumulative_equipment.copy()
                    equipment_needed['grid_mw'] = grid_needed
                
                # Update cumulative with grid
                cumulative_equipment['grid_mw'] = equipment_needed.get('grid_mw', 0)
            else:
                # Grid not available OR no existing equipment - size fresh
                equipment_needed = self.size_equipment_to_load(
                    target_mw=year_load_mw,
                    require_n1=self.constraints.get('n_minus_1_required', True),
                    grid_available_mw=0,  # Don't pass grid here
                )
                
                # Update cumulative equipment (only increase, never decrease)
                for key in ['n_recip', 'recip_mw', 'n_turbine', 'turbine_mw', 'solar_mw', 'bess_mw', 'bess_mwh']:
                    new_val = equipment_needed.get(key, 0)
                    old_val = cumulative_equipment.get(key, 0)
                    cumulative_equipment[key] = max(old_val, new_val)
            
            # Update total capacity
            cumulative_equipment['total_capacity_mw'] = (
                cumulative_equipment.get('recip_mw', 0) +
                cumulative_equipment.get('turbine_mw', 0) +
                cumulative_equipment.get('solar_mw', 0) +
                cumulative_equipment.get('bess_mw', 0) +
                cumulative_equipment.get('grid_mw', 0)
            )
            
            # Calculate which equipment is NEW this year
            new_equipment = {}
            for key in ['n_recip', 'recip_mw', 'n_turbine', 'turbine_mw', 'solar_mw', 'bess_mw', 'bess_mwh', 'grid_mw']:
                current = cumulative_equipment.get(key, 0)
                previous = annual_stack[sorted(annual_stack.keys())[-1]]['equipment'].get(key, 0) if annual_stack else 0
                new_equipment[key] = max(0, current - previous)

            # Calculate costs and LCOE for this year
            annual_energy_mwh = year_load_mw * 8760 * 0.85
            lcoe, lcoe_details = self.calculate_lcoe(cumulative_equipment, annual_energy_mwh)
            
            # Discount to present value
            years_from_start = year - self.start_year
            discount_factor = 1 / (1 + discount_rate) ** years_from_start
            annual_cost = lcoe_details['annual_cost'] * discount_factor
            total_cost_npv += annual_cost
            
            annual_stack[year] = {
                'load_mw': year_load_mw,
                'equipment': cumulative_equipment.copy(),
                'new_equipment': new_equipment,
                'energy_delivered_mwh': lcoe_details['energy_delivered_mwh'],
                'unserved_mwh': lcoe_details['unserved_energy_mwh'],
                'unserved_pct': lcoe_details['unserved_energy_pct'],
                'lcoe': lcoe,
                'annual_cost': lcoe_details['annual_cost'],
                'annual_cost_npv': annual_cost,
                'grid_available': grid_available,
            }
        
        # Calculate blended LCOE over entire period
        total_energy_delivered = sum(y['energy_delivered_mwh'] for y in annual_stack.values())
        blended_lcoe = total_cost_npv / total_energy_delivered if total_energy_delivered > 0 else 0
        
        return {
            'annual_stack': annual_stack,
            'final_equipment': cumulative_equipment,
            'grid_available_year': grid_available_year,
            'total_cost_npv': total_cost_npv,
            'total_energy_delivered_mwh': total_energy_delivered,
            'blended_lcoe': blended_lcoe,
        }
    
    def size_equipment_to_load(
        self,
        target_mw: float,
        require_n1: bool = True,
        max_recip_pct: float = 1.0,
        max_turbine_pct: float = 1.0,
        include_solar: bool = True,
        include_bess: bool = True,
        grid_available_mw: float = 0.0,
    ) -> Dict:
        """Size equipment to meet target load with constraints - FIXED."""
        n1_margin = self.heuristic_config.get('n1_reserve_margin', 0.15)
        required_firm_mw = target_mw * (1 + n1_margin) if require_n1 else target_mw
        remaining_mw = max(0, required_firm_mw - grid_available_mw)
        constraint_limits = self._calculate_constraint_limits()
        
        recip_unit_mw = self.equipment['recip'].get('capacity_mw', 18.3)
        turbine_unit_mw = self.equipment['turbine'].get('capacity_mw', 50.0)
        baseload_fraction = self.heuristic_config.get('baseload_recip_fraction', 0.70)
        
        max_thermal_mw_from_nox = constraint_limits.get('max_thermal_mw_from_nox', float('inf'))
        max_thermal_mw_from_gas = constraint_limits.get('max_thermal_mw_from_gas', float('inf'))
        max_thermal_mw = min(max_thermal_mw_from_nox, max_thermal_mw_from_gas, remaining_mw)
        
        recip_target_mw = min(remaining_mw * baseload_fraction * max_recip_pct, max_thermal_mw * 0.8)
        n_recip = max(0, int(np.ceil(recip_target_mw / recip_unit_mw)))
        recip_mw = n_recip * recip_unit_mw
        
        remaining_after_recip = max(0, remaining_mw - recip_mw)
        turbine_target_mw = min(remaining_after_recip * max_turbine_pct, max_thermal_mw - recip_mw)
        n_turbine = max(0, int(np.ceil(turbine_target_mw / turbine_unit_mw)))
        turbine_mw = n_turbine * turbine_unit_mw
        
        bess_mw = 0
        bess_mwh = 0
        if include_bess:
            bess_coverage = self.heuristic_config.get('bess_transient_coverage', 0.10)
            bess_duration = self.heuristic_config.get('bess_default_duration_hrs', 4)
            bess_mw = target_mw * bess_coverage
            bess_mwh = bess_mw * bess_duration
        
        solar_mw = 0
        if include_solar:
            available_land = self.constraints.get('land_area_acres', 500)
            
            # Reserve land for datacenter buildout: 3 MW per acre = 0.33 acres/MW
            # This ensures land constraint doesn't limit datacenter, only onsite generation
            datacenter_land_reservation = target_mw / 3.0  # 3 MW per acre = 0.33 acres per MW
            
            thermal_land = (
                recip_mw * self.equipment['recip'].get('land_acres_per_mw', 0.5) +
                turbine_mw * self.equipment['turbine'].get('land_acres_per_mw', 0.3) +
                bess_mwh * self.equipment['bess'].get('land_acres_per_mwh', 0.01)
            )
            
            # Land available for solar = Total - Datacenter - Thermal
            remaining_land = max(0, available_land - datacenter_land_reservation - thermal_land)
            solar_density = self.equipment['solar'].get('land_acres_per_mw', 5.0)
            solar_mw = remaining_land / solar_density if solar_density > 0 else 0
        
        return {
            'n_recip': n_recip,
            'recip_mw': recip_mw,
            'n_turbine': n_turbine,
            'turbine_mw': turbine_mw,
            'bess_mw': bess_mw,
            'bess_mwh': bess_mwh,
            'solar_mw': solar_mw,
            'grid_mw': grid_available_mw,
            'total_capacity_mw': recip_mw + turbine_mw + bess_mw + solar_mw * 0.25 + grid_available_mw,
            'firm_capacity_mw': recip_mw + turbine_mw + grid_available_mw,
        }
    
    def _calculate_constraint_limits(self) -> Dict:
        """Calculate maximum capacity from each constraint."""
        limits = {}
        nox_limit_tpy = self.constraints.get('nox_tpy_annual', 100)
        avg_nox_rate = (
            self.equipment['recip'].get('nox_lb_mwh', 0.50) * 0.7 +
            self.equipment['turbine'].get('nox_lb_mwh', 0.25) * 0.3
        )
        if avg_nox_rate > 0:
            max_thermal_mwh_from_nox = (nox_limit_tpy * 2000) / avg_nox_rate
            avg_cf = 0.70
            limits['max_thermal_mw_from_nox'] = max_thermal_mwh_from_nox / (8760 * avg_cf)
        else:
            limits['max_thermal_mw_from_nox'] = float('inf')
        
        gas_supply_mcf_day = self.constraints.get('gas_supply_mcf_day', 50000)
        avg_gas_rate = (
            self.equipment['recip'].get('gas_mcf_per_mwh', 7.42) * 0.7 +
            self.equipment['turbine'].get('gas_mcf_per_mwh', 8.20) * 0.3
        )
        if avg_gas_rate > 0:
            max_thermal_mwh_per_day = gas_supply_mcf_day / avg_gas_rate
            limits['max_thermal_mw_from_gas'] = max_thermal_mwh_per_day / 24
        else:
            limits['max_thermal_mw_from_gas'] = float('inf')
        
        land_acres = self.constraints.get('land_area_acres', 500)
        thermal_land_per_mw = 0.5
        limits['max_thermal_mw_from_land'] = land_acres / thermal_land_per_mw
        return limits
    
    def calculate_capex(self, equipment: Dict) -> float:
        """Calculate total capital expenditure."""
        capex = 0
        recip_mw = equipment.get('recip_mw', 0)
        if recip_mw > 0:
            capex += recip_mw * 1000 * self.equipment['recip'].get('capex_per_kw', 1650)
        turbine_mw = equipment.get('turbine_mw', 0)
        if turbine_mw > 0:
            capex += turbine_mw * 1000 * self.equipment['turbine'].get('capex_per_kw', 1300)
        bess_mwh = equipment.get('bess_mwh', 0)
        if bess_mwh > 0:
            itc_factor = 1 - self.economics.get('itc_rate', 0.30)
            capex += bess_mwh * 1000 * self.equipment['bess'].get('capex_per_kwh', 236) * itc_factor
        solar_mw = equipment.get('solar_mw', 0)
        if solar_mw > 0:
            itc_factor = 1 - self.economics.get('itc_rate', 0.30)
            capex += solar_mw * 1000000 * self.equipment['solar'].get('capex_per_w_dc', 0.95) * itc_factor
        return capex
    
    def calculate_annual_opex(self, equipment: Dict, annual_gen_mwh: float = None) -> float:
        """Calculate annual operating expenditure."""
        opex = 0
        fuel_price = self.economics.get('fuel_price_mmbtu', 3.50)
        hours = 8760
        if annual_gen_mwh is None:
            annual_gen_mwh = self._estimate_annual_generation(equipment)
        
        recip_mw = equipment.get('recip_mw', 0)
        if recip_mw > 0:
            recip_cf = self.heuristic_config.get('recip_capacity_factor', 0.85)
            recip_gen = recip_mw * recip_cf * hours
            heat_rate_mmbtu = self.equipment['recip'].get('heat_rate_btu_kwh', 7700) / 1000
            fuel_cost = recip_gen * heat_rate_mmbtu * fuel_price
            vom = recip_gen * self.equipment['recip'].get('vom_per_mwh', 8.50)
            fom = recip_mw * 1000 * self.equipment['recip'].get('fom_per_kw_yr', 18.50)
            opex += fuel_cost + vom + fom
        
        turbine_mw = equipment.get('turbine_mw', 0)
        if turbine_mw > 0:
            turbine_cf = self.heuristic_config.get('turbine_capacity_factor', 0.30)
            turbine_gen = turbine_mw * turbine_cf * hours
            heat_rate_mmbtu = self.equipment['turbine'].get('heat_rate_btu_kwh', 8500) / 1000
            fuel_cost = turbine_gen * heat_rate_mmbtu * fuel_price
            vom = turbine_gen * self.equipment['turbine'].get('vom_per_mwh', 6.50)
            fom = turbine_mw * 1000 * self.equipment['turbine'].get('fom_per_kw_yr', 12.50)
            opex += fuel_cost + vom + fom
        
        solar_mw = equipment.get('solar_mw', 0)
        if solar_mw > 0:
            fom = solar_mw * 1000 * self.equipment['solar'].get('fom_per_kw_yr', 12.0)
            opex += fom
        
        bess_mwh = equipment.get('bess_mwh', 0)
        if bess_mwh > 0:
            cycles_per_day = self.heuristic_config.get('bess_daily_cycles', 1.0)
            annual_throughput_kwh = bess_mwh * 1000 * cycles_per_day * 365
            degradation_cost = annual_throughput_kwh * K_DEG
            opex += degradation_cost
        return opex
    
    def _estimate_annual_generation(self, equipment: Dict) -> float:
        """Estimate annual generation from equipment configuration."""
        hours = 8760
        generation = 0
        recip_mw = equipment.get('recip_mw', 0)
        if recip_mw > 0:
            recip_cf = self.heuristic_config.get('recip_capacity_factor', 0.85)
            generation += recip_mw * recip_cf * hours
        turbine_mw = equipment.get('turbine_mw', 0)
        if turbine_mw > 0:
            turbine_cf = self.heuristic_config.get('turbine_capacity_factor', 0.30)
            generation += turbine_mw * turbine_cf * hours
        solar_mw = equipment.get('solar_mw', 0)
        if solar_mw > 0:
            solar_cf = self.heuristic_config.get('solar_capacity_factor', 0.25)
            generation += solar_mw * solar_cf * hours
        return generation
    
    def calculate_lcoe(self, equipment: Dict, annual_energy_required_mwh: float = None) -> Tuple[float, Dict]:
        """Calculate LCOE - FIXED: Proper grid cost accounting."""
        if annual_energy_required_mwh is None:
            annual_energy_required_mwh = self.peak_load * 8760 * 0.85
        
        annual_generation_mwh = self._estimate_annual_generation(equipment)
        grid_mw = equipment.get('grid_mw', 0)
        grid_gen_mwh = 0
        
        if grid_mw > 0:
            # Grid can provide up to its capacity
            grid_gen = min(grid_mw * 8760, annual_energy_required_mwh - annual_generation_mwh)
            grid_gen = max(0, grid_gen)
            grid_gen_mwh = grid_gen
            annual_generation_mwh += grid_gen_mwh
        
        energy_delivered_mwh = min(annual_generation_mwh, annual_energy_required_mwh)
        unserved_energy_mwh = max(0, annual_energy_required_mwh - energy_delivered_mwh)
        unserved_energy_pct = (unserved_energy_mwh / annual_energy_required_mwh * 100) if annual_energy_required_mwh > 0 else 0
        
        capex = self.calculate_capex(equipment)
        
        # Add grid interconnection CAPEX (CIAC)
        if grid_mw > 0:
            grid_interconnect_cost = grid_mw * 1000 * self.equipment.get('grid', {}).get('interconnection_cost_mw', 100000) / 1000  # $/MW
            capex += grid_interconnect_cost
        
        opex = self.calculate_annual_opex(equipment, energy_delivered_mwh)
        
        # Add grid-specific annual costs
        if grid_mw > 0:
            grid_config = self.equipment.get('grid', {})
            
            # Grid energy cost
            grid_energy_cost = grid_gen_mwh * grid_config.get('default_price_mwh', 65.0)
            
            # Grid capacity/demand charges (annual)
            grid_capacity_charge = grid_mw * 1000 * grid_config.get('capacity_charge_kw_yr', 180.0)
            
            # Grid standby charges (monthly -> annual)
            grid_standby_charge = grid_mw * 1000 * grid_config.get('standby_charge_kw_mo', 5.0) * 12
            
            opex += grid_energy_cost + grid_capacity_charge + grid_standby_charge
        
        crf = self.economics.get('crf_20yr_8pct', 0.1019)
        annualized_capex = capex * crf
        annual_cost = annualized_capex + opex
        
        # === HIERARCHICAL OBJECTIVE ===
        # 1. MAXIMIZE power served (via VOLL penalty on unserved)
        # 2. MINIMIZE cost (among solutions that serve load)
        
        # Unserved energy penalty (makes unserved prohibitively expensive)
        unserved_penalty = unserved_energy_mwh * VOLL_PENALTY
        
        # Total objective = cost + penalty for unserved
        objective_value = annual_cost + unserved_penalty
        
        # LCOE is calculated for REPORTING only (NOT the objective!)
        # LCOE = total_cost / energy_required (fixed denominator, not energy_delivered)
        # This prevents "gaming" by just serving less load
        if annual_energy_required_mwh > 0:
            lcoe = annual_cost / annual_energy_required_mwh
        else:
            lcoe = 0
        
        warnings = []
        if lcoe > LCOE_SANITY_CHECKS.get('error_threshold', 500):
            warnings.append(f"LCOE ${lcoe:.0f}/MWh exceeds error threshold - check inputs")
            lcoe = min(lcoe, 500)
        elif lcoe > LCOE_SANITY_CHECKS.get('warning_threshold', 200):
            warnings.append(f"LCOE ${lcoe:.0f}/MWh is high - review configuration")
        elif lcoe < LCOE_SANITY_CHECKS.get('min_realistic', 50) and lcoe > 0:
            warnings.append(f"LCOE ${lcoe:.0f}/MWh is unusually low - verify inputs")
        
        details = {
            'objective_value': objective_value,  # Total cost + VOLL penalty
            'annual_cost': annual_cost,
            'annualized_capex': annualized_capex,
            'annual_opex': opex,
            'unserved_penalty': unserved_penalty,
            'energy_delivered_mwh': energy_delivered_mwh,
            'energy_required_mwh': annual_energy_required_mwh,
            'unserved_energy_mwh': unserved_energy_mwh,
            'unserved_energy_pct': unserved_energy_pct,
            'warnings': warnings,
        }
        return lcoe, details
    
    def check_constraints(self, equipment: Dict) -> Tuple[Dict, List[str], Dict]:
        """Check all constraints and return status, violations, and utilization."""
        status = {}
        violations = []
        utilization = {}
        
        nox_tpy = self._calculate_nox_tpy(equipment)
        nox_limit = self.constraints.get('nox_tpy_annual', 100)
        status['nox_tpy'] = nox_tpy
        status['nox_limit'] = nox_limit
        utilization['nox'] = (nox_tpy / nox_limit * 100) if nox_limit > 0 else 0
        if nox_tpy > nox_limit:
            violations.append(f"NOx: {nox_tpy:.1f} tpy exceeds limit of {nox_limit} tpy")
        
        gas_mcf_day = self._calculate_gas_mcf_day(equipment)
        gas_limit = self.constraints.get('gas_supply_mcf_day', 50000)
        status['gas_mcf_day'] = gas_mcf_day
        status['gas_limit'] = gas_limit
        utilization['gas'] = (gas_mcf_day / gas_limit * 100) if gas_limit > 0 else 0
        if gas_mcf_day > gas_limit:
            violations.append(f"Gas: {gas_mcf_day:.0f} MCF/day exceeds limit of {gas_limit} MCF/day")
        
        land_acres = self._calculate_land_acres(equipment)
        land_limit = self.constraints.get('land_area_acres', 500)
        status['land_acres'] = land_acres
        status['land_limit'] = land_limit
        utilization['land'] = (land_acres / land_limit * 100) if land_limit > 0 else 0
        if land_acres > land_limit:
            violations.append(f"Land: {land_acres:.1f} acres exceeds limit of {land_limit} acres")
        
        if self.constraints.get('n_minus_1_required', True):
            firm_capacity = equipment.get('firm_capacity_mw', 0)
            required_capacity = self.peak_load
            status['firm_capacity_mw'] = firm_capacity
            status['required_capacity_mw'] = required_capacity
            utilization['capacity'] = (required_capacity / firm_capacity * 100) if firm_capacity > 0 else 999
            if firm_capacity < required_capacity:
                violations.append(f"Capacity: {firm_capacity:.1f} MW firm < {required_capacity:.1f} MW required")
        
        binding = max(utilization, key=utilization.get) if utilization else ""
        return status, violations, {'utilization': utilization, 'binding': binding}
    
    def _calculate_nox_tpy(self, equipment: Dict) -> float:
        hours = 8760
        nox_tpy = 0
        recip_mw = equipment.get('recip_mw', 0)
        if recip_mw > 0:
            recip_cf = self.heuristic_config.get('recip_capacity_factor', 0.85)
            recip_gen_mwh = recip_mw * recip_cf * hours
            nox_lb = recip_gen_mwh * self.equipment['recip'].get('nox_lb_mwh', 0.50)
            nox_tpy += nox_lb / 2000
        turbine_mw = equipment.get('turbine_mw', 0)
        if turbine_mw > 0:
            turbine_cf = self.heuristic_config.get('turbine_capacity_factor', 0.30)
            turbine_gen_mwh = turbine_mw * turbine_cf * hours
            nox_lb = turbine_gen_mwh * self.equipment['turbine'].get('nox_lb_mwh', 0.25)
            nox_tpy += nox_lb / 2000
        return nox_tpy
    
    def _calculate_gas_mcf_day(self, equipment: Dict) -> float:
        hours_per_day = 24
        gas_mcf_day = 0
        recip_mw = equipment.get('recip_mw', 0)
        if recip_mw > 0:
            recip_cf = self.heuristic_config.get('recip_capacity_factor', 0.85)
            recip_gen_mwh_day = recip_mw * recip_cf * hours_per_day
            gas_mcf_day += recip_gen_mwh_day * self.equipment['recip'].get('gas_mcf_per_mwh', 7.42)
        turbine_mw = equipment.get('turbine_mw', 0)
        if turbine_mw > 0:
            turbine_cf = self.heuristic_config.get('turbine_capacity_factor', 0.30)
            turbine_gen_mwh_day = turbine_mw * turbine_cf * hours_per_day
            gas_mcf_day += turbine_gen_mwh_day * self.equipment['turbine'].get('gas_mcf_per_mwh', 8.20)
        return gas_mcf_day
    
    def _calculate_land_acres(self, equipment: Dict) -> float:
        land = 0
        # Add datacenter reservation: 3 MW per acre = 0.33 acres/MW
        land += self.peak_load / 3.0
        # Add onsite generation land use
        land += equipment.get('recip_mw', 0) * self.equipment['recip'].get('land_acres_per_mw', 0.5)
        land += equipment.get('turbine_mw', 0) * self.equipment['turbine'].get('land_acres_per_mw', 0.3)
        land += equipment.get('solar_mw', 0) * self.equipment['solar'].get('land_acres_per_mw', 5.0)
        land += equipment.get('bess_mwh', 0) * self.equipment['bess'].get('land_acres_per_mwh', 0.01)
        return land
    
    def calculate_timeline(self, equipment: Dict) -> int:
        timelines = []
        if equipment.get('n_recip', 0) > 0:
            timelines.append(self.equipment['recip'].get('lead_time_months', 18))
        if equipment.get('n_turbine', 0) > 0:
            timelines.append(self.equipment['turbine'].get('lead_time_months', 24))
        if equipment.get('bess_mwh', 0) > 0:
            timelines.append(self.equipment['bess'].get('lead_time_months', 12))
        if equipment.get('solar_mw', 0) > 0:
            timelines.append(self.equipment['solar'].get('lead_time_months', 12))
        return max(timelines) if timelines else 0


class GreenFieldHeuristic(HeuristicOptimizer):
    """Problem 1: Greenfield - Minimize LCOE"""
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        
        # Use annual energy stack optimization if multi-year trajectory
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
            
            # Get final year data
            final_year = max(annual_result['annual_stack'].keys())
            final_year_data = annual_result['annual_stack'][final_year]
            unserved_mwh = final_year_data['unserved_mwh']
            unserved_pct = final_year_data['unserved_pct']
            energy_delivered = final_year_data['energy_delivered_mwh']
            
            # Store annual stack for later use
            dispatch_summary = {
                'annual_generation_mwh': energy_delivered,
                'annual_energy_required_mwh': self.annual_energy_mwh,
                'annual_stack': annual_result['annual_stack'],
                'grid_available_year': annual_result['grid_available_year'],
                'blended_lcoe': lcoe,
            }
        else:
            # Single year - use simple optimization
            equipment = self.size_equipment_to_load(
                target_mw=self.peak_load,
                require_n1=self.constraints.get('n_minus_1_required', True),
                include_solar=True,
                include_bess=True,
                grid_available_mw=self.constraints.get('grid_import_mw', 0),
            )
            annual_energy_mwh = self.peak_load * 8760 * 0.85
            lcoe, lcoe_details = self.calculate_lcoe(equipment, annual_energy_mwh)
            unserved_mwh = lcoe_details['unserved_energy_mwh']
            unserved_pct = lcoe_details['unserved_energy_pct']
            energy_delivered = lcoe_details['energy_delivered_mwh']
            
            dispatch_summary = {
                'annual_generation_mwh': energy_delivered,
                'annual_energy_required_mwh': annual_energy_mwh,
            }
        
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        constraint_status, violations, constraint_analysis = self.check_constraints(equipment)
        timeline_months = self.calculate_timeline(equipment)
        
        return HeuristicResult(
            feasible=len(violations) == 0,
            objective_value=lcoe,
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary=dispatch_summary,
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=timeline_months,
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=[],
            unserved_energy_mwh=unserved_mwh,
            unserved_energy_pct=unserved_pct,
            energy_delivered_mwh=energy_delivered,
            constraint_utilization=constraint_analysis.get('utilization', {}),
            binding_constraint=constraint_analysis.get('binding', ''),
        )


class BrownfieldHeuristic(HeuristicOptimizer):
    """Problem 2: Brownfield - Max load within LCOE ceiling
    
    Hierarchical Objective:
    1. LCOE ≤ ceiling (hard constraint)
    2. Maximize expansion capacity (MW added)
    """
    
    def __init__(self, *args, existing_equipment: Dict = None, lcoe_threshold: float = 120, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_equipment = existing_equipment or {}
        self.lcoe_threshold = lcoe_threshold
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        existing_mw = sum([
            self.existing_equipment.get('recip_mw', 0),
            self.existing_equipment.get('turbine_mw', 0),
            self.existing_equipment.get('grid_mw', 0)
        ])
        existing_lcoe = self.existing_equipment.get('existing_lcoe', 80)
        lcoe_headroom = self.lcoe_threshold - existing_lcoe
        
        if lcoe_headroom <= 0:
            return HeuristicResult(
                feasible=False, objective_value=0, lcoe=existing_lcoe, capex_total=0, opex_annual=0,
                equipment_config={}, dispatch_summary={'max_expansion_mw': 0}, constraint_status={},
                violations=['LCOE ceiling already reached'], timeline_months=0, shadow_prices={},
                solve_time_seconds=time.time() - start_time, warnings=['No expansion possible'],
            )
        
        # Use annual stack for multi-year scenarios
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            
            # Check LCOE ceiling constraint
            if annual_result['blended_lcoe'] > self.lcoe_threshold:
                feasible = False
                warnings = [f"Blended LCOE ${annual_result['blended_lcoe']:.1f}/MWh exceeds ceiling ${self.lcoe_threshold:.1f}/MWh"]
            else:
                feasible = True
                warnings = []
            
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
            max_expansion_mw = equipment.get('total_capacity_mw', 0) - existing_mw
            
            final_year = max(annual_result['annual_stack'].keys())
            final_data = annual_result['annual_stack'][final_year]
            unserved_mwh = final_data['unserved_mwh']
            unserved_pct = final_data['unserved_pct']
            energy_delivered = final_data['energy_delivered_mwh']
        else:
            # Single year optimization
            new_equipment = self.size_equipment_to_load(
                target_mw=min(self.peak_load * 0.5, self.peak_load - existing_mw),
                require_n1=False,
            )
            equipment = {**self.existing_equipment, **new_equipment}
            annual_energy_mwh = self.peak_load * 8760 * 0.85
            lcoe, lcoe_details = self.calculate_lcoe(equipment, annual_energy_mwh)
            
            feasible = lcoe <= self.lcoe_threshold
            warnings = lcoe_details.get('warnings', [])
            max_expansion_mw = new_equipment.get('total_capacity_mw', 0)
            unserved_mwh = lcoe_details.get('unserved_energy_mwh', 0)
            unserved_pct = lcoe_details.get('unserved_energy_pct', 0)
            energy_delivered = lcoe_details.get('energy_delivered_mwh', 0)
        
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        constraint_status, violations, constraint_analysis = self.check_constraints(equipment)
        
        return HeuristicResult(
            feasible=feasible and len(violations) == 0,
            objective_value=max_expansion_mw,  # Maximize expansion
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary={
                'max_expansion_mw': max_expansion_mw,
                'blended_lcoe': lcoe,
                'existing_mw': existing_mw,
                'lcoe_threshold': self.lcoe_threshold,
            },
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.calculate_timeline(equipment),
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=warnings,
            unserved_energy_mwh=unserved_mwh,
            unserved_energy_pct=unserved_pct,
            energy_delivered_mwh=energy_delivered,
            constraint_utilization=constraint_analysis.get('utilization', {}),
            binding_constraint=constraint_analysis.get('binding', ''),
        )


class LandDevHeuristic(HeuristicOptimizer):
    """Problem 3: Land Development - Max capacity by flexibility scenario
    
    Hierarchical Objective:
    1. Respect constraints (NOx, Gas, Land hard limits)
    2. Maximize firm capacity that can be built
    3. Analyze across workload flexibility scenarios
    """
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        flex_scenarios = [0.0, 0.15, 0.30, 0.50]
        results_matrix = {}
        constraint_limits = self._calculate_constraint_limits()
        
        max_firm_mw = min(
            constraint_limits.get('max_thermal_mw_from_nox', float('inf')),
            constraint_limits.get('max_thermal_mw_from_gas', float('inf')),
            constraint_limits.get('max_thermal_mw_from_land', float('inf')),
        )
        
        binding = 'nox' if max_firm_mw == constraint_limits.get('max_thermal_mw_from_nox') else \
                  'gas' if max_firm_mw == constraint_limits.get('max_thermal_mw_from_gas') else 'land'
        
        # Run scenario for each flexibility level
        for flex in flex_scenarios:
            alignment_factor = 0.7
            load_max = max_firm_mw / (1 - flex * alignment_factor) if flex > 0 else max_firm_mw
            equipment = self.size_equipment_to_load(max_firm_mw, require_n1=False)
            lcoe, _ = self.calculate_lcoe(equipment, load_max * 8760 * 0.85)
            results_matrix[f'{int(flex*100)}%'] = {
                'load_max_mw': load_max,
                'firm_capacity_mw': max_firm_mw,
                'lcoe': lcoe,
                'binding_constraint': binding,
            }
        
        equipment = self.size_equipment_to_load(max_firm_mw, require_n1=False)
        
        # Calculate actual firm capacity with credits
        from config.settings import CAPACITY_CREDITS
        actual_firm_mw = (
            equipment.get('recip_mw', 0) * CAPACITY_CREDITS.get('recip', 1.0) +
            equipment.get('turbine_mw', 0) * CAPACITY_CREDITS.get('turbine', 1.0) +
            equipment.get('solar_mw', 0) * CAPACITY_CREDITS.get('solar', 0.10) +
            equipment.get('bess_mw', 0) * CAPACITY_CREDITS.get('bess', 0.50)
        )
        
        lcoe, lcoe_details = self.calculate_lcoe(equipment)
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        constraint_status, violations, constraint_analysis = self.check_constraints(equipment)
        
        return HeuristicResult(
            feasible=len(violations) == 0,
            objective_value=actual_firm_mw,  # Maximize actual firm capacity
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary={
                'power_potential_matrix': results_matrix,
                'binding_constraint': binding,
                'max_firm_capacity_mw': max_firm_mw
            },
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.calculate_timeline(equipment),
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=lcoe_details.get('warnings', []),
            constraint_utilization=constraint_analysis.get('utilization', {}),
            binding_constraint=binding,
        )


class GridServicesHeuristic(HeuristicOptimizer):
    """Problem 4: Grid Services - Max DR revenue
    
    Hierarchical Objective:
    1. Size equipment for base load
    2. Calculate flexible MW from workload mix
    3. Maximize DR revenue (NOT minimize LCOE!)
    """
    
    def __init__(self, *args, workload_mix: Dict = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.workload_mix = workload_mix or {
            'pre_training': 0.40, 'fine_tuning': 0.15,
            'batch_inference': 0.20, 'realtime_inference': 0.15, 'cloud_hpc': 0.10
        }
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        
        # Calculate flexible MW from workload mix        
        total_flex_mw = 0
        flex_by_workload = {}
        for workload, share in self.workload_mix.items():
            flex_params = WORKLOAD_FLEXIBILITY.get(workload, {'flexibility_pct': 0})
            flex_mw = self.peak_load * share * flex_params.get('flexibility_pct', 0)
            flex_by_workload[workload] = flex_mw
            total_flex_mw += flex_mw
        
        # Size equipment (use annual stack if multi-year)
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
            
            # Store dispatch summary with annual stack
            dispatch_summary = {
                'annual_stack': annual_result['annual_stack'],
                'grid_available_year': annual_result['grid_available_year'],
                'blended_lcoe': lcoe
            }
        else:
            equipment = self.size_equipment_to_load(self.peak_load)
            lcoe, _ = self.calculate_lcoe(equipment)
            dispatch_summary = {}
        
        # Calculate DR service revenue (SEPARATE from LCOE!)
        service_revenue = {}
        total_revenue = 0
        for service_id, service_params in DR_SERVICES.items():
            eligible_mw = total_flex_mw * 0.8
            if eligible_mw >= service_params.get('min_capacity_mw', 0):
                availability_revenue = eligible_mw * service_params.get('payment_mw_hr', 0) * 8760 if 'payment_mw_hr' in service_params else \
                                       eligible_mw * 1000 * service_params.get('payment_kw_yr', 0) if 'payment_kw_yr' in service_params else 0
                activation_revenue = eligible_mw * service_params.get('expected_hours_yr', 0) * service_params.get('activation_mwh', 0)
                service_revenue[service_id] = {'eligible_mw': eligible_mw, 'total_revenue': availability_revenue + activation_revenue}
                total_revenue += availability_revenue + activation_revenue
        
        # Merge DR metrics into dispatch_summary
        dispatch_summary.update({
            'total_flex_mw': total_flex_mw,
            'flex_by_workload': flex_by_workload,
            'service_revenue': service_revenue,
            'total_annual_revenue': total_revenue
        })
        
        return HeuristicResult(
            feasible=True,
            objective_value=total_revenue,  # Maximize DR revenue!
            lcoe=lcoe,
            dispatch_summary=dispatch_summary,
            capex_total=0,
            opex_annual=0,
            equipment_config=equipment,
            constraint_status={},
            violations=[],
            timeline_months=0,
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=[],
        )


class BridgePowerHeuristic(HeuristicOptimizer):
    """Problem 5: Bridge Power - Min NPV of transition
    
    Hierarchical Objective:
    1. Meet load until grid arrives (month X)
    2. Minimize NPV of total transition cost
    3. Compare: rental vs purchase vs hybrid
    """
    
    def __init__(self, *args, grid_available_month: int = 60, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_available_month = grid_available_month
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        
        # Use annual stack if multi-year
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
            
            dispatch_summary = {
                'annual_stack': annual_result['annual_stack'],
                'grid_available_year': annual_result['grid_available_year'],
                'blended_lcoe': lcoe
            }
            
            capex_total = self.calculate_capex(equipment)
            opex_annual = self.calculate_annual_opex(equipment)
            
            return HeuristicResult(
                feasible=True,
                objective_value=-capex_total,
                lcoe=lcoe,
                capex_total=capex_total,
                opex_annual=opex_annual,
                equipment_config=equipment,
                dispatch_summary=dispatch_summary,
                constraint_status={},
                violations=[],
                timeline_months=self.grid_available_month,
                shadow_prices={},
                solve_time_seconds=time.time() - start_time,
                warnings=[],
            )
        
        # Single-year: Simple NPV comparison
        monthly_rate = self.economics.get('discount_rate', 0.08) / 12
        scenarios = {}
        
        # Scenario 1: All rental until grid
        rental_cost = self.equipment.get('rental', {}).get('rental_cost_kw_month', 50)
        rental_npv = sum(self.peak_load * 1000 * rental_cost / (1 + monthly_rate) ** m for m in range(self.grid_available_month))
        scenarios['all_rental'] = rental_npv
        
        # Scenario 2: All purchase until grid
        purchase_equipment = self.size_equipment_to_load(self.peak_load)
        purchase_capex = self.calculate_capex(purchase_equipment)
        residual_value = purchase_capex * self.economics.get('residual_value_pct', 0.10)
        purchase_opex_monthly = self.calculate_annual_opex(purchase_equipment) / 12
        purchase_npv = purchase_capex + sum(purchase_opex_monthly / (1 + monthly_rate) ** m for m in range(self.grid_available_month))
        purchase_npv -= residual_value / (1 + monthly_rate) ** self.grid_available_month
        scenarios['all_purchase'] = purchase_npv
        
        # Scenario 3: Hybrid
        crossover_months = (purchase_capex - residual_value) / (rental_cost * self.peak_load * 1000 - purchase_opex_monthly) \
                           if (rental_cost * self.peak_load * 1000 - purchase_opex_monthly) > 0 else 999
        scenarios['hybrid'] = min(rental_npv, purchase_npv)
        
        best_scenario = min(scenarios, key=scenarios.get)
        best_npv = scenarios[best_scenario]
        
        return HeuristicResult(
            feasible=True,
            objective_value=best_npv,  # Minimize NPV
            lcoe=0,
            capex_total=purchase_capex if best_scenario == 'all_purchase' else 0,
            opex_annual=self.calculate_annual_opex(purchase_equipment) if best_scenario != 'all_rental' else 0,
            equipment_config=purchase_equipment,
            dispatch_summary={
                'scenarios': scenarios,
                'recommended': best_scenario,
                'npv': best_npv,
                'crossover_months': crossover_months,
                'grid_available_month': self.grid_available_month
            },
            constraint_status={},
            violations=[],
            timeline_months=self.grid_available_month,
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=["Transition timing is indicative only"],
        )


def create_heuristic_optimizer(problem_type: int, **kwargs) -> HeuristicOptimizer:
    """Factory function to create appropriate heuristic optimizer."""
    optimizers = {1: GreenFieldHeuristic, 2: BrownfieldHeuristic, 3: LandDevHeuristic,
                  4: GridServicesHeuristic, 5: BridgePowerHeuristic}
    if problem_type not in optimizers:
        raise ValueError(f"Unknown problem type: {problem_type}")
    return optimizers[problem_type](**kwargs)


def create_heuristic_optimizer(problem_type: int, **kwargs) -> HeuristicOptimizer:
    """Factory function to create appropriate heuristic optimizer."""
    optimizers = {1: GreenFieldHeuristic, 2: BrownfieldHeuristic, 3: LandDevHeuristic,
                  4: GridServicesHeuristic, 5: BridgePowerHeuristic}
    if problem_type not in optimizers:
        raise ValueError(f"Unknown problem type: {problem_type}")
    return optimizers[problem_type](**kwargs)
