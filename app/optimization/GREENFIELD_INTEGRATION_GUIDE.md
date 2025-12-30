# GREENFIELD_INTEGRATION_GUIDE.md

## Complete Deployment Guide for Greenfield Heuristic v2.1.1

**Version:** 2.1.1  
**Date:** December 2025  
**Status:** PRODUCTION READY

---

## 1. Overview

This guide covers the complete deployment of Greenfield Heuristic Optimizer v2.1.1 into the bvNexus application. It includes:

- Archive procedure for old files
- File placement instructions
- Backend schema updates
- Testing procedures
- UI integration
- Rollback instructions

---

## 2. Version History

| Version | Key Changes | Contributor |
|---------|-------------|-------------|
| 2.0.0 | Initial corrected version with locked calculations | Claude |
| 2.1.0 | Added gspread, dynamic ramp, BESS charging | Gemini |
| 2.1.1 | OPEX fix, solar profile, constraint checking, economic dispatch | Claude |

### 2.1.1 Changelog Summary

**From Gemini (v2.1.0):**
- ✅ gspread integration for Google Sheets connectivity
- ✅ Dynamic ramp calculation based on workload mix
- ✅ BESS reliability charging (from excess thermal/grid)
- ✅ Grid CAPEX added to total capital cost
- ✅ Fuel annual calculation fixed (divide by active years)

**From Claude (v2.1.1 patches):**
- ✅ OPEX bug fixed (was using missing `recip_mw` key)
- ✅ Added `recip_mw`/`turbine_mw` storage in equipment config
- ✅ Solar profile generation restored
- ✅ Constraint checking logic restored
- ✅ Economic dispatch (compare grid vs thermal cost)

---

## 3. Pre-Deployment Checklist

Before deploying, verify:

- [ ] Python 3.9+ installed
- [ ] Required packages: `numpy`, `pandas`, `gspread`
- [ ] Google Sheets backend accessible
- [ ] Service account credentials available (for gspread)
- [ ] Backup of existing optimization files created

---

## 4. Archive Procedure

### 4.1 Create Archive Directory

```bash
# Navigate to optimization directory
cd bvnexus_rebuild/app/optimization/

# Create archive folder if not exists
mkdir -p archive
```

### 4.2 Archive Old Files

```bash
# Archive existing files with date suffix
cp heuristic_optimizer.py archive/heuristic_optimizer_v1_DEPRECATED_2024-12.py
cp phased_optimizer.py archive/phased_optimizer_v1_DEPRECATED_2024-12.py

# If v2.0 exists
cp greenfield_heuristic_v2.py archive/greenfield_heuristic_v2.0_2024-12.py 2>/dev/null || true
```

### 4.3 Add Deprecation Headers

Add this header to archived files:

```python
"""
╔══════════════════════════════════════════════════════════════════╗
║  DEPRECATED - DO NOT USE                                         ║
║  This file has been superseded by greenfield_heuristic_v2.py     ║
║  Archive Date: December 2024                                     ║
║  Reason: Incorrect calculations identified during QA/QC review   ║
╚══════════════════════════════════════════════════════════════════╝
"""
```

---

## 5. File Placement

### 5.1 Directory Structure

After deployment:

```
bvnexus_rebuild/
└── app/
    └── optimization/
        ├── archive/
        │   ├── heuristic_optimizer_v1_DEPRECATED_2024-12.py
        │   ├── phased_optimizer_v1_DEPRECATED_2024-12.py
        │   └── greenfield_heuristic_v2.0_2024-12.py
        ├── greenfield_heuristic_v2.py          # ← NEW (main optimizer)
        ├── GREENFIELD_HEURISTIC_RULES.md       # ← NEW (governance)
        ├── BACKEND_SCHEMA_UPDATES.md           # ← NEW (schema guide)
        ├── __init__.py                         # ← UPDATE
        └── README.md                           # ← UPDATE
```

### 5.2 Copy New Files

```bash
# Copy new optimizer file
cp greenfield_heuristic_v2_FINAL.py bvnexus_rebuild/app/optimization/greenfield_heuristic_v2.py

# Copy governance document
cp GREENFIELD_HEURISTIC_RULES_FINAL.md bvnexus_rebuild/app/optimization/GREENFIELD_HEURISTIC_RULES.md

# Copy schema guide
cp BACKEND_SCHEMA_UPDATES.md bvnexus_rebuild/app/optimization/BACKEND_SCHEMA_UPDATES.md
```

### 5.3 Update __init__.py

Replace the optimization module's `__init__.py`:

