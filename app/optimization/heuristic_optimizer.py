"""
Heuristic Optimization Engine (Phase 1 / Tier 1)
Fast screening optimization using deterministic rules and merit-order dispatch

This provides quick (~30-60 second) indicative results for all 5 problem statements.
Results are labeled as "Indicative Only" with ±50% accuracy (Class 5 estimate).

Phase 2 (MILP with HiGHS) will be added later for production-grade optimization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    EQUIPMENT_DEFAULTS, CONSTRAINT_DEFAULTS, ECONOMIC_DEFAULTS,
    WORKLOAD_FLEXIBILITY, DR_SERVICES, VOLL_PENALTY, K_DEG
)


@dataclass
class HeuristicResult:
    """Container for heuristic optimization results"""
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
    shadow_prices: Dict  # Indicative only for heuristic
    solve_time_seconds: float
    warnings: List[str] = field(default_factory=list)


class HeuristicOptimizer:
    """
    Base class for heuristic optimization across all problem types.
    
    Uses deterministic rules:
    1. Size equipment to meet peak load with N-1 redundancy
    2. Apply constraint limits (NOx, gas, land)
    3. Run merit-order dispatch simulation
    4. Calculate economics (LCOE, CAPEX, OPEX)
    """
    
    def __init__(
        self,
        site: Dict,
        load_trajectory: Dict[int, float],  # {year: load_mw}
        constraints: Dict,
        equipment_options: Dict = None,
        economic_params: Dict = None,
    ):
        self.site = site
        self.load_trajectory = load_trajectory
        self.constraints = {**CONSTRAINT_DEFAULTS, **constraints}
        self.equipment = equipment_options or EQUIPMENT_DEFAULTS
        self.economics = economic_params or ECONOMIC_DEFAULTS
        
        # Derived parameters
        self.peak_load = max(load_trajectory.values())
        self.years = sorted(load_trajectory.keys())
        self.start_year = min(self.years)
        self.end_year = max(self.years)
        
    def size_equipment_to_load(
        self,
        target_mw: float,
        require_n1: bool = True,
        max_recip_pct: float = 1.0,
        max_turbine_pct: float = 1.0,
        include_solar: bool = True,
        include_bess: bool = True,
    ) -> Dict:
        """
        Size equipment to meet target load with constraints.
        
        Uses simple heuristic:
        1. Calculate required firm capacity (with N-1 if needed)
        2. Allocate to recips first (faster deployment, lower heat rate)
        3. Fill remaining with turbines
        4. Add solar for energy savings
        5. Add BESS for load shaping / solar firming
        """
        
        # N-1 sizing factor
        n1_factor = 1.0
        if require_n1:
            # Need enough capacity that loss of largest unit still covers load
            # Assume largest unit is max(recip_mw, turbine_mw)
            largest_unit = max(
                self.equipment['recip']['capacity_mw'],
                self.equipment['turbine']['capacity_mw']
            )
            n1_factor = (target_mw + largest_unit) / target_mw if target_mw > 0 else 1.0
        
        required_firm_mw = target_mw * n1_factor
        
        # Check NOx constraint - limits recip capacity
        nox_limit = self.constraints.get('nox_tpy_annual', 100)
        recip_nox_rate = self.equipment['recip']['nox_lb_mwh'] / 2000  # tons/MWh
        turbine_nox_rate = self.equipment['turbine']['nox_lb_mwh'] / 2000
        
        # Assume 70% capacity factor for baseload operation
        cf = 0.70
        hours = 8760
        
        # Max recip capacity from NOx (very rough heuristic)
        # NOx_annual = capacity * cf * hours * nox_rate
        max_recip_from_nox = nox_limit / (cf * hours * recip_nox_rate) if recip_nox_rate > 0 else 9999
        
        # Check land constraint
        land_limit = self.constraints.get('land_area_acres', 500)
        
        # Start allocation
        recip_mw = 0
        turbine_mw = 0
        solar_mw = 0
        bess_mwh = 0
        bess_mw = 0
        
        # Allocate recips (up to NOx and percentage limits)
        recip_unit_mw = self.equipment['recip']['capacity_mw']
        max_recip_mw = min(
            required_firm_mw * max_recip_pct,
            max_recip_from_nox * 0.9,  # Leave some NOx headroom
        )
        
        n_recips = int(max_recip_mw / recip_unit_mw)
        recip_mw = n_recips * recip_unit_mw
        
        # Remaining capacity from turbines
        remaining_mw = required_firm_mw - recip_mw
        if remaining_mw > 0 and max_turbine_pct > 0:
            turbine_unit_mw = self.equipment['turbine']['capacity_mw']
            n_turbines = int(np.ceil(remaining_mw / turbine_unit_mw))
            turbine_mw = n_turbines * turbine_unit_mw
        
        # Check land for thermal generation
        land_used_thermal = (
            recip_mw * self.equipment['recip']['land_acres_per_mw'] +
            turbine_mw * self.equipment['turbine']['land_acres_per_mw']
        )
        
        land_remaining = land_limit - land_used_thermal
        
        # Add solar if land available and enabled
        if include_solar and land_remaining > 0:
            solar_land_rate = self.equipment['solar']['land_acres_per_mw']
            max_solar_mw = land_remaining / solar_land_rate
            # Size solar to ~25% of peak (common heuristic)
            solar_mw = min(max_solar_mw, target_mw * 0.25)
            solar_mw = max(0, solar_mw)
        
        # Add BESS if enabled
        if include_bess:
            # Size BESS for 2-4 hours of solar firming
            bess_duration = 4.0
            if solar_mw > 0:
                bess_mw = solar_mw * 0.5  # 50% of solar for firming
            else:
                bess_mw = target_mw * 0.10  # 10% of load for grid services
            
            bess_mwh = bess_mw * bess_duration
        
        return {
            'recip_mw': recip_mw,
            'n_recips': n_recips,
            'turbine_mw': turbine_mw,
            'n_turbines': int(turbine_mw / self.equipment['turbine']['capacity_mw']) if turbine_mw > 0 else 0,
            'solar_mw': solar_mw,
            'bess_mw': bess_mw,
            'bess_mwh': bess_mwh,
            'total_firm_mw': recip_mw + turbine_mw,
            'land_used_acres': land_used_thermal + solar_mw * self.equipment['solar']['land_acres_per_mw'],
        }
    
    def calculate_capex(self, equipment: Dict) -> float:
        """Calculate total CAPEX for equipment configuration"""
        
        itc_rate = self.economics.get('itc_rate', 0.30)
        
        capex = 0
        
        # Recips
        if equipment.get('recip_mw', 0) > 0:
            capex += equipment['recip_mw'] * 1000 * self.equipment['recip']['capex_per_kw']
        
        # Turbines
        if equipment.get('turbine_mw', 0) > 0:
            capex += equipment['turbine_mw'] * 1000 * self.equipment['turbine']['capex_per_kw']
        
        # Solar (with ITC)
        if equipment.get('solar_mw', 0) > 0:
            solar_capex = equipment['solar_mw'] * 1000 * 1000 * self.equipment['solar']['capex_per_w_dc']
            capex += solar_capex * (1 - itc_rate)
        
        # BESS (with ITC)
        if equipment.get('bess_mwh', 0) > 0:
            bess_capex = equipment['bess_mwh'] * 1000 * self.equipment['bess']['capex_per_kwh']
            capex += bess_capex * (1 - itc_rate)
        
        return capex
    
    def calculate_annual_opex(self, equipment: Dict, capacity_factor: float = 0.70) -> float:
        """Calculate annual operating costs"""
        
        fuel_price = self.economics.get('fuel_price_mmbtu', 3.50)
        hours = 8760
        
        opex = 0
        
        # Recip OPEX
        if equipment.get('recip_mw', 0) > 0:
            recip_gen = equipment['recip_mw'] * capacity_factor * hours
            # Fuel cost
            heat_rate = self.equipment['recip']['heat_rate_btu_kwh'] / 1000  # MMBtu/MWh
            fuel_cost = recip_gen * heat_rate * fuel_price
            # VOM
            vom = recip_gen * self.equipment['recip']['vom_per_mwh']
            # FOM
            fom = equipment['recip_mw'] * 1000 * self.equipment['recip']['fom_per_kw_yr']
            
            opex += fuel_cost + vom + fom
        
        # Turbine OPEX
        if equipment.get('turbine_mw', 0) > 0:
            turbine_gen = equipment['turbine_mw'] * capacity_factor * 0.5 * hours  # Lower CF for peaking
            heat_rate = self.equipment['turbine']['heat_rate_btu_kwh'] / 1000
            fuel_cost = turbine_gen * heat_rate * fuel_price
            vom = turbine_gen * self.equipment['turbine']['vom_per_mwh']
            fom = equipment['turbine_mw'] * 1000 * self.equipment['turbine']['fom_per_kw_yr']
            
            opex += fuel_cost + vom + fom
        
        # Solar OPEX (minimal)
        if equipment.get('solar_mw', 0) > 0:
            solar_gen = equipment['solar_mw'] * self.equipment['solar']['capacity_factor'] * hours
            opex += solar_gen * 2.0  # ~$2/MWh O&M
        
        # BESS OPEX
        if equipment.get('bess_mwh', 0) > 0:
            # Assume 1 cycle per day
            cycles = 365
            throughput = equipment['bess_mwh'] * cycles * 1000  # kWh
            degradation_cost = throughput * K_DEG
            opex += degradation_cost
        
        return opex
    
    def calculate_lcoe(self, equipment: Dict, annual_generation_mwh: float) -> float:
        """Calculate Levelized Cost of Energy"""
        
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        
        crf = self.economics.get('crf_20yr_8pct', 0.1019)
        project_life = self.economics.get('project_life_years', 20)
        discount_rate = self.economics.get('discount_rate', 0.08)
        
        # NPV of OPEX over project life
        npv_opex = opex * sum(1 / (1 + discount_rate) ** y for y in range(1, project_life + 1))
        
        # Total NPV cost
        total_cost = capex + npv_opex
        
        # NPV of generation
        npv_generation = annual_generation_mwh * sum(1 / (1 + discount_rate) ** y for y in range(1, project_life + 1))
        
        lcoe = total_cost / npv_generation if npv_generation > 0 else 999
        
        return lcoe
    
    def check_constraints(self, equipment: Dict) -> Tuple[Dict, List[str]]:
        """Check all constraints and return status + violations"""
        
        status = {}
        violations = []
        
        # NOx constraint
        recip_nox = equipment.get('recip_mw', 0) * 0.70 * 8760 * self.equipment['recip']['nox_lb_mwh'] / 2000
        turbine_nox = equipment.get('turbine_mw', 0) * 0.35 * 8760 * self.equipment['turbine']['nox_lb_mwh'] / 2000
        total_nox = recip_nox + turbine_nox
        nox_limit = self.constraints.get('nox_tpy_annual', 100)
        
        status['nox_tpy'] = {'value': total_nox, 'limit': nox_limit, 'binding': total_nox >= nox_limit * 0.95}
        if total_nox > nox_limit:
            violations.append(f"NOx: {total_nox:.1f} tpy exceeds limit of {nox_limit} tpy")
        
        # Gas constraint
        recip_gas = equipment.get('recip_mw', 0) * (self.equipment['recip']['heat_rate_btu_kwh'] / 1000) / 1.037 * 24
        turbine_gas = equipment.get('turbine_mw', 0) * (self.equipment['turbine']['heat_rate_btu_kwh'] / 1000) / 1.037 * 24
        total_gas = recip_gas + turbine_gas
        gas_limit = self.constraints.get('gas_supply_mcf_day', 50000)
        
        status['gas_mcf_day'] = {'value': total_gas, 'limit': gas_limit, 'binding': total_gas >= gas_limit * 0.95}
        if total_gas > gas_limit:
            violations.append(f"Gas: {total_gas:.0f} MCF/day exceeds limit of {gas_limit} MCF/day")
        
        # Land constraint
        land_used = equipment.get('land_used_acres', 0)
        land_limit = self.constraints.get('land_area_acres', 500)
        
        status['land_acres'] = {'value': land_used, 'limit': land_limit, 'binding': land_used >= land_limit * 0.95}
        if land_used > land_limit:
            violations.append(f"Land: {land_used:.1f} acres exceeds limit of {land_limit} acres")
        
        # N-1 check
        if self.constraints.get('n_minus_1_required', True):
            total_capacity = equipment.get('total_firm_mw', 0)
            largest_unit = max(
                self.equipment['recip']['capacity_mw'] if equipment.get('n_recips', 0) > 0 else 0,
                self.equipment['turbine']['capacity_mw'] if equipment.get('n_turbines', 0) > 0 else 0
            )
            n1_capacity = total_capacity - largest_unit
            
            status['n_minus_1'] = {'capacity': n1_capacity, 'required': self.peak_load, 'met': n1_capacity >= self.peak_load}
            if n1_capacity < self.peak_load:
                violations.append(f"N-1: {n1_capacity:.1f} MW capacity after loss of largest unit < {self.peak_load:.1f} MW load")
        
        return status, violations
    
    def calculate_timeline(self, equipment: Dict) -> int:
        """Calculate deployment timeline in months"""
        
        timelines = []
        
        if equipment.get('recip_mw', 0) > 0:
            timelines.append(self.equipment['recip']['lead_time_months'])
        
        if equipment.get('turbine_mw', 0) > 0:
            timelines.append(self.equipment['turbine']['lead_time_months'])
        
        if equipment.get('solar_mw', 0) > 0:
            timelines.append(self.equipment['solar']['lead_time_months'])
        
        if equipment.get('bess_mwh', 0) > 0:
            timelines.append(self.equipment['bess']['lead_time_months'])
        
        # Critical path is longest lead time
        return max(timelines) if timelines else 0
    
    def generate_8760_dispatch(self, equipment: Dict, load_profile: np.ndarray = None) -> pd.DataFrame:
        """Generate hourly dispatch schedule for full year"""
        
        if load_profile is None:
            # Generate synthetic load profile
            peak = self.peak_load
            load_factor = 0.70
            load_profile = self._generate_synthetic_load(peak, load_factor)
        
        hours = len(load_profile)
        
        # Initialize dispatch arrays
        dispatch = {
            'hour': np.arange(hours),
            'load_mw': load_profile,
            'recip_mw': np.zeros(hours),
            'turbine_mw': np.zeros(hours),
            'solar_mw': np.zeros(hours),
            'bess_charge_mw': np.zeros(hours),
            'bess_discharge_mw': np.zeros(hours),
            'bess_soc_mwh': np.zeros(hours),
            'grid_mw': np.zeros(hours),
            'unserved_mw': np.zeros(hours),
        }
        
        # Solar generation profile (simplified)
        solar_cap = equipment.get('solar_mw', 0)
        if solar_cap > 0:
            solar_cf = self._generate_solar_profile(hours)
            dispatch['solar_mw'] = solar_cap * solar_cf
        
        # BESS state
        bess_mwh = equipment.get('bess_mwh', 0)
        bess_mw = equipment.get('bess_mw', 0)
        soc = bess_mwh * 0.5  # Start at 50% SOC
        
        # Merit-order dispatch
        recip_cap = equipment.get('recip_mw', 0)
        turbine_cap = equipment.get('turbine_mw', 0)
        
        for h in range(hours):
            load = load_profile[h]
            solar = dispatch['solar_mw'][h]
            
            # Net load after solar
            net_load = load - solar
            
            # Dispatch recips first (lower VOM, faster ramp)
            if net_load > 0 and recip_cap > 0:
                recip_dispatch = min(net_load, recip_cap)
                dispatch['recip_mw'][h] = recip_dispatch
                net_load -= recip_dispatch
            
            # Then turbines
            if net_load > 0 and turbine_cap > 0:
                turbine_dispatch = min(net_load, turbine_cap)
                dispatch['turbine_mw'][h] = turbine_dispatch
                net_load -= turbine_dispatch
            
            # BESS discharge if still need power
            if net_load > 0 and soc > 0 and bess_mw > 0:
                discharge = min(net_load, bess_mw, soc)
                dispatch['bess_discharge_mw'][h] = discharge
                soc -= discharge
                net_load -= discharge
            
            # BESS charge if excess solar
            excess_solar = solar - load
            if excess_solar > 0 and soc < bess_mwh and bess_mw > 0:
                charge = min(excess_solar, bess_mw, bess_mwh - soc)
                dispatch['bess_charge_mw'][h] = charge
                soc += charge * 0.90  # Round-trip efficiency
            
            # Track SOC
            dispatch['bess_soc_mwh'][h] = soc
            
            # Unserved energy
            if net_load > 0:
                dispatch['unserved_mw'][h] = net_load
        
        return pd.DataFrame(dispatch)
    
    def _generate_synthetic_load(self, peak_mw: float, load_factor: float) -> np.ndarray:
        """Generate synthetic 8760 load profile"""
        hours = 8760
        
        # Base load
        base = peak_mw * load_factor * 0.8
        
        # Daily pattern (peaks during business hours)
        daily_pattern = np.tile(
            np.array([0.85, 0.82, 0.80, 0.78, 0.80, 0.85, 0.92, 0.98, 
                      1.0, 1.0, 0.98, 0.96, 0.94, 0.96, 0.98, 1.0,
                      0.98, 0.95, 0.92, 0.90, 0.88, 0.86, 0.85, 0.84]),
            365
        )[:hours]
        
        # Seasonal variation (higher in summer for cooling)
        day_of_year = np.arange(hours) // 24
        seasonal = 0.95 + 0.10 * np.sin(2 * np.pi * (day_of_year - 172) / 365)
        
        # Random variation (AI workloads)
        np.random.seed(42)
        random_var = 1 + 0.05 * np.random.randn(hours)
        
        load = base + (peak_mw - base) * daily_pattern * seasonal * random_var
        load = np.clip(load, peak_mw * 0.3, peak_mw)
        
        return load
    
    def _generate_solar_profile(self, hours: int = 8760) -> np.ndarray:
        """Generate synthetic solar capacity factor profile"""
        
        cf = np.zeros(hours)
        
        for h in range(hours):
            day = h // 24
            hour_of_day = h % 24
            
            # Only generate during daylight (6 AM - 6 PM simplified)
            if 6 <= hour_of_day <= 18:
                # Bell curve centered at noon
                hour_factor = np.exp(-((hour_of_day - 12) ** 2) / 8)
                
                # Seasonal variation
                day_of_year = day % 365
                seasonal = 0.7 + 0.3 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
                
                cf[h] = hour_factor * seasonal * 0.9  # Max ~90% of nameplate
        
        return cf


# =============================================================================
# Problem-Specific Heuristic Optimizers
# =============================================================================

class GreenFieldHeuristic(HeuristicOptimizer):
    """Problem 1: Greenfield Datacenter - Minimize LCOE"""
    
    def optimize(self) -> HeuristicResult:
        """Run heuristic optimization for greenfield problem"""
        
        import time
        start_time = time.time()
        
        # Size equipment to meet peak load
        equipment = self.size_equipment_to_load(
            target_mw=self.peak_load,
            require_n1=self.constraints.get('n_minus_1_required', True),
        )
        
        # Check constraints
        constraint_status, violations = self.check_constraints(equipment)
        feasible = len(violations) == 0
        
        # Calculate economics
        annual_gen = self.peak_load * 0.70 * 8760  # 70% CF
        lcoe = self.calculate_lcoe(equipment, annual_gen)
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        
        # Timeline
        timeline = self.calculate_timeline(equipment)
        
        # Dispatch summary
        dispatch_df = self.generate_8760_dispatch(equipment)
        dispatch_summary = {
            'total_generation_gwh': dispatch_df[['recip_mw', 'turbine_mw', 'solar_mw', 'bess_discharge_mw']].sum().sum() / 1000,
            'total_load_gwh': dispatch_df['load_mw'].sum() / 1000,
            'unserved_mwh': dispatch_df['unserved_mw'].sum(),
            'solar_penetration_pct': dispatch_df['solar_mw'].sum() / dispatch_df['load_mw'].sum() * 100 if dispatch_df['load_mw'].sum() > 0 else 0,
            'recip_cf': dispatch_df['recip_mw'].mean() / equipment['recip_mw'] if equipment.get('recip_mw', 0) > 0 else 0,
        }
        
        # Indicative shadow prices (heuristic approximation)
        # Shadow price = marginal value of relaxing constraint by 1 unit
        shadow_prices = {}
        
        # NOx shadow price ($/ton of additional NOx allowance)
        if constraint_status.get('nox_tpy', {}).get('binding', False):
            # Rough estimate: cost of reducing recip capacity by one less unit
            # Each recip emits ~7-10 tpy NOx at 70% CF
            # Replacing 1 recip (18MW) with solar+BESS costs ~$50M
            # So ~$50M / 8 tpy = ~$6M/ton avoided
            # Shadow price for allowing 1 more ton = savings from not avoiding it
            recip_nox_per_unit = (18 * 0.70 * 8760 * self.equipment['recip']['nox_lb_mwh'] / 2000)
            if recip_nox_per_unit > 0:
                cost_per_recip = 18000 * self.equipment['recip']['capex_per_kw']
                shadow_prices['nox'] = cost_per_recip / recip_nox_per_unit
            else:
                shadow_prices['nox'] = 5000000  # $5M/ton
        
        # Gas shadow price ($/MCF of additional daily capacity)
        if constraint_status.get('gas_mcf_day', {}).get('binding', False):
            # Additional gas allows more thermal generation
            # 1 MCF/day over a year = 365 MCF = ~377 MMBtu
            # At 8200 Btu/kWh, that's ~46 MWh annual generation
            # Marginal value = LCOE * generation = ~$50/MWh * 46 MWh = $2,300/year NPV
            # NPV over 20 years at 8% = $2,300 * 10 = ~$23,000
            mcf_per_day = 1.0
            annual_mcf = mcf_per_day * 365
            btu_value = annual_mcf * 1037  # MMBtu
            gen_value = btu_value / (self.equipment['recip']['heat_rate_btu_kwh'] / 1000)  # MWh
            annual_value = gen_value * (lcoe - opex / annual_gen if annual_gen > 0 else 50)
            npv_factor = sum(1 / (1.08 ** y) for y in range(1, 21))  # ~10
            shadow_prices['gas'] = annual_value * npv_factor
        
        # Land shadow price ($/acre of additional land)
        if constraint_status.get('land_acres', {}).get('binding', False):
            # Additional acre allows ~0.2 MW solar (at 5 acres/MW)
            # Solar value = CAPEX + energy value
            solar_per_acre = 1.0 / self.equipment['solar']['land_acres_per_mw']
            solar_capex = solar_per_acre * 1000 * self.equipment['solar']['capex_per_w_dc'] * (1 - self.economics.get('itc_rate', 0.3))
            # Annual generation value
            annual_solar_gen = solar_per_acre * self.equipment['solar']['capacity_factor'] * 8760
            annual_energy_value = annual_solar_gen * 50  # $/MWh avoided cost
            npv_factor = sum(1 / (1.08 ** y) for y in range(1, 21))
            shadow_prices['land'] = solar_capex + annual_energy_value * npv_factor
        
        solve_time = time.time() - start_time
        
        return HeuristicResult(
            feasible=feasible,
            objective_value=lcoe,
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary=dispatch_summary,
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=timeline,
            shadow_prices=shadow_prices,
            solve_time_seconds=solve_time,
            warnings=["Phase 1 Heuristic: Results are indicative only (±50% accuracy)"],
        )


class BrownfieldHeuristic(HeuristicOptimizer):
    """Problem 2: Brownfield Expansion - Maximize Load within LCOE ceiling"""
    
    def __init__(self, *args, lcoe_ceiling: float = 80.0, existing_load_mw: float = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.lcoe_ceiling = lcoe_ceiling
        self.existing_load_mw = existing_load_mw
    
    def optimize(self) -> HeuristicResult:
        """Find maximum additional load that can be served within LCOE ceiling"""
        
        import time
        start_time = time.time()
        
        # Binary search for maximum load
        low = 0
        high = self.peak_load * 2  # Search up to 2x target
        best_load = 0
        best_equipment = None
        
        while high - low > 1:
            mid = (low + high) / 2
            
            equipment = self.size_equipment_to_load(mid)
            _, violations = self.check_constraints(equipment)
            
            if len(violations) == 0:
                annual_gen = mid * 0.70 * 8760
                lcoe = self.calculate_lcoe(equipment, annual_gen)
                
                if lcoe <= self.lcoe_ceiling:
                    best_load = mid
                    best_equipment = equipment
                    low = mid
                else:
                    high = mid
            else:
                high = mid
        
        if best_equipment is None:
            best_equipment = self.size_equipment_to_load(self.peak_load)
        
        constraint_status, violations = self.check_constraints(best_equipment)
        feasible = len(violations) == 0
        
        annual_gen = best_load * 0.70 * 8760
        lcoe = self.calculate_lcoe(best_equipment, annual_gen)
        capex = self.calculate_capex(best_equipment)
        opex = self.calculate_annual_opex(best_equipment)
        timeline = self.calculate_timeline(best_equipment)
        
        dispatch_df = self.generate_8760_dispatch(best_equipment)
        dispatch_summary = {
            'max_additional_load_mw': best_load - self.existing_load_mw,
            'total_load_mw': best_load,
            'lcoe_achieved': lcoe,
            'total_generation_gwh': dispatch_df[['recip_mw', 'turbine_mw', 'solar_mw']].sum().sum() / 1000,
        }
        
        solve_time = time.time() - start_time
        
        return HeuristicResult(
            feasible=feasible,
            objective_value=best_load,
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=best_equipment,
            dispatch_summary=dispatch_summary,
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=timeline,
            shadow_prices={},
            solve_time_seconds=solve_time,
            warnings=["Phase 1 Heuristic: Results are indicative only (±50% accuracy)"],
        )


class LandDevHeuristic(HeuristicOptimizer):
    """Problem 3: Land Development - Maximize firm power by flexibility scenario"""
    
    def __init__(self, *args, flexibility_scenarios: List[float] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.flexibility_scenarios = flexibility_scenarios or [0.0, 0.15, 0.30, 0.50]
    
    def optimize(self) -> Dict[float, HeuristicResult]:
        """Run optimization for each flexibility scenario"""
        
        results = {}
        
        for flex in self.flexibility_scenarios:
            # With flexibility, effective load can be reduced during peak
            effective_peak = self.peak_load * (1 - flex)
            
            equipment = self.size_equipment_to_load(effective_peak)
            constraint_status, violations = self.check_constraints(equipment)
            
            # The flex factor allows us to serve more total load
            max_load_with_flex = equipment['total_firm_mw'] / (1 - flex) if flex < 1 else equipment['total_firm_mw']
            
            annual_gen = max_load_with_flex * 0.70 * 8760
            lcoe = self.calculate_lcoe(equipment, annual_gen)
            capex = self.calculate_capex(equipment)
            opex = self.calculate_annual_opex(equipment)
            timeline = self.calculate_timeline(equipment)
            
            results[flex] = HeuristicResult(
                feasible=len(violations) == 0,
                objective_value=max_load_with_flex,
                lcoe=lcoe,
                capex_total=capex,
                opex_annual=opex,
                equipment_config=equipment,
                dispatch_summary={'max_load_mw': max_load_with_flex, 'flexibility_pct': flex * 100},
                constraint_status=constraint_status,
                violations=violations,
                timeline_months=timeline,
                shadow_prices={},
                solve_time_seconds=0,
                warnings=["Phase 1 Heuristic: Results are indicative only"],
            )
        
        return results


class GridServicesHeuristic(HeuristicOptimizer):
    """Problem 4: Grid Services - Maximize DR revenue"""
    
    def __init__(self, *args, workload_mix: Dict = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.workload_mix = workload_mix or {'pre_training': 0.4, 'batch_inference': 0.4, 'real_time_inference': 0.2}
    
    def optimize(self) -> HeuristicResult:
        """Optimize DR service enrollment and revenue"""
        
        import time
        start_time = time.time()
        
        # Calculate available flexibility
        total_flex_mw = 0
        for workload, fraction in self.workload_mix.items():
            flex_params = WORKLOAD_FLEXIBILITY.get(workload, {})
            flex_pct = flex_params.get('flexibility_pct', 0)
            total_flex_mw += self.peak_load * fraction * flex_pct
        
        # Size equipment
        equipment = self.size_equipment_to_load(self.peak_load)
        
        # Calculate DR revenue potential
        dr_revenue = {}
        total_revenue = 0
        
        for service_id, service in DR_SERVICES.items():
            # Check if workload mix is compatible
            compatible = any(
                wl in service['compatible_workloads'] 
                for wl in self.workload_mix.keys()
            )
            
            if compatible and total_flex_mw > 0:
                # Simplified revenue calculation
                if 'price_per_mw_hr' in service:
                    # Assume 100 event hours per year
                    annual_revenue = service['price_per_mw_hr'] * total_flex_mw * 100
                else:
                    # Capacity payment
                    annual_revenue = service['price_per_mw_month'] * total_flex_mw * 12
                
                dr_revenue[service_id] = annual_revenue
                total_revenue += annual_revenue
        
        constraint_status, violations = self.check_constraints(equipment)
        
        annual_gen = self.peak_load * 0.70 * 8760
        lcoe = self.calculate_lcoe(equipment, annual_gen)
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        
        dispatch_summary = {
            'total_flex_mw': total_flex_mw,
            'dr_revenue_annual': total_revenue,
            'dr_revenue_per_mw': total_revenue / total_flex_mw if total_flex_mw > 0 else 0,
            'services': dr_revenue,
        }
        
        solve_time = time.time() - start_time
        
        return HeuristicResult(
            feasible=len(violations) == 0,
            objective_value=total_revenue,
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary=dispatch_summary,
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.calculate_timeline(equipment),
            shadow_prices={},
            solve_time_seconds=solve_time,
            warnings=["Phase 1 Heuristic: DR revenue estimates are indicative only"],
        )


class BridgePowerHeuristic(HeuristicOptimizer):
    """Problem 5: Bridge Power Transition - Minimize NPV of BTM-to-Grid transition"""
    
    def __init__(self, *args, grid_available_month: int = 60, horizon_months: int = 72, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_available_month = grid_available_month
        self.horizon_months = horizon_months
    
    def optimize(self) -> HeuristicResult:
        """Optimize rental vs permanent asset mix during grid transition"""
        
        import time
        start_time = time.time()
        
        discount_rate = self.economics.get('discount_rate', 0.08)
        monthly_rate = (1 + discount_rate) ** (1/12) - 1
        
        # Monthly load trajectory (interpolate from annual)
        monthly_loads = []
        for m in range(self.horizon_months):
            year = self.start_year + m // 12
            if year in self.load_trajectory:
                monthly_loads.append(self.load_trajectory[year])
            elif year < min(self.load_trajectory.keys()):
                monthly_loads.append(0)
            else:
                monthly_loads.append(self.load_trajectory[max(self.load_trajectory.keys())])
        
        # Simple heuristic: rent until grid, then transition
        rental_costs = []
        perm_capex = 0
        grid_import = []
        
        rental_cost_per_mw_month = 15000  # $/MW-month rental
        
        for m in range(self.horizon_months):
            load = monthly_loads[m]
            
            if m < self.grid_available_month:
                # Pre-grid: use rentals for gap, build permanent for base
                # Heuristic: 70% permanent, 30% rental
                perm_share = 0.70
                rental_share = 0.30
                
                rental_mw = load * rental_share
                rental_costs.append(rental_mw * rental_cost_per_mw_month)
                grid_import.append(0)
                
                if m == 0:  # Build permanent capacity at start
                    perm_equipment = self.size_equipment_to_load(load * perm_share, require_n1=False)
                    perm_capex = self.calculate_capex(perm_equipment)
            else:
                # Post-grid: use grid, phase out rentals
                rental_costs.append(0)
                grid_import.append(load)
        
        # NPV calculation
        npv_rental = sum(cost / (1 + monthly_rate) ** m for m, cost in enumerate(rental_costs))
        npv_total = perm_capex + npv_rental
        
        # Equipment config for reporting
        equipment = self.size_equipment_to_load(self.peak_load * 0.70)
        constraint_status, violations = self.check_constraints(equipment)
        
        dispatch_summary = {
            'npv_total': npv_total,
            'npv_rental': npv_rental,
            'perm_capex': perm_capex,
            'grid_month': self.grid_available_month,
            'rental_months': self.grid_available_month,
            'monthly_loads': monthly_loads,
            'rental_costs': rental_costs,
        }
        
        solve_time = time.time() - start_time
        
        return HeuristicResult(
            feasible=len(violations) == 0,
            objective_value=npv_total,
            lcoe=0,  # Not primary metric for this problem
            capex_total=perm_capex,
            opex_annual=sum(rental_costs[:12]),
            equipment_config=equipment,
            dispatch_summary=dispatch_summary,
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.grid_available_month,
            shadow_prices={},
            solve_time_seconds=solve_time,
            warnings=["Phase 1 Heuristic: Transition timing is indicative only"],
        )


# =============================================================================
# Factory Function
# =============================================================================

def create_heuristic_optimizer(problem_type: int, **kwargs) -> HeuristicOptimizer:
    """Factory function to create appropriate heuristic optimizer"""
    
    optimizers = {
        1: GreenFieldHeuristic,
        2: BrownfieldHeuristic,
        3: LandDevHeuristic,
        4: GridServicesHeuristic,
        5: BridgePowerHeuristic,
    }
    
    if problem_type not in optimizers:
        raise ValueError(f"Unknown problem type: {problem_type}")
    
    return optimizers[problem_type](**kwargs)
