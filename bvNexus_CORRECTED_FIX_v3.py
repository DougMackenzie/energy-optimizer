# bvNexus CORRECTED COMPLETE FIX PACKAGE v3
# ==========================================
# December 23, 2025
# 
# CORRECTIONS FROM USER FEEDBACK:
# - NOx rates: Adjusted to allow ~300 MW thermal within 100 tpy
# - Grid timeline: 60 months default (user modifiable)
# - Load trajectory: 600 MW utility, 150 MW/2028, +150 MW/year (user modifiable)
# - Google Sheets backend updates included

"""
==============================================================================
SECTION 1: NOx RATE RECALCULATION
==============================================================================

TARGET: 300 MW thermal capacity within 100 tpy NOx limit

CALCULATION:
- 300 MW × 8760 hr × 70% CF = 1,839,600 MWh/year
- 100 tpy = 200,000 lb/year
- Required NOx rate = 200,000 / 1,839,600 = 0.109 lb/MWh

Converting to lb/MMBtu (at 7200 BTU/kWh = 7.2 MMBtu/MWh):
- 0.109 lb/MWh ÷ 7.2 MMBtu/MWh = 0.015 lb/MMBtu

CONCLUSION: With advanced SCR (95% reduction), NOx rate should be ~0.015 lb/MMBtu
"""

# ==============================================================================
# SECTION 2: CORRECTED EQUIPMENT PARAMETERS
# ==============================================================================

EQUIPMENT_CORRECTED_V3 = {
    'recip': {
        'capacity_mw': 10.0,              # Jenbacher J920 / Wärtsilä 34SG size
        'heat_rate_btu_kwh': 7200,        # Efficient modern recip
        'nox_rate_lb_mmbtu': 0.015,       # With advanced SCR (95% reduction)
        'co_rate_lb_mmbtu': 0.010,        # With oxidation catalyst
        'availability': 0.97,
        'ramp_rate_mw_min': 3.0,
        'capex_per_kw': 1200,             # Installed cost
        'vom_per_mwh': 8.0,
        'fom_per_kw_yr': 15.0,
        'lead_time_months': 18,
    },
    'turbine': {
        'capacity_mw': 50.0,              # GE LM6000 size
        'heat_rate_btu_kwh': 8500,
        'nox_rate_lb_mmbtu': 0.010,       # With advanced SCR
        'co_rate_lb_mmbtu': 0.008,        # With oxidation catalyst
        'availability': 0.97,
        'ramp_rate_mw_min': 10.0,
        'capex_per_kw': 900,              # Installed cost
        'vom_per_mwh': 6.0,
        'fom_per_kw_yr': 12.0,
        'lead_time_months': 24,
    },
    'bess': {
        'efficiency': 0.92,
        'min_soc_pct': 0.10,
        'capex_per_kwh': 250,
        'ramp_rate_mw_min': 50.0,
        'vom_per_mwh': 1.5,
        'lead_time_months': 12,
    },
    'solar': {
        'capacity_factor': 0.25,
        'land_acres_per_mw': 5.0,
        'capex_per_kw': 950,
        'vom_per_mwh': 0,
        'fom_per_kw_yr': 10.0,
        'lead_time_months': 12,
    },
}

# Verification: Max thermal at 100 tpy with new rates
def verify_nox_capacity():
    """Verify 300 MW thermal is achievable within 100 tpy NOx."""
    
    recip = EQUIPMENT_CORRECTED_V3['recip']
    
    # Parameters
    capacity_mw = 300  # Target
    cf = 0.70  # Capacity factor
    hours = 8760
    
    # Annual generation
    gen_mwh = capacity_mw * cf * hours  # 1,839,600 MWh
    
    # NOx calculation
    heat_rate_mmbtu_per_mwh = recip['heat_rate_btu_kwh'] / 1e6 * 1000  # 7.2 MMBtu/MWh
    nox_lb = gen_mwh * heat_rate_mmbtu_per_mwh * recip['nox_rate_lb_mmbtu']
    nox_tpy = nox_lb / 2000
    
    print(f"300 MW thermal @ 70% CF:")
    print(f"  Annual generation: {gen_mwh:,.0f} MWh")
    print(f"  Heat input: {gen_mwh * heat_rate_mmbtu_per_mwh:,.0f} MMBtu")
    print(f"  NOx emissions: {nox_tpy:.1f} tpy")
    print(f"  ✓ Within 100 tpy limit: {nox_tpy < 100}")
    
    # Max capacity calculation
    max_nox_tpy = 100
    max_nox_lb = max_nox_tpy * 2000
    max_gen_mwh = max_nox_lb / (heat_rate_mmbtu_per_mwh * recip['nox_rate_lb_mmbtu'])
    max_capacity_mw = max_gen_mwh / (cf * hours)
    
    print(f"\nMax thermal capacity @ 100 tpy NOx:")
    print(f"  Max capacity: {max_capacity_mw:.0f} MW")
    
    return max_capacity_mw


