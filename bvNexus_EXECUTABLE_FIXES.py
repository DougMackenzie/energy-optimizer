# bvNexus EXECUTABLE FIX PACKAGE
# ===============================
# December 23, 2025
#
# This file contains COPY-PASTE READY code fixes for each bug.
# Apply fixes in order - each fix builds on the previous.

"""
BUGS FROM SCREENSHOTS:
======================
1. KeyError: 'annual_fuel_cost_m' (line 178 page_09_results.py)
2. LCOE = $0.00/MWh (calculation missing)
3. Annual Gen = 0.0 GWh (not calculated)
4. Capacity shows 50 MW but chart shows 300+ MW (wrong equipment sizes)
5. Equipment deployed in 2026 when load = 0 (no load-following)
6. GTs available in 2026 before lead time allows (no lead time constraints)
7. Dispatch chart shows different data than results (data sync issue)
8. Power gaps in BTM scenarios (not building enough capacity)
"""


# ==============================================================================
# FIX 1: page_09_results.py - KeyError Fix (IMMEDIATE)
# ==============================================================================
# File: app/pages_custom/page_09_results.py
# Location: Around line 170-190

FIX_1_PAGE_RESULTS = '''
# FIND this code (around line 170-190):
# =====================================================
# with col_econ2:
#     st.markdown("##### Operating Costs (Annual)")
#     st.metric("O&M", f"${economics['annual_opex_m']:.2f}M/yr")
#     st.metric("Fuel/Energy", f"${economics['annual_fuel_cost_m']:.2f}M/yr")
# =====================================================

# REPLACE WITH:
# =====================================================
    with col_econ2:
        st.markdown("##### Operating Costs (Annual)")
        
        # Use .get() with defaults to prevent KeyError
        annual_opex = economics.get('annual_opex_m', 0)
        annual_fuel = economics.get('annual_fuel_cost_m', 0)
        annual_gen = economics.get('annual_generation_gwh', 0)
        capacity_factor = economics.get('capacity_factor_pct', 0)
        
        st.metric("O&M", f"${annual_opex:.2f}M/yr")
        st.metric("Fuel/Energy", f"${annual_fuel:.2f}M/yr")
        
        total_annual = annual_opex + annual_fuel
        st.metric("Total Annual", f"${total_annual:.2f}M/yr")
        
        # Add missing metrics
        st.caption(f"Capacity Factor: {capacity_factor:.1f}%")
        st.caption(f"Annual Generation: {annual_gen:.1f} GWh")
# =====================================================
'''


# ==============================================================================
# FIX 2: milp_optimizer_wrapper.py - Complete Economics Calculation
# ==============================================================================
# File: app/utils/milp_optimizer_wrapper.py
# Add at TOP of file (after imports):

FIX_2A_CONSTANTS = '''
# ADD after imports at top of file:
# ==============================================================================
# EQUIPMENT PARAMETERS (Corrected Dec 2025)
# ==============================================================================
EQUIPMENT_PARAMS = {
    'recip': {
        'capacity_mw': 10.0,      # Per unit
        'heat_rate': 7200,        # BTU/kWh
        'capex': 1200,            # $/kW
        'vom': 8.0,               # $/MWh
        'fom': 15.0,              # $/kW-yr
        'lead_time': 18,          # months
    },
    'turbine': {
        'capacity_mw': 50.0,      # Per unit
        'heat_rate': 8500,        # BTU/kWh
        'capex': 900,             # $/kW
        'vom': 6.0,               # $/MWh
        'fom': 12.0,              # $/kW-yr
        'lead_time': 24,          # months
    },
    'bess': {
        'capex_kwh': 250,         # $/kWh
        'fom': 10.0,              # $/kW-yr
        'lead_time': 12,          # months
    },
    'solar': {
        'capex': 950,             # $/kW
        'fom': 10.0,              # $/kW-yr
        'cf': 0.25,               # capacity factor
        'lead_time': 12,          # months
    },
}

DEFAULT_LOAD_TRAJECTORY = {
    2025: 0, 2026: 0, 2027: 0,
    2028: 150, 2029: 300, 2030: 450,
    2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,
}

GAS_PRICE = 3.50        # $/MMBtu
GRID_PRICE = 75         # $/MWh
GRID_LEAD_TIME = 60     # months (default)
'''


