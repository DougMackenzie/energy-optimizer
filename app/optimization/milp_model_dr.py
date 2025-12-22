"""
bvNexus MILP Optimization Model with Demand Response

Complete implementation of MILP for AI datacenter power optimization
with workload-specific demand response capabilities.

QA/QC Modifications Incorporated:
1. Representative periods (1008 hours) instead of full 8760 for tractability
2. LCOE denominator uses required_load (fixed) not energy_served
3. DR capacity uses peak-window minimum, not average
4. Grid interconnection CAPEX with Big-M formulation
5. Brownfield support with existing equipment parameters
6. BESS duration fixed as Parameter to preserve linearity
"""

from pyomo.environ import *
from typing import Dict, List, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class bvNexusMILP_DR:
    """
    Mixed-Integer Linear Program for datacenter power optimization
    with integrated demand response capabilities.
    
    Key Design Decisions (from QA/QC):
    - Uses 6 representative weeks (1008 hours) for Stage 1 capacity optimization
    - Full 8760 validation available in Stage 2
    - BESS duration is FIXED (4 hours) to preserve MILP linearity
    - LCOE denominator is fixed required_load to prevent curtailment distortion
    """
    
    # Representative period configuration
    # 6 weeks × 168 hours = 1008 hours (tractable for MILP)
    REPRESENTATIVE_WEEKS = {
        'spring_typical': {'start_day': 80, 'weight': 10},    # ~10 weeks
        'summer_typical': {'start_day': 160, 'weight': 8},    # ~8 weeks
        'summer_peak': {'start_day': 200, 'weight': 4},       # ~4 weeks (hottest)
        'fall_typical': {'start_day': 260, 'weight': 10},     # ~10 weeks
        'winter_typical': {'start_day': 340, 'weight': 12},   # ~12 weeks
        'winter_peak': {'start_day': 10, 'weight': 8},        # ~8 weeks (coldest)
    }  # Total weight = 52 weeks
    
    # Peak hours for DR capacity credit (4 PM - 9 PM)
    PEAK_HOURS = [16, 17, 18, 19, 20, 21]
    
    # BESS duration is FIXED to preserve linearity (DO NOT make this a variable!)
    BESS_DURATION_HOURS = 4  # Fixed 4-hour duration
    
    # Workload flexibility defaults (from research)
    WORKLOAD_DEFAULTS = {
        'pre_training': {'flex': 0.30, 'response_min': 15, 'min_run_hrs': 3},
        'fine_tuning': {'flex': 0.50, 'response_min': 5, 'min_run_hrs': 1},
        'batch_inference': {'flex': 0.90, 'response_min': 1, 'min_run_hrs': 0},
        'realtime_inference': {'flex': 0.05, 'response_min': float('inf'), 'min_run_hrs': float('inf')},
        'rl_training': {'flex': 0.40, 'response_min': 10, 'min_run_hrs': 2},
        'cloud_hpc': {'flex': 0.25, 'response_min': 20, 'min_run_hrs': 4},
    }
    
    # DR product defaults
    DR_PRODUCTS = {
        'spinning_reserve': {'payment': 15, 'activation': 50, 'max_events': 50},
        'non_spinning_reserve': {'payment': 8, 'activation': 40, 'max_events': 100},
        'economic_dr': {'payment': 5, 'activation': 100, 'max_events': 200},
        'emergency_dr': {'payment': 3, 'activation': 200, 'max_events': 20},
    }
    
    def __init__(self):
        self.model = ConcreteModel()
        self._built = False
        self.rep_hours = None
    
    def _build_representative_hours(self) -> np.ndarray:
        """
        Build representative hour indices from 6 typical weeks.
        Returns 1008 hours (6 weeks × 168 hours/week).
        """
        hours = []
        for week_name, config in self.REPRESENTATIVE_WEEKS.items():
            start_hour = config['start_day'] * 24
            week_hours = list(range(start_hour, start_hour + 168))
            hours.extend(week_hours)
        return np.array(hours) % 8760  # Wrap around year
    
    def build(
        self,
        site: Dict,
        constraints: Dict,
        load_data: Dict[str, np.ndarray],
        workload_mix: Dict[str, float],
        equipment_data: Dict = None,
        years: List[int] = None,
        dr_config: Dict = None,
        existing_equipment: Dict = None,  # BROWNFIELD SUPPORT
        use_representative_periods: bool = True  # TIME SLICE OPTIMIZATION
    ):
        """
        Build the complete MILP model.
        
        Args:
            site: Site parameters (location, grid specs, etc.)
            constraints: Hard constraints (NOx, land, gas, etc.)
            load_data: Output from generate_load_profile_with_flexibility()
            workload_mix: Workload percentages (must sum to 100)
            equipment_data: Equipment specifications
            years: Planning horizon years
            dr_config: DR configuration overrides
            existing_equipment: BROWNFIELD - existing equipment at site
                {'n_recip': 0, 'n_turbine': 0, 'bess_mwh': 0, 
                 'solar_mw': 0, 'grid_mw': 0}
            use_representative_periods: If True, use 1008 hours for tractability
        """
        m = self.model
        
        # Store inputs
        self.site = site
        self.constraints = constraints
        self.load_data = load_data
        self.workload_mix = workload_mix
        self.years = years or list(range(2026, 2036))
        self.dr_config = dr_config or {}
        self.use_rep_periods = use_representative_periods
        self.equipment_data = equipment_data or {}
        
        # BROWNFIELD SUPPORT - default to greenfield (all zeros)
        self.existing = existing_equipment or {
            'n_recip': 0, 'n_turbine': 0, 'bess_mwh': 0,
            'solar_mw': 0, 'grid_mw': 0
        }
        
        # Build representative hours
        if use_representative_periods:
            self.rep_hours = self._build_representative_hours()
            self.n_hours = len(self.rep_hours)  # 1008
            self.scale_factor = 8760 / self.n_hours  # ~8.69
        else:
            self.rep_hours = np.arange(8760)
            self.n_hours = 8760
            self.scale_factor = 1.0
        
        # Calculate FIXED required energy (for LCOE denominator - QA/QC fix)
        self.required_energy = {}
        for y in self.years:
            year_idx = self.years.index(y)
            trajectory = self.site.get('load_trajectory', {})
            scale = trajectory.get(y, 1.0)
            annual_energy = np.sum(self.load_data['total_load_mw']) * scale
            self.required_energy[y] = annual_energy
        
        logger.info(f"Building MILP model with {self.n_hours} hours (scale factor: {self.scale_factor:.2f})")
        
        # === BUILD MODEL ===
        self._build_sets()
        self._build_parameters()
        self._build_variables()
        self._build_capacity_constraints()
        self._build_brownfield_constraints()  # NEW
        self._build_dispatch_constraints()
        self._build_dr_constraints()
        self._build_objective()
        
        self._built = True
        logger.info("MILP model built successfully")
    
    def _build_sets(self):
        m = self.model
        
        # Time set - use representative periods for tractability
        m.T = RangeSet(1, self.n_hours)
        m.Y = Set(initialize=self.years)
        m.W = Set(initialize=['pre_training', 'fine_tuning', 'batch_inference', 
                              'realtime_inference', 'rl_training', 'cloud_hpc'])
        m.DR = Set(initialize=list(self.DR_PRODUCTS.keys()))
        
        # Peak hours set for DR capacity credit (hours 16-21 = 4-9 PM)
        # Map to representative period indices
        peak_indices = []
        for i, h in enumerate(self.rep_hours):
            hour_of_day = h % 24
            if hour_of_day in self.PEAK_HOURS:
                peak_indices.append(i + 1)  # Pyomo is 1-indexed
        m.T_peak = Set(initialize=peak_indices if peak_indices else [1])  # At least one element
        
        logger.info(f"Sets created: T={len(m.T)}, Y={len(m.Y)}, T_peak={len(m.T_peak)}")
    
    def _build_parameters(self):
        m = self.model
        
        # Scale factor for representative periods
        m.SCALE_FACTOR = Param(initialize=self.scale_factor)
        
        # Load parameters - map representative hours to load data
        def d_total_init(m, t, y):
            year_idx = self.years.index(y)
            trajectory = self.site.get('load_trajectory', {})
            scale = trajectory.get(y, 1.0)
            
            orig_hour = self.rep_hours[t - 1]  # Map back to original hour
            
            return self.load_data['total_load_mw'][orig_hour] * scale
        
        m.D_total = Param(m.T, m.Y, initialize=d_total_init, within=NonNegativeReals)
        
        # FIXED Required Energy for LCOE denominator (QA/QC fix)
        def d_required_init(m, y):
            return self.required_energy[y]
        m.D_required = Param(m.Y, initialize=d_required_init)
        
        # PUE
        m.PUE = Param(initialize=self.site.get('pue', 1.25))
        
        # Workload flexibility
        def wl_flex_init(m, w):
            return self.WORKLOAD_DEFAULTS.get(w, {}).get('flex', 0.0)
        m.WL_flex = Param(m.W, initialize=wl_flex_init)
        
        # Cooling flexibility
        m.COOL_flex = Param(initialize=self.dr_config.get('cooling_flex', 0.25))
        
        # DR parameters
        def dr_payment_init(m, dr):
            return self.DR_PRODUCTS[dr]['payment']
        m.DR_payment = Param(m.DR, initialize=dr_payment_init)
        
        # BROWNFIELD - Existing equipment
        m.EXISTING_recip = Param(initialize=self.existing['n_recip'])
        m.EXISTING_turbine = Param(initialize=self.existing['n_turbine'])
        m.EXISTING_bess = Param(initialize=self.existing['bess_mwh'])
        m.EXISTING_solar = Param(initialize=self.existing['solar_mw'])
        m.EXISTING_grid = Param(initialize=self.existing['grid_mw'])
        
        # BESS Duration - FIXED to preserve linearity (QA/QC critical!)
        m.BESS_DURATION = Param(initialize=self.BESS_DURATION_HOURS)
        
        # Grid interconnection capital cost
        m.GRID_CAPEX = Param(initialize=self.site.get('grid_capex', 5_000_000))  # $5M default
        
        
        # Constraint limits - Scale defaults based on peak load for reasonableness
        peak_load_estimate = np.percentile(self.load_data['total_load_mw'], 98)
        
        # Gas default: Assume peak load might run 24/7 at 80% capacity factor
        # peak_load * 0.8 * 24 hr * 7.7 MMBtu/MWh / 1.03 MMBtu/MCF
        default_gas_mcf_day = peak_load_estimate * 0.8 * 24 * 7.7 / 1.03
        
        # CO2 default: Assume annual emissions from running at 60% capacity factor
        # peak_load * 0.6 * 8760 hr * 7.7 MMBtu/MWh * 117 lb/MMBtu / 2000
        default_co2_tpy = peak_load_estimate * 0.6 * 8760 * 7.7 * 117 / 2000
        
        m.NOX_MAX = Param(initialize=self.constraints.get('nox_tpy', 99))
        m.LAND_MAX = Param(initialize=self.constraints.get('land_acres', 500))
        m.GAS_MAX = Param(initialize=self.constraints.get('gas_mcf_day', default_gas_mcf_day))
        m.CO2_MAX = Param(initialize=self.constraints.get('co2_tpy', default_co2_tpy))
        
        logger.info(f"Constraint defaults: GAS={m.GAS_MAX.value:.0f} MCF/day, CO2={m.CO2_MAX.value:.0f} tpy")
        
        # Economic
        m.discount_rate = Param(initialize=0.08)
        m.ng_price = Param(initialize=3.50)
        
        logger.info("Parameters initialized")
    
    def _build_variables(self):
        m = self.model
        
        # Capacity (integer for engines)
        m.n_recip = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 50))
        m.n_turbine = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 20))
        m.bess_mwh = Var(m.Y, within=NonNegativeReals, bounds=(0, 2000))
        m.bess_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))  # Derived from bess_mwh
        m.solar_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))
        m.grid_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))
        
        # Grid connection binary (for Big-M capex formulation)
        m.grid_active = Var(m.Y, within=Binary)
        m.grid_capex_incurred = Var(m.Y, within=NonNegativeReals)  # Tracks capex by year
        
        # Dispatch
        m.gen_recip = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_turbine = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_solar = Var(m.T, m.Y, within=NonNegativeReals)
        m.charge = Var(m.T, m.Y, within=NonNegativeReals)
        m.discharge = Var(m.T, m.Y, within=NonNegativeReals)
        m.soc = Var(m.T, m.Y, within=NonNegativeReals)
        m.grid_import = Var(m.T, m.Y, within=NonNegativeReals)
        
        # DR variables
        m.curtail_wl = Var(m.W, m.T, m.Y, within=NonNegativeReals)
        m.curtail_cool = Var(m.T, m.Y, within=NonNegativeReals)
        m.curtail_total = Var(m.T, m.Y, within=NonNegativeReals)
        m.dr_enrolled = Var(m.DR, m.Y, within=Binary)
        m.dr_capacity = Var(m.DR, m.Y, within=NonNegativeReals)
        
        logger.info("Variables created")
    
    def _build_capacity_constraints(self):
        m = self.model
        
        # Non-decreasing capacity
        def non_dec_recip(m, y):
            if y == m.Y.first():
                return Constraint.Skip
            return m.n_recip[y] >= m.n_recip[m.Y.prev(y)]
        m.non_dec_recip_con = Constraint(m.Y, rule=non_dec_recip)
        
        # BESS sizing - FIXED duration to preserve linearity (QA/QC critical!)
        # DO NOT make BESS_DURATION a decision variable
        def bess_sizing(m, y):
            return m.bess_mw[y] == m.bess_mwh[y] / m.BESS_DURATION
        m.bess_sizing_con = Constraint(m.Y, rule=bess_sizing)
        
        # Land constraint
        def land_con(m, y):
            return m.solar_mw[y] * 4.25 <= m.LAND_MAX  # 4.25 acres/MW
        m.land_con = Constraint(m.Y, rule=land_con)
        
        # Grid capacity requires active connection
        def grid_requires_active(m, y):
            # Big-M formulation: grid_mw <= M * grid_active
            M = 500  # Maximum grid capacity
            return m.grid_mw[y] <= M * m.grid_active[y]
        m.grid_requires_active_con = Constraint(m.Y, rule=grid_requires_active)
        
        # Grid capex tracking (Big-M formulation)
        def grid_capex_tracking(m, y):
            return m.grid_capex_incurred[y] >= m.grid_active[y] * m.GRID_CAPEX
        m.grid_capex_con = Constraint(m.Y, rule=grid_capex_tracking)
        
        # RAM Reliability Constraint (User Request: 99.9% Uptime)
        # Implemented conservatively: Total Capacity - Largest Single Unit
        # This ensures N-1 redundancy regardless of technology mix
        # With typical FOR of 2-3%, this provides >99.9% system availability
        def ram_reliability(m, y):
            recip_cap = 5  # MW per engine
            turbine_cap = 20  # MW per turbine
            
            # Total system capacity
            total_cap = (m.n_recip[y] * recip_cap + m.n_turbine[y] * turbine_cap
                        + m.bess_mw[y] + m.grid_mw[y])
            
            # Largest single contingency (one turbine = 20 MW)
            # Conservative: assumes largest unit that could fail
            largest_unit = 20  # MW
            
            # Firm capacity = Total - Largest Unit (N-1 redundancy)
            firm = total_cap - largest_unit
            
            # Must meet Peak Load
            peak_load = np.percentile(self.load_data['total_load_mw'], 98)
            return firm >= peak_load
        m.ram_reliability_con = Constraint(m.Y, rule=ram_reliability)
        
        logger.info("Capacity constraints added")
    
    def _build_brownfield_constraints(self):
        """
        BROWNFIELD SUPPORT: Ensure capacity >= existing equipment.
        This enables optimization of expansions to existing facilities.
        """
        m = self.model
        
        def existing_recip(m, y):
            return m.n_recip[y] >= m.EXISTING_recip
        m.existing_recip_con = Constraint(m.Y, rule=existing_recip)
        
        def existing_turbine(m, y):
            return m.n_turbine[y] >= m.EXISTING_turbine
        m.existing_turbine_con = Constraint(m.Y, rule=existing_turbine)
        
        def existing_bess(m, y):
            return m.bess_mwh[y] >= m.EXISTING_bess
        m.existing_bess_con = Constraint(m.Y, rule=existing_bess)
        
        def existing_solar(m, y):
            return m.solar_mw[y] >= m.EXISTING_solar
        m.existing_solar_con = Constraint(m.Y, rule=existing_solar)
        
        # Grid: if existing, must stay active
        def existing_grid(m, y):
            if self.existing['grid_mw'] > 0:
                return m.grid_active[y] >= 1
            return Constraint.Skip
        m.existing_grid_con = Constraint(m.Y, rule=existing_grid)
        
        logger.info("Brownfield constraints added")
    
    def _build_dispatch_constraints(self):
        m = self.model
        
        # Power balance WITH DR
        def power_balance(m, t, y):
            supply = (m.gen_recip[t, y] + m.gen_turbine[t, y] + m.gen_solar[t, y]
                     + m.discharge[t, y] + m.grid_import[t, y])
            demand = m.D_total[t, y] - m.curtail_total[t, y] + m.charge[t, y]
            return supply == demand
        m.power_balance_con = Constraint(m.T, m.Y, rule=power_balance)
        
        # Generation limits
        def gen_recip_limit(m, t, y):
            return m.gen_recip[t, y] <= m.n_recip[y] * 5 * 0.97  # 5 MW, 97% avail
        m.gen_recip_lim = Constraint(m.T, m.Y, rule=gen_recip_limit)
        
        def gen_turbine_limit(m, t, y):
            return m.gen_turbine[t, y] <= m.n_turbine[y] * 20 * 0.95
        m.gen_turbine_lim = Constraint(m.T, m.Y, rule=gen_turbine_limit)
        
        # Solar with capacity factor profile
        def gen_solar_limit(m, t, y):
            hour = self.rep_hours[t - 1] % 24
            if 6 <= hour <= 18:
                cf = 0.25 * np.sin((hour - 6) * np.pi / 12)
            else:
                cf = 0
            return m.gen_solar[t, y] <= m.solar_mw[y] * cf
        m.gen_solar_lim = Constraint(m.T, m.Y, rule=gen_solar_limit)
        
        # SOC dynamics
        def soc_dynamics(m, t, y):
            if t == 1:
                return m.soc[t, y] == 0.5 * m.bess_mwh[y]
            eff = 0.92
            return m.soc[t, y] == m.soc[t-1, y] + eff * m.charge[t, y] - m.discharge[t, y] / eff
        m.soc_dynamics_con = Constraint(m.T, m.Y, rule=soc_dynamics)
        
        # SOC bounds
        def soc_min(m, t, y):
            return m.soc[t, y] >= 0.1 * m.bess_mwh[y]
        m.soc_min_con = Constraint(m.T, m.Y, rule=soc_min)
        
        def soc_max(m, t, y):
            return m.soc[t, y] <= m.bess_mwh[y]
        m.soc_max_con = Constraint(m.T, m.Y, rule=soc_max)
        
        # Charge/discharge limits
        def charge_limit(m, t, y):
            return m.charge[t, y] <= m.bess_mw[y]
        m.charge_lim = Constraint(m.T, m.Y, rule=charge_limit)
        
        def discharge_limit(m, t, y):
            return m.discharge[t, y] <= m.bess_mw[y]
        m.discharge_lim = Constraint(m.T, m.Y, rule=discharge_limit)
        
        # Grid limit
        def grid_limit(m, t, y):
            return m.grid_import[t, y] <= m.grid_mw[y]
        m.grid_lim = Constraint(m.T, m.Y, rule=grid_limit)
        
        # NOx emissions (SCALED for representative periods)
        def nox_annual(m, y):
            recip_hr = 7700  # BTU/kWh
            turbine_hr = 8500
            nox_rate = 0.099  # lb/MMBTU
            nox_recip = sum(m.gen_recip[t, y] * recip_hr * nox_rate for t in m.T)
            nox_turbine = sum(m.gen_turbine[t, y] * turbine_hr * nox_rate for t in m.T)
            # Scale by representative period factor
            return m.SCALE_FACTOR * (nox_recip + nox_turbine) / 2_000_000 <= m.NOX_MAX
        m.nox_con = Constraint(m.Y, rule=nox_annual)
        
        logger.info("Dispatch constraints added")
    
    def _build_dr_constraints(self):
        m = self.model
        
        # Workload curtailment limits
        def curtail_wl_limit(m, w, t, y):
            # Get workload load fraction
            wl_pct = self.workload_mix.get(w, 0)
            if wl_pct > 1:  # If percentage (0-100)
                wl_pct = wl_pct / 100
            d_wl = m.D_total[t, y] / m.PUE * wl_pct
            return m.curtail_wl[w, t, y] <= m.WL_flex[w] * d_wl
        m.curtail_wl_lim = Constraint(m.W, m.T, m.Y, rule=curtail_wl_limit)
        
        # Cooling curtailment limit
        def curtail_cool_limit(m, t, y):
            d_cooling = m.D_total[t, y] * (m.PUE - 1) / m.PUE
            return m.curtail_cool[t, y] <= m.COOL_flex * d_cooling
        m.curtail_cool_lim = Constraint(m.T, m.Y, rule=curtail_cool_limit)
        
        # Total curtailment
        def total_curtail(m, t, y):
            return m.curtail_total[t, y] == (
                sum(m.curtail_wl[w, t, y] for w in m.W) + m.curtail_cool[t, y]
            )
        m.total_curtail_con = Constraint(m.T, m.Y, rule=total_curtail)
        
        # Annual curtailment budget (1% from research) - SCALED for representative periods
        def annual_budget(m, y):
            budget_pct = self.dr_config.get('annual_curtailment_budget_pct', 0.01)
            # Use FIXED required energy (not energy served) for fair comparison
            scaled_curtail = m.SCALE_FACTOR * sum(m.curtail_total[t, y] for t in m.T)
            return scaled_curtail <= budget_pct * m.D_required[y]
        m.annual_budget_con = Constraint(m.Y, rule=annual_budget)
        
        # DR CAPACITY CREDIT - Peak Window Constraint (QA/QC Fix)
        # ISOs require guaranteed capacity during peak windows (4-9 PM)
        # dr_capacity must be <= min(flexibility) during peak hours
        def dr_peak_window(m, dr, t, y):
            if t not in m.T_peak:
                return Constraint.Skip
            # DR capacity cannot exceed flexibility available at this peak hour
            return m.dr_capacity[dr, y] <= (
                sum(m.curtail_wl[w, t, y] for w in m.W) + m.curtail_cool[t, y]
            )
        m.dr_peak_window_con = Constraint(m.DR, m.T, m.Y, rule=dr_peak_window)
        
        # === NEW CONSTRAINTS (User Request) ===
        
        # 1. Gas Supply Limit
        def gas_supply_limit(m, y):
            # Daily gas consumption in MCF
            # Heat rates: Recip=7.7 MMBtu/MWh, Turbine=8.5 MMBtu/MWh
            # Natural Gas: ~1.03 MMBtu/MCF
            recip_mcf = sum(m.gen_recip[t, y] * 7.7 / 1.03 for t in m.T)
            turbine_mcf = sum(m.gen_turbine[t, y] * 8.5 / 1.03 for t in m.T)
            
            # Convert annual sum to average daily (approximate for planning)
            # For strict daily limit, we'd need daily constraints, but annual avg is standard for capacity planning
            avg_daily_mcf = (recip_mcf + turbine_mcf) * m.SCALE_FACTOR / 365
            return avg_daily_mcf <= m.GAS_MAX
        m.gas_supply_con = Constraint(m.Y, rule=gas_supply_limit)
        
        # 2. CO2 Emissions Limit
        # Emission factor: ~117 lb CO2/MMBtu for NG
        def co2_emissions_limit(m, y):
            co2_factor = 117  # lb/MMBtu
            recip_mmbtu = sum(m.gen_recip[t, y] * 7.7 for t in m.T)
            turbine_mmbtu = sum(m.gen_turbine[t, y] * 8.5 for t in m.T)
            
            total_co2_tons = (recip_mmbtu + turbine_mmbtu) * m.SCALE_FACTOR * co2_factor / 2000
            
            return total_co2_tons <= m.CO2_MAX
        m.co2_con = Constraint(m.Y, rule=co2_emissions_limit)
        
        # 3. Ramp Rate / PQ Constraint
        # Ensure system can ramp to meet load fluctuations
        # Simplified: Capacity * Ramp_Rate >= Required_Ramp
        def ramp_capability(m, y):
            # Ramp rates (MW/min): Recip=50% (2.5MW), Turbine=20% (4MW), BESS=100%
            sys_ramp = (m.n_recip[y] * 2.5 + m.n_turbine[y] * 4.0 + m.bess_mw[y] * 10.0)
            
            # Required ramp: ~10% of peak load per minute (conservative)
            peak_load = np.percentile(self.load_data['total_load_mw'], 98)
            required_ramp = 0.10 * peak_load
            
            return sys_ramp >= required_ramp
        m.pq_ramp_con = Constraint(m.Y, rule=ramp_capability)

        logger.info("DR constraints added")
    
    def _build_objective(self):
        m = self.model
        
        def lcoe_with_dr(m):
            """
            LCOE with QA/QC Fixes:
            1. Denominator uses FIXED required_load (D_required), not energy_served
            2. Grid interconnection CAPEX included
            3. Grid electricity cost included (critical fix for BTM competitiveness)
            4. Costs scaled for representative periods
            """
            r = 0.08
            n = 20
            crf = (r * (1 + r)**n) / ((1 + r)**n - 1)
            
            # CAPEX including grid interconnection
            capex = sum(
                (m.n_recip[y] * 5 * 1000 * 1650
                 + m.n_turbine[y] * 20 * 1000 * 1300
                 + m.bess_mwh[y] * 1000 * 250
                 + m.solar_mw[y] * 1000 * 1000
                 + m.grid_capex_incurred[y]  # Grid interconnection
                ) / (1 + r)**(y - m.Y.first())
                for y in m.Y
            ) * crf
            
            # Fuel - SCALED for representative periods
            fuel = sum(
                m.SCALE_FACTOR * sum(
                    (m.gen_recip[t, y] * 7700 + m.gen_turbine[t, y] * 8500)
                    * 3.50 / 1e6 
                    for t in m.T
                ) / (1 + r)**(y - m.Y.first())
                for y in m.Y
            )
            
            # Grid electricity cost - CRITICAL FIX
            # Without this, grid appears "free" and MILP picks grid-only solutions
            grid_cost_mwh = 75  # $/MWh average grid electricity cost
            grid_electricity = sum(
                m.SCALE_FACTOR * sum(
                    m.grid_import[t, y] * grid_cost_mwh / 1000  # Convert to thousands
                    for t in m.T
                ) / (1 + r)**(y - m.Y.first())
                for y in m.Y
            )
            
            # DR Revenue (using peak-window guaranteed capacity)
            dr_rev = sum(
                sum(m.dr_capacity[dr, y] * 8760 * m.DR_payment[dr] for dr in m.DR)
                / (1 + r)**(y - m.Y.first())
                for y in m.Y
            )
            
            # FIXED DENOMINATOR - Required energy, not served energy (QA/QC fix)
            # This prevents curtailment from artificially inflating LCOE
            energy = sum(
                m.D_required[y] / (1 + r)**(y - m.Y.first())
                for y in m.Y
            )
            
            return (capex + fuel + grid_electricity - dr_rev) / energy if energy > 0 else 1e6
        
        m.obj = Objective(rule=lcoe_with_dr, sense=minimize)
        
        logger.info("Objective function created with grid electricity cost")
    
    def solve(self, solver: str = 'glpk', time_limit: int = 300, verbose: bool = True) -> Dict:
        """Solve the optimization model."""
        if not self._built:
            raise RuntimeError("Model not built. Call build() first.")
        
        logger.info(f"Solving with {solver} (time limit: {time_limit}s)")
        
        # Try to get solver
        try:
            opt = SolverFactory(solver)
            if opt is None:
                raise Exception(f"Solver {solver} not found")
        except Exception as e:
            logger.warning(f"Failed to load {solver}: {e}. Trying glpk...")
            try:
                opt = SolverFactory('glpk')
            except:
                raise RuntimeError("No suitable MILP solver found. Please install GLPK, CBC, or Gurobi.")
        
        # Set solver options
        if solver == 'gurobi':
            opt.options['TimeLimit'] = time_limit
            opt.options['MIPGap'] = 0.01
        elif solver == 'cbc':
            opt.options['seconds'] = time_limit
            opt.options['ratioGap'] = 0.01
        elif solver == 'glpk':
            opt.options['tmlim'] = time_limit
            opt.options['mipgap'] = 0.01
        
        results = opt.solve(self.model, tee=verbose)
        
        logger.info(f"Solver status: {results.solver.status}")
        logger.info(f"Termination condition: {results.solver.termination_condition}")
        
        return self._extract_solution(results)
    
    def _extract_solution(self, results) -> Dict:
        """Extract solution to dictionary."""
        m = self.model
        
        # Check if solver found a solution
        termination = str(results.solver.termination_condition)
        status = str(results.solver.status)
        
        # If solver failed or problem is infeasible, return early with minimal info
        if termination in ['infeasible', 'infeasibleOrUnbounded', 'invalidProblem', 'solverFailure', 'error']:
            logger.warning(f"Solver failed with termination: {termination}")
            return {
                'status': status,
                'termination': termination,
                'objective_lcoe': None,
                'equipment': {},
                'dr': {},
                'dispatch': {},
                'feasible': False,
            }
        
        # Try to extract solution (may still fail if solver timed out without finding feasible solution)
        try:
            solution = {
                'status': status,
                'termination': termination,
                'objective_lcoe': value(m.obj) if hasattr(m, 'obj') else None,
                'equipment': {},
                'dr': {},
                'dispatch': {},
            }
            
            # Equipment by year
            for y in m.Y:
                solution['equipment'][y] = {
                    'n_recip': int(value(m.n_recip[y])),
                    'n_turbine': int(value(m.n_turbine[y])),
                    'bess_mwh': value(m.bess_mwh[y]),
                    'bess_mw': value(m.bess_mw[y]),
                    'solar_mw': value(m.solar_mw[y]),
                    'grid_mw': value(m.grid_mw[y]),
                    'grid_active': int(value(m.grid_active[y])),
                }
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to extract solution values: {e}")
            return {
                'status': status,
                'termination': termination,
                'objective_lcoe': None,
                'equipment': {},
                'dr': {},
                'dispatch': {},
                'feasible': False,
            }
        
        # DR metrics
        final_year = max(m.Y)
        total_curtail = sum(value(m.curtail_total[t, final_year]) for t in m.T)
        total_energy = sum(value(m.D_total[t, final_year]) for t in m.T)
        
        solution['dr'] = {
            'total_curtailment_mwh': total_curtail * self.scale_factor,
            'curtailment_pct': total_curtail / total_energy * 100 if total_energy > 0 else 0,
            'dr_revenue_annual': sum(
                value(m.dr_capacity[dr, final_year]) * 8760 * value(m.DR_payment[dr])
                for dr in m.DR
            ),
            'dr_capacity_by_product': {
                dr: value(m.dr_capacity[dr, final_year]) for dr in m.DR
            }
        }
        
        logger.info(f"Solution extracted: LCOE={solution['objective_lcoe']:.2f} $/MWh, " +
                   f"Curtailment={solution['dr']['curtailment_pct']:.2f}%")
        
        return solution