```python
"""
bvNexus Optimization Module
===========================
Version: 2.1.1
Date: December 2025

This module provides optimization capabilities for datacenter power systems.
Primary optimizer: GreenfieldHeuristicV2

GOVERNANCE: See GREENFIELD_HEURISTIC_RULES.md for modification guidelines.
"""

# Primary optimizer (v2.1.1)
from .greenfield_heuristic_v2 import (
    GreenfieldHeuristicV2,
    HeuristicResultV2,
    ConstraintResult,
    DispatchResult,
    BackendDataLoader,
    # Locked calculation functions
    calculate_nox_annual_tpy,
    calculate_gas_consumption_mcf_day,
    calculate_capital_recovery_factor,
    calculate_lcoe,
    calculate_firm_capacity,
    calculate_ramp_capacity,
)

# Backward compatibility alias
GreenFieldHeuristic = GreenfieldHeuristicV2
HeuristicResult = HeuristicResultV2

__all__ = [
    'GreenfieldHeuristicV2',
    'GreenFieldHeuristic',  # Deprecated alias
    'HeuristicResultV2',
    'HeuristicResult',      # Deprecated alias
    'ConstraintResult',
    'DispatchResult',
    'BackendDataLoader',
    'calculate_nox_annual_tpy',
    'calculate_gas_consumption_mcf_day',
    'calculate_capital_recovery_factor',
    'calculate_lcoe',
    'calculate_firm_capacity',
    'calculate_ramp_capacity',
]

__version__ = '2.1.1'
```

---

## 6. Backend Setup

### 6.1 Google Sheets Configuration

1. **Create Service Account:**
   - Go to Google Cloud Console → IAM & Admin → Service Accounts
   - Create new service account
   - Download JSON credentials
   - Save as `credentials.json` in secure location

2. **Share Spreadsheet:**
   - Open your bvNexus backend spreadsheet
   - Click "Share" → Add service account email
   - Grant "Editor" access

3. **Update Schema:**
   - Follow `BACKEND_SCHEMA_UPDATES.md` to add required columns
   - Verify all equipment has lead times and ramp rates
   - Add new Global_Parameters rows

### 6.2 gspread Installation

```bash
pip install gspread --break-system-packages
```

### 6.3 Connection Test

```python
import gspread

# Test connection
gc = gspread.service_account(filename='path/to/credentials.json')
sheet = gc.open_by_key('YOUR_SPREADSHEET_ID')

# Verify tabs exist
print("Tabs found:", [ws.title for ws in sheet.worksheets()])
# Should show: Equipment, Global_Parameters, Sites, Load_Profiles
```

---

## 7. Testing Procedures

### 7.1 Unit Test (Standalone)

```bash
# Run standalone validation
python greenfield_heuristic_v2.py
```

Expected output:
```
======================================================================
Greenfield Heuristic v2.1.1 - Validation Test
======================================================================

Running optimization...

==============================RESULTS==============================
Feasible: True
LCOE: $XX.XX/MWh
Objective (w/VOLL): $XX.XX/MWh
Load Coverage: XX.X%
Analysis Period: 15 years
...
```

### 7.2 Integration Test (With Backend)

```python
import gspread
from optimization import GreenfieldHeuristicV2

# Connect to backend
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_ID = 'your_spreadsheet_id'

# Test configuration
site = {'name': 'Test Site', 'location': 'Dallas, TX'}
load_trajectory = {2028: 200, 2029: 400, 2030: 600, 2031: 750}
constraints = {
    'nox_tpy_annual': 100,
    'gas_supply_mcf_day': 100000,
    'land_area_acres': 500,
    'grid_available_year': 2030,
    'grid_capacity_mw': 500,
}
load_profile_data = {
    'flexibility_pct': 30.6,
    'workload_mix': {
        'pre_training': 45.0,
        'fine_tuning': 20.0,
        'batch_inference': 15.0,
        'real_time_inference': 20.0,
    }
}

# Run optimizer with backend
optimizer = GreenfieldHeuristicV2(
    site=site,
    load_trajectory=load_trajectory,
    constraints=constraints,
    sheets_client=gc,
    spreadsheet_id=SPREADSHEET_ID,
    load_profile_data=load_profile_data,
)

result = optimizer.optimize()

# Validate results
assert result.feasible, "Optimization should be feasible"
assert 50 <= result.lcoe <= 200, f"LCOE out of range: {result.lcoe}"
assert result.load_coverage_pct >= 95, f"Coverage too low: {result.load_coverage_pct}"
print("✅ Integration test passed!")
```

### 7.3 Validation Checklist