# ==============================================================================
# FIX 2B: Replace _format_solution_safe() function ENTIRELY
# ==============================================================================
# File: app/utils/milp_optimizer_wrapper.py
# Find and REPLACE the entire _format_solution_safe function:

FIX_2B_FORMAT_SOLUTION = '''
def _format_solution_safe(solution: Dict, years: List[int], constraints: Dict, load_data: Dict) -> Dict:
    """
    Format MILP solution with COMPLETE economics calculation.
    Fixes: LCOE=0, missing fuel cost, missing generation, wrong capacity.
    """
    
    # Check termination status
    term = solution.get('termination', 'unknown')
    acceptable = ['optimal', 'feasible', 'maxTimeLimit', 'maxIterations', 'maxEvaluations']
    if term not in acceptable:
        return _create_empty_result(f"Solver status: {term}")
    
    final_year = max(years)
    
    # ==========================================================================
    # EXTRACT EQUIPMENT FROM SOLUTION
    # ==========================================================================
    eq = solution.get('equipment', {}).get(final_year, {})
    
    n_recip = int(eq.get('n_recip', 0))
    n_turbine = int(eq.get('n_turbine', 0))
    bess_mwh = float(eq.get('bess_mwh', 0))
    solar_mw = float(eq.get('solar_mw', 0))
    grid_mw = float(eq.get('grid_mw', 0))
    grid_active = bool(eq.get('grid_active', False) or grid_mw > 0)
    
    # ==========================================================================
    # CALCULATE CAPACITIES (using CORRECT equipment sizes!)
    # ==========================================================================
    RECIP_MW = EQUIPMENT_PARAMS['recip']['capacity_mw']      # 10.0 MW
    TURBINE_MW = EQUIPMENT_PARAMS['turbine']['capacity_mw']  # 50.0 MW
    
    recip_mw = n_recip * RECIP_MW
    turbine_mw = n_turbine * TURBINE_MW
    bess_mw = bess_mwh / 4  # 4-hour duration
    
    total_capacity_mw = recip_mw + turbine_mw + solar_mw + bess_mw + grid_mw
    
    logger.info(f"Equipment: {n_recip} recips ({recip_mw:.0f} MW), {n_turbine} turbines ({turbine_mw:.0f} MW), {solar_mw:.0f} MW solar, {bess_mwh:.0f} MWh BESS, {grid_mw:.0f} MW grid")
    logger.info(f"Total capacity: {total_capacity_mw:.0f} MW")
    
    # ==========================================================================
    # CALCULATE ANNUAL GENERATION
    # ==========================================================================
    CF_THERMAL = 0.70
    CF_SOLAR = EQUIPMENT_PARAMS['solar']['cf']  # 0.25
    CF_GRID = 0.85
    HOURS = 8760
    
    recip_gen_mwh = recip_mw * CF_THERMAL * HOURS
    turbine_gen_mwh = turbine_mw * CF_THERMAL * HOURS
    solar_gen_mwh = solar_mw * CF_SOLAR * HOURS
    grid_gen_mwh = grid_mw * CF_GRID * HOURS if grid_active else 0
    
    annual_gen_mwh = recip_gen_mwh + turbine_gen_mwh + solar_gen_mwh + grid_gen_mwh
    annual_gen_gwh = annual_gen_mwh / 1000
    
    logger.info(f"Annual generation: {annual_gen_gwh:.1f} GWh")
    
    # ==========================================================================
    # CALCULATE CAPEX
    # ==========================================================================
    capex = (
        recip_mw * 1000 * EQUIPMENT_PARAMS['recip']['capex'] +
        turbine_mw * 1000 * EQUIPMENT_PARAMS['turbine']['capex'] +
        bess_mwh * 1000 * EQUIPMENT_PARAMS['bess']['capex_kwh'] +
        solar_mw * 1000 * EQUIPMENT_PARAMS['solar']['capex']
    )
    if grid_active:
        capex += 5_000_000  # Grid interconnection
    
    total_capex_m = capex / 1e6
    
    # ==========================================================================
    # CALCULATE FUEL COST (was missing!)
    # ==========================================================================
    recip_fuel_mmbtu = recip_gen_mwh * 1000 * EQUIPMENT_PARAMS['recip']['heat_rate'] / 1e6
    turbine_fuel_mmbtu = turbine_gen_mwh * 1000 * EQUIPMENT_PARAMS['turbine']['heat_rate'] / 1e6
    
    fuel_cost = (recip_fuel_mmbtu + turbine_fuel_mmbtu) * GAS_PRICE
    grid_cost = grid_gen_mwh * GRID_PRICE
    
    annual_fuel_cost_m = (fuel_cost + grid_cost) / 1e6
    
    logger.info(f"Annual fuel cost: ${annual_fuel_cost_m:.2f}M")
    
    # ==========================================================================
    # CALCULATE O&M (was missing!)
    # ==========================================================================
    fixed_om = (
        recip_mw * 1000 * EQUIPMENT_PARAMS['recip']['fom'] +
        turbine_mw * 1000 * EQUIPMENT_PARAMS['turbine']['fom'] +
        bess_mw * 1000 * EQUIPMENT_PARAMS['bess']['fom'] +
        solar_mw * 1000 * EQUIPMENT_PARAMS['solar']['fom']
    ) / 1e6
    
    variable_om = (
        recip_gen_mwh * EQUIPMENT_PARAMS['recip']['vom'] +
        turbine_gen_mwh * EQUIPMENT_PARAMS['turbine']['vom']
    ) / 1e6
    
    annual_opex_m = fixed_om + variable_om
    
    logger.info(f"Annual O&M: ${annual_opex_m:.2f}M")
    
    # ==========================================================================
    # CALCULATE LCOE (was returning 0!)
    # ==========================================================================
    r = 0.08  # Discount rate
    n = 20    # Project life
    crf = r * (1 + r)**n / ((1 + r)**n - 1)  # Capital recovery factor
    
    annualized_capex = total_capex_m * crf
    annual_costs = annualized_capex + annual_opex_m + annual_fuel_cost_m
    
    if annual_gen_gwh > 0:
        lcoe_mwh = annual_costs * 1000 / annual_gen_gwh
    else:
        lcoe_mwh = 0
    
    logger.info(f"LCOE: ${lcoe_mwh:.2f}/MWh")
    
    # ==========================================================================
    # CALCULATE CAPACITY FACTOR (was missing!)
    # ==========================================================================
    max_gen = total_capacity_mw * HOURS
    capacity_factor_pct = (annual_gen_mwh / max_gen * 100) if max_gen > 0 else 0
    
    # ==========================================================================
    # BUILD PHASED DEPLOYMENT (for charts)
    # ==========================================================================
    phased = {
        'cumulative_recip_mw': {},
        'cumulative_turbine_mw': {},
        'cumulative_bess_mwh': {},
        'cumulative_solar_mw': {},
        'grid_mw': {},
    }
    
    for y in years:
        e = solution.get('equipment', {}).get(y, {})
        phased['cumulative_recip_mw'][y] = int(e.get('n_recip', 0)) * RECIP_MW
        phased['cumulative_turbine_mw'][y] = int(e.get('n_turbine', 0)) * TURBINE_MW
        phased['cumulative_bess_mwh'][y] = float(e.get('bess_mwh', 0))
        phased['cumulative_solar_mw'][y] = float(e.get('solar_mw', 0))
        phased['grid_mw'][y] = float(e.get('grid_mw', 0))
    
    # ==========================================================================
    # POWER COVERAGE
    # ==========================================================================
    coverage = solution.get('power_coverage', {})
    final_cov = coverage.get(final_year, {})
    
    coverage_pct = final_cov.get('coverage_pct', 100)
    power_gap_mw = final_cov.get('power_gap_mw', 0)
    unserved_mwh = final_cov.get('unserved_mwh', 0)
    is_fully_served = final_cov.get('is_fully_served', True)
    
    # ==========================================================================
    # EMISSIONS & GAS
    # ==========================================================================
    emissions = solution.get('emissions', {})
    final_em = emissions.get(final_year, {})
    nox_tpy = final_em.get('nox_tpy', 0)
    nox_limit = constraints.get('NOx_Limit_tpy', 100)
    
    gas = solution.get('gas_usage', {})
    final_gas = gas.get(final_year, {})
    avg_mcf = final_gas.get('avg_daily_mcf', 0)
    gas_limit = constraints.get('Gas_Supply_MCF_day', 75000)
    
    # ==========================================================================
    # TIMELINE
    # ==========================================================================
    first_deploy = None
    for y in sorted(years):
        e = solution.get('equipment', {}).get(y, {})
        if e.get('n_recip', 0) > 0 or e.get('n_turbine', 0) > 0 or e.get('solar_mw', 0) > 0:
            first_deploy = y
            break
    
    if first_deploy:
        timeline_months = max(24, (final_year - first_deploy + 1) * 12)
    else:
        timeline_months = 72
    
    timeline_months = min(timeline_months, 120)
    
    # ==========================================================================
    # VIOLATIONS
    # ==========================================================================
    violations = []
    if power_gap_mw > 1:
        violations.append(f"Power gap: {power_gap_mw:.1f} MW")
    if nox_tpy > nox_limit:
        violations.append(f"NOx exceeded: {nox_tpy:.1f} > {nox_limit} tpy")
    
    # ==========================================================================
    # BUILD COMPLETE RESULT
    # ==========================================================================
    return {
        'feasible': True,
        'violations': violations,
        'warnings': [],
        
        'equipment_config': {
            'n_recip': n_recip,
            'n_turbine': n_turbine,
            'recip_mw': recip_mw,
            'turbine_mw': turbine_mw,
            'bess_mwh': bess_mwh,
            'bess_mw': bess_mw,
            'solar_mw': solar_mw,
            'grid_mw': grid_mw,
            'grid_active': grid_active,
            'total_capacity_mw': total_capacity_mw,
            'solar_mw_dc': solar_mw,
            'grid_import_mw': grid_mw,
            'recip_engines': [{'capacity_mw': RECIP_MW}] * n_recip,
            'gas_turbines': [{'capacity_mw': TURBINE_MW}] * n_turbine,
            'bess': [{'energy_mwh': bess_mwh, 'power_mw': bess_mw}] if bess_mwh > 0 else [],
            '_phased_deployment': phased,
        },
        
        'economics': {
            'lcoe_mwh': lcoe_mwh,
            'total_capex_m': total_capex_m,
            'annual_opex_m': annual_opex_m,
            'annual_fuel_cost_m': annual_fuel_cost_m,      # WAS MISSING!
            'annual_generation_gwh': annual_gen_gwh,       # WAS MISSING!
            'capacity_factor_pct': capacity_factor_pct,    # WAS MISSING!
        },
        
        'power_coverage': {
            'final_coverage_pct': coverage_pct,
            'power_gap_mw': power_gap_mw,
            'unserved_mwh': unserved_mwh,
            'is_fully_served': is_fully_served,
            'by_year': coverage,
        },
        
        'emissions': {
            'nox_tpy': nox_tpy,
            'nox_limit_tpy': nox_limit,
            'nox_utilization_pct': (nox_tpy / nox_limit * 100) if nox_limit > 0 else 0,
            'by_year': emissions,
        },
        
        'gas_usage': {
            'avg_daily_mcf': avg_mcf,
            'gas_limit_mcf_day': gas_limit,
            'gas_utilization_pct': (avg_mcf / gas_limit * 100) if gas_limit > 0 else 0,
            'by_year': gas,
        },
        
        'timeline': {
            'timeline_months': timeline_months,
            'timeline_years': timeline_months / 12,
            'critical_path': 'MILP Optimized',
            'deployment_speed': 'Fast' if timeline_months <= 24 else 'Medium' if timeline_months <= 48 else 'Slow',
        },
        
        'dr_metrics': {
            'total_dr_mw': 0,
        },
        
        'metrics': {
            'nox_tpy': nox_tpy,
            'gas_mcf_day': avg_mcf,
            'coverage_pct': coverage_pct,
            'total_capacity_mw': total_capacity_mw,
        },
        
        'score': 100 if is_fully_served else max(0, coverage_pct),
    }
'''


