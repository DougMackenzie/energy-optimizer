"""
Full Optimization Engine with Multi-Objective Optimization and Pareto Frontier Analysis
Uses scipy.optimize for constrained optimization with comprehensive constraint validation
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from typing import Dict, List, Tuple, Optional
import pandas as pd


class OptimizationEngine:
    """
    Multi-objective optimization engine for datacenter energy systems
    Uses scipy to find optimal equipment configurations
    """
    
    def __init__(self, site: Dict, constraints: Dict, scenario: Dict, equipment_data: Dict, grid_config: Dict):
        self.site = site
        self.constraints = constraints
        self.scenario = scenario
        self.equipment_data = equipment_data
        self.grid_config = grid_config
        
        # Site parameters
        self.total_load_mw = site.get('Total_Facility_MW', 200)
        self.load_factor = site.get('Load_Factor_Pct', 75) / 100
        
        # Constraint limits
        self.nox_limit_tpy = constraints.get('NOx_Limit_tpy', 100)
        self.co_limit_tpy = constraints.get('CO_Limit_tpy', 100)
        self.gas_supply_mcf_day = constraints.get('Gas_Supply_MCF_day', 100000)
        self.available_land_acres = constraints.get('Available_Land_Acres', 50)
        self.grid_available_mw = grid_config.get('grid_capacity_override') or constraints.get('Grid_Available_MW', 200)
        
        # Equipment availability
        self.recip_enabled = str(scenario.get('Recip_Engines', 'False')).lower() == 'true'
        self.turbine_enabled = str(scenario.get('Gas_Turbines', 'False')).lower() == 'true'
        self.bess_enabled = str(scenario.get('BESS', 'False')).lower() == 'true'
        self.solar_enabled = str(scenario.get('Solar_PV', 'False')).lower() == 'true'
        self.grid_enabled = str(scenario.get('Grid_Connection', 'False')).lower() == 'true'
        
        # Equipment specs
        self._load_equipment_specs()
    
    def _load_equipment_specs(self):
        """Load equipment specifications from database"""
        # Reciprocating engines - use smaller 4.7 MW unit
        recips = self.equipment_data.get('Reciprocating_Engines', [])
        self.recip_spec = next((e for e in recips if e and '34SG' in e.get('Model', '')), recips[0] if recips else None)
        
        # Gas turbines - use 35 MW unit
        turbines = self.equipment_data.get('Gas_Turbines', [])
        self.turbine_spec = next((t for t in turbines if t and 'TM2500' in t.get('Model', '')), turbines[0] if turbines else None)
        
        # BESS - Tesla Megapack
        bess_systems = self.equipment_data.get('BESS', [])
        self.bess_spec = next((b for b in bess_systems if b and 'Megapack' in b.get('Model', '')), bess_systems[0] if bess_systems else None)
        
        # Solar - regional
        solar_systems = self.equipment_data.get('Solar_PV', [])
        state = self.site.get('State', '')
        if 'Texas' in state or 'Oklahoma' in state:
            region = 'Southwest'
        elif 'Virginia' in state:
            region = 'Southeast'
        else:
            region = 'National'
        self.solar_spec = next((s for s in solar_systems if s and region in s.get('Region', '')), solar_systems[0] if solar_systems else None)
    
    def decode_solution(self, x: np.ndarray) -> Dict:
        """
        Decode optimization variable vector into equipment configuration
        
        x = [num_recip, recip_cf, num_turbine, turbine_cf, num_bess, solar_mw, grid_mw]
        """
        config = {}
        idx = 0
        
        if self.recip_enabled and self.recip_spec:
            num_recip = max(0, int(round(x[idx])))
            recip_cf = np.clip(x[idx + 1], 0.3, 0.8)
            idx += 2
            
            if num_recip > 0:
                unit_mw = self.recip_spec.get('Capacity_MW', 4.7)
                config['recip_engines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': recip_cf,
                    'heat_rate_btu_kwh': self.recip_spec.get('Heat_Rate_BTU_kWh', 7700),
                    'nox_lb_mmbtu': self.recip_spec.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': self.recip_spec.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': self.recip_spec.get('CAPEX_per_kW', 1650),
                    'vom_per_mwh': 8.5,
                    'fom_per_kw_yr': 18.5,
                    'quantity': 1
                }] * num_recip
        
        if self.turbine_enabled and self.turbine_spec:
            num_turbine = max(0, int(round(x[idx])))
            turbine_cf = np.clip(x[idx + 1], 0.1, 0.5)
            idx += 2
            
            if num_turbine > 0:
                unit_mw = self.turbine_spec.get('Capacity_MW', 35)
                config['gas_turbines'] = [{
                    'capacity_mw': unit_mw,
                    'capacity_factor': turbine_cf,
                    'heat_rate_btu_kwh': self.turbine_spec.get('Heat_Rate_BTU_kWh', 8500),
                    'nox_lb_mmbtu': self.turbine_spec.get('NOx_lb_MMBtu', 0.099),
                    'co_lb_mmbtu': self.turbine_spec.get('CO_lb_MMBtu', 0.015),
                    'capex_per_kw': self.turbine_spec.get('CAPEX_per_kW', 1300),
                    'vom_per_mwh': 6.5,
                    'fom_per_kw_yr': 12.5,
                    'quantity': 1
                }] * num_turbine
        
        if self.bess_enabled and self.bess_spec:
            num_bess = max(0, int(round(x[idx])))
            idx += 1
            
            if num_bess > 0:
                config['bess'] = [{
                    'energy_mwh': self.bess_spec.get('Energy_MWh', 3.9),
                    'power_mw': self.bess_spec.get('Power_MW', 1.9),
                    'capex_per_kwh': self.bess_spec.get('CAPEX_per_kWh', 236),
                    'vom_per_mwh': 1.5,
                    'fom_per_kw_yr': 8.0,
                    'quantity': 1
                }] * num_bess
        
        if self.solar_enabled and self.solar_spec:
            solar_mw = max(0, x[idx])
            idx += 1
            
            if solar_mw > 0:
                config['solar_mw_dc'] = solar_mw
                config['solar_capex_per_w'] = self.solar_spec.get('CAPEX_per_W_DC', 0.95)
                config['solar_cf'] = self.solar_spec.get('Capacity_Factor_Pct', 30) / 100
        
        if self.grid_enabled:
            grid_mw = max(0, x[idx])
            config['grid_import_mw'] = grid_mw
        
        return config
    
    def calculate_emissions(self, config: Dict) -> Tuple[float, float]:
        """Calculate annual NOx and CO emissions in tons/year"""
        nox_tpy = 0
        co_tpy = 0
        hours_per_year = 8760
        
        # Reciprocating engines
        if 'recip_engines' in config:
            for engine in config['recip_engines']:
                capacity_mw = engine['capacity_mw']
                cf = engine['capacity_factor']
                heat_rate = engine['heat_rate_btu_kwh']
                nox_rate = engine['nox_lb_mmbtu']
                co_rate = engine['co_lb_mmbtu']
                
                # Energy generated (MWh)
                energy_mwh = capacity_mw * cf * hours_per_year
                
                # Fuel consumption (MMBtu)
                fuel_mmbtu = energy_mwh * 1000 * heat_rate / 1e6
                
                # Emissions (lb)
                nox_lb = fuel_mmbtu * nox_rate
                co_lb = fuel_mmbtu * co_rate
                
                # Convert to tons
                nox_tpy += nox_lb / 2000
                co_tpy += co_lb / 2000
        
        # Gas turbines
        if 'gas_turbines' in config:
            for turbine in config['gas_turbines']:
                capacity_mw = turbine['capacity_mw']
                cf = turbine['capacity_factor']
                heat_rate = turbine['heat_rate_btu_kwh']
                nox_rate = turbine['nox_lb_mmbtu']
                co_rate = turbine['co_lb_mmbtu']
                
                energy_mwh = capacity_mw * cf * hours_per_year
                fuel_mmbtu = energy_mwh * 1000 * heat_rate / 1e6
                
                nox_lb = fuel_mmbtu * nox_rate
                co_lb = fuel_mmbtu * co_rate
                
                nox_tpy += nox_lb / 2000
                co_tpy += co_lb / 2000
        
        return nox_tpy, co_tpy
    
    def calculate_gas_consumption(self, config: Dict) -> float:
        """Calculate daily natural gas consumption in MCF/day"""
        mcf_per_day = 0
        hours_per_year = 8760
        
        # Reciprocating engines
        if 'recip_engines' in config:
            for engine in config['recip_engines']:
                capacity_mw = engine['capacity_mw']
                cf = engine['capacity_factor']
                heat_rate = engine['heat_rate_btu_kwh']
                
                # Average hourly energy
                avg_mwh_per_hour = capacity_mw * cf
                
                # Fuel per hour (MMBtu)
                fuel_mmbtu_per_hour = avg_mwh_per_hour * 1000 * heat_rate / 1e6
                
                # Convert to MCF/hour (1 MCF = 1.037 MMBtu)
                mcf_per_hour = fuel_mmbtu_per_hour / 1.037
                
                # Daily consumption
                mcf_per_day += mcf_per_hour * 24
        
        # Gas turbines
        if 'gas_turbines' in config:
            for turbine in config['gas_turbines']:
                capacity_mw = turbine['capacity_mw']
                cf = turbine['capacity_factor']
                heat_rate = turbine['heat_rate_btu_kwh']
                
                avg_mwh_per_hour = capacity_mw * cf
                fuel_mmbtu_per_hour = avg_mwh_per_hour * 1000 * heat_rate / 1e6
                mcf_per_hour = fuel_mmbtu_per_hour / 1.037
                
                mcf_per_day += mcf_per_hour * 24
        
        return mcf_per_day
    
    def calculate_land_use(self, config: Dict) -> float:
        """Calculate land use in acres"""
        land_acres = 0
        
        # Solar PV (4.25 acres per MW)
        if 'solar_mw_dc' in config:
            land_acres += config['solar_mw_dc'] * 4.25
        
        return land_acres
    
    def calculate_firm_capacity(self, config: Dict) -> float:
        """Calculate firm capacity with N-1 reliability (MW)"""
        firm_mw = 0
        
        # Reciprocating engines - lose largest unit
        if 'recip_engines' in config:
            recip_capacities = [e['capacity_mw'] for e in config['recip_engines']]
            if recip_capacities:
                total_recip = sum(recip_capacities)
                largest_recip = max(recip_capacities)
                firm_mw += (total_recip - largest_recip)  # N-1
        
        # Gas turbines - lose largest unit
        if 'gas_turbines' in config:
            turbine_capacities = [t['capacity_mw'] for t in config['gas_turbines']]
            if turbine_capacities:
                total_turbine = sum(turbine_capacities)
                largest_turbine = max(turbine_capacities)
                firm_mw += (total_turbine - largest_turbine)  # N-1
        
        # BESS - full capacity (can respond instantly)
        if 'bess' in config:
            bess_power = sum(b['power_mw'] for b in config['bess'])
            firm_mw += bess_power
        
        # Grid - assume reliable
        if 'grid_import_mw' in config:
            firm_mw += config['grid_import_mw']
        
        # Solar - not firm capacity (variable)
        
        return firm_mw
    
    # Constraint functions for scipy optimizer
    
    def constraint_nox_emissions(self, x: np.ndarray) -> float:
        """NOx emissions constraint (must be <= limit)"""
        config = self.decode_solution(x)
        nox_tpy, _ = self.calculate_emissions(config)
        return self.nox_limit_tpy - nox_tpy  # >= 0 means feasible
    
    def constraint_co_emissions(self, x: np.ndarray) -> float:
        """CO emissions constraint"""
        config = self.decode_solution(x)
        _, co_tpy = self.calculate_emissions(config)
        return self.co_limit_tpy - co_tpy
    
    def constraint_gas_supply(self, x: np.ndarray) -> float:
        """Natural gas supply constraint"""
        config = self.decode_solution(x)
        gas_mcf_day = self.calculate_gas_consumption(config)
        return self.gas_supply_mcf_day - gas_mcf_day
    
    def constraint_land_area(self, x: np.ndarray) -> float:
        """Land area constraint"""
        config = self.decode_solution(x)
        land_acres = self.calculate_land_use(config)
        return self.available_land_acres - land_acres
    
    def constraint_grid_capacity(self, x: np.ndarray) -> float:
        """Grid import capacity constraint"""
        config = self.decode_solution(x)
        grid_mw = config.get('grid_import_mw', 0)
        return self.grid_available_mw - grid_mw
    
    def constraint_n_minus_1_reliability(self, x: np.ndarray) -> float:
        """N-1 reliability constraint"""
        config = self.decode_solution(x)
        firm_capacity = self.calculate_firm_capacity(config)
        required_capacity = self.total_load_mw
        return firm_capacity - required_capacity
    
    def constraint_min_capacity(self, x: np.ndarray) -> float:
        """Minimum total capacity constraint"""
        config = self.decode_solution(x)
        
        total_capacity = 0
        if 'recip_engines' in config:
            total_capacity += sum(e['capacity_mw'] for e in config['recip_engines'])
        if 'gas_turbines' in config:
            total_capacity += sum(t['capacity_mw'] for t in config['gas_turbines'])
        if 'bess' in config:
            total_capacity += sum(b['power_mw'] for b in config['bess'])
        if 'solar_mw_dc' in config:
            total_capacity += config['solar_mw_dc'] * 0.3  # Derate solar
        if 'grid_import_mw' in config:
            total_capacity += config['grid_import_mw']
        
        return total_capacity - self.total_load_mw * 0.8  # At least 80% of load


# Continued in next file segment...

    # Objective functions
    
    def objective_lcoe(self, x: np.ndarray) -> float:
        """Calculate LCOE (Levelized Cost of Energy) in $/MWh"""
        config = self.decode_solution(x)
        
        # Calculate CAPEX
        total_capex = 0
        
        if 'recip_engines' in config:
            for engine in config['recip_engines']:
                total_capex += engine['capacity_mw'] * 1000 * engine['capex_per_kw']
        
        if 'gas_turbines' in config:
            for turbine in config['gas_turbines']:
                total_capex += turbine['capacity_mw'] * 1000 * turbine['capex_per_kw']
        
        if 'bess' in config:
            for bess in config['bess']:
                # Apply 30% ITC for BESS (Inflation Reduction Act)
                total_capex += bess['energy_mwh'] * 1000 * bess['capex_per_kwh'] * 0.70
        
        if 'solar_mw_dc' in config:
            # Apply 30% ITC for Solar (Inflation Reduction Act)
            total_capex += config['solar_mw_dc'] * 1e6 * config['solar_capex_per_w'] * 0.70
        
        # Calculate annual O&M and fuel costs
        annual_opex = 0
        annual_fuel_cost = 0
        
        hours_per_year = 8760
        ng_price_mmbtu = 4.0  # $/MMBtu
        grid_price_mwh = 45.0  # $/MWh
        
        if 'recip_engines' in config:
            for engine in config['recip_engines']:
                capacity_mw = engine['capacity_mw']
                cf = engine['capacity_factor']
                energy_mwh = capacity_mw * cf * hours_per_year
                
                # O&M
                annual_opex += capacity_mw * 1000 * engine['fom_per_kw_yr']
                annual_opex += energy_mwh * engine['vom_per_mwh']
                
                # Fuel
                fuel_mmbtu = energy_mwh * 1000 * engine['heat_rate_btu_kwh'] / 1e6
                annual_fuel_cost += fuel_mmbtu * ng_price_mmbtu
        
        if 'gas_turbines' in config:
            for turbine in config['gas_turbines']:
                capacity_mw = turbine['capacity_mw']
                cf = turbine['capacity_factor']
                energy_mwh = capacity_mw * cf * hours_per_year
                
                annual_opex += capacity_mw * 1000 * turbine['fom_per_kw_yr']
                annual_opex += energy_mwh * turbine['vom_per_mwh']
                
                fuel_mmbtu = energy_mwh * 1000 * turbine['heat_rate_btu_kwh'] / 1e6
                annual_fuel_cost += fuel_mmbtu * ng_price_mmbtu
        
        if 'bess' in config:
            for bess in config['bess']:
                power_mw = bess['power_mw']
                annual_opex += power_mw * 1000 * bess['fom_per_kw_yr']
        
        if 'solar_mw_dc' in config:
            solar_mw = config['solar_mw_dc']
            annual_opex += solar_mw * 1000 * 15  # $15/kW-yr
        
        if 'grid_import_mw' in config:
            grid_energy =  config['grid_import_mw'] * self.load_factor * hours_per_year
            annual_fuel_cost += grid_energy * grid_price_mwh
        
        # Annual generation
        total_generation = self.total_load_mw * self.load_factor * hours_per_year
        
        # LCOE calculation (simplified NPV)
        project_life = 20
        discount_rate = 0.08
        
        # Annualized CAPEX
        crf = (discount_rate * (1 + discount_rate)**project_life) / ((1 + discount_rate)**project_life - 1)
        annualized_capex = total_capex * crf
        
        # Total annual cost
        total_annual_cost = annualized_capex + annual_opex + annual_fuel_cost
        
        # LCOE
        lcoe = total_annual_cost / total_generation if total_generation > 0 else 1e6
        
        return lcoe
    
    def objective_timeline(self, x: np.ndarray) -> float:
        """Calculate deployment timeline in months"""
        config = self.decode_solution(x)
        
        max_timeline = 0
        
        # Equipment lead times
        if 'recip_engines' in config and len(config['recip_engines']) > 0:
            max_timeline = max(max_timeline, 18)  # 18 months for recip engines
        
        if 'gas_turbines' in config and len(config['gas_turbines']) > 0:
            max_timeline = max(max_timeline, 24)  # 24 months for turbines
        
        if 'bess' in config and len(config['bess']) > 0:
            max_timeline = max(max_timeline, 12)  # 12 months for BESS
        
        if 'solar_mw_dc' in config and config['solar_mw_dc'] > 0:
            max_timeline = max(max_timeline, 15)  # 15 months for solar
        
        if 'grid_import_mw' in config and config['grid_import_mw'] > 0:
            grid_timeline = self.grid_config.get('timeline_override') or self.grid_config.get('total_timeline_months', 96)
            max_timeline = max(max_timeline, grid_timeline)
        
        return max_timeline
    
    def objective_emissions(self, x: np.ndarray) -> float:
        """Calculate total emissions (NOx + CO) in tons/year"""
        config = self.decode_solution(x)
        nox_tpy, co_tpy = self.calculate_emissions(config)
        return nox_tpy + co_tpy
    
    def combined_objective(self, x: np.ndarray, weights: Dict[str, float]) -> float:
        """
        Combined weighted objective function with constraint penalties
        weights = {'lcoe': w1, 'timeline': w2, 'emissions': w3}
        
        For differential_evolution, we add penalty terms for constraint violations
        to guide the optimizer toward feasible regions.
        """
        # Normalize objectives to similar scales
        lcoe = self.objective_lcoe(x) / 100  # Normalize to ~0-2 range
        timeline = self.objective_timeline(x) / 100  # Normalize to ~0-1 range
        emissions = self.objective_emissions(x) / 100  # Normalize to ~0-5 range
        
        total_objective = (
            weights.get('lcoe', 0.33) * lcoe +
            weights.get('timeline', 0.33) * timeline +
            weights.get('emissions', 0.34) * emissions
        )
        
        # Add penalty terms for constraint violations
        # Large penalty (1000x) to strongly discourage infeasible solutions
        penalty_multiplier = 1000
        
        # NOx constraint penalty
        nox_violation = -self.constraint_nox_emissions(x)  # Negative = violation
        if nox_violation > 0:
            total_objective += penalty_multiplier * nox_violation
        
        # CO constraint penalty
        co_violation = -self.constraint_co_emissions(x)
        if co_violation > 0:
            total_objective += penalty_multiplier * co_violation
        
        # Gas supply constraint penalty
        gas_violation = -self.constraint_gas_supply(x)
        if gas_violation > 0:
            total_objective += penalty_multiplier * gas_violation
        
        # Land area constraint penalty
        land_violation = -self.constraint_land_area(x)
        if land_violation > 0:
            total_objective += penalty_multiplier * land_violation
        
        # Grid capacity constraint penalty
        grid_violation = -self.constraint_grid_capacity(x)
        if grid_violation > 0:
            total_objective += penalty_multiplier * grid_violation
        
        # N-1 reliability constraint penalty
        reliability_violation = -self.constraint_n_minus_1_reliability(x)
        if reliability_violation > 0:
            total_objective += penalty_multiplier * reliability_violation
        
        # Min capacity constraint penalty
        min_cap_violation = -self.constraint_min_capacity(x)
        if min_cap_violation > 0:
            total_objective += penalty_multiplier * min_cap_violation
        
        return total_objective
    
    def optimize(self, objective_weights: Dict[str, float] = None) -> Tuple[Dict, bool, List[str]]:
        """
        Run optimization to find optimal equipment configuration
        
        Returns:
            (config, feasible, violations)
        """
        if objective_weights is None:
            objective_weights = {'lcoe': 0.4, 'timeline': 0.3, 'emissions': 0.3}
        
        # Define decision variables bounds
        bounds = []
        x0 = []
        
        # Recip engines: [num_units, capacity_factor]
        if self.recip_enabled and self.recip_spec:
            bounds.extend([(0, 10), (0.3, 0.8)])
            x0.extend([2, 0.5])
        
        # Gas turbines: [num_units, capacity_factor]
        if self.turbine_enabled and self.turbine_spec:
            bounds.extend([(0, 5), (0.1, 0.5)])
            x0.extend([1, 0.25])
        
        # BESS: [num_units]
        if self.bess_enabled and self.bess_spec:
            bounds.append((0, 50))
            x0.append(20)
        
        # Solar: [capacity_mw]
        if self.solar_enabled and self.solar_spec:
            max_solar = min(self.total_load_mw * 0.3, self.available_land_acres / 4.25)
            bounds.append((0, max_solar))
            x0.append(10)
        
        # Grid: [import_mw]
        if self.grid_enabled:
            bounds.append((0, self.grid_available_mw))
            x0.append(self.total_load_mw * 0.5)
        
        x0 = np.array(x0)
        
        # Define constraints for scipy
        constraints = [
            {'type': 'ineq', 'fun': self.constraint_nox_emissions},
            {'type': 'ineq', 'fun': self.constraint_co_emissions},
            {'type': 'ineq', 'fun': self.constraint_gas_supply},
            {'type': 'ineq', 'fun': self.constraint_land_area},
            {'type': 'ineq', 'fun': self.constraint_grid_capacity},
            {'type': 'ineq', 'fun': self.constraint_n_minus_1_reliability},
            {'type': 'ineq', 'fun': self.constraint_min_capacity}
        ]
        
        # Run optimization using differential_evolution (handles discrete variables better)
        # Note: differential_evolution is a global optimizer that doesn't rely on gradients
        # This makes it suitable for problems with integer variables (num_engines, num_bess, etc.)
        
        # differential_evolution requires NonlinearConstraint objects (scipy >= 1.4.0)
        # For compatibility, we'll use it without explicit constraints, then validate afterward
        result = differential_evolution(
            func=lambda x: self.combined_objective(x, objective_weights),
            bounds=bounds,
            maxiter=100,
            popsize=15,
            tol=0.01,
            atol=0,
            workers=1,
            updating='deferred',
            seed=42  # Reproducible results
        )
        
        # Decode solution
        optimal_config = self.decode_solution(result.x)
        
        # Check feasibility
        feasible = result.success
        violations = []
        
        if not feasible or not self._check_all_constraints(result.x, violations):
            feasible = False
        
        return optimal_config, feasible, violations
    
    def _check_all_constraints(self, x: np.ndarray, violations: List[str]) -> bool:
        """Check all constraints and populate violations list"""
        all_feasible = True
        
        # NOx
        if self.constraint_nox_emissions(x) < -1e-6:
            config = self.decode_solution(x)
            nox, _ = self.calculate_emissions(config)
            violations.append(f"Air Permit: NOx emissions {nox:.1f} tpy exceeds limit of {self.nox_limit_tpy} tpy")
            all_feasible = False
        
        # CO
        if self.constraint_co_emissions(x) < -1e-6:
            config = self.decode_solution(x)
            _, co = self.calculate_emissions(config)
            violations.append(f"Air Permit: CO emissions {co:.1f} tpy exceeds limit of {self.co_limit_tpy} tpy")
            all_feasible = False
        
        # Gas supply
        if self.constraint_gas_supply(x) < -1e-6:
            config = self.decode_solution(x)
            gas = self.calculate_gas_consumption(config)
            violations.append(f"Gas Supply: requires {gas:.0f} MCF/day, only {self.gas_supply_mcf_day:.0f} MCF/day available")
            all_feasible = False
        
        # Land
        if self.constraint_land_area(x) < -1e-6:
            config = self.decode_solution(x)
            land = self.calculate_land_use(config)
            violations.append(f"Land Area: Solar requires {land:.1f} acres, only {self.available_land_acres} acres available")
            all_feasible = False
        
        # Grid
        if self.constraint_grid_capacity(x) < -1e-6:
            config = self.decode_solution(x)
            grid = config.get('grid_import_mw', 0)
            violations.append(f"Grid Capacity: requires {grid:.0f} MW, only {self.grid_available_mw} MW available")
            all_feasible = False
        
        # N-1
        if self.constraint_n_minus_1_reliability(x) < -1e-6:
            config = self.decode_solution(x)
            firm = self.calculate_firm_capacity(config)
            violations.append(f"N-1 Reliability: Firm capacity {firm:.1f} MW insufficient for {self.total_load_mw} MW load")
            all_feasible = False
        
        return all_feasible


def optimize_equipment_configuration(
    scenario: Dict,
    site: Dict,
    equipment_data: Dict,
    constraints: Dict,
    grid_config: Dict,
    objectives: Dict = None
) -> Tuple[Dict, bool, List[str]]:
    """
    Main optimization function
    
    Returns:
        (equipment_config, feasible, violations)
    """
    engine = OptimizationEngine(site, constraints, scenario, equipment_data, grid_config)
    
    objective_weights = {
        'lcoe': objectives.get('lcoe', {}).get('weight', 0.4) if objectives else 0.4,
        'timeline': objectives.get('timeline', {}).get('weight', 0.3) if objectives else 0.3,
        'emissions': objectives.get('emissions', {}).get('weight', 0.3) if objectives else 0.3
    }
    
    config, feasible, violations = engine.optimize(objective_weights)
    
    return config, feasible, violations


def calculate_pareto_frontier(solutions: List[Dict]) -> List[Dict]:
    """
    Calculate Pareto frontier from list of solutions
    A solution is Pareto optimal if no other solution dominates it on ALL objectives
    
    Solutions should have format:
    {
        'lcoe': float,
        'timeline': float,
        'emissions': float,
        'config': Dict,
        'scenario': str
    }
    """
    pareto_solutions = []
    
    for i, sol_i in enumerate(solutions):
        is_dominated = False
        
        for j, sol_j in enumerate(solutions):
            if i == j:
                continue
            
            # Check if sol_j dominates sol_i (better on ALL objectives)
            if (sol_j['lcoe'] <= sol_i['lcoe'] and
                sol_j['timeline'] <= sol_i['timeline'] and
                sol_j['emissions'] <= sol_i['emissions'] and
                (sol_j['lcoe'] < sol_i['lcoe'] or 
                 sol_j['timeline'] < sol_i['timeline'] or 
                 sol_j['emissions'] < sol_i['emissions'])):
                is_dominated = True
                break
        
        if not is_dominated:
            sol_i['pareto_optimal'] = True
            pareto_solutions.append(sol_i)
        else:
            sol_i['pareto_optimal'] = False
    
    return pareto_solutions