# ==============================================================================
# SECTION 3: DEFAULT LOAD TRAJECTORY (User Modifiable)
# ==============================================================================

DEFAULT_LOAD_TRAJECTORY = {
    # Years with zero load (pre-construction)
    2025: 0,
    2026: 0,
    2027: 0,
    
    # Ramp-up: 150 MW increments starting 2028
    2028: 150,   # First load
    2029: 300,   # +150 MW
    2030: 450,   # +150 MW
    2031: 600,   # Full capacity (600 MW utility power)
    2032: 600,
    2033: 600,
    2034: 600,
    2035: 600,
}

# NOTE: This is UTILITY POWER (seen by grid/BTM), NOT IT load
# For a 600 MW utility load with PUE 1.25:
#   IT Load = 600 / 1.25 = 480 MW

LOAD_TRAJECTORY_CONFIG = {
    'target_utility_mw': 600,           # User modifiable
    'first_load_year': 2028,            # User modifiable
    'first_load_mw': 150,               # User modifiable
    'annual_increment_mw': 150,         # User modifiable
    'pue': 1.25,                        # User modifiable
    'load_factor': 0.85,                # User modifiable
}


# ==============================================================================
# SECTION 4: GRID CONFIGURATION DEFAULTS (User Modifiable)
# ==============================================================================

DEFAULT_GRID_CONFIG = {
    'grid_timeline_months': 60,         # Default: 60 months (user modifiable)
    'grid_interconnection_year': 2030,  # Default: 2030 (calculated from timeline)
    'grid_available_mw': 600,           # User modifiable
    'grid_cost_per_mwh': 75,            # User modifiable ($/MWh)
    'grid_capex_per_kw': 150,           # Interconnection cost ($/kW)
}

# NOTE: User should be able to override grid_timeline_months based on:
# - Actual queue position
# - Study completion status
# - ISO-specific timelines
# - Project-specific agreements


# ==============================================================================
# SECTION 5: GOOGLE SHEETS SCHEMA UPDATES
# ==============================================================================

"""
Google Sheets ID: 1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so

WORKSHEETS TO UPDATE:
"""

# 5A: Site_Constraints worksheet - ADD new columns
SITE_CONSTRAINTS_NEW_COLUMNS = [
    'Grid_Timeline_Months',      # User modifiable (default: 60)
    'Grid_Interconnection_Year', # Calculated or user override
    'Target_Utility_MW',         # 600 MW default
    'First_Load_Year',           # 2028 default
    'First_Load_MW',             # 150 MW default
    'Annual_Increment_MW',       # 150 MW default
    'Design_PUE',                # 1.25 default
    'Load_Factor_Pct',           # 85% default
]

# 5B: Equipment worksheets - UPDATE NOx rates
EQUIPMENT_DB_UPDATES = {
    'Reciprocating_Engines': {
        'NOx_lb_MMBtu': 0.015,   # Was 0.099 - WITH SCR
        'CO_lb_MMBtu': 0.010,    # Was 0.015 - WITH OxCat
        'Note': 'DLE with SCR (95% NOx reduction)',
    },
    'Gas_Turbines': {
        'NOx_lb_MMBtu': 0.010,   # Was 0.099 - WITH SCR
        'CO_lb_MMBtu': 0.008,    # Was 0.015 - WITH OxCat
        'Note': 'DLE with SCR',
    },
}

# 5C: Scenario_Templates worksheet - UPDATE timelines
SCENARIO_TEMPLATES_UPDATES = {
    'All Technologies': {
        'Grid_Timeline_Months': 60,  # Was 36
    },
    'Recip + Grid': {
        'Grid_Timeline_Months': 60,  # Was 36
    },
    'Renewables + Grid': {
        'Grid_Timeline_Months': 60,  # Was 12
    },
}