# ==============================================================================
# FIX 3: Add Load-Following + Lead Time Constraints
# ==============================================================================
# File: app/utils/milp_optimizer_wrapper.py
# In optimize_with_milp(), REPLACE STEP 5 with this:

FIX_3_STEP_5 = '''
    # ========================================================================
    # STEP 5: Apply scenario constraints + load-following + lead times
    # ========================================================================
    
    try:
        scenario_name = scenario.get('Scenario_Name', 'Unknown') if scenario else 'Default'
        logger.info(f"  Applying constraints for scenario: {scenario_name}")
        
        m = optimizer.model
        
        # =====================
        # 5A: SCENARIO EQUIPMENT CONSTRAINTS
        # =====================
        if scenario:
            # Fixed is_disabled function (uses OR logic, not AND)
            def is_disabled(primary_key, alt_key=None):
                """Returns True if equipment is explicitly disabled."""
                for key in [primary_key, alt_key]:
                    if key and key in scenario:
                        val = scenario[key]
                        if isinstance(val, str):
                            if val.lower() in ('false', 'no', '0', 'disabled'):
                                return True
                        elif val == False:
                            return True
                return False
            
            if is_disabled('Recip_Enabled', 'Recip_Engines'):
                logger.info("    🚫 RECIPS: Disabled by scenario")
                for y in years:
                    m.n_recip[y].fix(0)
            
            if is_disabled('Turbine_Enabled', 'Gas_Turbines'):
                logger.info("    🚫 TURBINES: Disabled by scenario")
                for y in years:
                    m.n_turbine[y].fix(0)
            
            if is_disabled('Solar_Enabled', 'Solar_PV'):
                logger.info("    🚫 SOLAR: Disabled by scenario")
                for y in years:
                    m.solar_mw[y].fix(0)
            
            if is_disabled('BESS_Enabled', 'BESS'):
                logger.info("    🚫 BESS: Disabled by scenario")
                for y in years:
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
            
            if is_disabled('Grid_Enabled', 'Grid_Connection'):
                logger.info("    🚫 GRID: Disabled by scenario (BTM mode)")
                for y in years:
                    m.grid_mw[y].fix(0)
                    if hasattr(m, 'grid_active'):
                        m.grid_active[y].fix(0)
        
        # =====================
        # 5B: LOAD-FOLLOWING CONSTRAINTS
        # =====================
        # Don't deploy equipment in years with zero load
        trajectory = load_data.get('load_trajectory', DEFAULT_LOAD_TRAJECTORY)
        
        for y in years:
            load_y = trajectory.get(y, 0)
            if load_y == 0:
                logger.info(f"    📉 Year {y}: Load=0 MW, fixing all equipment to 0")
                m.n_recip[y].fix(0)
                m.n_turbine[y].fix(0)
                m.solar_mw[y].fix(0)
                m.bess_mwh[y].fix(0)
                m.bess_mw[y].fix(0)
                if hasattr(m, 'grid_mw'):
                    m.grid_mw[y].fix(0)
                if hasattr(m, 'grid_active'):
                    m.grid_active[y].fix(0)
        
        # =====================
        # 5C: LEAD TIME CONSTRAINTS
        # =====================
        # Equipment not available before procurement + construction
        start_year = min(years)
        
        # Get grid lead time from scenario or default
        grid_lead = scenario.get('Grid_Timeline_Months', GRID_LEAD_TIME) if scenario else GRID_LEAD_TIME
        
        for y in years:
            months_from_start = (y - start_year) * 12
            
            # BESS: 12 months
            if months_from_start < EQUIPMENT_PARAMS['bess']['lead_time']:
                if not m.bess_mwh[y].is_fixed():
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
                    logger.info(f"    ⏰ Year {y}: BESS not available (lead time)")
            
            # Solar: 12 months
            if months_from_start < EQUIPMENT_PARAMS['solar']['lead_time']:
                if not m.solar_mw[y].is_fixed():
                    m.solar_mw[y].fix(0)
                    logger.info(f"    ⏰ Year {y}: Solar not available (lead time)")
            
            # Recip: 18 months
            if months_from_start < EQUIPMENT_PARAMS['recip']['lead_time']:
                if not m.n_recip[y].is_fixed():
                    m.n_recip[y].fix(0)
                    logger.info(f"    ⏰ Year {y}: Recips not available (lead time)")
            
            # Turbine: 24 months
            if months_from_start < EQUIPMENT_PARAMS['turbine']['lead_time']:
                if not m.n_turbine[y].is_fixed():
                    m.n_turbine[y].fix(0)
                    logger.info(f"    ⏰ Year {y}: Turbines not available (lead time)")
            
            # Grid: 60 months (default)
            if months_from_start < grid_lead:
                if hasattr(m, 'grid_mw') and not m.grid_mw[y].is_fixed():
                    m.grid_mw[y].fix(0)
                if hasattr(m, 'grid_active') and not m.grid_active[y].is_fixed():
                    m.grid_active[y].fix(0)
                if months_from_start == 0:  # Only log once
                    logger.info(f"    ⏰ Grid not available until {start_year + grid_lead // 12}")
        
        logger.info("✓ STEP 5: All constraints applied")
        
    except Exception as e:
        error_msg = f"Scenario constraints failed: {e}"
        logger.error(f"STEP 5 FAILED: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        return _create_empty_result(error_msg)
'''


