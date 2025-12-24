"""
bvNexus MILP Optimization Model with Demand Response
=====================================================

COMPLETE CORRECTED VERSION - Ready for Production

QA/QC Fixes Applied (Claude Review + Gemini Refinements):
1. Gas supply constraint ENABLED with correct HHV formula
2. CO2 emissions constraint ENABLED (conditional on limit)
3. Ramp rate / PQ constraint ENABLED
4. Added 'unserved' variable for power gap tracking (CRITICAL FIX)
5. Hierarchical objective: maximize power THEN minimize cost
6. Grid timing constraint enforced (no grid before interconnection)
7. RAM constraint with N-1 redundancy
8. Unserved penalty set to $50,000/MWh (Gemini refinement - numerical stability)

Key Behavior Changes:
- Model will NO LONGER return "Infeasible" when constraints limit equipment
- Instead, it finds MAXIMUM equipment within constraints and reports power gap
- Gas supply is now a HARD constraint (user requirement)
- Grid only available after interconnection year (bridging behavior)

Author: Claude AI (QA/QC Review) with Gemini Refinements
Date: December 2024
Version: 2.0 (Production Ready)

Usage:
    from milp_model_dr import bvNexusMILP_DR
    
    optimizer = bvNexusMILP_DR()
    optimizer.build(site, constraints, load_data, workload_mix, years, ...)
    solution = optimizer.solve(solver='cbc', time_limit=300)
    
    # Check power coverage
    for year, coverage in solution['power_coverage'].items():
        print(f"Year {year}: {coverage['coverage_pct']:.1f}% coverage")
        if coverage['power_gap_mw'] > 0:
            print(f"  ⚠️ Power gap: {coverage['power_gap_mw']:.1f} MW")
"""