| Check | Expected | Status |
|-------|----------|--------|
| LCOE range | $60-150/MWh | ☐ |
| Load coverage | >95% | ☐ |
| Analysis period | 15 years | ☐ |
| NOx constraint | Checked | ☐ |
| Gas constraint | Checked | ☐ |
| Land constraint | Checked | ☐ |
| Ramp analysis | Populated | ☐ |
| Equipment by year | Populated | ☐ |
| Dispatch by year | Populated | ☐ |
| OPEX > 0 | Yes | ☐ |
| Solar profile | Non-zero (if solar_mw > 0) | ☐ |

---

## 8. UI Integration

### 8.1 Results Display Updates

Update the results page to show new fields:

```python
# In results_page.py or similar

def display_results(result: HeuristicResultV2):
    st.header("Optimization Results")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("LCOE", f"${result.lcoe:.2f}/MWh")
    col2.metric("Load Coverage", f"{result.load_coverage_pct:.1f}%")
    col3.metric("CAPEX", f"${result.capex_total/1e6:.1f}M")
    col4.metric("Timeline", f"{result.timeline_months} months")
    
    # Equipment configuration
    st.subheader("Equipment Configuration")
    cfg = result.equipment_config
    st.write(f"- Recips: {cfg.get('n_recips', 0)} units ({cfg.get('recip_mw', 0):.1f} MW)")
    st.write(f"- Turbines: {cfg.get('n_turbines', 0)} units ({cfg.get('turbine_mw', 0):.1f} MW)")
    st.write(f"- Solar: {cfg.get('solar_mw', 0):.1f} MW")
    st.write(f"- BESS: {cfg.get('bess_mw', 0):.1f} MW / {cfg.get('bess_mwh', 0):.1f} MWh")
    st.write(f"- Grid: {cfg.get('grid_mw', 0):.1f} MW")
    
    # NEW: Land allocation
    st.subheader("Land Allocation")
    land = result.land_allocation
    land_df = pd.DataFrame([
        {"Category": k.replace('_', ' ').title(), "Acres": v}
        for k, v in land.items()
    ])
    st.dataframe(land_df)
    
    # NEW: Ramp analysis
    st.subheader("Ramp Analysis")
    ramp = result.ramp_analysis
    st.write(f"- Required: {ramp.get('ramp_required_mw_min', 0):.1f} MW/min")
    st.write(f"- Capacity: {ramp.get('ramp_capacity_mw_min', 0):.1f} MW/min")
    st.write(f"- Margin: {ramp.get('ramp_margin_mw_min', 0):.1f} MW/min")
    
    # Constraints
    st.subheader("Constraint Status")
    for c in result.constraint_results:
        icon = "🟢" if c.status == "SLACK" else "🟡" if c.status == "NEAR_BINDING" else "🔴"
        st.write(f"{icon} {c.name}: {c.value:.1f}/{c.limit:.1f} {c.unit} [{c.status}]")
    
    # Warnings
    if result.warnings:
        st.warning("⚠️ Warnings:")
        for w in result.warnings:
            st.write(f"  - {w}")
    
    # Violations
    if result.violations:
        st.error("❌ Violations:")
        for v in result.violations:
            st.write(f"  - {v}")
```

### 8.2 Equipment By Year Chart

```python
def plot_equipment_by_year(equipment_by_year: Dict):
    """Plot equipment capacity by year."""
    years = sorted(equipment_by_year.keys())
    
    data = {
        'Year': years,
        'Recip (MW)': [equipment_by_year[y].get('recip_mw', 0) for y in years],
        'Turbine (MW)': [equipment_by_year[y].get('turbine_mw', 0) for y in years],
        'Solar (MW)': [equipment_by_year[y].get('solar_mw', 0) for y in years],
        'BESS (MW)': [equipment_by_year[y].get('bess_mw', 0) for y in years],
        'Grid (MW)': [equipment_by_year[y].get('grid_mw', 0) for y in years],
    }
    
    df = pd.DataFrame(data)
    df_melted = df.melt(id_vars='Year', var_name='Equipment', value_name='Capacity (MW)')
    
    fig = px.bar(df_melted, x='Year', y='Capacity (MW)', color='Equipment',
                 title='Equipment Deployment by Year',
                 barmode='stack')
    
    return fig
```

### 8.3 Grid Configuration Section

Add to site configuration page:

```python
st.subheader("Grid Configuration")

grid_available = st.checkbox("Grid Interconnection Available?", value=True)

if grid_available:
    col1, col2 = st.columns(2)
    with col1:
        grid_year = st.number_input("Grid Available Year", 
                                    min_value=2025, max_value=2040,
                                    value=2030)
    with col2:
        grid_capacity = st.number_input("Grid Capacity (MW)",
                                       min_value=0, max_value=2000,
                                       value=500)
    
    grid_lead_time = st.number_input("Grid Lead Time (months)",
                                     min_value=12, max_value=120,
                                     value=60,
                                     help="Default 60 months for large load interconnections")
else:
    grid_year = None
    grid_capacity = 0
    grid_lead_time = 60
```