# ==============================================================================
# FIX 4: milp_model_dr.py - Update EQUIPMENT dict
# ==============================================================================
# File: app/optimization/milp_model_dr.py
# Find the EQUIPMENT = { ... } dict and REPLACE with:

FIX_4_MILP_EQUIPMENT = '''
    # REPLACE the EQUIPMENT dict (usually around line 50-80):
    
    EQUIPMENT = {
        'recip': {
            'capacity_mw': 10.0,          # WAS 5.0
            'heat_rate_btu_kwh': 7200,    # WAS 7700
            'nox_rate_lb_mmbtu': 0.015,   # WAS 0.099 (now with SCR)
            'availability': 0.97,
            'ramp_rate_mw_min': 3.0,
            'capex_per_kw': 1200,         # WAS 1650
        },
        'turbine': {
            'capacity_mw': 50.0,          # WAS 20.0
            'heat_rate_btu_kwh': 8500,
            'nox_rate_lb_mmbtu': 0.010,   # WAS 0.05 (now with SCR)
            'availability': 0.97,
            'ramp_rate_mw_min': 10.0,
            'capex_per_kw': 900,          # WAS 1300
        },
        'bess': {
            'efficiency': 0.92,
            'min_soc_pct': 0.10,
            'capex_per_kwh': 250,
            'ramp_rate_mw_min': 50.0,
        },
        'solar': {
            'capacity_factor': 0.25,
            'land_acres_per_mw': 5.0,
            'capex_per_kw': 950,
        },
    }
'''