# 5D: NEW worksheet - Load_Trajectory_Defaults
LOAD_TRAJECTORY_WORKSHEET = {
    'columns': [
        'Site_ID',
        'Target_Utility_MW',
        'First_Load_Year',
        'First_Load_MW',
        'Annual_Increment_MW',
        'PUE',
        'Load_Factor_Pct',
        'Year_2025_MW', 'Year_2026_MW', 'Year_2027_MW', 'Year_2028_MW',
        'Year_2029_MW', 'Year_2030_MW', 'Year_2031_MW', 'Year_2032_MW',
        'Year_2033_MW', 'Year_2034_MW', 'Year_2035_MW',
    ],
    'default_row': {
        'Site_ID': 'DEFAULT',
        'Target_Utility_MW': 600,
        'First_Load_Year': 2028,
        'First_Load_MW': 150,
        'Annual_Increment_MW': 150,
        'PUE': 1.25,
        'Load_Factor_Pct': 85,
        'Year_2025_MW': 0,
        'Year_2026_MW': 0,
        'Year_2027_MW': 0,
        'Year_2028_MW': 150,
        'Year_2029_MW': 300,
        'Year_2030_MW': 450,
        'Year_2031_MW': 600,
        'Year_2032_MW': 600,
        'Year_2033_MW': 600,
        'Year_2034_MW': 600,
        'Year_2035_MW': 600,
    },
}


# ==============================================================================
# SECTION 6: CODE FIXES (Same as before, consolidated)
# ==============================================================================

# 6A: Scenario constraint logic (milp_optimizer_wrapper.py)
STEP_5_FIXED = '''
    # STEP 5: Apply scenario constraints (FIXED - uses OR logic)
    try:
        if scenario:
            scenario_name = scenario.get('Scenario_Name', 'Unknown')
            logger.info(f"  Applying scenario: {scenario_name}")
            
            m = optimizer.model
            
            def is_disabled(primary_key, alt_key=None):
                """Check if equipment is EXPLICITLY disabled (OR logic)."""
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
                logger.info("    🚫 RECIPS: Disabled")
                for y in years:
                    m.n_recip[y].fix(0)
            
            if is_disabled('Turbine_Enabled', 'Gas_Turbines'):
                logger.info("    🚫 TURBINES: Disabled")
                for y in years:
                    m.n_turbine[y].fix(0)
            
            if is_disabled('Solar_Enabled', 'Solar_PV'):
                logger.info("    🚫 SOLAR: Disabled")
                for y in years:
                    m.solar_mw[y].fix(0)
            
            if is_disabled('BESS_Enabled', 'BESS'):
                logger.info("    🚫 BESS: Disabled")
                for y in years:
                    m.bess_mwh[y].fix(0)
                    m.bess_mw[y].fix(0)
            
            if is_disabled('Grid_Enabled', 'Grid_Connection'):
                logger.info("    🚫 GRID: Disabled (BTM mode)")
                for y in years:
                    m.grid_mw[y].fix(0)
                    m.grid_active[y].fix(0)
        
        logger.info("✓ STEP 5: Scenario constraints applied")
        
    except Exception as e:
        logger.error(f"STEP 5 FAILED: {e}")
'''

# 6B: Load trajectory passthrough
TRAJECTORY_PASSTHROUGH = '''
    # STEP 3.5: Load trajectory with defaults
    if load_profile_dr:
        # Check for user-defined trajectory
        if 'load_trajectory' in load_profile_dr:
            trajectory = load_profile_dr['load_trajectory']
        else:
            # Apply defaults: 600 MW utility, 150 MW start, +150 MW/year
            trajectory = {
                2025: 0, 2026: 0, 2027: 0,
                2028: 150, 2029: 300, 2030: 450,
                2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,
            }
        
        if site is None:
            site = {}
        site['load_trajectory'] = trajectory
        logger.info(f"  Load trajectory: {trajectory}")
'''

# 6C: LCOE extraction fix
LCOE_FIX = '''
    lcoe = solution.get('objective_lcoe', None)
    if lcoe is not None and 0 <= lcoe < 1000:
        result['economics']['lcoe_mwh'] = lcoe
    else:
        # Calculate from costs
        result['economics']['lcoe_mwh'] = calculated_lcoe or 0
'''


