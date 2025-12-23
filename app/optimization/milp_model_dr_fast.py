"""
bvNexus MILP Optimization Model - FAST VERSION
===============================================

Optimizations for speed:
1. 3 representative weeks (504 hours) instead of 6 (1008 hours)
2. 5% MIP gap tolerance (vs 1%) - gets good solution faster
3. Prefers CBC solver over GLPK (10x faster)
4. Simplified constraints where possible
5. Better bounds on variables

Target solve time: 30-90 seconds (vs 10+ minutes)

Author: Claude AI
Date: December 2024
"""

from pyomo.environ import *
from typing import Dict, List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class bvNexusMILP_DR:
    """
    FAST MILP for AI datacenter power optimization.
    
    Speed optimizations:
    - 504 representative hours (3 weeks) instead of 1008
    - 5% MIP gap for faster convergence
    - Tighter variable bounds
    - Simplified SOC constraints
    """
    
    # FAST: Only 3 representative weeks (504 hours)
    REPRESENTATIVE_WEEKS = {
        'summer_peak': {'start_day': 200, 'weight': 20},   # Hot week
        'winter_typical': {'start_day': 340, 'weight': 20}, # Cold week  
        'spring_typical': {'start_day': 100, 'weight': 12}, # Mild week
    }  # Total weight = 52 weeks
    
    PEAK_HOURS = [16, 17, 18, 19, 20, 21]
    BESS_DURATION = 4
    UNSERVED_PENALTY = 50_000  # $/MWh
    
    # Equipment specs
    EQUIPMENT = {
        'recip': {'capacity_mw': 5.0, 'heat_rate': 7700, 'nox_rate': 0.099, 'avail': 0.97, 'capex': 1650},
        'turbine': {'capacity_mw': 20.0, 'heat_rate': 8500, 'nox_rate': 0.05, 'avail': 0.95, 'capex': 1300},
        'bess': {'efficiency': 0.92, 'capex_kwh': 250},
        'solar': {'cf': 0.25, 'acres_per_mw': 4.25, 'capex': 1000},
    }
    
    GAS_HHV = 1_037_000
    
    def __init__(self):
        self.model = None
        self._built = False
        self.years = []
        self.load_data = {}
        self.constraints = {}
        self.grid_config = {}
        self.existing = {}
        self.workload_mix = {}
        self.dr_config = {}
    
    def build(
        self,
        site: Dict,
        constraints: Dict,
        load_data: Dict,
        workload_mix: Dict,
        years: List[int],
        dr_config: Dict = None,
        existing_equipment: Dict = None,
        grid_config: Dict = None,
        use_representative_periods: bool = True,
    ):
        """Build MILP model optimized for speed."""
        
        logger.info("Building FAST MILP model (504 representative hours)")
        
        self.years = years
        self.load_data = load_data
        self.constraints = constraints
        self.workload_mix = workload_mix or {'pre_training': 0.3, 'fine_tuning': 0.2, 'batch_inference': 0.3, 'realtime_inference': 0.2}
        self.dr_config = dr_config or {'cooling_flex': 0.25}
        self.existing = existing_equipment or {'n_recip': 0, 'n_turbine': 0, 'bess_mwh': 0, 'solar_mw': 0, 'grid_mw': 0}
        
        # Grid config
        self.grid_config = grid_config or {}
        if 'available_year' not in self.grid_config:
            start_year = min(years)
            lead_months = self.grid_config.get('lead_time_months', 96)
            self.grid_config['available_year'] = start_year + (lead_months // 12)
        self.grid_config.setdefault('capex', 5_000_000)
        
        self.model = ConcreteModel()
        
        self._build_sets()
        self._build_parameters()
        self._build_variables()
        self._build_constraints()
        self._build_objective()
        
        self._built = True
        logger.info(f"Model built: {len(self.model.T)} hours × {len(self.years)} years")
    
    def _build_sets(self):
        m = self.model
        
        m.Y = Set(initialize=self.years)
        
        # FAST: 3 weeks = 504 hours
        n_hours = 3 * 168  # 504 hours
        m.T = RangeSet(1, n_hours)
        m.SCALE_FACTOR = Param(initialize=8760 / n_hours)  # ~17.4
        
        # Peak hours
        peak_idx = []
        for week in range(3):
            for day in range(7):
                for h in self.PEAK_HOURS:
                    idx = week * 168 + day * 24 + h + 1
                    if idx <= n_hours:
                        peak_idx.append(idx)
        m.T_peak = Set(initialize=peak_idx)
        
        m.W = Set(initialize=['pre_training', 'fine_tuning', 'batch_inference', 'realtime_inference'])
        m.DR = Set(initialize=['spinning_reserve', 'economic_dr'])  # Simplified DR
    
    def _build_parameters(self):
        m = self.model
        
        # Sample load
        load_array = self._sample_load(np.array(self.load_data.get('total_load_mw', [100]*8760)))
        m.D_total = Param(m.T, m.Y, initialize=lambda m, t, y: float(load_array[t-1]))
        
        # Annual required energy
        annual = float(np.sum(self.load_data.get('total_load_mw', [100]*8760)))
        m.D_required = Param(m.Y, initialize=lambda m, y: annual)
        
        # Constraints
        m.NOX_MAX = Param(initialize=self.constraints.get('NOx_Limit_tpy', 
                         self.constraints.get('max_nox_tpy', 99)))
        m.GAS_MAX = Param(initialize=self.constraints.get('Gas_Supply_MCF_day',
                         self.constraints.get('gas_supply_mcf_day', 50000)))
        m.LAND_MAX = Param(initialize=self.constraints.get('Available_Land_Acres', 500))
        
        # Grid timing
        grid_year = self.grid_config.get('available_year', 2034)
        m.GRID_AVAIL = Param(m.Y, initialize=lambda m, y: 1.0 if y >= grid_year else 0.0)
        m.GRID_CAPEX = Param(initialize=self.grid_config.get('capex', 5_000_000))
        
        # Other params
        m.PUE = Param(initialize=self.load_data.get('pue', 1.25))
        m.BESS_EFF = Param(initialize=0.92)
        
        wl_flex = {'pre_training': 0.30, 'fine_tuning': 0.50, 'batch_inference': 0.90, 'realtime_inference': 0.05}
        m.WL_flex = Param(m.W, initialize=lambda m, w: wl_flex.get(w, 0.1))
        m.COOL_flex = Param(initialize=0.25)
        
        dr_pay = {'spinning_reserve': 15, 'economic_dr': 5}
        m.DR_payment = Param(m.DR, initialize=lambda m, dr: dr_pay.get(dr, 5))
        
        # Existing equipment
        m.EXISTING_recip = Param(initialize=self.existing.get('n_recip', 0))
        m.EXISTING_turbine = Param(initialize=self.existing.get('n_turbine', 0))
    
    def _sample_load(self, load_8760: np.ndarray) -> np.ndarray:
        """Sample 3 representative weeks."""
        if len(load_8760) != 8760:
            return load_8760[:504] if len(load_8760) >= 504 else np.tile(load_8760, 4)[:504]
        
        hours = []
        for week_info in self.REPRESENTATIVE_WEEKS.values():
            start = week_info['start_day'] * 24
            end = start + 168
            if end <= 8760:
                hours.extend(load_8760[start:end])
            else:
                hours.extend(load_8760[start:])
                hours.extend(load_8760[:end-8760])
        return np.array(hours)
    
    def _build_variables(self):
        m = self.model
        
        # Capacity - RELAXED bounds (was too tight causing infeasibility)
        # Still provides upper bounds for faster solve, but realistic for datacenter scale
        m.n_recip = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 100))  # Was 50, now 100
        m.n_turbine = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 30))  # Was 20, now 30
        m.bess_mwh = Var(m.Y, within=NonNegativeReals, bounds=(0, 2000))    # Was 1000, now 2000
        m.bess_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))      # Was 250, now 500
        m.solar_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))     # Was 200, now 500
        m.grid_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))      # Was 300, now 500
        
        m.grid_active = Var(m.Y, within=Binary)
        m.grid_capex_incurred = Var(m.Y, within=NonNegativeReals)
        
        # Dispatch
        m.gen_recip = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_turbine = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_solar = Var(m.T, m.Y, within=NonNegativeReals)
        m.grid_import = Var(m.T, m.Y, within=NonNegativeReals)
        m.charge = Var(m.T, m.Y, within=NonNegativeReals)
        m.discharge = Var(m.T, m.Y, within=NonNegativeReals)
        m.soc = Var(m.T, m.Y, within=NonNegativeReals)
        
        # DR - simplified
        m.curtail_total = Var(m.T, m.Y, within=NonNegativeReals)
        m.dr_capacity = Var(m.DR, m.Y, within=NonNegativeReals)
        
        # Unserved energy
        m.unserved = Var(m.T, m.Y, within=NonNegativeReals, bounds=(0, 500))  # Was 300, now 500
    
    def _build_constraints(self):
        m = self.model
        
        eq = self.EQUIPMENT
        
        # === CAPACITY CONSTRAINTS ===
        
        # BESS sizing
        m.bess_size = Constraint(m.Y, rule=lambda m, y: m.bess_mw[y] == m.bess_mwh[y] / 4)
        
        # Land
        m.land = Constraint(m.Y, rule=lambda m, y: m.solar_mw[y] * eq['solar']['acres_per_mw'] <= m.LAND_MAX)
        
        # Grid requires active
        m.grid_active_con = Constraint(m.Y, rule=lambda m, y: m.grid_mw[y] <= 500 * m.grid_active[y])
        
        # Grid capex
        m.grid_capex = Constraint(m.Y, rule=lambda m, y: m.grid_capex_incurred[y] >= m.grid_active[y] * m.GRID_CAPEX)
        
        # Grid timing - can't use before available
        grid_year = self.grid_config.get('available_year', 2034)
        def grid_timing(m, y):
            if y < grid_year:
                return m.grid_active[y] == 0
            return Constraint.Skip
        m.grid_timing = Constraint(m.Y, rule=grid_timing)
        
        # Non-decreasing capacity
        def nondec_recip(m, y):
            if y == m.Y.first(): return Constraint.Skip
            return m.n_recip[y] >= m.n_recip[m.Y.prev(y)]
        m.nondec_recip = Constraint(m.Y, rule=nondec_recip)
        
        def nondec_turbine(m, y):
            if y == m.Y.first(): return Constraint.Skip
            return m.n_turbine[y] >= m.n_turbine[m.Y.prev(y)]
        m.nondec_turbine = Constraint(m.Y, rule=nondec_turbine)
        
        # Existing equipment
        m.exist_recip = Constraint(m.Y, rule=lambda m, y: m.n_recip[y] >= m.EXISTING_recip)
        m.exist_turbine = Constraint(m.Y, rule=lambda m, y: m.n_turbine[y] >= m.EXISTING_turbine)
        
        # === DISPATCH CONSTRAINTS ===
        
        # Power balance with unserved
        def power_bal(m, t, y):
            supply = m.gen_recip[t,y] + m.gen_turbine[t,y] + m.gen_solar[t,y] + m.grid_import[t,y] + m.discharge[t,y] + m.unserved[t,y]
            demand = m.D_total[t,y] - m.curtail_total[t,y] + m.charge[t,y]
            return supply == demand
        m.power_bal = Constraint(m.T, m.Y, rule=power_bal)
        
        # Generation limits
        m.gen_recip_lim = Constraint(m.T, m.Y, 
            rule=lambda m,t,y: m.gen_recip[t,y] <= m.n_recip[y] * eq['recip']['capacity_mw'] * eq['recip']['avail'])
        m.gen_turbine_lim = Constraint(m.T, m.Y,
            rule=lambda m,t,y: m.gen_turbine[t,y] <= m.n_turbine[y] * eq['turbine']['capacity_mw'] * eq['turbine']['avail'])
        m.gen_solar_lim = Constraint(m.T, m.Y,
            rule=lambda m,t,y: m.gen_solar[t,y] <= m.solar_mw[y] * eq['solar']['cf'])
        m.grid_lim = Constraint(m.T, m.Y,
            rule=lambda m,t,y: m.grid_import[t,y] <= m.grid_mw[y] * m.GRID_AVAIL[y])
        
        # BESS
        m.charge_lim = Constraint(m.T, m.Y, rule=lambda m,t,y: m.charge[t,y] <= m.bess_mw[y])
        m.discharge_lim = Constraint(m.T, m.Y, rule=lambda m,t,y: m.discharge[t,y] <= m.bess_mw[y])
        
        # Simplified SOC (just bounds, no dynamics for speed)
        m.soc_lo = Constraint(m.T, m.Y, rule=lambda m,t,y: m.soc[t,y] >= 0.1 * m.bess_mwh[y])
        m.soc_hi = Constraint(m.T, m.Y, rule=lambda m,t,y: m.soc[t,y] <= m.bess_mwh[y])
        
        # Energy conservation (simplified)
        def soc_dyn(m, t, y):
            if t == 1:
                return m.soc[t,y] == 0.5 * m.bess_mwh[y]
            return m.soc[t,y] == m.soc[t-1,y] + 0.92*m.charge[t,y] - m.discharge[t,y]/0.92
        m.soc_dyn = Constraint(m.T, m.Y, rule=soc_dyn)
        
        # === EMISSIONS ===
        
        # NOx
        def nox_limit(m, y):
            nox = sum(
                m.gen_recip[t,y] * eq['recip']['heat_rate'] * eq['recip']['nox_rate'] +
                m.gen_turbine[t,y] * eq['turbine']['heat_rate'] * eq['turbine']['nox_rate']
                for t in m.T
            )
            return m.SCALE_FACTOR * nox / 2_000_000 <= m.NOX_MAX
        m.nox_con = Constraint(m.Y, rule=nox_limit)
        
        # Gas supply
        def gas_limit(m, y):
            recip_mcf = m.SCALE_FACTOR * sum(m.gen_recip[t,y] for t in m.T) * eq['recip']['heat_rate'] * 1000 / self.GAS_HHV
            turbine_mcf = m.SCALE_FACTOR * sum(m.gen_turbine[t,y] for t in m.T) * eq['turbine']['heat_rate'] * 1000 / self.GAS_HHV
            return (recip_mcf + turbine_mcf) / 365 <= m.GAS_MAX
        m.gas_con = Constraint(m.Y, rule=gas_limit)
        
        # === DR (simplified) ===
        
        # Curtailment limit
        def curtail_lim(m, t, y):
            max_curtail = m.D_total[t,y] * 0.15  # Max 15% curtailment
            return m.curtail_total[t,y] <= max_curtail
        m.curtail_lim = Constraint(m.T, m.Y, rule=curtail_lim)
        
        # Annual curtailment budget
        def curtail_budget(m, y):
            return m.SCALE_FACTOR * sum(m.curtail_total[t,y] for t in m.T) <= 0.01 * m.D_required[y]
        m.curtail_budget = Constraint(m.Y, rule=curtail_budget)
    
    def _build_objective(self):
        m = self.model
        eq = self.EQUIPMENT
        r = 0.08
        first_year = min(self.years)
        
        def objective(m):
            # CAPEX
            capex = sum(
                (m.n_recip[y] * eq['recip']['capacity_mw'] * 1000 * eq['recip']['capex'] +
                 m.n_turbine[y] * eq['turbine']['capacity_mw'] * 1000 * eq['turbine']['capex'] +
                 m.bess_mwh[y] * 1000 * eq['bess']['capex_kwh'] +
                 m.solar_mw[y] * 1000 * eq['solar']['capex'] +
                 m.grid_capex_incurred[y]) / (1+r)**(y-first_year)
                for y in m.Y
            )
            
            # Fuel
            fuel = sum(
                m.SCALE_FACTOR * sum(
                    (m.gen_recip[t,y] * eq['recip']['heat_rate'] + 
                     m.gen_turbine[t,y] * eq['turbine']['heat_rate']) * 3.50 / 1000
                    for t in m.T
                ) / (1+r)**(y-first_year)
                for y in m.Y
            )
            
            # Grid electricity
            grid_cost = sum(
                m.SCALE_FACTOR * sum(m.grid_import[t,y] * 75 for t in m.T) / (1+r)**(y-first_year)
                for y in m.Y
            )
            
            # DR revenue
            dr_rev = sum(
                sum(m.dr_capacity[dr,y] * 8760 * m.DR_payment[dr] for dr in m.DR) / (1+r)**(y-first_year)
                for y in m.Y
            )
            
            # Unserved penalty
            unserved = sum(
                m.SCALE_FACTOR * sum(m.unserved[t,y] * self.UNSERVED_PENALTY for t in m.T) / (1+r)**(y-first_year)
                for y in m.Y
            )
            
            # Energy denominator
            energy = sum(m.D_required[y] / (1+r)**(y-first_year) for y in m.Y)
            
            return (capex + fuel + grid_cost + unserved - dr_rev) / energy if energy > 0 else 1e9
        
        m.obj = Objective(rule=objective, sense=minimize)
    
    def solve(self, solver: str = 'cbc', time_limit: int = 120, verbose: bool = False) -> Dict:
        """Solve with optimized settings for speed."""
        
        if not self._built:
            raise RuntimeError("Model not built")
        
        # Prefer faster solvers
        solver_priority = ['cbc', 'gurobi', 'glpk', 'cplex']
        
        opt = None
        used_solver = None
        
        for s in ([solver] + solver_priority):
            try:
                opt = SolverFactory(s)
                if opt is not None and opt.available():
                    used_solver = s
                    break
            except:
                continue
        
        if opt is None:
            raise RuntimeError("No solver found")
        
        logger.info(f"Solving with {used_solver} (time limit: {time_limit}s)")
        
        # FAST settings: 5% gap tolerance
        if used_solver == 'gurobi':
            opt.options['TimeLimit'] = time_limit
            opt.options['MIPGap'] = 0.05  # 5% gap
            opt.options['Threads'] = 4
        elif used_solver == 'cbc':
            opt.options['seconds'] = time_limit
            opt.options['ratioGap'] = 0.05
            opt.options['threads'] = 4
        elif used_solver == 'glpk':
            opt.options['tmlim'] = time_limit
            opt.options['mipgap'] = 0.05
        
        results = opt.solve(self.model, tee=verbose)
        
        logger.info(f"Status: {results.solver.status}, Term: {results.solver.termination_condition}")
        
        return self._extract_solution(results)
    
    def _extract_solution(self, results) -> Dict:
        m = self.model
        eq = self.EQUIPMENT
        
        solution = {
            'status': str(results.solver.status),
            'termination': str(results.solver.termination_condition),
            'objective_lcoe': 0,
            'equipment': {},
            'power_coverage': {},
            'emissions': {},
            'gas_usage': {},
            'dr': {},
        }
        
        if results.solver.termination_condition not in [TerminationCondition.optimal, TerminationCondition.feasible]:
            return solution
        
        try:
            solution['objective_lcoe'] = value(m.obj)
        except:
            pass
        
        for y in m.Y:
            # Equipment
            n_recip = int(value(m.n_recip[y]))
            n_turbine = int(value(m.n_turbine[y]))
            
            solution['equipment'][y] = {
                'n_recip': n_recip,
                'n_turbine': n_turbine,
                'recip_mw': n_recip * eq['recip']['capacity_mw'],
                'turbine_mw': n_turbine * eq['turbine']['capacity_mw'],
                'bess_mwh': value(m.bess_mwh[y]),
                'bess_mw': value(m.bess_mw[y]),
                'solar_mw': value(m.solar_mw[y]),
                'grid_mw': value(m.grid_mw[y]),
                'grid_active': bool(value(m.grid_active[y])),
                'total_capacity_mw': (
                    n_recip * eq['recip']['capacity_mw'] +
                    n_turbine * eq['turbine']['capacity_mw'] +
                    value(m.bess_mw[y]) +
                    value(m.solar_mw[y]) * eq['solar']['cf'] +
                    value(m.grid_mw[y]) * value(m.GRID_AVAIL[y])
                ),
            }
            
            # Power coverage
            unserved = sum(value(m.unserved[t,y]) for t in m.T) * value(m.SCALE_FACTOR)
            total_load = value(m.D_required[y])
            coverage = (1 - unserved/total_load) * 100 if total_load > 0 else 100
            
            solution['power_coverage'][y] = {
                'total_load_mwh': total_load,
                'unserved_mwh': unserved,
                'coverage_pct': coverage,
                'power_gap_mw': unserved / 8760 if unserved > 0 else 0,
                'is_fully_served': unserved < 0.01 * total_load,
            }
            
            # Emissions
            nox = sum(
                value(m.gen_recip[t,y]) * eq['recip']['heat_rate'] * eq['recip']['nox_rate'] +
                value(m.gen_turbine[t,y]) * eq['turbine']['heat_rate'] * eq['turbine']['nox_rate']
                for t in m.T
            ) * value(m.SCALE_FACTOR) / 2_000_000
            
            solution['emissions'][y] = {
                'nox_tpy': nox,
                'nox_limit_tpy': value(m.NOX_MAX),
                'nox_utilization_pct': nox / value(m.NOX_MAX) * 100 if value(m.NOX_MAX) > 0 else 0,
            }
            
            # Gas
            recip_gen = sum(value(m.gen_recip[t,y]) for t in m.T) * value(m.SCALE_FACTOR)
            turbine_gen = sum(value(m.gen_turbine[t,y]) for t in m.T) * value(m.SCALE_FACTOR)
            
            recip_mcf = recip_gen * eq['recip']['heat_rate'] * 1000 / self.GAS_HHV
            turbine_mcf = turbine_gen * eq['turbine']['heat_rate'] * 1000 / self.GAS_HHV
            daily_mcf = (recip_mcf + turbine_mcf) / 365
            
            solution['gas_usage'][y] = {
                'avg_daily_mcf': daily_mcf,
                'gas_limit_mcf_day': value(m.GAS_MAX),
                'gas_utilization_pct': daily_mcf / value(m.GAS_MAX) * 100 if value(m.GAS_MAX) > 0 else 0,
            }
            
            # DR
            solution['dr'][y] = {
                'total_dr_mw': sum(value(m.dr_capacity[dr,y]) for dr in m.DR),
            }
        
        return solution