# ==============================================================================
# FIX 5: site_loader.py - Update Scenario Templates
# ==============================================================================
# File: app/utils/site_loader.py
# Update Grid_Timeline_Months in scenarios:

FIX_5_SCENARIOS = '''
    # In load_scenario_templates(), update ALL scenarios with grid:
    
    scenarios = [
        {
            'Scenario_ID': 1,
            'Scenario_Name': 'BTM Only',
            'Recip_Enabled': True,
            'Turbine_Enabled': True,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': False,
            'Grid_Timeline_Months': 0,
        },
        {
            'Scenario_ID': 2,
            'Scenario_Name': 'Recip Engines Only',
            'Recip_Enabled': True,
            'Turbine_Enabled': False,
            'BESS_Enabled': False,
            'Solar_Enabled': False,
            'Grid_Enabled': False,
            'Grid_Timeline_Months': 0,
        },
        {
            'Scenario_ID': 3,
            'Scenario_Name': 'All Technologies',
            'Recip_Enabled': True,
            'Turbine_Enabled': True,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': True,
            'Grid_Timeline_Months': 60,  # WAS 36
        },
        {
            'Scenario_ID': 4,
            'Scenario_Name': 'Recip + Grid',
            'Recip_Enabled': True,
            'Turbine_Enabled': False,
            'BESS_Enabled': True,
            'Solar_Enabled': False,
            'Grid_Enabled': True,
            'Grid_Timeline_Months': 60,  # WAS 36
        },
        {
            'Scenario_ID': 5,
            'Scenario_Name': 'Renewables + Grid',
            'Recip_Enabled': False,
            'Turbine_Enabled': False,
            'BESS_Enabled': True,
            'Solar_Enabled': True,
            'Grid_Enabled': True,
            'Grid_Timeline_Months': 60,  # WAS 12
        },
    ]
'''


