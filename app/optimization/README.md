# bvNexus Optimization Module

**Version:** 2.1.1  
**Last Updated:** December 30, 2025  
**Status:** Production Ready

## Overview

This module provides comprehensive power optimization capabilities for AI datacenter greenfield developments:

- **Greenfield Heuristic v2.1.1** (NEW) - Production-ready optimizer with Google Sheets backend integration
- **MILP Optimizer** - Mixed-Integer Linear Programming for detailed design
- **Legacy Heuristics** - Original multi-problem optimizers (maintained for backward compatibility)

## Quick Start

### Using Greenfield Heuristic v2.1.1

```python
from app.optimization import GreenfieldHeuristicV2

# Define site and load trajectory
site = {'name': 'Dallas DC', 'location': 'Dallas, TX'}
load_trajectory = {
    2028: 200,  # MW
    2029: 400,
    2030: 600,
    2031: 750,
}

# Define constraints
constraints = {
    'nox_tpy_annual': 100,          # NOx emissions limit (tpy)
    'gas_supply_mcf_day': 100000,   # Gas supply limit (MCF/day)
    'land_area_acres': 500,         # Available land (acres)
    'grid_available_year': 2030,    # Grid interconnection year
    'grid_capacity_mw': 500,        # Grid capacity (MW)
}

# Optional: Define load profile characteristics
load_profile_data = {
    'flexibility_pct': 30.6,  # % of load that is flexible
    'workload_mix': {
        'pre_training': 45.0,
        'fine_tuning': 20.0,
        'batch_inference': 15.0,
        'real_time_inference': 20.0,
    }
}

# Create and run optimizer
optimizer = GreenfieldHeuristicV2(
    site=site,
    load_trajectory=load_trajectory,
    constraints=constraints,
    load_profile_data=load_profile_data,
)

result = optimizer.optimize()

# Access results
print(f"Feasible: {result.feasible}")
print(f"LCOE: ${result.lcoe:.2f}/MWh")
print(f"Load Coverage: {result.load_coverage_pct:.1f}%")
print(f"Equipment: {result.equipment_config}")
```

### With Google Sheets Backend

```python
import gspread
from app.optimization import GreenfieldHeuristicV2

# Connect to Google Sheets
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_ID = 'your_spreadsheet_id'

# Run with backend
optimizer = GreenfieldHeuristicV2(
    site=site,
    load_trajectory=load_trajectory,
    constraints=constraints,
    sheets_client=gc,
    spreadsheet_id=SPREADSHEET_ID,
    load_profile_data=load_profile_data,
)

result = optimizer.optimize()
```

## New in v2.1.1

### Features

- ✅ **gspread Integration** - Direct connection to Google Sheets backend for equipment specs and parameters
- ✅ **Dynamic Ramp Calculation** - Ramp requirements calculated based on AI workload mix
- ✅ **BESS Reliability Charging** - Battery charges from excess thermal/grid power (not just solar)
- ✅ **Economic Dispatch** - Merit order dispatch comparing grid vs thermal costs
- ✅ **Grid CAPEX** - Grid interconnection costs properly included in total CAPEX
- ✅ **OPEX Bug Fix** - Fixed calculation using stored MW values
- ✅ **Solar Profile Generation** - Realistic 8760 solar output profiles
- ✅ **Constraint Checking** - Hard (0% tolerance) and soft (10% tolerance) constraints

### Key Improvements

**Lead Times (Corrected per User Spec):**
- Recip: 12 → **24 months**
- Gas Turbine: 18 → **30 months**
- BESS: 6 months
- Solar: 12 months
- Grid: 60 months (default, site-specific override available)

**Ramp Rates (From Equipment Research):**
- Recip Engine: 100%/min (< 5 min to full load)
- Aero Turbine: 50%/min (8-10 min to full load)
- Frame Turbine: 17.5%/min (20-30 min to full load)
- BESS: Instantaneous (100%+/min)

**Workload-Based Ramp Factors:**
| Workload Type | Ramp Factor | Rationale |
|---------------|-------------|-----------|
| Pre-training | 0.00 | Stable, days-long jobs |
| Fine-tuning | 0.05 | Moderate cycling |
| Batch Inference | 0.00 | Deferrable/queued |
| Real-time Inference | 0.50 | High volatility (SLA protected) |
| RL Training | 0.10 | Moderate |
| Cloud HPC | 0.02 | Batch-like |

## Files

| File | Purpose |
|------|---------|
| `greenfield_heuristic_v2.py` | Main optimizer implementation (v2.1.1) |
| `GREENFIELD_HEURISTIC_RULES.md` | **Governance document** - LOCKED calculations and change control |
| `BACKEND_SCHEMA_UPDATES.md` | Google Sheets schema requirements |
| `GREENFIELD_INTEGRATION_GUIDE.md` | Complete deployment guide |
| `heuristic_optimizer.py` | Legacy multi-problem heuristic optimizers |
| `milp_model_dr.py` | MILP optimizer with demand response |
| `__init__.py` | Module exports |

