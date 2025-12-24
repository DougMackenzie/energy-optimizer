# bvNexus Complete Fix Package v3 - Executive Summary

**Date:** December 23, 2025  
**Status:** All tests passed ✅

---

## Key Corrections Applied

| Item | Previous | Corrected | Impact |
|------|----------|-----------|--------|
| **Recip NOx Rate** | 0.099 lb/MMBtu | **0.015 lb/MMBtu** | ~302 MW thermal within 100 tpy (was ~130 MW) |
| **Turbine NOx Rate** | 0.05 lb/MMBtu | **0.010 lb/MMBtu** | Consistent with SCR |
| **Grid Timeline** | 36 months | **60 months** (user modifiable) | Realistic interconnection |
| **Load Default** | Undefined | **600 MW utility** | 150 MW → 600 MW over 4 years |

---

## 1. Code Bugs Fixed (3)

### Bug 1: Scenario Constraint Logic
```python
# WRONG (AND logic - both must be False):
if not is_enabled('Grid_Enabled', True) and not is_enabled('Grid_Connection', True):

# CORRECT (OR logic - either being False disables):
if is_disabled('Grid_Enabled', 'Grid_Connection'):
```

### Bug 2: LCOE Extraction
```python
# WRONG (0 is falsy):
if lcoe and lcoe < 1000:

# CORRECT:
if lcoe is not None and 0 <= lcoe < 1000:
```

### Bug 3: Load Trajectory Passthrough
```python
# ADD before optimizer.build():
site['load_trajectory'] = load_profile_dr.get('load_trajectory', DEFAULT_TRAJECTORY)
```

---

## 2. Equipment Parameters Corrected

### milp_model_dr.py EQUIPMENT dict

```python
EQUIPMENT = {
    'recip': {
        'capacity_mw': 10.0,
        'heat_rate_btu_kwh': 7200,
        'nox_rate_lb_mmbtu': 0.015,  # WITH ADVANCED SCR
        'capex_per_kw': 1200,
        'availability': 0.97,
        'ramp_rate_mw_min': 3.0,
    },
    'turbine': {
        'capacity_mw': 50.0,
        'heat_rate_btu_kwh': 8500,
        'nox_rate_lb_mmbtu': 0.010,  # WITH ADVANCED SCR
        'capex_per_kw': 900,
        'availability': 0.97,
        'ramp_rate_mw_min': 10.0,
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
```

### NOx Verification
```
300 MW thermal @ 70% CF:
  Annual generation: 1,839,600 MWh
  Heat input: 13,245,120 MMBtu
  NOx emissions: 99.3 tpy
  ✓ Within 100 tpy limit
```

---

## 3. Default Load Trajectory (User Modifiable)

| Year | Utility MW | Notes |
|------|------------|-------|
| 2025 | 0 | Pre-construction |
| 2026 | 0 | Pre-construction |
| 2027 | 0 | Pre-construction |
| 2028 | **150** | First load |
| 2029 | **300** | +150 MW |
| 2030 | **450** | +150 MW |
| 2031 | **600** | Full capacity |
| 2032+ | 600 | Steady state |

**Note:** This is UTILITY power (seen by grid/BTM), not IT load.  
For PUE = 1.25: IT Load = 600 ÷ 1.25 = 480 MW

### User Modifiable Settings
- `target_utility_mw`: Default 600
- `first_load_year`: Default 2028
- `first_load_mw`: Default 150
- `annual_increment_mw`: Default 150

---

## 4. Grid Configuration (User Modifiable)

| Setting | Default | Notes |
|---------|---------|-------|
| `grid_timeline_months` | **60** | Large load interconnection |
| `grid_interconnection_year` | 2030 | Calculated from timeline |
| `grid_available_mw` | 600 | User sets based on study |
| `grid_cost_per_mwh` | $75 | Market dependent |

---

## 5. Google Sheets Updates

**Spreadsheet ID:** `1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so`

### Updates Required

| Worksheet | Change |
|-----------|--------|
| Reciprocating_Engines | NOx_lb_MMBtu: 0.099 → **0.015** |
| Gas_Turbines | NOx_lb_MMBtu: 0.099 → **0.010** |
| Site_Constraints | ADD columns for user settings |
| **NEW: Load_Trajectory_Defaults** | Trajectory configuration |

### New Columns for Site_Constraints
- `Grid_Timeline_Months`
- `Target_Utility_MW`
- `First_Load_Year`
- `First_Load_MW`
- `Annual_Increment_MW`

---

## 6. Files to Modify

| File | Changes |
|------|---------|
| `app/optimization/milp_model_dr.py` | Replace EQUIPMENT dict |
| `app/utils/milp_optimizer_wrapper.py` | Fix STEP 5, add trajectory, fix LCOE |
| `app/utils/milp_optimizer_wrapper_fast.py` | Same as above |
| `app/utils/site_loader.py` | Update scenario timelines |
| `scripts/update_google_sheets.py` | NEW: Run to update sheets |

---

## 7. Expected Results After Fixes

### BTM Only Scenario (600 MW load)

| Metric | Before | After |
|--------|--------|-------|
| Grid MW | >0 (bug) | **0** |
| Recip Count | 0 | 20-30 units |
| Turbine Count | 0 | 2-4 units |
| BESS | 0 | 200-400 MWh |
| NOx Usage | N/A | 80-100 tpy |
| LCOE | $0 (bug) | **$60-75/MWh** |

### Thermal Capacity Within NOx Limit

| Limit | Before (wrong NOx) | After (with SCR) |
|-------|-------------------|------------------|
| 100 tpy | ~130 MW | **~300 MW** |
| 50 tpy | ~65 MW | **~150 MW** |

---

## 8. Verification Results

```
✓ Max thermal @ 100 tpy NOx: 302 MW
✓ Grid timeline default: 60 months
✓ Load trajectory: 150→300→450→600 MW
✓ Scenario constraint logic: All tests passed
✓ LCOE extraction: Fixed
```

---

## Quick Reference - Copy/Paste Code

### EQUIPMENT Dict (milp_model_dr.py)
```python
EQUIPMENT = {
    'recip': {'capacity_mw': 10.0, 'heat_rate_btu_kwh': 7200, 'nox_rate_lb_mmbtu': 0.015, 'capex_per_kw': 1200, 'availability': 0.97, 'ramp_rate_mw_min': 3.0},
    'turbine': {'capacity_mw': 50.0, 'heat_rate_btu_kwh': 8500, 'nox_rate_lb_mmbtu': 0.010, 'capex_per_kw': 900, 'availability': 0.97, 'ramp_rate_mw_min': 10.0},
    'bess': {'efficiency': 0.92, 'min_soc_pct': 0.10, 'capex_per_kwh': 250, 'ramp_rate_mw_min': 50.0},
    'solar': {'capacity_factor': 0.25, 'land_acres_per_mw': 5.0, 'capex_per_kw': 950},
}
```

### is_disabled() Function (milp_optimizer_wrapper.py)
```python
def is_disabled(primary_key, alt_key=None):
    for key in [primary_key, alt_key]:
        if key and key in scenario:
            val = scenario[key]
            if isinstance(val, str) and val.lower() in ('false', 'no', '0', 'disabled'):
                return True
            elif val == False:
                return True
    return False
```

### Default Load Trajectory
```python
DEFAULT_LOAD_TRAJECTORY = {
    2025: 0, 2026: 0, 2027: 0,
    2028: 150, 2029: 300, 2030: 450,
    2031: 600, 2032: 600, 2033: 600, 2034: 600, 2035: 600,
}
```
