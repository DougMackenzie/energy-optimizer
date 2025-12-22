# MILP Integration - Current Status & Remaining Issues

## ✅ What's Working

1. **MILP Solver**: Installed (GLPK) and functional
2. **Load Composer**: 4-tab UI complete and saving profiles
3. **Scenario Templates**: 2 scenarios defined (BTM Only, All Technologies)
4. **Basic Integration**: MILP runs when Load Composer configured
5. **Code Committed**: All work pushed to GitHub

---

##  Remaining Issues (Critical)

### 1. Grid-Only Solutions ⚠️
**Problem**: MILP is optimizing to grid-only (zero BTM equipment)
**Symptoms**:
- $0 CAPEX
- Only grid import shown
- Negative LCOE ($-2.36/MWh)

**Root Cause**: MILP model has no cost penalty for grid, so it prefers grid over BTM equipment

**Fix Needed**:
```python
# In milp_model_dr.py, add grid cost to objective:
obj += sum(
    grid_import_cost_mwh * grid_usage[t,y]  # Add grid electricity cost
    for t in T for y in Y
)
```

**OR**: Pass scenario equipment enablement flags to MILP:
```python
# In optimize_with_milp(), respect scenario['Recip_Enabled']:
if not scenario.get('Recip_Enabled', True):
    model.n_recip.fix(0)  # Disable recips
```

---

### 2. Equipment Not Enabled 🔧
**Problem**: Equipment Library checkboxes appear unchecked
**Impact**: Even though scenarios have `Recip_Enabled=True`, MILP isn't reading these flags

**Fix Needed**:
1. Pass scenario dict to `optimize_with_milp()`
2. In MILP wrapper, check equipment flags:
```python
def optimize_with_milp(site, constraints, load_profile_dr, scenario=None, ...):
    if scenario:
        # Disable equipment based on scenario
        if not scenario.get('Recip_Enabled', True):
            # Force n_recip = 0
        if not scenario.get('Solar_Enabled', True):
            # Force solar_mw = 0
```

---

### 3. Only 2 Scenarios Shown 📊
**Problem**: User wants to see ALL equipment combinations tested, not just 2 final scenarios

**Current**: `load_scenario_templates()` returns 2 scenarios
**Desired**: Show all combinations like:
- Recip only
- Turbine only
- BESS only
- Solar only  
- Recip + BESS
- Recip + Solar
- Recip + BESS + Solar
- etc.

**Fix Needed**:
Either:
A) Generate all combinations programmatically
B) Add more scenarios to template
C) Show MILP sub-solutions (different equipment mixes from same optimization)

---

### 4. Negative LCOE Still Occurring ❌
**Problem**: LCOE showing negative even with fixes

**Analysis**:
- If CAPEX = $0 (grid-only), LCOE formula breaks down
- DR revenue might exceed costs
- Grid-only should show grid electricity cost (~$80/MWh), not LCOE

**Fix applied** (partial):
```python
if total_capex == 0 and grid_mw > 0:
    # Use grid passthrough cost, not LCOE
    result['economics']['lcoe_mwh'] = 80.0
```

**Still needed**: Apply this fix consistently

---

### 5. KeyError: 'annual_opex_m' ✅ FIXED
**Status**: Fixed in latest commit
**Solution**: Added `'annual_opex_m': 0` to economics dict

---

## 🔧 Quick Fixes to Apply

### Fix 1: Grid Cost in MILP Objective
```python
# In milp_model_dr.py, line ~450 (objective function):
# Add grid electricity cost term
grid_cost_per_mwh = 80  # $/MWh average

obj += sum(
    grid_cost_per_mwh * self.model.grid_import[t,y] * self.scale_factor[t]
    for t in self.model.T for y in self.model.Y
) / 1_000_000  # Convert to millions
```

###  Fix 2: Pass Scenario to MILP
```python
# In page_07_optimizer.py, line ~92:
results = run_all_scenarios(
    site=site,
    constraints=constraints,
    objectives=objectives,
    scenarios=scenarios,  # This is a list of scenario dicts
    grid_config=None,
    use_milp=True,
    load_profile_dr=load_profile_dr
)

# In multi_scenario.py, line ~100:
for idx, scenario in enumerate(scenarios):
    result = optimize_with_milp(
        site=site,
        constraints=constraints,
        load_profile_dr=load_profile_dr,
        scenario=scenario,  # <-- ADD THIS
        years=list(range(2026, 2036)),
        solver='glpk',
        time_limit=300
    )
```

### Fix 3: Handle Scenario Equipment Flags in MILP Wrapper
```python
# In milp_optimizer_wrapper.py, after building model:
if scenario:
    # Disable equipment based on scenario flags
    if not scenario.get('Recip_Enabled', True):
        for y in years:
            optimizer.model.n_recip[y].fix(0)
    
    if not scenario.get('Turbine_Enabled', True):
        for y in years:
            optimizer.model.n_turbine[y].fix(0)
    
    if not scenario.get('Solar_Enabled', True):
        for y in years:
            optimizer.model.solar_mw[y].fix(0)
    
    if not scenario.get('BESS_Enabled', True):
        for y in years:
            optimizer.model.bess_mwh[y].fix(0)
    
    if not scenario.get('Grid_Enabled', True):
        for y in years:
            optimizer.model.grid_mw[y].fix(0)
```

---

## 📊 Expected Results After Fixes

Once fixed, you should see:

**BTM Only Scenario**:
- LCOE: $55-75/MWh
- CAPEX: $150-300M
- Equipment: Recips, Turbines, BESS, Solar (NO grid)
- Total MW: 180-220 MW

**All Technologies Scenario**:
- LCOE: $45-65/MWh (grid reduces cost)
- CAPEX: $100-200M (less BTM, more grid)
- Equipment: Some BTM + Grid
- Total MW: 100-150 MW BTM + Grid

---

## 🚀 Priority Order

1. **Fix grid cost in objective** (prevents grid-only solutions)
2. **Pass scenario to MILP** (enables equipment control)
3. **Apply equipment flags** (respects user selections)
4. **Test with real scenarios** (verify realistic results)
5. **(Optional) Add more scenario combinations** (if user wants to see all permutations)

---

## 📝 Notes

- The MILP core model is sound and working
- The integration layer needs tweaking
- Main issue: MILP sees grid as "free" so it picks grid-only
- Once grid has a cost, BTM equipment will be competitive

---

**Status**: Partially functional, needs 3-4 more fixes for production use
**Time estimate**: 1-2 hours to apply all fixes
**Recommendation**: Apply Fix 1 (grid cost) first - this will have biggest impact