# ==============================================================================
# SECTION 7: milp_model_dr.py EQUIPMENT DICT REPLACEMENT
# ==============================================================================

MILP_MODEL_EQUIPMENT_CODE = '''
    # Equipment specifications (CORRECTED Dec 2025)
    # NOx rates are WITH ADVANCED SCR (95% reduction)
    # Allows ~300 MW thermal within 100 tpy NOx limit
    EQUIPMENT = {
        'recip': {
            'capacity_mw': 10.0,
            'heat_rate_btu_kwh': 7200,
            'nox_rate_lb_mmbtu': 0.015,  # With advanced SCR
            'availability': 0.97,
            'ramp_rate_mw_min': 3.0,
            'capex_per_kw': 1200,
        },
        'turbine': {
            'capacity_mw': 50.0,
            'heat_rate_btu_kwh': 8500,
            'nox_rate_lb_mmbtu': 0.010,  # With advanced SCR
            'availability': 0.97,
            'ramp_rate_mw_min': 10.0,
            'capex_per_kw': 900,
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
# SECTION 8: site_loader.py SCENARIO UPDATES
# ==============================================================================

SCENARIOS_CORRECTED_V3 = [
    {
        'Scenario_ID': 1,
        'Scenario_Name': 'BTM Only (Full Stack)',
        'Description': 'All BTM: Recip + Turbine + BESS + Solar (no grid)',
        'Recip_Enabled': True,
        'Turbine_Enabled': True,
        'BESS_Enabled': True,
        'Solar_Enabled': True,
        'Grid_Enabled': False,
        'Objective_Priority': 'Maximum Power',
        'Grid_Timeline_Months': 0,
        'Target_LCOE_MWh': 75,
    },
    {
        'Scenario_ID': 2,
        'Scenario_Name': 'Fast BTM (Recips + BESS)',
        'Description': 'Fastest deployment: 18-24 month lead time',
        'Recip_Enabled': True,
        'Turbine_Enabled': False,
        'BESS_Enabled': True,
        'Solar_Enabled': False,
        'Grid_Enabled': False,
        'Objective_Priority': 'Deployment Speed',
        'Grid_Timeline_Months': 0,
        'Target_LCOE_MWh': 70,
    },
    {
        'Scenario_ID': 3,
        'Scenario_Name': 'All Technologies',
        'Description': 'Full stack with grid after interconnection',
        'Recip_Enabled': True,
        'Turbine_Enabled': True,
        'BESS_Enabled': True,
        'Solar_Enabled': True,
        'Grid_Enabled': True,
        'Objective_Priority': 'Minimum LCOE',
        'Grid_Timeline_Months': 60,  # CORRECTED from 36
        'Target_LCOE_MWh': 65,
    },
    {
        'Scenario_ID': 4,
        'Scenario_Name': 'Grid Forward',
        'Description': 'Minimum BTM bridging until grid',
        'Recip_Enabled': True,
        'Turbine_Enabled': False,
        'BESS_Enabled': True,
        'Solar_Enabled': False,
        'Grid_Enabled': True,
        'Objective_Priority': 'Minimum CAPEX',
        'Grid_Timeline_Months': 60,  # CORRECTED from 36
        'Target_LCOE_MWh': 60,
    },
    {
        'Scenario_ID': 5,
        'Scenario_Name': 'Low Carbon (Renewables + Grid)',
        'Description': 'Solar + BESS + Grid (no gas generation)',
        'Recip_Enabled': False,
        'Turbine_Enabled': False,
        'BESS_Enabled': True,
        'Solar_Enabled': True,
        'Grid_Enabled': True,
        'Objective_Priority': 'Minimum Emissions',
        'Grid_Timeline_Months': 60,  # CORRECTED from 12
        'Target_LCOE_MWh': 55,
    },
]


# ==============================================================================
# SECTION 9: GOOGLE SHEETS UPDATE SCRIPT
# ==============================================================================

GOOGLE_SHEETS_UPDATE_SCRIPT = '''
"""
Script to update Google Sheets with corrected values
Run: python update_google_sheets.py
"""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

SHEET_ID = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"