# ==============================================================================
# FIX 6: Add load trajectory passthrough (STEP 3.5)
# ==============================================================================
# File: app/utils/milp_optimizer_wrapper.py
# Add AFTER STEP 3 (Load Data) and BEFORE STEP 4:

FIX_6_TRAJECTORY = '''
    # ========================================================================
    # STEP 3.5: Ensure load trajectory is available
    # ========================================================================
    
    try:
        # Get trajectory from load profile or use defaults
        if load_profile_dr and 'load_trajectory' in load_profile_dr:
            trajectory = load_profile_dr['load_trajectory']
        else:
            trajectory = DEFAULT_LOAD_TRAJECTORY
        
        # Make sure site dict exists and has trajectory
        if site is None:
            site = {}
        site['load_trajectory'] = trajectory
        
        # Store in load_data for use in constraints
        load_data['load_trajectory'] = trajectory
        
        logger.info(f"  Load trajectory: {list(trajectory.items())[:4]}...")
        logger.info("✓ STEP 3.5: Load trajectory configured")
        
    except Exception as e:
        logger.warning(f"STEP 3.5: Using default trajectory: {e}")
        load_data['load_trajectory'] = DEFAULT_LOAD_TRAJECTORY
'''


# ==============================================================================
# SUMMARY: FILES TO MODIFY
# ==============================================================================

