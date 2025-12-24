# bvNexus MILP Corrected Package

## Installation Instructions

**Drop-in replacement for the MILP optimization module.**

### Files Included

| File | Destination | Description |
|------|-------------|-------------|
| `milp_model_dr.py` | `app/optimization/milp_model_dr.py` | Core MILP model (REPLACE existing) |
| `milp_optimizer_wrapper.py` | `app/utils/milp_optimizer_wrapper.py` | Wrapper functions (REPLACE existing) |

### Quick Install

```bash
# From your energy-optimizer directory:
cp milp_model_dr.py app/optimization/milp_model_dr.py
cp milp_optimizer_wrapper.py app/utils/milp_optimizer_wrapper.py
```

---

## What's Fixed

### Critical Issues

| Issue | Before | After |
|-------|--------|-------|
| **Infeasible errors** | Model crashes when constraints limit equipment | Returns solution with power gap tracked |
| **Gas constraint** | DISABLED (commented out) | ENABLED - hard limit enforced |
| **CO2 constraint** | DISABLED | ENABLED (if limit > 0) |
| **Ramp constraint** | DISABLED | ENABLED |
| **Grid timing** | Could use grid before interconnection | Forced to 0 until available year |

### New Features

1. **Power Coverage Tracking**
   ```python
   result['power_coverage'] = {
       'coverage_pct': 85.2,      # % of load served
       'power_gap_mw': 24.5,      # Average unserved MW
       'is_fully_served': False,  # True if gap < 1%
   }
   ```

2. **Gas Usage Tracking**
   ```python
   result['gas_usage'] = {
       'avg_daily_mcf': 38500,
       'gas_utilization_pct': 96.3,  # % of limit used
   }
   ```

3. **Hierarchical Objective**
   - Primary: Maximize power (minimize unserved)
   - Secondary: Minimize cost
   - Implemented via $50,000/MWh penalty for unserved energy

---

## Expected Behavior

### Example: 100 tpy NOx, Grid in 2030

**Before Fix:**
```
ERROR: Model infeasible - cannot meet 200 MW load with 100 tpy NOx limit
```

**After Fix:**
```
Year 2026: 15 recips, 2 turbines | Coverage: 82% | NOx: 98 tpy (98% of limit)
Year 2027: 15 recips, 2 turbines | Coverage: 78% | NOx: 98 tpy
Year 2028: 15 recips, 2 turbines | Coverage: 74% | NOx: 99 tpy
Year 2029: 15 recips, 2 turbines | Coverage: 70% | NOx: 99 tpy
Year 2030: 15 recips, 2 turbines, 80 MW grid | Coverage: 100% | NOx: 65 tpy
```

The optimizer now:
1. Builds MAXIMUM equipment within NOx constraint
2. Reports the power gap explicitly
3. Fills gap with grid when it becomes available

---

## Constraint Reference

### Hard Constraints (Enforced)

| Constraint | Parameter Key | Default | Unit |
|------------|---------------|---------|------|
| NOx Emissions | `NOx_Limit_tpy` or `max_nox_tpy` | 99 | tpy |
| Gas Supply | `Gas_Supply_MCF_day` or `gas_supply_mcf_day` | 50,000 | MCF/day |
| CO2 Emissions | `CO2_Limit_tpy` or `co2_limit_tpy` | 0 (disabled) | tpy |
| Land Area | `Available_Land_Acres` or `land_area_acres` | 500 | acres |
| Ramp Rate | `min_ramp_rate_mw_min` | 10 | MW/min |
| RAM/N-1 | Automatic | Peak load | MW |

### Grid Configuration

| Parameter | Key | Default |
|-----------|-----|---------|
| Available Year | `grid_available_year` | 2030 |
| Interconnection CAPEX | `grid_interconnection_capex` | $5,000,000 |
| Lead Time | `Estimated_Interconnection_Months` | 96 months |

---

## API Reference

### Main Function

```python
from app.utils.milp_optimizer_wrapper import optimize_with_milp

result = optimize_with_milp(
    site={'name': 'My Site'},
    constraints={
        'NOx_Limit_tpy': 100,
        'Gas_Supply_MCF_day': 40000,
        'Available_Land_Acres': 500,
    },
    load_profile_dr={
        'peak_it_mw': 160,
        'pue': 1.25,
        'load_factor': 0.75,
        'workload_mix': {...},
    },
    years=list(range(2026, 2036)),
    scenario={'Scenario_Name': 'BTM Only', 'Grid_Enabled': False},
    solver='glpk',
)

# Check results
print(f"Feasible: {result['feasible']}")
print(f"LCOE: ${result['economics']['lcoe_mwh']:.2f}/MWh")
print(f"Coverage: {result['power_coverage']['final_coverage_pct']:.1f}%")
print(f"Power Gap: {result['power_coverage']['power_gap_mw']:.1f} MW")
```

### Multi-Scenario

```python
from app.utils.milp_optimizer_wrapper import run_milp_scenarios

results = run_milp_scenarios(
    site=site,
    constraints=constraints,
    load_profile_dr=load_profile_dr,
    scenarios=[
        {'Scenario_Name': 'All Tech', 'Grid_Enabled': True},
        {'Scenario_Name': 'BTM Only', 'Grid_Enabled': False},
    ],
)

# Results sorted by LCOE
for r in results:
    print(f"{r['scenario_name']}: ${r['economics']['lcoe_mwh']:.2f}/MWh")
```

---

## Technical Notes

### Unserved Penalty (Gemini Refinement)

The unserved energy penalty is set to **$50,000/MWh** (not $1M/MWh) to:
- Still be >> any real cost (~500x higher than LCOE)
- Avoid numerical instability in solvers
- Ensure power maximization takes priority

### Gas Constraint Formula

```
Annual MCF = Σ(generation_MWh × heat_rate_BTU/kWh × 1000) / 1,037,000 BTU/MCF
Daily MCF = Annual MCF / 365
```

**Note:** Heat rates should be on HHV (Higher Heating Value) basis. If your equipment specs use LHV, multiply heat rates by 1.11.

### Representative Periods

Uses 6 representative weeks (1008 hours) for tractability:
- Spring typical (10 weeks weight)
- Summer typical (8 weeks)
- Summer peak (4 weeks)
- Fall typical (10 weeks)
- Winter typical (12 weeks)
- Winter peak (8 weeks)

Scale factor of 8.69 (8760/1008) applied to all energy calculations.

---

## Troubleshooting

### "No solver found"

Install a MILP solver:
```bash
# Option 1: GLPK (easiest)
brew install glpk  # macOS
apt-get install glpk-utils  # Ubuntu

# Option 2: CBC (faster)
brew install coin-or-tools/coinor/cbc
```

### Very long solve times

1. Check if using representative periods: `use_representative_periods=True`
2. Reduce time limit: `time_limit=60`
3. Try CBC instead of GLPK (faster for large problems)

### Power gap even with no constraints binding

Check if:
1. Grid is available (check `grid_available_year`)
2. Land limit allows enough solar
3. Ramp rate constraint isn't limiting BESS

---

## Version History

- **2.0** (Dec 2024): Complete rewrite with all fixes
  - Gas/CO2/Ramp constraints enabled
  - Unserved energy tracking
  - Grid timing enforcement
  - Gemini penalty refinement ($50K)
  
- **1.0** (Nov 2024): Original implementation
  - Had disabled constraints
  - Returned infeasible for tight constraints