---

## 9. Rollback Procedures

### 9.1 Quick Rollback (Import Change)

If issues found, quickly rollback by modifying `__init__.py`:

```python
# ROLLBACK: Uncomment to use archived v2.0
# from .archive.greenfield_heuristic_v2_0_2024_12 import (
#     GreenfieldHeuristicV2,
#     ...
# )

# CURRENT: v2.1.1
from .greenfield_heuristic_v2 import (
    GreenfieldHeuristicV2,
    ...
)
```

### 9.2 Full Rollback (File Restore)

```bash
# Restore archived files
cp archive/greenfield_heuristic_v2.0_2024-12.py greenfield_heuristic_v2.py

# Restart application
# Backend changes are additive - no rollback needed
```

### 9.3 Rollback Verification

After rollback, verify:
- [ ] Application starts without errors
- [ ] Test optimization runs
- [ ] Results display correctly

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Column not found" warning | Backend missing new columns | Add columns per BACKEND_SCHEMA_UPDATES.md |
| LCOE too high (>$200) | Analysis period wrong or costs wrong | Verify `analysis_period_years = 15` |
| LCOE too low (<$30) | Energy calculation issue | Check dispatch results |
| Solar always 0 | Expected if land < 800 acres | Increase land or lower threshold |
| OPEX = 0 | Old bug (fixed in v2.1.1) | Ensure using latest version |
| Grid doesn't appear | Year not reached or capacity=0 | Check `grid_available_year` and `grid_capacity_mw` |
| Ramp deficit | Insufficient fast-response equipment | Add BESS or recips |
| gspread auth error | Credentials issue | Verify service account setup |

### 10.2 Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run optimizer
result = optimizer.optimize()
```

### 10.3 Manual Calculation Check

Verify NOx calculation manually:

```python
# Example: 100 MW recip at 85% CF for 1 year
generation_mwh = 100 * 8760 * 0.85  # 744,600 MWh
heat_rate = 8500  # BTU/kWh
nox_rate = 0.15  # lb/MMBtu

mmbtu = generation_mwh * heat_rate / 1000  # 6,329,100 MMBtu
nox_lb = mmbtu * nox_rate  # 949,365 lb
nox_tpy = nox_lb / 2000  # 474.7 tpy

print(f"Expected NOx: {nox_tpy:.1f} tpy")
```

---

## 11. Post-Deployment Verification

### 11.1 Smoke Test (Production)

After deploying to production:

1. Run optimization with default test case
2. Verify LCOE in expected range ($60-150)
3. Verify constraint checking works
4. Verify results display correctly
5. Save successful run for regression testing

### 11.2 Performance Baseline

Record baseline metrics:

| Metric | Expected | Actual |
|--------|----------|--------|
| Solve time (100 MW) | < 5 sec | |
| Solve time (500 MW) | < 15 sec | |
| Solve time (1 GW) | < 30 sec | |
| Memory usage | < 2 GB | |

### 11.3 Sign-Off Checklist

- [ ] Unit tests pass
- [ ] Integration tests pass with backend
- [ ] UI displays results correctly
- [ ] No console errors or warnings
- [ ] Performance acceptable
- [ ] Documentation updated
- [ ] Team notified of deployment

---

## 12. Support

For issues or questions:

- **Technical Owner:** Doug Mackenzie
- **Project:** bvNexus
- **Organization:** Black & Veatch
- **Governance:** See GREENFIELD_HEURISTIC_RULES.md

---

## Appendix A: Quick Reference

### File Locations

| File | Purpose | Location |
|------|---------|----------|
| Main optimizer | Production code | `app/optimization/greenfield_heuristic_v2.py` |
| Governance doc | Rules for changes | `app/optimization/GREENFIELD_HEURISTIC_RULES.md` |
| Schema guide | Backend setup | `app/optimization/BACKEND_SCHEMA_UPDATES.md` |
| This guide | Deployment | `app/optimization/GREENFIELD_INTEGRATION_GUIDE.md` |

### Key Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| Discount rate | 8% | Global_Parameters |
| Analysis period | 15 years | Global_Parameters |
| BESS capacity credit | 25% | Global_Parameters |
| VOLL penalty | $50,000/MWh | Global_Parameters |
| Solar threshold | 800 acres | Global_Parameters |
| Recip lead time | 24 months | Equipment / Global_Parameters |
| GT lead time | 30 months | Equipment / Global_Parameters |
| Grid lead time | 60 months | Site-specific / Global_Parameters |

### Import Statement

```python
from optimization import GreenfieldHeuristicV2, HeuristicResultV2
```
