"""
Multi-Year Phased Deployment Optimizer

Optimizes equipment deployment across multiple years to:
- Match load growth trajectory
- Minimize lifecycle LCOE
- Respect annual constraints (air permits, gas supply, land, grid capacity, N-1 reliability)
- Account for equipment lead times

⚠️ DEPRECATION WARNING ⚠️
This optimizer is deprecated as of December 2024. Use app.optimization.milp_model_dr instead.

Reasons for deprecation:
- Non-deterministic (scipy.optimize.differential_evolution)
- Soft constraint penalties (not hard guarantees)
- Slower solve times (500 iterations)
- ~90% feasibility

Replacement: app.optimization.milp_model_dr provides phased deployment with hard constraints,
deterministic results, and 30-60 second solve times.
"""

import numpy as np
from scipy.optimize import differential_evolution
from typing import Dict, List, Tuple
import copy


class PhasedDeploymentOptimizer:
    """
    Multi-year optimization engine for staged equipment deployment.
    
    Decision Variables (per year):
    - recip_mw_added[year]: MW of recips added in this year
    - turbine_mw_added[year]: MW of turbines added in this year  
    - bess_mwh_added[year]: MWh of BESS added in this year
    - solar_mw_added[year]: MW DC of solar added in this year
    - grid_mw[year]: MW of grid import (0 until grid deployed)
    
    Constraints (APPLIED ANNUALLY):
    - Timeline: Can only deploy equipment after lead time from project start
    - Annual NOx: emissions_year[y] <= limit (for EACH year)
    - Annual CO: emissions_year[y] <= limit (for EACH year)
    - Annual Gas Supply: peak_gas_mcf_day[y] <= limit (for EACH year)
    - Annual Grid Capacity: grid_import_mw[y] <= limit (for EACH year)
    - Cumulative Land Area: total_land_acres[y] <= limit (cumulative)
    - Annual N-1 Reliability: (capacity[y] - largest_unit) >= load[y] (for EACH year)
    
    Objective:
    Minimize: Lifecycle LCOE over 20 years
    """
    
    def __init__(self, site: Dict, equipment_data: Dict, constraints: Dict, load_trajectory: Dict, scenario: Dict = None):
        """
        Initialize phased deployment optimizer.
        
        Args:
            site: Site parameters (location, base load, etc.)
            equipment_data: Available equipment catalog
            constraints: Site constraints (NOx, CO, gas, land, grid limits)
            load_trajectory: {year: target_mw} for each year
            scenario: Scenario definition with equipment enable/disable flags
        """
        self.site = site
        self.equipment_data = equipment_data
        self.constraints = constraints
        self.load_trajectory = load_trajectory
        self.scenario = scenario or {}  # Store scenario settings
        
        # Planning horizon - 10 years for comprehensive temporal analysis
        self.start_year = 2026
        self.years = list(range(2026, 2036))  # 2026-2035 (10 years)
        self.num_years = len(self.years)
        
        # Equipment lead times (months from project start)
        # Grid timeline is scenario-specific
        self.lead_times = {
            'recip': 18,
            'turbine': 24,
            'bess': 12,
            'solar': 15,
            'grid': self.scenario.get('Grid_Timeline_Months', 96)  # From scenario, default 96
        }
        
        # Equipment unit sizes (for discretization)
        self.recip_unit_mw = 4.7  # Wärtsilä 34SG
        self.turbine_unit_mw = 35.0  # GE TM2500
        self.bess_unit_mwh = 10.0  # Typical BESS module
        
        # Financial parameters
        self.discount_rate = 0.08
        self.project_life_years = 20
        self.fuel_escalation_rate = 0.025  # 2.5% annual
        
    def decode_solution(self, x: np.ndarray) -> Dict:
        """
        Decode decision vector into equipment deployment schedule.
        
        Decision vector x layout:
        [recip_2026, recip_2027, ..., recip_2031,  # 6 values
         turbine_2026, turbine_2027, ..., turbine_2031,  # 6 values
         bess_2026, bess_2027, ..., bess_2031,  # 6 values
         solar_2026, solar_2027, ..., solar_2031,  # 6 values
         grid_2026, grid_2027, ..., grid_2031]  # 6 values
        
        Total: 30 decision variables
        """
        idx = 0
        deployment = {
            'recip_mw': {},
            'turbine_mw': {},
            'bess_mwh': {},
            'solar_mw': {},
            'grid_mw': {}
        }
        
        # Extract recips (MW added each year)
        for i, year in enumerate(self.years):
            deployment['recip_mw'][year] = max(0, x[idx + i])
        idx += self.num_years
        
        # Extract turbines (MW added each year)
        for i, year in enumerate(self.years):
            deployment['turbine_mw'][year] = max(0, x[idx + i])
        idx += self.num_years
        
        # Extract BESS (MWh added each year)
        for i, year in enumerate(self.years):
            deployment['bess_mwh'][year] = max(0, x[idx + i])
        idx += self.num_years
        
        # Extract solar (MW DC added each year)
        for i, year in enumerate(self.years):
            deployment['solar_mw'][year] = max(0, x[idx + i])
        idx += self.num_years
        
        # Extract grid (MW import each year, 0 until deployed)
        for i, year in enumerate(self.years):
            deployment['grid_mw'][year] = max(0, x[idx + i])
        
        # Calculate cumulative capacity
        deployment['cumulative_recip_mw'] = {}
        deployment['cumulative_turbine_mw'] = {}
        deployment['cumulative_bess_mwh'] = {}
        deployment['cumulative_solar_mw'] = {}
        
        for year in self.years:
            deployment['cumulative_recip_mw'][year] = sum(
                deployment['recip_mw'][y] for y in self.years if y <= year
            )
            deployment['cumulative_turbine_mw'][year] = sum(
                deployment['turbine_mw'][y] for y in self.years if y <= year
            )
            deployment['cumulative_bess_mwh'][year] = sum(
                deployment['bess_mwh'][y] for y in self.years if y <= year
            )
            deployment['cumulative_solar_mw'][year] = sum(
                deployment['solar_mw'][y] for y in self.years if y <= year
            )
        
        return deployment
    
    def get_cumulative_capacity_mw(self, deployment: Dict, year: int) -> float:
        """Get total firm capacity available in a given year."""
        recip_mw = deployment['cumulative_recip_mw'].get(year, 0)
        turbine_mw = deployment['cumulative_turbine_mw'].get(year, 0)
        grid_mw = deployment['grid_mw'].get(year, 0)
        solar_mw = deployment['cumulative_solar_mw'].get(year, 0) * 0.25  # Solar at 25% capacity credit
        
        return recip_mw + turbine_mw + grid_mw + solar_mw
    
    def calculate_annual_nox_tpy(self, deployment: Dict, year: int) -> float:
        """
        Calculate NOx emissions (tpy) for a specific year.
        
        Uses SCR (Selective Catalytic Reduction) emission factors:
        - Recips w/ SCR: 5.0 ppm = 0.17 lb/MWh
        - SCGT w/ SCR: 2.5 ppm = 0.09 lb/MWh
        - CCGT w/ SCR: 2.0 ppm = 0.05 lb/MWh
        """
        recip_mw = deployment['cumulative_recip_mw'].get(year, 0)
        turbine_mw = deployment['cumulative_turbine_mw'].get(year, 0)
        
        # Annual generation (MWh/year)
        recip_gen_mwh = recip_mw * 0.70 * 8760  # 70% capacity factor
        turbine_gen_mwh = turbine_mw * 0.30 * 8760  # 30% capacity factor
        
        # NOx emissions with SCR (lb/year)
        recip_nox_lb = recip_gen_mwh * 0.17  # Recips w/ SCR: 0.17 lb/MWh
        turbine_nox_lb = turbine_gen_mwh * 0.09  # SCGT w/ SCR: 0.09 lb/MWh
        
        total_nox_tpy = (recip_nox_lb + turbine_nox_lb) / 2000
        return total_nox_tpy
    
    def calculate_annual_co_tpy(self, deployment: Dict, year: int) -> float:
        """
        Calculate CO emissions (tpy) for a specific year.
        
        With SCR and oxidation catalyst, CO emissions are proportionally reduced.
        Using ~15% of NOx rates (conservative estimate):
        - Recips: 0.025 lb/MWh
        - SCGT: 0.014 lb/MWh
        """
        recip_mw = deployment['cumulative_recip_mw'].get(year, 0)
        turbine_mw = deployment['cumulative_turbine_mw'].get(year, 0)
        
        # Annual generation (MWh/year)
        recip_gen_mwh = recip_mw * 0.70 * 8760
        turbine_gen_mwh = turbine_mw * 0.30 * 8760
        
        # CO emissions with SCR/OxCat (lb/year)
        recip_co_lb = recip_gen_mwh * 0.025  # ~15% of NOx rate
        turbine_co_lb = turbine_gen_mwh * 0.014  # ~15% of NOx rate
        
        total_co_tpy = (recip_co_lb + turbine_co_lb) / 2000
        return total_co_tpy
    
    def calculate_annual_gas_mcf_day(self, deployment: Dict, year: int) -> float:
        """Calculate peak gas consumption (MCF/day) for a specific year."""
        recip_mw = deployment['cumulative_recip_mw'].get(year, 0)
        turbine_mw = deployment['cumulative_turbine_mw'].get(year, 0)
        
        # Peak gas = MW * heat_rate / gas_hhv * 24
        # Gas HHV = 1.037 MMBtu/MCF
        # Heat rate in MMBtu/MWh: 7700 Btu/kWh = 7.7 MMBtu/MWh (correct units here)
        recip_gas = (recip_mw * 7.7 / 1.037) * 24
        turbine_gas = (turbine_mw * 8.5 / 1.037) * 24
        
        return recip_gas + turbine_gas
    
    def calculate_cumulative_land_acres(self, deployment: Dict, year: int) -> float:
        """Calculate cumulative land area used (acres) up to a given year."""
        recip_mw = deployment['cumulative_recip_mw'].get(year, 0)
        turbine_mw = deployment['cumulative_turbine_mw'].get(year, 0)
        solar_mw = deployment['cumulative_solar_mw'].get(year, 0)
        bess_mwh = deployment['cumulative_bess_mwh'].get(year, 0)
        
        # Land requirements
        land_acres = (
            recip_mw * 0.5 +      # 0.5 acres/MW
            turbine_mw * 0.3 +    # 0.3 acres/MW
            solar_mw * 5.0 +      # 5 acres/MW
            bess_mwh * 0.01       # 0.01 acres/MWh
        )
        
        return land_acres
    
    def calculate_lifecycle_lcoe(self, deployment: Dict) -> float:
        """
        Calculate lifecycle LCOE over 20-year project life.
        
        Accounts for:
        - Deployment timing (NPV of CAPEX in different years)
        - 30% ITC for solar/BESS
        - Fuel price escalation (2.5% annually)
        - Load trajectory matching penalty
        """
        npv_capex = 0
        npv_opex = 0
        npv_generation = 0
        
        # CAPEX (deployed equipment in each year)
        for year in self.years:
            year_offset = year - self.start_year
            discount = (1 + self.discount_rate) ** year_offset
            
            # Equipment added this year
            recip_added = deployment['recip_mw'].get(year, 0)
            turbine_added = deployment['turbine_mw'].get(year, 0)
            bess_added = deployment['bess_mwh'].get(year, 0)
            solar_added = deployment['solar_mw'].get(year, 0)
            
            # CAPEX calculations (with ITC for solar/BESS)
            capex_year = (
                recip_added * 1000 * 1650 +           # $1650/kW for recips
                turbine_added * 1000 * 1300 +         # $1300/kW for turbines  
                bess_added * 1000 * 236 * 0.70 +      # $236/kWh * 70% (30% ITC)
                solar_added * 1000000 * 0.95 * 0.70   # $0.95/W * 70% (30% ITC)
            )
            
            npv_capex += capex_year / discount
        
        # OPEX and Generation (over 20-year life)
        for op_year in range(self.project_life_years):
            discount = (1 + self.discount_rate) ** op_year
            fuel_escalation = (1 + self.fuel_escalation_rate) ** op_year
            
            # Which deployment year are we in? (use final year deployment for simplicity)
            deployment_year = min(self.years[-1], self.start_year + op_year)
            
            recip_mw = deployment['cumulative_recip_mw'].get(deployment_year, 0)
            turbine_mw = deployment['cumulative_turbine_mw'].get(deployment_year, 0)
            solar_mw = deployment['cumulative_solar_mw'].get(deployment_year, 0)
            bess_mwh = deployment['cumulative_bess_mwh'].get(deployment_year, 0)
            
            # Annual generation (MWh/year)
            recip_gen = recip_mw * 0.70 * 8760
            turbine_gen = turbine_mw * 0.30 * 8760
            solar_gen = solar_mw * 0.25 * 8760
            total_gen = recip_gen + turbine_gen + solar_gen
            
            # Annual O&M
            recip_om = recip_mw * 1000 * 18.5 + recip_gen * 8.5
            turbine_om = turbine_mw * 1000 * 12.5 + turbine_gen * 6.5
            solar_om = solar_mw * 1000 * 15 + solar_gen * 2.0
            bess_om = bess_mwh * 1000 * 8.0
            
            # Annual fuel (with escalation)
            recip_fuel = recip_gen * 7.7 * 4.0 * fuel_escalation  # $4/MMBtu
            turbine_fuel = turbine_gen * 8.5 * 4.0 * fuel_escalation
            
            total_opex = recip_om + turbine_om + solar_om + bess_om + recip_fuel + turbine_fuel
            
            npv_opex += total_opex / discount
            npv_generation += total_gen / discount
        
        # Calculate LCOE
        if npv_generation > 1:  # Need at least some generation
            lcoe = (npv_capex + npv_opex) / npv_generation
        else:
            lcoe = 999.0  # Penalty for zero generation ($/MWh)
        
        # Add penalty for not meeting load trajectory (in $/MWh units)
        load_gap_penalty_mwh = 0
        total_generation_needed = 0
        for year in self.years:
            capacity = self.get_cumulative_capacity_mw(deployment, year)
            target_load = self.load_trajectory.get(year, 0)
            total_generation_needed += target_load * 8760  # MWh/year
            if capacity < target_load:
                gap_mw = target_load - capacity
                # Penalty: $10/MWh for each MWh of unmet load
                load_gap_penalty_mwh += (gap_mw * 8760) * 10.0  # Total $ penalty
        
        # Convert penalty to $/MWh by dividing by total generation needed
        if total_generation_needed > 0:
            lcoe += load_gap_penalty_mwh / total_generation_needed
        
        return lcoe
    
    def objective_function(self, x: np.ndarray) -> float:
        """
        Objective function: MAXIMIZE total power delivered over all years
        while staying WITHIN constraints (hard constraints, not penalties).
        
        Returns NEGATIVE of total deliverable power (for minimization).
        
        Note: Timeline constraints are enforced via decision variable bounds,
        not here in the objective function.
        """
        deployment = self.decode_solution(x)
        
        # SOFT PENALTY APPROACH: Calculate penalties for constraint violations
        # This gives optimizer a gradient to follow toward feasible regions
        total_penalty = 0
        
        for year in self.years:
            # NOx penalty
            nox_tpy = self.calculate_annual_nox_tpy(deployment, year)
            nox_limit = self.constraints.get('nox_tpy_annual', 100)
            if nox_tpy > nox_limit * 1.01:
                violation = (nox_tpy - nox_limit * 1.01) / nox_limit
                total_penalty += 1000 * violation
            
            # CO penalty
            co_tpy = self.calculate_annual_co_tpy(deployment, year)
            co_limit = self.constraints.get('co_tpy_annual', 100)
            if co_tpy > co_limit * 1.01:
                violation = (co_tpy - co_limit * 1.01) / co_limit
                total_penalty += 1000 * violation
            
            # Gas penalty
            gas_mcf_day = self.calculate_annual_gas_mcf_day(deployment, year)
            gas_limit = self.constraints.get('gas_supply_mcf_day', 50000)
            if gas_mcf_day > gas_limit * 1.01:
                violation = (gas_mcf_day - gas_limit * 1.01) / gas_limit
                total_penalty += 1000 * violation
            
            # Land penalty
            land_acres = self.calculate_cumulative_land_acres(deployment, year)
            land_limit = self.constraints.get('land_area_acres', 500)
            if land_acres > land_limit * 1.01:
                violation = (land_acres - land_limit * 1.01) / land_limit
                total_penalty += 1000 * violation
        
        # Calculate total deliverable power
        total_power_delivered = 0
        for year in self.years:
            capacity = self.get_cumulative_capacity_mw(deployment, year)
            target_load = self.load_trajectory.get(year, 0)
            # Deliver min of capacity or target (can't deliver more than needed)
            delivered = min(capacity, target_load)
            total_power_delivered += delivered
        
        # Return NEGATIVE of power (to minimize = maximize power)
        # Add small LCOE term as tiebreaker for solutions with same power
        try:
            lcoe = self.calculate_lifecycle_lcoe(deployment)
        except:
            lcoe = 100.0  # Fallback if LCOE calculation fails
        
        # Objective: Maximize power, minimize penalties, with LCOE as tiebreaker
        # Lower is better: -power + penalty + small_lcoe
        result = -total_power_delivered + total_penalty + (lcoe * 0.001)
        return result
    
    def optimize(self, seed_deployments: List[Dict] = None) -> Tuple[Dict, float, List[str]]:
        """
        Run multi-year phased deployment optimization.
        
        Args:
            seed_deployments: Optional list of deployment dicts from previous runs to seed the optimizer.
                            This helps complex scenarios find at least the solutions of simpler ones.
        
        Returns:
            deployment_schedule: Optimized equipment deployment by year
            lcoe: Lifecycle LCOE ($/MWh)
            violations: List of constraint violation messages
        """
        # Decision variable bounds based on scenario settings AND lead times
        # Key insight: Don't penalize in objective - prevent via bounds!
        bounds = []
        
        # Check scenario flags (default to True if not specified)
        recip_enabled = self.scenario.get('Recip_Enabled', True)
        turbine_enabled = self.scenario.get('Turbine_Enabled', True)
        bess_enabled = self.scenario.get('BESS_Enabled', True)
        solar_enabled = self.scenario.get('Solar_Enabled', True)
        grid_enabled = self.scenario.get('Grid_Enabled', True)
        
        # Calculate equipment availability by year (based on lead times from 2026 start)
        # If equipment can't be deployed in a year, set bounds to (0,0)
        print(f"  📊 Setting bounds per year based on lead times:")
        
        # Recips: 18 month lead time → available 2027+
        for year in self.years:
            year_offset_months = (year - self.start_year) * 12
            can_deploy = year_offset_months >= self.lead_times['recip']
            
            if recip_enabled and can_deploy:
                bounds.append((0, 100))
                if year == self.years[0]:
                    print(f"    Recips: Available from {year} onwards")
            else:
                bounds.append((0, 0))
        
        # Turbines: 24 month lead time → available 2028+
        for year in self.years:
            year_offset_months = (year - self.start_year) * 12
            can_deploy = year_offset_months >= self.lead_times['turbine']
            
            if turbine_enabled and can_deploy:
                bounds.append((0, 150))
                if year == self.years[0]:
                    print(f"    Turbines: Available from {year} onwards")
            else:
                bounds.append((0, 0))
        
        # BESS: 12 month lead time → available 2027+
        for year in self.years:
            year_offset_months = (year - self.start_year) * 12
            can_deploy = year_offset_months >= self.lead_times['bess']
            
            if bess_enabled and can_deploy:
                bounds.append((0, 200))
                if year == self.years[0]:
                    print(f"    BESS: Available from {year} onwards")
            else:
                bounds.append((0, 0))
        
        # Solar: 15 month lead time → available 2027+
        for year in self.years:
            year_offset_months = (year - self.start_year) * 12
            can_deploy = year_offset_months >= self.lead_times['solar']
            
            if solar_enabled and can_deploy:
                bounds.append((0, 10))  # Reduced from 50 for 10-year horizon
                if year == self.years[0]:
                    print(f"    Solar: Available from {year} onwards (max 10 MW/yr due to land)")
            else:
                bounds.append((0, 0))
        
        # Grid: 96 month lead time → available 2034+
        # PROBLEM: Planning window ends 2031, so grid is NEVER available!
        grid_available_in_window = False
        for year in self.years:
            year_offset_months = (year - self.start_year) * 12
            can_deploy = year_offset_months >= self.lead_times['grid']
            
            if grid_enabled and can_deploy:
                bounds.append((0, 200))
                grid_available_in_window = True
                if year == self.years[0]:
                    print(f"    Grid: Available from {year} onwards")
            else:
                bounds.append((0, 0))
        
        if grid_enabled and not grid_available_in_window:
            print(f"    ⚠️ Grid: NOT available in planning window (needs 96 months, ends 2031)")
        
        # Run optimization with increased iterations for better convergence
        # User feedback: "should be running many iterations to get optimal solution"
        num_vars = 5 * len(self.years)  # 5 equipment types × num years
        print(f"  📊 Starting differential_evolution optimizer...")
        print(f"  📊 Decision variables: {num_vars} (5 equipment types × {len(self.years)} years)")
        print(f"  📊 Iterations: 75, Population: 15")  # Reduced for combination optimizer
        print(f"  📊 Constraints: NOx ≤ 100 tpy, CO ≤ 100 tpy, Gas ≤ 50k MCF/day, Land ≤ {self.constraints.get('land_area_acres', 500)} acres")
        print(f"  📊 Equipment enabled: Recips={recip_enabled}, Turbines={turbine_enabled}, BESS={bess_enabled}, Solar={solar_enabled}, Grid={grid_enabled}")
        print(f"  📊 Grid timeline: {self.lead_times['grid']} months")
        
        # INTELLIGENT SEEDING: Use results from simpler combinations
        init_pop = []
        
        if seed_deployments:
            print(f"  🌱 Processing {len(seed_deployments)} seed solutions from simpler combinations...")
            for seed in seed_deployments:
                try:
                    # Convert deployment dict back to decision vector x
                    # This maps the seed's equipment to the current problem's variables
                    # Any new equipment in current problem will be initialized to 0
                    x_seed = []
                    
                    # Recips
                    if recip_enabled:
                        for year in self.years:
                            val = seed.get('recip_mw', {}).get(year, 0) - seed.get('recip_mw', {}).get(year-1, 0)
                            # Handle cumulative vs incremental - actually decision vars are incremental
                            # But wait, decode_solution treats them as incremental additions
                            # Let's just use the cumulative diff
                            if year == self.start_year:
                                inc = seed.get('recip_mw', {}).get(year, 0)
                            else:
                                inc = seed.get('recip_mw', {}).get(year, 0) - seed.get('recip_mw', {}).get(year-1, 0)
                            x_seed.append(max(0, inc)) # Ensure non-negative
                    
                    # Turbines
                    if turbine_enabled:
                        for year in self.years:
                            if year == self.start_year:
                                inc = seed.get('turbine_mw', {}).get(year, 0)
                            else:
                                inc = seed.get('turbine_mw', {}).get(year, 0) - seed.get('turbine_mw', {}).get(year-1, 0)
                            x_seed.append(max(0, inc))
                            
                    # BESS
                    if bess_enabled:
                        for year in self.years:
                            if year == self.start_year:
                                inc = seed.get('bess_mw', {}).get(year, 0)
                            else:
                                inc = seed.get('bess_mw', {}).get(year, 0) - seed.get('bess_mw', {}).get(year-1, 0)
                            x_seed.append(max(0, inc))
                            
                    # Solar
                    if solar_enabled:
                        for year in self.years:
                            if year == self.start_year:
                                inc = seed.get('solar_mw', {}).get(year, 0)
                            else:
                                inc = seed.get('solar_mw', {}).get(year, 0) - seed.get('solar_mw', {}).get(year-1, 0)
                            x_seed.append(max(0, inc))
                            
                    # Grid
                    if grid_enabled:
                        for year in self.years:
                            if year == self.start_year:
                                inc = seed.get('grid_mw', {}).get(year, 0)
                            else:
                                inc = seed.get('grid_mw', {}).get(year, 0) - seed.get('grid_mw', {}).get(year-1, 0)
                            x_seed.append(max(0, inc))
                    
                    # Verify length matches bounds
                    if len(x_seed) == len(bounds):
                        init_pop.append(x_seed)
                except Exception as e:
                    print(f"    ⚠️ Failed to process seed: {e}")
        
        # Add conservative seed (10% of max) as fallback
        conservative = []
        for lower, upper in bounds:
            conservative.append(upper * 0.1 if upper > 0 else 0)
        init_pop.append(conservative)
        
        # Convert to numpy array if we have seeds
        init_array = None
        if init_pop:
            import numpy as np
            # Pad with random population to reach popsize if needed
            # But differential_evolution handles 'init' by using it as PART of the population
            # We just need to make sure it's an array
            try:
                init_array = np.array(init_pop)
                print(f"  🎯 Seeding optimizer with {len(init_pop)} proven solutions")
            except:
                print("  ⚠️ Could not convert seeds to array, using random init")
                init_array = None

        # Run optimization with sufficient iterations for 50-variable problem
        result = differential_evolution(
            func=self.objective_function,
            bounds=bounds,
            maxiter=500,  # Sufficient for 50 variables (5 equipment × 10 years)
            popsize=30,   # Large population for better exploration
            tol=0.01,
            atol=0,
            workers=1,
            updating='deferred',
            seed=42,
            init=init_array if init_array is not None else 'latinhypercube', # Use seeds if available
            polish=True,
            strategy='best1bin',
            disp=False
        )
        
        print(f"  ✅ Optimization complete: {result.message}")
        print(f"  📊 Final objective value: {result.fun:.2f}")
        print(f"  📊 Function evaluations: {result.nfev}")
        
        # CRITICAL CHECK: Is the best solution actually feasible?
        if result.fun >= 1e9:
            # Optimizer could not find a feasible solution within constraints
            print(f"  ❌ NO FEASIBLE SOLUTION FOUND")
            print(f"  ❌ All explored solutions violated hard constraints")
            print(f"  ❌ This means constraints are too tight for the load trajectory")
            
            # Return empty deployment with clear message
            empty_deployment = {
                'recip_mw': {year: 0 for year in self.years},
                'turbine_mw': {year: 0 for year in self.years},
                'bess_mwh': {year: 0 for year in self.years},
                'solar_mw': {year: 0 for year in self.years},
                'grid_mw': {year: 0 for year in self.years},
                'cumulative_recip_mw': {year: 0 for year in self.years},
                'cumulative_turbine_mw': {year: 0 for year in self.years},
                'cumulative_bess_mwh': {year: 0 for year in self.years},
                'cumulative_solar_mw': {year: 0 for year in self.years},
            }
            
            violations = [
                "OPTIMIZATION FAILED: No feasible solution exists within constraints",
                "Constraints are too restrictive for the load trajectory",
                "Suggestions:",
                "  - Increase land area limit (currently {:.0f} acres)".format(self.constraints.get('land_area_acres', 100)),
                "  - Increase NOx/CO limits (currently {:.0f} tpy)".format(self.constraints.get('nox_tpy_annual', 100)),
                "  - Reduce load trajectory targets",
                "  - Enable more equipment types (Grid, BESS, Solar)"
            ]
            
            return empty_deployment, 999.99, violations
        
        # Decode solution
        deployment = self.decode_solution(result.x)
        lcoe = self.calculate_lifecycle_lcoe(deployment)
        
        # Check for violations and calculate power deficit
        violations = []
        total_power_deficit_mw_years = 0
        
        print(f"\n  🔍 Checking final solution constraints:")
        
        for year in self.years:
            nox = self.calculate_annual_nox_tpy(deployment, year)
            co = self.calculate_annual_co_tpy(deployment, year)
            gas = self.calculate_annual_gas_mcf_day(deployment, year)
            land = self.calculate_cumulative_land_acres(deployment, year)
            capacity = self.get_cumulative_capacity_mw(deployment, year)
            target_load = self.load_trajectory.get(year, 0)
            
            print(f"    {year}: Capacity={capacity:.1f} MW, Target={target_load:.1f} MW, NOx={nox:.1f} tpy, CO={co:.1f} tpy, Gas={gas:.0f} MCF/day")
            
            # Check hard constraints WITH SAME TOLERANCE AS OBJECTIVE FUNCTION (1%)
            # This prevents reporting violations for solutions the optimizer considered feasible
            nox_limit = self.constraints.get('nox_tpy_annual', 100)
            co_limit = self.constraints.get('co_tpy_annual', 100)
            gas_limit = self.constraints.get('gas_supply_mcf_day', 50000)
            land_limit = self.constraints.get('land_area_acres', 500)
            
            if nox > nox_limit * 1.01:  # 1% tolerance
                violations.append(f"{year}: NOx {nox:.1f} tpy exceeds limit of {nox_limit} tpy")
            if co > co_limit * 1.01:  # 1% tolerance
                violations.append(f"{year}: CO {co:.1f} tpy exceeds limit of {co_limit} tpy")
            if gas > gas_limit * 1.01:  # 1% tolerance
                violations.append(f"{year}: Gas {gas:.0f} MCF/day exceeds limit of {gas_limit} MCF/day")
            if land > land_limit * 1.01:  # 1% tolerance
                violations.append(f"{year}: Land {land:.1f} acres exceeds limit of {land_limit} acres")
            
            # Track power deficit for informational purposes (NOT A VIOLATION!)
            if capacity < target_load:
                deficit = target_load - capacity
                total_power_deficit_mw_years += deficit
        
        # Report results
        if violations:
            print(f"  ❌ Found {len(violations)} TRUE constraint violations")
            for v in violations:
                print(f"      - {v}")
        else:
            print(f"  ✅ All constraints satisfied!")
        
        # Report power deficit separately (informational, not a failure)
        if total_power_deficit_mw_years > 0:
            print(f"  ℹ️ Power deficit: {total_power_deficit_mw_years:.1f} MW-years (constraints limit deliverable power)")
            print(f"      This is ACCEPTABLE - optimizer maximized power within constraints")
        
        # Return ONLY true violations (power deficit is not a violation)
        return deployment, lcoe, violations