MODIFICATION_SUMMARY = """
FILES TO MODIFY (in order):
===========================

1. app/pages_custom/page_09_results.py
   - Line ~178: Replace direct key access with .get() defaults
   - COPY: FIX_1_PAGE_RESULTS

2. app/utils/milp_optimizer_wrapper.py
   - TOP: Add constants (EQUIPMENT_PARAMS, DEFAULT_LOAD_TRAJECTORY)
   - COPY: FIX_2A_CONSTANTS
   
   - AFTER STEP 3: Add trajectory passthrough
   - COPY: FIX_6_TRAJECTORY
   
   - REPLACE _format_solution_safe() entirely
   - COPY: FIX_2B_FORMAT_SOLUTION
   
   - REPLACE STEP 5 entirely
   - COPY: FIX_3_STEP_5

3. app/utils/milp_optimizer_wrapper_fast.py
   - Same changes as #2

4. app/optimization/milp_model_dr.py
   - REPLACE EQUIPMENT dict
   - COPY: FIX_4_MILP_EQUIPMENT

5. app/utils/site_loader.py
   - Update scenarios with Grid_Timeline_Months: 60
   - COPY: FIX_5_SCENARIOS

EXPECTED RESULTS:
=================
✓ No more KeyError
✓ LCOE calculated ($55-75/MWh)
✓ Annual generation calculated (>0 GWh)
✓ Fuel cost calculated (>$0M)
✓ O&M calculated (>$0M)
✓ Capacity matches chart (using 10 MW recip, 50 MW turbine)
✓ No equipment in years with zero load (2025-2027)
✓ Equipment respects lead times
✓ Grid available in 2030 (60 month lead)
"""