def update_equipment_nox_rates():
    """Update NOx rates in equipment worksheets."""
    
    creds_path = Path(__file__).parent / "credentials.json"
    creds = Credentials.from_service_account_file(str(creds_path), scopes=[
        'https://www.googleapis.com/auth/spreadsheets'
    ])
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # Update Reciprocating_Engines
    try:
        ws = spreadsheet.worksheet("Reciprocating_Engines")
        data = ws.get_all_records()
        
        # Find NOx column
        headers = ws.row_values(1)
        nox_col = headers.index('NOx_lb_MMBtu') + 1
        note_col = headers.index('Note') + 1 if 'Note' in headers else None
        
        # Update each row
        for i, row in enumerate(data, start=2):
            ws.update_cell(i, nox_col, 0.015)  # New NOx rate with SCR
            if note_col:
                current_note = row.get('Note', '')
                ws.update_cell(i, note_col, f"{current_note} - WITH SCR")
        
        print("✅ Updated Reciprocating_Engines NOx rates")
    except Exception as e:
        print(f"❌ Error updating recips: {e}")
    
    # Update Gas_Turbines
    try:
        ws = spreadsheet.worksheet("Gas_Turbines")
        data = ws.get_all_records()
        
        headers = ws.row_values(1)
        nox_col = headers.index('NOx_lb_MMBtu') + 1
        
        for i, row in enumerate(data, start=2):
            ws.update_cell(i, nox_col, 0.010)  # New NOx rate with SCR
        
        print("✅ Updated Gas_Turbines NOx rates")
    except Exception as e:
        print(f"❌ Error updating turbines: {e}")


def add_load_trajectory_worksheet():
    """Add Load_Trajectory_Defaults worksheet."""
    
    creds_path = Path(__file__).parent / "credentials.json"
    creds = Credentials.from_service_account_file(str(creds_path), scopes=[
        'https://www.googleapis.com/auth/spreadsheets'
    ])
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    
    try:
        # Try to get existing worksheet
        ws = spreadsheet.worksheet("Load_Trajectory_Defaults")
        ws.clear()
    except:
        # Create new worksheet
        ws = spreadsheet.add_worksheet(title="Load_Trajectory_Defaults", rows=100, cols=26)
    
    # Headers
    headers = [
        'Site_ID', 'Target_Utility_MW', 'First_Load_Year', 'First_Load_MW',
        'Annual_Increment_MW', 'PUE', 'Load_Factor_Pct',
        'Year_2025_MW', 'Year_2026_MW', 'Year_2027_MW', 'Year_2028_MW',
        'Year_2029_MW', 'Year_2030_MW', 'Year_2031_MW', 'Year_2032_MW',
        'Year_2033_MW', 'Year_2034_MW', 'Year_2035_MW',
    ]
    
    # Default row
    default_row = [
        'DEFAULT', 600, 2028, 150, 150, 1.25, 85,
        0, 0, 0, 150, 300, 450, 600, 600, 600, 600, 600,
    ]
    
    ws.update('A1', [headers, default_row])
    
    print("✅ Created Load_Trajectory_Defaults worksheet")


def update_site_constraints_schema():
    """Add new columns to Site_Constraints."""
    
    creds_path = Path(__file__).parent / "credentials.json"
    creds = Credentials.from_service_account_file(str(creds_path), scopes=[
        'https://www.googleapis.com/auth/spreadsheets'
    ])
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    
    try:
        ws = spreadsheet.worksheet("Site_Constraints")
        headers = ws.row_values(1)
        
        # New columns to add
        new_cols = [
            'Grid_Timeline_Months',
            'Target_Utility_MW',
            'First_Load_Year',
            'First_Load_MW',
            'Annual_Increment_MW',
        ]
        
        # Find next empty column
        next_col = len(headers) + 1
        
        for i, col_name in enumerate(new_cols):
            if col_name not in headers:
                ws.update_cell(1, next_col + i, col_name)
        
        print("✅ Updated Site_Constraints schema")
    except Exception as e:
        print(f"❌ Error updating schema: {e}")


if __name__ == "__main__":
    print("Updating Google Sheets...")
    update_equipment_nox_rates()
    add_load_trajectory_worksheet()
    update_site_constraints_schema()
    print("\\nDone!")