## Governance

> [!IMPORTANT]
> The Greenfield Heuristic v2.1.1 includes **LOCKED calculations** that require explicit user approval to modify. See `GREENFIELD_HEURISTIC_RULES.md` for:
> - LOCKED formulas (NOx, gas, LCOE, firm capacity, N-1, ramp rates, land allocation)
> - Backend sync requirements (all values from Google Sheets)
> - Change control procedures for AI assistants
> - Validation requirements before deployment

## Backend Requirements

### Google Sheets Schema

The optimizer requires specific columns in the backend spreadsheet:

**Equipment Tab - 4 New Columns:**
- `lead_time_months` - Equipment deployment timeline
- `ramp_rate_pct_per_min` - Ramp capability (% capacity/min)
- `time_to_full_load_min` - Startup time to 100%
- `land_acres_per_mw` - Land footprint per MW

**Global_Parameters Tab - 12 New Rows:**
- Land parameters (datacenter_mw_per_acre, thresholds, etc.)
- BESS capacity credit (25% default)
- VOLL penalty ($50,000/MWh default)
- Equipment lead times (recip, turbine, BESS, solar, grid)

**Sites Tab - 3 New Columns:**
- `grid_available_year` - Year grid becomes available
- `grid_capacity_mw` - Grid interconnection capacity
- `grid_lead_time_months` - Site-specific override

**Load_Profiles Tab - Workload Mix Columns:**
- `flexibility_pct`, `pre_training_pct`, `fine_tuning_pct`, etc.

> [!NOTE]
> **Fallback Behavior:** If backend is unavailable, the optimizer uses hardcoded defaults and logs warnings. This is acceptable for development/testing but **NOT for production**.

See `BACKEND_SCHEMA_UPDATES.md` for complete details.

## Backward Compatibility

The `GreenFieldHeuristic` import now points to `GreenfieldHeuristicV2`:

```python
from app.optimization import GreenFieldHeuristic  # Points to v2.1.1

# To use legacy implementation explicitly:
from app.optimization import GreenFieldHeuristic_Legacy
```

This ensures existing code continues to work while benefiting from v2.1.1 improvements.

## Testing

### Standalone Validation

```bash
python app/optimization/greenfield_heuristic_v2.py
```

Expected output:
- Feasible solution (depending on constraints)
- LCOE: $60-150/MWh (typical range)
- Load coverage: >95% (for unconstrained scenarios)

### Integration Testing

```python
import pytest
from app.optimization import GreenfieldHeuristicV2

def test_greenfield_optimizer():
    site = {'name': 'Test Site'}
    load_trajectory = {2028: 100, 2029: 200}
    constraints = {'nox_tpy_annual': 100, 'gas_supply_mcf_day': 50000, 'land_area_acres': 500}
    
    optimizer = GreenfieldHeuristicV2(site=site, load_trajectory=load_trajectory, constraints=constraints)
    result = optimizer.optimize()
    
    assert result.lcoe > 0
    assert 30 <= result.lcoe <= 300  # Sanity check
    assert result.load_coverage_pct >= 0
```

## Rollback Procedures

### Quick Rollback (Import Change)

Modify `__init__.py`:

```python
# ROLLBACK: Use legacy implementation
from .heuristic_optimizer import GreenFieldHeuristic
# GreenFieldHeuristic = GreenfieldHeuristicV2  # COMMENT OUT
```

### Full Rollback (File Restore)

```bash
# Restore from archive
cp app/optimization/archive/heuristic_optimizer_v1_*.py \
   app/optimization/heuristic_optimizer.py
```

Backend changes are additive and don't require rollback.

## Dependencies

- Python 3.9+
- numpy
- pandas
- gspread (for backend integration)

Install gspread:
```bash
pip install gspread
```

## Support

- **Owner:** Doug Mackenzie
- **Project:** bvNexus / Energy Optimizer
- **Governance:** See `GREENFIELD_HEURISTIC_RULES.md`
- **Integration Guide:** See `GREENFIELD_INTEGRATION_GUIDE.md`

## Version History

| Version | Date | Key Changes | Contributor |
|---------|------|-------------|-------------|
| 2.1.1 | Dec 2025 | OPEX fix, solar profile, constraint checking, economic dispatch | Claude |
| 2.1.0 | Dec 2025 | gspread, dynamic ramp, BESS charging, grid CAPEX | Gemini |
| 2.0.0 | Dec 2025 | Initial corrected version with locked calculations | Claude |
| 1.x | 2024 | Legacy multi-problem heuristics | Original Team |