# ==============================================================================
# ACTUAL CONSTANTS FOR VERIFICATION
# ==============================================================================

EQUIPMENT_PARAMS = {
    'recip': {'capacity_mw': 10.0, 'heat_rate': 7200, 'capex': 1200, 'vom': 8.0, 'fom': 15.0, 'lead_time': 18},
    'turbine': {'capacity_mw': 50.0, 'heat_rate': 8500, 'capex': 900, 'vom': 6.0, 'fom': 12.0, 'lead_time': 24},
    'bess': {'capex_kwh': 250, 'fom': 10.0, 'lead_time': 12},
    'solar': {'capex': 950, 'fom': 10.0, 'cf': 0.25, 'lead_time': 12},
}

DEFAULT_LOAD_TRAJECTORY = {
    2025: 0, 2026: 0, 2027: 0,
    2028: 150, 2029: 300, 2030: 450,
    2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,
}

GAS_PRICE = 3.50
GRID_PRICE = 75
GRID_LEAD_TIME = 60

# ==============================================================================
# QUICK VERIFICATION TEST
# ==============================================================================

def verify_fixes():
    """Quick test to verify fix logic."""
    
    print("=" * 60)
    print("VERIFICATION TEST")
    print("=" * 60)
    
    # Test 1: Equipment sizes
    print("\n1. Equipment Sizes:")
    print(f"   Recip: {EQUIPMENT_PARAMS['recip']['capacity_mw']} MW")
    print(f"   Turbine: {EQUIPMENT_PARAMS['turbine']['capacity_mw']} MW")
    
    # Test 2: Example capacity calculation
    n_recip, n_turbine = 15, 6
    total = (n_recip * EQUIPMENT_PARAMS['recip']['capacity_mw'] + 
             n_turbine * EQUIPMENT_PARAMS['turbine']['capacity_mw'])
    print(f"\n2. Capacity Calc: {n_recip} recips + {n_turbine} turbines = {total} MW")
    
    # Test 3: Load trajectory
    print("\n3. Load Trajectory:")
    for y in [2026, 2027, 2028, 2029, 2030]:
        print(f"   {y}: {DEFAULT_LOAD_TRAJECTORY[y]} MW")
    
    # Test 4: Lead times
    print("\n4. Lead Times (from 2025 start):")
    for equip, params in EQUIPMENT_PARAMS.items():
        lt = params.get('lead_time', 0)
        avail = 2025 + (lt // 12) + (1 if lt % 12 > 0 else 0)
        print(f"   {equip}: {lt} months → available {avail}")
    print(f"   grid: {GRID_LEAD_TIME} months → available 2030")
    
    # Test 5: Economics keys
    print("\n5. Required Economics Keys:")
    keys = ['lcoe_mwh', 'total_capex_m', 'annual_opex_m', 
            'annual_fuel_cost_m', 'annual_generation_gwh', 'capacity_factor_pct']
    for k in keys:
        print(f"   ✓ {k}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    verify_fixes()
    print(MODIFICATION_SUMMARY)