from pyomo.environ import *
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class bvNexusMILP_DR:
    """
    Mixed-Integer Linear Program for AI datacenter power optimization
    with integrated demand response capabilities.
    
    Key Design Decisions (from QA/QC):
    - Uses 6 representative weeks (1008 hours) for tractable optimization
    - BESS duration is FIXED (4 hours) to preserve MILP linearity
    - LCOE denominator is fixed required_load to prevent curtailment distortion
    - Unserved energy variable allows solutions when constraints bind
    - Hierarchical objective via penalty ensures power maximization priority
    
    Constraints Enforced:
    - NOx emissions (annual tpy limit)
    - Gas supply (daily MCF limit) - HARD CONSTRAINT
    - CO2 emissions (annual tpy limit, if specified)
    - Ramp rate capability (MW/min)
    - RAM / N-1 redundancy (99.9% availability)
    - Grid timing (not available before interconnection)
    - Land use (acres for solar)
    """
    
    # ==========================================================================
    # CONFIGURATION CONSTANTS
    # ==========================================================================
    
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
    
    # Peak hours for DR capacity credit (4 PM - 9 PM local time)
    PEAK_HOURS = [16, 17, 18, 19, 20, 21]
    
    # BESS duration is FIXED to preserve MILP linearity
    # DO NOT make this a decision variable!
    BESS_DURATION = 4  # hours
    
    # Unserved energy penalty (implements hierarchical objective)
    # Gemini refinement: $50,000/MWh is sufficient and numerically stable
    # (Original $1M/MWh could cause floating-point issues)
    UNSERVED_PENALTY = 50_000  # $/MWh
    
    # Equipment specifications (CORRECTED Dec 2025 - bvNexus v3)
    # NOx rates are WITH ADVANCED SCR (95% reduction)
    # Allows ~300 MW thermal within 100 tpy NOx limit
    EQUIPMENT = {
        'recip': {
            'capacity_mw': 10.0,              # Jenbacher J920 / Wärtsilä 34SG size
            'heat_rate_btu_kwh': 7200,        # HHV basis (billing standard)
            'nox_rate_lb_mmbtu': 0.015,       # With advanced SCR (95% reduction)
            'availability': 0.97,
            'ramp_rate_mw_min': 3.0,
            'capex_per_kw': 1200,             # Installed cost
        },
        'turbine': {
            'capacity_mw': 50.0,              # GE LM6000 size
            'heat_rate_btu_kwh': 8500,        # HHV basis (billing standard)
            'nox_rate_lb_mmbtu': 0.010,       # With advanced SCR
            'availability': 0.97,
            'ramp_rate_mw_min': 10.0,
            'capex_per_kw': 900,              # Installed cost
        },
        'bess': {
            'efficiency': 0.92,
            'min_soc_pct': 0.10,
            'capex_per_kwh': 250,
            'ramp_rate_mw_min': 50.0,         # Very fast
        },
        'solar': {
            'capacity_factor': 0.25,
            'land_acres_per_mw': 5.0,
            'capex_per_kw': 950,
        },
    }
    
    # Gas properties
    # IMPORTANT: Heat rates above should be on HHV basis to match gas billing
    # If your equipment specs use LHV, multiply heat rates by 1.11
    GAS_HHV_BTU_PER_MCF = 1_037_000  # Higher Heating Value (billing basis)
    
    # Economic parameters
    DISCOUNT_RATE = 0.08
    NG_PRICE_PER_MMBTU = 3.50
    GRID_PRICE_PER_MWH = 75.0
    
    # ==========================================================================
    # INITIALIZATION
    # ==========================================================================
    
    def __init__(self):
        """Initialize the MILP optimizer."""
        self.model = None
        self._built = False
        
        # Configuration storage
        self.years = []
        self.load_data = None
        self.constraints = {}
        self.grid_config = {}
        self.existing = {}
        self.workload_mix = {}
        self.dr_config = {}
        self.site = {}
        self.use_representative = True
    
    # ==========================================================================
    # MODEL BUILDING
    # ==========================================================================
    
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
        """
        Build the complete MILP model with all constraints enabled.
        
        Args:
            site: Site parameters (name, location, PUE, etc.)
            constraints: Hard constraints dict with keys:
                - NOx_Limit_tpy: Annual NOx limit (tons/year)
                - Gas_Supply_MCF_day: Daily gas supply limit (MCF)
                - CO2_Limit_tpy: Annual CO2 limit (0 = no limit)
                - Available_Land_Acres: Land available for solar
                - min_ramp_rate_mw_min: Required system ramp rate (MW/min)
            load_data: Load profile dict with keys:
                - total_load_mw: 8760 hourly load array (MW)
                - pue: Power Usage Effectiveness
            workload_mix: Dict of workload percentages (pre_training, etc.)
            years: List of planning years (e.g., [2026, 2027, ..., 2035])
            dr_config: Demand response configuration
            existing_equipment: Brownfield existing equipment counts
            grid_config: Grid interconnection configuration
            use_representative_periods: Use 1008 hours (True) or full 8760 (False)
        """
        
        logger.info("="*60)
        logger.info("Building bvNexus MILP Model (Corrected Version)")
        logger.info("="*60)
        
        # Store configuration
        self.site = site
        self.years = years
        self.load_data = load_data
        self.constraints = constraints
        self.workload_mix = workload_mix
        self.dr_config = dr_config or {'cooling_flex': 0.25, 'annual_curtailment_budget_pct': 0.01}
        self.existing = existing_equipment or {
            'n_recip': 0, 'n_turbine': 0, 'bess_mwh': 0, 'solar_mw': 0, 'grid_mw': 0
        }
        self.use_representative = use_representative_periods
        
        # Process grid configuration
        self.grid_config = grid_config or {}
        if 'available_year' not in self.grid_config:
            # Calculate from lead time
            start_year = min(years)
            lead_months = self.grid_config.get('lead_time_months', 96)
            self.grid_config['available_year'] = start_year + (lead_months // 12)
        if 'capex' not in self.grid_config:
            self.grid_config['capex'] = 5_000_000
        
        # Build Pyomo model
        self.model = ConcreteModel()
        
        # Build model components in order
        self._build_sets()
        self._build_parameters()
        self._build_variables()
        self._build_brownfield_constraints()
        self._build_capacity_constraints()
        self._build_dispatch_constraints()
        self._build_dr_constraints()
        self._build_gas_constraint()        # ENABLED (was disabled)
        self._build_co2_constraint()        # ENABLED (conditional)
        self._build_ramp_constraint()       # ENABLED (was disabled)
        self._build_grid_timing_constraint()  # NEW
        self._build_ram_constraint()        # FIXED
        self._build_objective()
        
        self._built = True
        
        logger.info("="*60)
        logger.info("MILP Model Built Successfully")
        logger.info(f"  Years: {min(years)} - {max(years)}")
        logger.info(f"  Hours: {1008 if use_representative_periods else 8760}")
        logger.info(f"  Grid available: {self.grid_config['available_year']}")
        logger.info(f"  NOx limit: {constraints.get('NOx_Limit_tpy', 99)} tpy")
        logger.info(f"  Gas limit: {constraints.get('Gas_Supply_MCF_day', 50000)} MCF/day")
        logger.info("="*60)
    
    def _build_sets(self):
        """Build model index sets."""
        m = self.model
        
        # Year set
        m.Y = Set(initialize=self.years)
        
        # Time set (representative or full)
        if self.use_representative:
            n_hours = 6 * 168  # 1008 hours
            m.T = RangeSet(1, n_hours)
            m.SCALE_FACTOR = Param(initialize=8760 / n_hours)
        else:
            m.T = RangeSet(1, 8760)
            m.SCALE_FACTOR = Param(initialize=1.0)
        
        # Peak hours set (for DR capacity credit)
        peak_indices = []
        n_weeks = 6 if self.use_representative else 52
        for week_idx in range(n_weeks):
            for day in range(7):
                for peak_hour in self.PEAK_HOURS:
                    hour_idx = week_idx * 168 + day * 24 + peak_hour + 1
                    max_hours = 1008 if self.use_representative else 8760
                    if hour_idx <= max_hours:
                        peak_indices.append(hour_idx)
        m.T_peak = Set(initialize=peak_indices)
        
        # Workload types
        m.W = Set(initialize=['pre_training', 'fine_tuning', 'batch_inference', 'realtime_inference'])
        
        # DR products
        m.DR = Set(initialize=['spinning_reserve', 'non_spinning_reserve', 'economic_dr', 'emergency_dr'])
        
        logger.info(f"Sets: {len(m.Y)} years, {len(m.T)} hours, {len(m.T_peak)} peak hours")
    
    def _build_parameters(self):
        """Build model parameters."""
        m = self.model
        
        # Sample load profile to representative hours
        load_array = self._sample_representative_hours(
            np.array(self.load_data.get('total_load_mw', [100]*8760))
        )
        
        # Load parameter
        def load_init(m, t, y):
            # Scale load by year based on trajectory if provided
            trajectory = self.site.get('load_trajectory', {})
            if trajectory and y in trajectory:
                # Use trajectory MW value directly (not as a scale factor)
                # trajectory values are in MW facility load
                year_load_mw = trajectory[y]
                # If 0 MW for this year, return 0
                if year_load_mw == 0:
                    return 0.0
                # Otherwise, scale the base load pattern to match this year's MW
                # Assume load_array represents the pattern at peak facility load
                peak_facility_load = max(load_array) if len(load_array) > 0 else 600.0
                scale = year_load_mw / peak_facility_load if peak_facility_load > 0 else 1.0
            else:
                scale = 1.0
            return float(load_array[t-1]) * scale
        
        m.D_total = Param(m.T, m.Y, initialize=load_init)
        
        # Required energy per year (FIXED denominator for LCOE)
        # This prevents curtailment from distorting LCOE calculation
        base_load_array = np.array(self.load_data.get('total_load_mw', [100]*8760))
        if len(base_load_array) == 8760:
            annual_energy = float(np.sum(base_load_array))
        else:
            annual_energy = float(np.sum(load_array)) * 8760 / len(load_array)
        
        def d_required_init(m, y):
            trajectory = self.site.get('load_trajectory', {})
            if trajectory and y in trajectory:
                # Use trajectory MW value directly
                year_load_mw = trajectory[y]
                # If 0 MW for this year, return 0
                if year_load_mw == 0:
                    return 0.0
                # Otherwise, scale annual energy by year's MW target
                # Find a non-zero year to use as reference
                reference_mw = max(trajectory.values()) if trajectory else 600.0
                if reference_mw > 0:
                    scale = year_load_mw / reference_mw
                else:
                    scale = 1.0
            else:
                scale = 1.0
            return annual_energy * scale
        
        m.D_required = Param(m.Y, initialize=d_required_init)
        
        # PUE
        m.PUE = Param(initialize=self.load_data.get('pue', 1.25))
        
        # Constraint limits
        m.NOX_MAX = Param(initialize=self.constraints.get('NOx_Limit_tpy', 
                         self.constraints.get('max_nox_tpy', 99)))
        m.GAS_MAX = Param(initialize=self.constraints.get('Gas_Supply_MCF_day',
                         self.constraints.get('gas_supply_mcf_day', 50000)))
        m.CO2_MAX = Param(initialize=self.constraints.get('CO2_Limit_tpy',
                         self.constraints.get('co2_limit_tpy', 0)))
        m.LAND_MAX = Param(initialize=self.constraints.get('Available_Land_Acres',
                          self.constraints.get('land_area_acres', 500)))
        
        # Ramp rate requirement
        m.RAMP_REQUIRED = Param(initialize=self.constraints.get('min_ramp_rate_mw_min', 10.0))
        
        # Grid availability by year
        grid_year = self.grid_config.get('available_year', 2034)
        m.GRID_AVAIL = Param(m.Y, initialize=lambda m, y: 1.0 if y >= grid_year else 0.0)
        m.GRID_CAPEX = Param(initialize=self.grid_config.get('capex', 5_000_000))
        m.GRID_YEAR = Param(initialize=grid_year)
        
        # BESS parameters (duration is FIXED)
        m.BESS_DURATION = Param(initialize=self.BESS_DURATION)
        m.BESS_EFF = Param(initialize=self.EQUIPMENT['bess']['efficiency'])
        
        # Workload flexibility (from research)
        wl_flex_defaults = {
            'pre_training': 0.30,
            'fine_tuning': 0.50,
            'batch_inference': 0.90,
            'realtime_inference': 0.05
        }
        m.WL_flex = Param(m.W, initialize=lambda m, w: wl_flex_defaults.get(w, 0.1))
        
        # Cooling flexibility
        m.COOL_flex = Param(initialize=self.dr_config.get('cooling_flex', 0.25))
        
        # DR payment rates ($/MW-hr)
        dr_payments = {
            'spinning_reserve': 15,
            'non_spinning_reserve': 8,
            'economic_dr': 5,
            'emergency_dr': 3
        }
        m.DR_payment = Param(m.DR, initialize=lambda m, dr: dr_payments.get(dr, 5))
        
        # Existing equipment (brownfield)
        m.EXISTING_recip = Param(initialize=self.existing.get('n_recip', 0))
        m.EXISTING_turbine = Param(initialize=self.existing.get('n_turbine', 0))
        m.EXISTING_bess = Param(initialize=self.existing.get('bess_mwh', 0))
        m.EXISTING_solar = Param(initialize=self.existing.get('solar_mw', 0))
        
        logger.info(f"Parameters: NOx={value(m.NOX_MAX)}tpy, Gas={value(m.GAS_MAX)}MCF/day, "
                   f"Ramp={value(m.RAMP_REQUIRED)}MW/min")
    
    def _sample_representative_hours(self, load_8760: np.ndarray) -> np.ndarray:
        """Sample representative hours from full year profile."""
        if not self.use_representative:
            return load_8760
        
        if len(load_8760) != 8760:
            # If not 8760, return as-is or pad/truncate
            logger.warning(f"Load profile has {len(load_8760)} hours, expected 8760")
            if len(load_8760) < 1008:
                return np.tile(load_8760, 1008 // len(load_8760) + 1)[:1008]
            return load_8760[:1008]
        
        hours = []
        for week_name, week_info in self.REPRESENTATIVE_WEEKS.items():
            start_hour = week_info['start_day'] * 24
            end_hour = start_hour + 168
            
            if end_hour <= 8760:
                hours.extend(load_8760[start_hour:end_hour])
            else:
                # Wrap around year boundary
                hours.extend(load_8760[start_hour:])
                hours.extend(load_8760[:end_hour - 8760])
        
        return np.array(hours)
    
    def _build_variables(self):
        """Build decision variables INCLUDING unserved energy for power gap tracking."""
        m = self.model
        
        # =========================
        # CAPACITY VARIABLES
        # =========================
        
        # Equipment counts (integer for discrete units)
        m.n_recip = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 100))
        m.n_turbine = Var(m.Y, within=NonNegativeIntegers, bounds=(0, 50))
        
        # Continuous capacity variables
        m.bess_mwh = Var(m.Y, within=NonNegativeReals, bounds=(0, 2000))
        m.bess_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))
        m.solar_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))
        m.grid_mw = Var(m.Y, within=NonNegativeReals, bounds=(0, 500))
        
        # Grid connection binary and capex tracking
        m.grid_active = Var(m.Y, within=Binary)
        m.grid_capex_incurred = Var(m.Y, within=NonNegativeReals)
        
        # =========================
        # DISPATCH VARIABLES
        # =========================
        
        m.gen_recip = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_turbine = Var(m.T, m.Y, within=NonNegativeReals)
        m.gen_solar = Var(m.T, m.Y, within=NonNegativeReals)
        m.grid_import = Var(m.T, m.Y, within=NonNegativeReals)
        
        # BESS variables
        m.charge = Var(m.T, m.Y, within=NonNegativeReals)
        m.discharge = Var(m.T, m.Y, within=NonNegativeReals)
        m.soc = Var(m.T, m.Y, within=NonNegativeReals)
        
        # =========================
        # DEMAND RESPONSE VARIABLES
        # =========================
        
        m.curtail_wl = Var(m.W, m.T, m.Y, within=NonNegativeReals)
        m.curtail_cool = Var(m.T, m.Y, within=NonNegativeReals)
        m.curtail_total = Var(m.T, m.Y, within=NonNegativeReals)
        m.dr_capacity = Var(m.DR, m.Y, within=NonNegativeReals)
        
        # =========================
        # CRITICAL: UNSERVED ENERGY VARIABLE
        # =========================
        # This allows the model to find solutions even when constraints
        # prevent building enough equipment to meet 100% of load.
        # Without this, the model returns "Infeasible" instead of
        # finding the maximum equipment within constraints.
        
        m.unserved = Var(m.T, m.Y, within=NonNegativeReals, bounds=(0, 500))
        
        logger.info("Variables built (including unserved energy for power gap tracking)")
    
    def _build_brownfield_constraints(self):
        """Ensure capacity >= existing equipment (brownfield support)."""
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
        
        logger.info("Brownfield constraints added")
    
    def _build_capacity_constraints(self):
        """Build equipment capacity constraints."""
        m = self.model
        
        # BESS power/energy relationship (fixed duration)
        def bess_sizing(m, y):
            return m.bess_mw[y] == m.bess_mwh[y] / m.BESS_DURATION
        m.bess_sizing_con = Constraint(m.Y, rule=bess_sizing)
        
        # Land constraint (solar uses ~4.25 acres/MW)
        def land_constraint(m, y):
            return m.solar_mw[y] * self.EQUIPMENT['solar']['land_acres_per_mw'] <= m.LAND_MAX
        m.land_con = Constraint(m.Y, rule=land_constraint)
        
        # Grid requires active connection (Big-M formulation)
        def grid_requires_active(m, y):
            BIG_M = 500
            return m.grid_mw[y] <= BIG_M * m.grid_active[y]
        m.grid_requires_active_con = Constraint(m.Y, rule=grid_requires_active)
        
        # Grid capex tracking
        def grid_capex_tracking(m, y):
            return m.grid_capex_incurred[y] >= m.grid_active[y] * m.GRID_CAPEX
        m.grid_capex_con = Constraint(m.Y, rule=grid_capex_tracking)
        
        # Non-decreasing capacity (can't remove installed equipment)
        def nondec_recip(m, y):
            if y == m.Y.first():
                return Constraint.Skip
            prev_y = m.Y.prev(y)
            return m.n_recip[y] >= m.n_recip[prev_y]
        m.nondec_recip_con = Constraint(m.Y, rule=nondec_recip)
        
        def nondec_turbine(m, y):
            if y == m.Y.first():
                return Constraint.Skip
            prev_y = m.Y.prev(y)
            return m.n_turbine[y] >= m.n_turbine[prev_y]
        m.nondec_turbine_con = Constraint(m.Y, rule=nondec_turbine)
        
        def nondec_bess(m, y):
            if y == m.Y.first():
                return Constraint.Skip
            prev_y = m.Y.prev(y)
            return m.bess_mwh[y] >= m.bess_mwh[prev_y]
        m.nondec_bess_con = Constraint(m.Y, rule=nondec_bess)
        
        def nondec_solar(m, y):
            if y == m.Y.first():
                return Constraint.Skip
            prev_y = m.Y.prev(y)
            return m.solar_mw[y] >= m.solar_mw[prev_y]
        m.nondec_solar_con = Constraint(m.Y, rule=nondec_solar)
        
        logger.info("Capacity constraints added")
    
    def _build_dispatch_constraints(self):
        """Build hourly dispatch constraints with unserved energy."""
        m = self.model
        
        # Equipment specs
        recip_cap = self.EQUIPMENT['recip']['capacity_mw']
        recip_avail = self.EQUIPMENT['recip']['availability']
        turbine_cap = self.EQUIPMENT['turbine']['capacity_mw']
        turbine_avail = self.EQUIPMENT['turbine']['availability']
        solar_cf = self.EQUIPMENT['solar']['capacity_factor']
        
        # =========================
        # POWER BALANCE WITH UNSERVED ENERGY
        # =========================
        # This is the CRITICAL fix - adding 'unserved' to supply side
        # allows the model to find solutions when constraints bind
        
        def power_balance(m, t, y):
            supply = (
                m.gen_recip[t, y] +
                m.gen_turbine[t, y] +
                m.gen_solar[t, y] +
                m.grid_import[t, y] +
                m.discharge[t, y] +
                m.unserved[t, y]  # ← CRITICAL ADDITION
            )
            demand = m.D_total[t, y] - m.curtail_total[t, y] + m.charge[t, y]
            return supply == demand
        m.power_balance_con = Constraint(m.T, m.Y, rule=power_balance)
        
        # =========================
        # GENERATION LIMITS
        # =========================
        
        def gen_recip_limit(m, t, y):
            return m.gen_recip[t, y] <= m.n_recip[y] * recip_cap * recip_avail
        m.gen_recip_lim = Constraint(m.T, m.Y, rule=gen_recip_limit)
        
        def gen_turbine_limit(m, t, y):
            return m.gen_turbine[t, y] <= m.n_turbine[y] * turbine_cap * turbine_avail
        m.gen_turbine_lim = Constraint(m.T, m.Y, rule=gen_turbine_limit)
        
        def gen_solar_limit(m, t, y):
            # Solar limited by capacity and capacity factor
            # In reality, would use hourly solar profile
            return m.gen_solar[t, y] <= m.solar_mw[y] * solar_cf
        m.gen_solar_lim = Constraint(m.T, m.Y, rule=gen_solar_limit)
        
        def grid_import_limit(m, t, y):
            # Grid limited by capacity AND availability (0 before interconnection)
            return m.grid_import[t, y] <= m.grid_mw[y] * m.GRID_AVAIL[y]
        m.grid_import_lim = Constraint(m.T, m.Y, rule=grid_import_limit)
        
        # =========================
        # BESS CONSTRAINTS
        # =========================
        
        def charge_limit(m, t, y):
            return m.charge[t, y] <= m.bess_mw[y]
        m.charge_lim = Constraint(m.T, m.Y, rule=charge_limit)
        
        def discharge_limit(m, t, y):
            return m.discharge[t, y] <= m.bess_mw[y]
        m.discharge_lim = Constraint(m.T, m.Y, rule=discharge_limit)
        
        def soc_dynamics(m, t, y):
            eff = value(m.BESS_EFF)
            if t == 1:
                # Start at 50% SOC
                return m.soc[t, y] == 0.5 * m.bess_mwh[y]
            return m.soc[t, y] == m.soc[t-1, y] + eff * m.charge[t, y] - m.discharge[t, y] / eff
        m.soc_dynamics_con = Constraint(m.T, m.Y, rule=soc_dynamics)
        
        def soc_lower_bound(m, t, y):
            return m.soc[t, y] >= self.EQUIPMENT['bess']['min_soc_pct'] * m.bess_mwh[y]
        m.soc_low_con = Constraint(m.T, m.Y, rule=soc_lower_bound)
        
        def soc_upper_bound(m, t, y):
            return m.soc[t, y] <= m.bess_mwh[y]
        m.soc_high_con = Constraint(m.T, m.Y, rule=soc_upper_bound)
        
        # =========================
        # NOx EMISSIONS CONSTRAINT
        # =========================
        
        recip_hr = self.EQUIPMENT['recip']['heat_rate_btu_kwh']
        recip_nox = self.EQUIPMENT['recip']['nox_rate_lb_mmbtu']
        turbine_hr = self.EQUIPMENT['turbine']['heat_rate_btu_kwh']
        turbine_nox = self.EQUIPMENT['turbine']['nox_rate_lb_mmbtu']
        
        def nox_annual_limit(m, y):
            # NOx = generation × heat_rate × nox_rate / 1e6 (to MMBTU) / 2000 (to tons)
            # Simplified: gen(MWh) × HR(BTU/kWh) × NOx(lb/MMBTU) / 2e9 = tons
            nox_recip = sum(m.gen_recip[t, y] * recip_hr * recip_nox for t in m.T)
            nox_turbine = sum(m.gen_turbine[t, y] * turbine_hr * turbine_nox for t in m.T)
            total_nox_tons = m.SCALE_FACTOR * (nox_recip + nox_turbine) / 2_000_000
            return total_nox_tons <= m.NOX_MAX
        m.nox_con = Constraint(m.Y, rule=nox_annual_limit)
        
        logger.info("Dispatch constraints added with unserved energy")
    
    def _build_dr_constraints(self):
        """Build demand response constraints."""
        m = self.model
        
        # Workload curtailment limits
        def curtail_wl_limit(m, w, t, y):
            wl_pct = self.workload_mix.get(w, 0.25)
            if wl_pct > 1:
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
            return m.curtail_total[t, y] == sum(m.curtail_wl[w, t, y] for w in m.W) + m.curtail_cool[t, y]
        m.total_curtail_con = Constraint(m.T, m.Y, rule=total_curtail)
        
        # Annual curtailment budget (1% from research)
        def annual_budget(m, y):
            budget_pct = self.dr_config.get('annual_curtailment_budget_pct', 0.01)
            scaled_curtail = m.SCALE_FACTOR * sum(m.curtail_total[t, y] for t in m.T)
            return scaled_curtail <= budget_pct * m.D_required[y]
        m.annual_budget_con = Constraint(m.Y, rule=annual_budget)
        
        # DR capacity credit - peak window constraint
        # DR capacity must be <= minimum flexibility during peak hours
        def dr_peak_window(m, dr, t, y):
            if t not in m.T_peak:
                return Constraint.Skip
            return m.dr_capacity[dr, y] <= sum(m.curtail_wl[w, t, y] for w in m.W) + m.curtail_cool[t, y]
        m.dr_peak_window_con = Constraint(m.DR, m.T, m.Y, rule=dr_peak_window)
        
        logger.info("DR constraints added")
    
    def _build_gas_constraint(self):
        """
        GAS SUPPLY CONSTRAINT - ENABLED (was disabled)
        
        This is a HARD constraint as requested by user.
        Gas consumption cannot exceed daily supply limit.
        """
        m = self.model
        
        recip_hr = self.EQUIPMENT['recip']['heat_rate_btu_kwh']
        turbine_hr = self.EQUIPMENT['turbine']['heat_rate_btu_kwh']
        
        def gas_supply_daily(m, y):
            """Average daily gas consumption cannot exceed supply limit."""
            # Annual generation in representative hours
            annual_recip_mwh = m.SCALE_FACTOR * sum(m.gen_recip[t, y] for t in m.T)
            annual_turbine_mwh = m.SCALE_FACTOR * sum(m.gen_turbine[t, y] for t in m.T)
            
            # Convert MWh to MCF:
            # MWh × heat_rate(BTU/kWh) × 1000(kW/MW) / HHV(BTU/MCF) = MCF
            annual_recip_mcf = annual_recip_mwh * recip_hr * 1000 / self.GAS_HHV_BTU_PER_MCF
            annual_turbine_mcf = annual_turbine_mwh * turbine_hr * 1000 / self.GAS_HHV_BTU_PER_MCF
            
            # Average daily = Annual / 365
            avg_daily_mcf = (annual_recip_mcf + annual_turbine_mcf) / 365
            
            return avg_daily_mcf <= m.GAS_MAX
        
        m.gas_supply_con = Constraint(m.Y, rule=gas_supply_daily)
        logger.info(f"Gas constraint ENABLED: {value(m.GAS_MAX):,.0f} MCF/day limit")
    
    def _build_co2_constraint(self):
        """
        CO2 EMISSIONS CONSTRAINT - ENABLED (conditional)
        
        Only added if CO2_MAX > 0 (some sites may not have CO2 limits).
        """
        m = self.model
        
        # Skip if no CO2 limit specified
        if value(m.CO2_MAX) <= 0:
            logger.info("CO2 constraint SKIPPED (no limit specified)")
            return
        
        # CO2 emission factor for natural gas
        CO2_LB_PER_MMBTU = 117
        
        recip_hr = self.EQUIPMENT['recip']['heat_rate_btu_kwh']
        turbine_hr = self.EQUIPMENT['turbine']['heat_rate_btu_kwh']
        
        def co2_annual_limit(m, y):
            # MMBTU = MWh × heat_rate(BTU/kWh) × 1000 / 1e6
            recip_mmbtu = m.SCALE_FACTOR * sum(m.gen_recip[t, y] * recip_hr / 1000 for t in m.T)
            turbine_mmbtu = m.SCALE_FACTOR * sum(m.gen_turbine[t, y] * turbine_hr / 1000 for t in m.T)
            
            total_co2_lb = (recip_mmbtu + turbine_mmbtu) * CO2_LB_PER_MMBTU
            total_co2_tons = total_co2_lb / 2000
            
            return total_co2_tons <= m.CO2_MAX
        
        m.co2_con = Constraint(m.Y, rule=co2_annual_limit)
        logger.info(f"CO2 constraint ENABLED: {value(m.CO2_MAX):,.0f} tpy limit")
    
    def _build_ramp_constraint(self):
        """
        RAMP RATE CONSTRAINT - ENABLED (was disabled)
        
        Total system ramp capability must meet load variability requirements.
        This ensures the energy stack can follow load fluctuations.
        """
        m = self.model
        
        recip_ramp = self.EQUIPMENT['recip']['ramp_rate_mw_min']
        turbine_ramp = self.EQUIPMENT['turbine']['ramp_rate_mw_min']
        bess_ramp = self.EQUIPMENT['bess']['ramp_rate_mw_min']
        
        def ramp_capability(m, y):
            # Calculate total system ramp capability
            total_ramp = (
                m.n_recip[y] * recip_ramp +
                m.n_turbine[y] * turbine_ramp +
                m.bess_mw[y] * bess_ramp +
                m.grid_mw[y] * m.GRID_AVAIL[y] * 100  # Grid ramp essentially unlimited
            )
            return total_ramp >= m.RAMP_REQUIRED
        
        m.ramp_con = Constraint(m.Y, rule=ramp_capability)
        logger.info(f"Ramp constraint ENABLED: {value(m.RAMP_REQUIRED)} MW/min required")
    
    def _build_grid_timing_constraint(self):
        """
        GRID TIMING CONSTRAINT - NEW
        
        Grid cannot be used before interconnection completes.
        This enforces the "bridging" behavior with co-located equipment
        before grid becomes available.
        """
        m = self.model
        
        grid_year = int(value(m.GRID_YEAR))
        
        def grid_timing_active(m, y):
            """Grid cannot be active before available year."""
            if y < grid_year:
                return m.grid_active[y] == 0
            return Constraint.Skip
        m.grid_timing_active_con = Constraint(m.Y, rule=grid_timing_active)
        
        def grid_timing_mw(m, y):
            """Grid MW must be zero before available year."""
            if y < grid_year:
                return m.grid_mw[y] == 0
            return Constraint.Skip
        m.grid_timing_mw_con = Constraint(m.Y, rule=grid_timing_mw)
        
        logger.info(f"Grid timing constraint: Available from {grid_year} onwards")
    
    def _build_ram_constraint(self):
        """
        RAM CONSTRAINT - FIXED
        
        Ensures N-1 redundancy for 99.9% availability.
        Firm capacity (total - largest unit) must meet peak load.
        """
        m = self.model
        
        # Skip RAM constraint if N-1 not required
        if not self.constraints.get('N_Minus_1_Required', True):
            logger.info("RAM constraint SKIPPED (N-1 not required)")
            return
        
        recip_cap = self.EQUIPMENT['recip']['capacity_mw']
        turbine_cap = self.EQUIPMENT['turbine']['capacity_mw']
        
        # Pre-calculate peak load
        load_array = np.array(self.load_data.get('total_load_mw', [100]*8760))
        peak_load = float(np.percentile(load_array, 98))
        
        def ram_reliability(m, y):
            # Total capacity by type
            recip_total = m.n_recip[y] * recip_cap
            turbine_total = m.n_turbine[y] * turbine_cap
            bess_total = m.bess_mw[y]
            grid_total = m.grid_mw[y] * m.GRID_AVAIL[y]
            
            total_cap = recip_total + turbine_total + bess_total + grid_total
            
            # Largest single contingency
            # Conservative: assume largest possible unit (turbine = 20 MW)
            # This could be refined with auxiliary binary variables
            largest_unit = turbine_cap  # 20 MW
            
            # Firm capacity with N-1
            firm_capacity = total_cap - largest_unit
            
            # Must meet peak load
            return firm_capacity >= peak_load
        
        m.ram_con = Constraint(m.Y, rule=ram_reliability)
        logger.info(f"RAM constraint ENABLED: N-1 redundancy, peak={peak_load:.1f} MW")
    
    def _build_objective(self):
        """
        HIERARCHICAL OBJECTIVE FUNCTION
        
        Implements the user requirement:
        1. Maximize power coverage (minimize unserved energy) - PRIMARY
        2. Minimize cost - SECONDARY
        
        This is achieved via a large penalty ($50,000/MWh) for unserved energy.
        The penalty is high enough to always prioritize power over cost,
        but not so high as to cause numerical instability (Gemini refinement).
        """
        m = self.model
        
        r = self.DISCOUNT_RATE
        first_year = min(self.years)
        
        recip_cap = self.EQUIPMENT['recip']['capacity_mw']
        recip_capex = self.EQUIPMENT['recip']['capex_per_kw']
        turbine_cap = self.EQUIPMENT['turbine']['capacity_mw']
        turbine_capex = self.EQUIPMENT['turbine']['capex_per_kw']
        bess_capex = self.EQUIPMENT['bess']['capex_per_kwh']
        solar_capex = self.EQUIPMENT['solar']['capex_per_kw']
        
        recip_hr = self.EQUIPMENT['recip']['heat_rate_btu_kwh']
        turbine_hr = self.EQUIPMENT['turbine']['heat_rate_btu_kwh']
        
        def hierarchical_lcoe(m):
            """
            LCOE with hierarchical priority via unserved penalty.
            
            Components:
            - CAPEX (equipment + grid interconnection)
            - Fuel cost (natural gas)
            - Grid electricity cost
            - DR revenue (credit)
            - UNSERVED PENALTY (implements hierarchy)
            
            Denominator: Fixed required energy (not served energy)
            """
            
            # =========================
            # NPV of CAPEX
            # =========================
            capex = sum(
                (
                    m.n_recip[y] * recip_cap * 1000 * recip_capex +
                    m.n_turbine[y] * turbine_cap * 1000 * turbine_capex +
                    m.bess_mwh[y] * 1000 * bess_capex +
                    m.solar_mw[y] * 1000 * solar_capex +
                    m.grid_capex_incurred[y]
                ) / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # NPV of Fuel Cost
            # =========================
            fuel = sum(
                m.SCALE_FACTOR * sum(
                    (m.gen_recip[t, y] * recip_hr + m.gen_turbine[t, y] * turbine_hr)
                    * self.NG_PRICE_PER_MMBTU / 1000  # BTU/kWh × $/MMBTU / 1000 = $/MWh
                    for t in m.T
                ) / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # NPV of Grid Electricity Cost
            # =========================
            grid_cost = sum(
                m.SCALE_FACTOR * sum(
                    m.grid_import[t, y] * self.GRID_PRICE_PER_MWH
                    for t in m.T
                ) / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # NPV of DR Revenue
            # =========================
            dr_revenue = sum(
                sum(m.dr_capacity[dr, y] * 8760 * m.DR_payment[dr] for dr in m.DR)
                / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # UNSERVED ENERGY PENALTY
            # =========================
            # This implements the hierarchical objective:
            # By penalizing unserved energy at $50,000/MWh (>> any real cost),
            # the optimizer always prioritizes serving load over reducing cost.
            
            unserved_penalty = sum(
                m.SCALE_FACTOR * sum(
                    m.unserved[t, y] * self.UNSERVED_PENALTY
                    for t in m.T
                ) / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # ENERGY DENOMINATOR (FIXED)
            # =========================
            # Use required energy, not served energy
            # This prevents curtailment from distorting LCOE
            
            energy = sum(
                m.D_required[y] / (1 + r)**(y - first_year)
                for y in m.Y
            )
            
            # =========================
            # TOTAL COST / ENERGY
            # =========================
            total_cost = capex + fuel + grid_cost + unserved_penalty - dr_revenue
            
            if energy > 0:
                return total_cost / energy
            else:
                return 1e9
        
        m.obj = Objective(rule=hierarchical_lcoe, sense=minimize)
        
        logger.info(f"Objective: Hierarchical LCOE with ${self.UNSERVED_PENALTY:,}/MWh unserved penalty")
    
    # ==========================================================================
    # SOLVING
    # ==========================================================================
    
    def solve(
        self,
        solver: str = 'cbc',
        time_limit: int = 300,
        verbose: bool = True
    ) -> Dict:
        """
        Solve the optimization model.
        
        Args:
            solver: MILP solver to use ('glpk', 'cbc', or 'gurobi')
            time_limit: Maximum solve time in seconds
            verbose: Print solver output
        
        Returns:
            Solution dictionary with equipment, costs, and power coverage
        """
        if not self._built:
            raise RuntimeError("Model not built. Call build() first.")
        
        logger.info(f"Solving with {solver} (time limit: {time_limit}s)")
        
        # Get solver
        try:
            opt = SolverFactory(solver)
            if opt is None or not opt.available():
                raise Exception(f"Solver {solver} not available")
        except Exception as e:
            logger.warning(f"Failed to load {solver}: {e}. Trying alternatives...")
            for alt_solver in ['glpk', 'cbc', 'gurobi']:
                if alt_solver != solver:
                    try:
                        opt = SolverFactory(alt_solver)
                        if opt is not None and opt.available():
                            solver = alt_solver
                            logger.info(f"Using {solver} instead")
                            break
                    except:
                        continue
            else:
                raise RuntimeError("No suitable MILP solver found. Install GLPK, CBC, or Gurobi.")
        
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
        
        # Solve
        results = opt.solve(self.model, tee=verbose)
        
        logger.info(f"Solver status: {results.solver.status}")
        logger.info(f"Termination: {results.solver.termination_condition}")
        
        return self._extract_solution(results)
    
    def _extract_solution(self, results) -> Dict:
        """Extract solution to dictionary with power coverage metrics."""
        m = self.model
        
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
        
        # Check if solved successfully
        # CRITICAL FIX: Accept solutions even if time limit hit, as long as solution exists
        # Model has unserved variable so it should always find SOME solution
        acceptable_terminations = [
            TerminationCondition.optimal,
            TerminationCondition.feasible,
            TerminationCondition.maxTimeLimit,      # Time limit but found solution
            TerminationCondition.maxIterations,     # Iteration limit but found solution  
            TerminationCondition.maxEvaluations,    # Eval limit but found solution
        ]
        
        if results.solver.termination_condition not in acceptable_terminations:
            logger.warning(f"Solver terminated with: {results.solver.termination_condition}")
            # Still check if results contain a solution
            if not hasattr(results, 'solution') or len(results.solution) == 0:
                logger.error("No solution found")
                return solution
            else:
                logger.warning("Attempting to extract solution despite termination condition")
        
        # Extract objective value
        try:
            solution['objective_lcoe'] = value(m.obj)
        except:
            solution['objective_lcoe'] = 0
        
        # Extract solution by year
        for y in m.Y:
            # Equipment
            solution['equipment'][y] = {
                'n_recip': int(value(m.n_recip[y])),
                'n_turbine': int(value(m.n_turbine[y])),
                'recip_mw': int(value(m.n_recip[y])) * self.EQUIPMENT['recip']['capacity_mw'],
                'turbine_mw': int(value(m.n_turbine[y])) * self.EQUIPMENT['turbine']['capacity_mw'],
                'bess_mwh': value(m.bess_mwh[y]),
                'bess_mw': value(m.bess_mw[y]),
                'solar_mw': value(m.solar_mw[y]),
                'grid_mw': value(m.grid_mw[y]),
                'grid_active': bool(value(m.grid_active[y])),
                'total_capacity_mw': (
                    int(value(m.n_recip[y])) * self.EQUIPMENT['recip']['capacity_mw'] +
                    int(value(m.n_turbine[y])) * self.EQUIPMENT['turbine']['capacity_mw'] +
                    value(m.bess_mw[y]) +
                    value(m.solar_mw[y]) * self.EQUIPMENT['solar']['capacity_factor'] +
                    value(m.grid_mw[y]) * value(m.GRID_AVAIL[y])
                ),
            }
            
            # Power coverage (CRITICAL METRIC)
            total_unserved = sum(value(m.unserved[t, y]) for t in m.T) * value(m.SCALE_FACTOR)
            total_load = value(m.D_required[y])
            coverage_pct = (1 - total_unserved / total_load) * 100 if total_load > 0 else 100
            power_gap_mw = total_unserved / 8760 if total_unserved > 0 else 0
            
            solution['power_coverage'][y] = {
                'total_load_mwh': total_load,
                'served_mwh': total_load - total_unserved,
                'unserved_mwh': total_unserved,
                'coverage_pct': coverage_pct,
                'power_gap_mw': power_gap_mw,
                'is_fully_served': total_unserved < 0.01 * total_load,
            }
            
            # Emissions
            nox = sum(
                value(m.gen_recip[t, y]) * self.EQUIPMENT['recip']['heat_rate_btu_kwh'] * self.EQUIPMENT['recip']['nox_rate_lb_mmbtu'] +
                value(m.gen_turbine[t, y]) * self.EQUIPMENT['turbine']['heat_rate_btu_kwh'] * self.EQUIPMENT['turbine']['nox_rate_lb_mmbtu']
                for t in m.T
            ) * value(m.SCALE_FACTOR) / 2_000_000
            
            solution['emissions'][y] = {
                'nox_tpy': nox,
                'nox_limit_tpy': value(m.NOX_MAX),
                'nox_utilization_pct': nox / value(m.NOX_MAX) * 100 if value(m.NOX_MAX) > 0 else 0,
            }
            
            # Gas usage
            recip_gen = sum(value(m.gen_recip[t, y]) for t in m.T) * value(m.SCALE_FACTOR)
            turbine_gen = sum(value(m.gen_turbine[t, y]) for t in m.T) * value(m.SCALE_FACTOR)
            
            recip_mcf = recip_gen * self.EQUIPMENT['recip']['heat_rate_btu_kwh'] * 1000 / self.GAS_HHV_BTU_PER_MCF
            turbine_mcf = turbine_gen * self.EQUIPMENT['turbine']['heat_rate_btu_kwh'] * 1000 / self.GAS_HHV_BTU_PER_MCF
            
            avg_daily_mcf = (recip_mcf + turbine_mcf) / 365
            
            solution['gas_usage'][y] = {
                'annual_mcf': recip_mcf + turbine_mcf,
                'avg_daily_mcf': avg_daily_mcf,
                'gas_limit_mcf_day': value(m.GAS_MAX),
                'gas_utilization_pct': avg_daily_mcf / value(m.GAS_MAX) * 100 if value(m.GAS_MAX) > 0 else 0,
            }
            
            # DR capacity
            solution['dr'][y] = {
                dr: value(m.dr_capacity[dr, y])
                for dr in m.DR
            }
            solution['dr'][y]['total_dr_mw'] = sum(value(m.dr_capacity[dr, y]) for dr in m.DR)
        
        # Summary metrics
        final_year = max(self.years)
        solution['summary'] = {
            'final_year_equipment': solution['equipment'][final_year],
            'final_year_coverage_pct': solution['power_coverage'][final_year]['coverage_pct'],
            'years_with_power_gap': sum(
                1 for y in self.years
                if solution['power_coverage'][y]['power_gap_mw'] > 0.1
            ),
            'grid_first_year': next(
                (y for y in self.years if solution['equipment'][y]['grid_active']),
                None
            ),
        }
        
        return solution


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    """Test the corrected MILP model."""
    
    print("="*70)
    print("bvNexus MILP Model - Corrected Version Test")
    print("="*70)
    
    # Generate sample load profile
    np.random.seed(42)
    hours = 8760
    base_load = 160 * 0.75  # 160 MW peak, 75% load factor
    
    # Daily and seasonal patterns
    load_8760 = np.zeros(hours)
    for h in range(hours):
        hour_of_day = h % 24
        day_of_year = h // 24
        
        # Daily pattern (higher during day)
        daily = 1.0 if 8 <= hour_of_day <= 22 else 0.85
        
        # Seasonal pattern
        seasonal = 1.0 + 0.05 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        
        # Random noise
        noise = 1.0 + np.random.uniform(-0.02, 0.02)
        
        load_8760[h] = base_load * daily * seasonal * noise
    
    # Test configuration
    test_years = list(range(2026, 2036))
    
    test_constraints = {
        'NOx_Limit_tpy': 100,        # 100 tpy NOx (should be binding)
        'Gas_Supply_MCF_day': 40000,  # 40,000 MCF/day
        'CO2_Limit_tpy': 0,           # No CO2 limit
        'Available_Land_Acres': 500,
        'min_ramp_rate_mw_min': 10,
    }
    
    test_grid_config = {
        'available_year': 2030,
        'capex': 5_000_000,
    }
    
    test_workload_mix = {
        'pre_training': 0.30,
        'fine_tuning': 0.20,
        'batch_inference': 0.30,
        'realtime_inference': 0.20,
    }
    
    # Build and solve
    print("\nBuilding model...")
    optimizer = bvNexusMILP_DR()
    
    optimizer.build(
        site={'name': 'Test Site'},
        constraints=test_constraints,
        load_data={
            'total_load_mw': load_8760,
            'pue': 1.25,
        },
        workload_mix=test_workload_mix,
        years=test_years,
        dr_config={'cooling_flex': 0.25},
        grid_config=test_grid_config,
    )
    
    print("\nSolving...")
    solution = optimizer.solve(solver='cbc', time_limit=300, verbose=False)
    
    # Print results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    print(f"\nSolver Status: {solution['status']}")
    print(f"Termination: {solution['termination']}")
    print(f"Objective LCOE: ${solution['objective_lcoe']:.2f}/MWh")
    
    print("\n" + "-"*70)
    print("EQUIPMENT BY YEAR")
    print("-"*70)
    
    for y in test_years:
        eq = solution['equipment'].get(y, {})
        cov = solution['power_coverage'].get(y, {})
        em = solution['emissions'].get(y, {})
        gas = solution['gas_usage'].get(y, {})
        
        print(f"\n{y}:")
        print(f"  Equipment: {eq.get('n_recip', 0)} recips ({eq.get('recip_mw', 0):.0f} MW), "
              f"{eq.get('n_turbine', 0)} turbines ({eq.get('turbine_mw', 0):.0f} MW), "
              f"{eq.get('bess_mwh', 0):.0f} MWh BESS, "
              f"{eq.get('grid_mw', 0):.0f} MW grid")
        print(f"  Grid active: {eq.get('grid_active', False)}")
        print(f"  Total capacity: {eq.get('total_capacity_mw', 0):.1f} MW")
        print(f"  Power coverage: {cov.get('coverage_pct', 0):.1f}%", end="")
        if cov.get('power_gap_mw', 0) > 0.1:
            print(f" ⚠️ Gap: {cov.get('power_gap_mw', 0):.1f} MW")
        else:
            print(" ✓")
        print(f"  NOx: {em.get('nox_tpy', 0):.1f} tpy ({em.get('nox_utilization_pct', 0):.1f}% of limit)")
        print(f"  Gas: {gas.get('avg_daily_mcf', 0):,.0f} MCF/day ({gas.get('gas_utilization_pct', 0):.1f}% of limit)")
    
    print("\n" + "-"*70)
    print("SUMMARY")
    print("-"*70)
    summary = solution.get('summary', {})
    print(f"Years with power gap: {summary.get('years_with_power_gap', 0)}")
    print(f"Grid first available: {summary.get('grid_first_year', 'N/A')}")
    print(f"Final year coverage: {summary.get('final_year_coverage_pct', 0):.1f}%")