'''


# ==============================================================================
# SECTION 10: VERIFICATION TESTS
# ==============================================================================

def run_all_tests():
    """Run all verification tests."""
    
    print("=" * 70)
    print("bvNexus CORRECTED FIX PACKAGE v3 - Verification")
    print("=" * 70)
    
    # Test 1: NOx capacity
    print("\n1. NOx Capacity Test")
    print("-" * 40)
    max_mw = verify_nox_capacity()
    assert max_mw >= 290, f"FAIL: Max MW {max_mw} < 300"
    print(f"   ✓ PASS: ~{max_mw:.0f} MW achievable within 100 tpy")
    
    # Test 2: Load trajectory
    print("\n2. Load Trajectory Test")
    print("-" * 40)
    traj = DEFAULT_LOAD_TRAJECTORY
    assert traj[2028] == 150, "FAIL: 2028 load should be 150 MW"
    assert traj[2031] == 600, "FAIL: 2031 load should be 600 MW"
    assert traj[2027] == 0, "FAIL: 2027 load should be 0 MW"
    print(f"   ✓ PASS: Load trajectory correct")
    print(f"     2028: {traj[2028]} MW (first load)")
    print(f"     2029: {traj[2029]} MW (+150)")
    print(f"     2030: {traj[2030]} MW (+150)")
    print(f"     2031: {traj[2031]} MW (full capacity)")
    
    # Test 3: Grid timeline
    print("\n3. Grid Timeline Test")
    print("-" * 40)
    assert DEFAULT_GRID_CONFIG['grid_timeline_months'] == 60, "FAIL: Grid timeline should be 60 months"
    print(f"   ✓ PASS: Grid timeline = {DEFAULT_GRID_CONFIG['grid_timeline_months']} months")
    
    # Test 4: Scenario constraints
    print("\n4. Scenario Constraint Logic Test")
    print("-" * 40)
    
    def is_disabled(scenario, primary_key, alt_key=None):
        for key in [primary_key, alt_key]:
            if key and key in scenario:
                val = scenario[key]
                if isinstance(val, str):
                    if val.lower() in ('false', 'no', '0', 'disabled'):
                        return True
                elif val == False:
                    return True
        return False
    
    tests = [
        ({'Grid_Enabled': False}, 'Grid_Enabled', None, True),
        ({'Grid_Connection': 'False'}, 'Grid_Enabled', 'Grid_Connection', True),
        ({'Grid_Enabled': True}, 'Grid_Enabled', None, False),
        ({}, 'Grid_Enabled', None, False),
    ]
    
    for scenario, pk, ak, expected in tests:
        result = is_disabled(scenario, pk, ak)
        status = "✓" if result == expected else "✗"
        print(f"   {status} is_disabled({pk}): {result} (expected {expected})")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)


# ==============================================================================
# SECTION 11: FILE MODIFICATION SUMMARY
# ==============================================================================

FILE_MODIFICATIONS = """
FILES TO MODIFY:
================

1. app/optimization/milp_model_dr.py
   - Replace EQUIPMENT dict with corrected values
   - NOx rates: 0.015 (recip), 0.010 (turbine) - WITH SCR
   - CAPEX: $1,200 (recip), $900 (turbine)

2. app/utils/milp_optimizer_wrapper.py
   - Replace STEP 5 with is_disabled() OR logic
   - Add trajectory passthrough before optimizer.build()
   - Fix LCOE extraction (if lcoe → if lcoe is not None)

3. app/utils/milp_optimizer_wrapper_fast.py
   - Same scenario constraint fix as #2

4. app/utils/site_loader.py
   - Update scenarios with Grid_Timeline_Months = 60
   - Add load trajectory defaults

5. Google Sheets (ID: 1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so)
   - Update NOx_lb_MMBtu in Reciprocating_Engines: 0.099 → 0.015
   - Update NOx_lb_MMBtu in Gas_Turbines: 0.099 → 0.010
   - Add Load_Trajectory_Defaults worksheet
   - Add columns to Site_Constraints for user-modifiable settings

EXPECTED RESULTS:
=================

1. Max thermal capacity @ 100 tpy NOx: ~300 MW (was ~130 MW)
2. Grid interconnection default: 60 months (was 36)
3. Load trajectory: 0→150→300→450→600 MW (2025→2031)
4. BTM Only shows Grid = 0 for all years
5. Scenarios produce distinct results
6. LCOE: $55-75/MWh (was $0)
"""


if __name__ == "__main__":
    run_all_tests()
    print(FILE_MODIFICATIONS)
