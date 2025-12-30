# GREENFIELD_HEURISTIC_RULES.md

## Governance Document for greenfield_heuristic_v2.py

**Version:** 2.1.1  
**Effective Date:** December 2025  
**Owner:** Doug Mackenzie  
**Status:** ACTIVE

---

## 1. Purpose

This document governs modifications to `greenfield_heuristic_v2.py` and establishes:

- **LOCKED** calculations that require user approval to modify
- **Backend sync requirements** - all variable values from Google Sheets via gspread
- **Change control procedures** for AI assistants (Antigravity, Claude, etc.)
- **Validation requirements** before deployment

---

## 2. Backend Sync Requirements

### 2.1 Data Sources

**ALL configurable values must be loaded from Google Sheets backend using gspread:**

| Tab | Purpose | Required |
|-----|---------|----------|
| `Equipment` | Equipment specifications (capacity, cost, ramp rates, lead times) | YES |
| `Global_Parameters` | Economic and constraint defaults | YES |
| `Sites` | Site-specific configurations | YES |
| `Load_Profiles` | 8760 load data with flexibility % and workload mix | YES |

### 2.2 gspread Integration

```python
# Required connection pattern
import gspread

# Initialize client (service account or OAuth)
gc = gspread.service_account(filename='credentials.json')

# Pass to optimizer
optimizer = GreenfieldHeuristicV2(
    site=site,
    load_trajectory=load_trajectory,
    constraints=constraints,
    sheets_client=gc,
    spreadsheet_id='YOUR_SPREADSHEET_ID',
)
```

### 2.3 Fallback Behavior

If backend is unavailable:
1. Log warning to console
2. Use hardcoded defaults from `BackendDataLoader.EQUIPMENT_DEFAULTS`
3. Continue optimization with warning in results

**CRITICAL:** Hardcoded defaults are ONLY for fallback. Production must sync with backend.

---

## 3. Locked Calculations

The following calculations are **LOCKED** and require explicit user approval before modification.

### 3.1 NOx Emissions (lb/MMBtu basis)

**Formula:**
```
NOx_tpy = (generation_MWh × heat_rate_BTU/kWh × nox_rate_lb/MMBtu) / 1,000,000 / 2000
```

**Implementation:**
```python
def calculate_nox_annual_tpy(generation_mwh, heat_rate_btu_kwh, nox_rate_lb_mmbtu):
    mmbtu = generation_mwh * heat_rate_btu_kwh / 1000
    nox_lb = mmbtu * nox_rate_lb_mmbtu
    nox_tpy = nox_lb / 2000
    return nox_tpy
```

**Constraint Type:** HARD (0% tolerance)

---

### 3.2 Gas Consumption

**Formula:**
```
Gas_MCF/day = (Annual_MWh × gas_consumption_MCF/MWh) / 365
```

**Source:** Uses `gas_consumption_mcf_mwh` directly from Equipment tab (NOT derived from heat rate).

**Constraint Type:** SOFT (10% tolerance)

---

### 3.3 LCOE Calculation (15-Year Analysis)

**Formula:**
```
CRF = r(1+r)^n / ((1+r)^n - 1)
LCOE = (CAPEX × CRF + OPEX_annual + Fuel_annual) / Energy_delivered_annual
```

**Parameters:**
- `r` = discount_rate (default 0.08)
- `n` = analysis_period_years (default 15)

**CRITICAL:** LCOE is CLEAN (no VOLL penalty). VOLL is added to objective separately.

---

### 3.4 Firm Capacity (BTM Only)

**Formula:**
```
Firm_capacity_MW = Thermal_MW + (BESS_MW × capacity_credit_pct)
```

**Notes:**
- Solar is NOT firm (intermittent)
- Grid is NOT included in BTM firm capacity
- Default `bess_capacity_credit_pct` = 0.25 (25%)

---

### 3.5 N-1 Redundancy (BTM Only)

**Formula:**
```
N1_capacity = Firm_BTM_capacity - Largest_single_unit
```

**Notes:**
- Grid does NOT count toward N-1 (it's not behind-the-meter)
- Largest unit determined from recip vs turbine unit sizes

---

### 3.6 Ramp Rate Calculation

**Formula:**
```
Ramp_capacity_MW/min = Σ(capacity_MW × ramp_rate_pct_per_min / 100)
```

**Equipment Ramp Rates (from backend):**
| Equipment | Ramp Rate | Time to Full Load |
|-----------|-----------|-------------------|
| Recip Engine | 100%/min | < 5 min |
| Aero Turbine | 50%/min | 8-10 min |
| Frame Turbine | 17.5%/min | 20-30 min |
| BESS | 100%+/min | Instantaneous |
| Grid | 100%/min | Instantaneous |

---

### 3.7 Dynamic Ramp Requirement (NEW in v2.1.1)

**Formula:**
```
Ramp_required_MW/min = Σ(load_MW × workload_pct × ramp_factor)
```

**Ramp Factors by Workload Type:**
| Workload | Ramp Factor | Rationale |
|----------|-------------|-----------|
| Pre-training | 0.00 | Stable, days-long jobs |
| Fine-tuning | 0.05 | Moderate cycling |
| Batch Inference | 0.00 | Deferrable/queued |
| Real-time Inference | 0.50 | High volatility, SLA protected |
| RL Training | 0.10 | Moderate |
| Cloud HPC | 0.02 | Batch-like |
| Cooling | 0.02 | Thermal inertia |

---

### 3.8 Land Allocation Priority

**Order (LOCKED):**
1. Datacenter footprint = peak_MW / datacenter_mw_per_acre (3.0)
2. Substation = 10 acres (fixed)
3. Infrastructure = 10% of total land
4. Thermal equipment = thermal_MW × 0.5 acres/MW
5. BESS = bess_MW × 0.25 acres/MW
6. Solar = ONLY if remaining > 800 acre threshold

**CRITICAL:** Solar cannot consume land needed for thermal. Thermal is 10× more land-efficient.

---

### 3.9 Thermal Marginal Cost (NEW in v2.1.1)

**Formula:**
```
Marginal_cost_$/MWh = (heat_rate_BTU/kWh × 1000 / 1,037,000) × gas_price + var_om
```

**Purpose:** Enables economic dispatch (compare grid vs thermal cost).

---

## 4. Constraint Classification

### 4.1 HARD Constraints (0% Tolerance)

| Constraint | Default Limit | Source |
|------------|---------------|--------|
| NOx Annual | 100 tpy | Site-specific or permit |

**Behavior:** Optimization is INFEASIBLE if violated.

### 4.2 SOFT Constraints (10% Tolerance)

| Constraint | Default Limit | Source |
|------------|---------------|--------|
| Gas Supply | 50,000 MCF/day | Site-specific |
| Land Area | 500 acres | Site-specific |

**Behavior:** Results flagged as NEAR_BINDING or VIOLATED but optimization continues.

---

## 5. Hierarchical Objectives

**Priority Order (LOCKED):**

1. **Reliability** - VOLL penalty ($50,000/MWh unserved)
2. **NOx Compliance** - HARD constraint (0% tolerance)
3. **Gas/Land** - SOFT constraints (10% tolerance)
4. **Ramp Rate** - Size equipment to meet dynamic requirement
5. **Minimize LCOE** - Primary economic objective

**Objective Function:**
```
Objective = LCOE + (VOLL × Unserved_MWh / Energy_delivered_MWh)
```

---

## 6. Change Control Procedures

### 6.1 AI Assistant Protocol

When modifying this file, AI assistants (Antigravity, Claude, etc.) MUST follow:

```
1. IDENTIFY the calculation or logic to change
2. CHECK if it is LOCKED (Section 3 or 4)
3. IF LOCKED:
   a. STOP - do not modify
   b. INFORM user of required approval
   c. PROVIDE approval request template (Section 6.2)
   d. WAIT for explicit user approval
   e. DOCUMENT change with approval reference
4. IF NOT LOCKED:
   a. Proceed with modification
   b. Add code comment documenting change
   c. Update version number
```

### 6.2 Approval Request Template

When requesting approval to modify a LOCKED calculation:

```markdown
## Modification Request

**Calculation:** [Name from Section 3]
**Current Formula:** [Existing formula]
**Proposed Change:** [New formula or logic]
**Rationale:** [Why this change is needed]
**Impact:** [What results will change]

**Approval Required:** Yes/No
**User Response:** [To be filled by user]
```

### 6.3 Documentation Requirements

All approved changes MUST include:
- Date of change
- Approval reference (message ID or timestamp)
- Before/after comparison
- Test results showing impact

---

## 7. Validation Requirements

### 7.1 Pre-Deployment Checklist

Before deploying changes to production:

- [ ] Backend sync verified (gspread connection works)
- [ ] All LOCKED calculations unchanged OR have documented approval
- [ ] LCOE in expected range ($60-150/MWh for typical scenarios)
- [ ] Load coverage > 95% for unconstrained scenarios
- [ ] NOx emissions calculated correctly (verify with manual calculation)
- [ ] Gas consumption uses backend value (not derived)
- [ ] Analysis period = 15 years
- [ ] VOLL penalty separate from LCOE

### 7.2 Test Scenarios

Run these scenarios before deployment:

| Scenario | Expected LCOE Range | Key Constraint |
|----------|---------------------|----------------|
| 100 MW, no constraints | $70-90/MWh | None |
| 300 MW, 100 tpy NOx | $80-110/MWh | NOx binding |
| 500 MW, 500 acres | $85-120/MWh | Land near-binding |
| 750 MW, grid Year 3 | $90-130/MWh | Lead time |

---

## 8. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 2.0.0 | Dec 2025 | Initial release | Claude |
| 2.1.0 | Dec 2025 | Added gspread, dynamic ramp, BESS charging | Gemini |
| 2.1.1 | Dec 2025 | OPEX bug fix, solar profile, constraint checking, economic dispatch | Claude |

---

## 9. Appendix: Default Values

### 9.1 Equipment Defaults (Fallback Only)

```python
EQUIPMENT_DEFAULTS = {
    'recip_engine': {
        'capacity_mw': 10.0,
        'capex_per_mw': 1_800_000,
        'opex_annual_per_mw': 45_000,
        'heat_rate_btu_kwh': 8500,
        'nox_rate_lb_mmbtu': 0.15,
        'gas_consumption_mcf_mwh': 7.2,
        'lead_time_months': 24,
        'ramp_rate_pct_per_min': 100.0,
        'land_acres_per_mw': 0.5,
    },
    'gas_turbine': {
        'capacity_mw': 50.0,
        'capex_per_mw': 1_200_000,
        'opex_annual_per_mw': 35_000,
        'heat_rate_btu_kwh': 10500,
        'nox_rate_lb_mmbtu': 0.10,
        'gas_consumption_mcf_mwh': 8.5,
        'lead_time_months': 30,
        'ramp_rate_pct_per_min': 50.0,
        'land_acres_per_mw': 0.5,
    },
    'bess': {
        'capex_per_mwh': 350_000,
        'opex_annual_per_mw': 5_000,
        'efficiency': 0.90,
        'lead_time_months': 6,
        'ramp_rate_pct_per_min': 100.0,
        'land_acres_per_mw': 0.25,
    },
    'solar_pv': {
        'capex_per_mw': 1_000_000,
        'opex_annual_per_mw': 12_000,
        'lead_time_months': 12,
        'land_acres_per_mw': 5.0,
    },
    'grid': {
        'capex_per_mw': 500_000,
        'lead_time_months': 60,
        'ramp_rate_pct_per_min': 100.0,
    },
}
```

### 9.2 Global Parameter Defaults (Fallback Only)

```python
GLOBAL_PARAM_DEFAULTS = {
    'discount_rate': 0.08,
    'analysis_period_years': 15,
    'electricity_price': 80.0,
    'gas_price': 5.0,
    'datacenter_mw_per_acre': 3.0,
    'solar_land_threshold_acres': 800.0,
    'bess_capacity_credit_pct': 0.25,
    'voll_penalty': 50_000,
    'recip_lead_time_months': 24,
    'gt_lead_time_months': 30,
    'bess_lead_time_months': 6,
    'solar_lead_time_months': 12,
    'default_grid_lead_time_months': 60,
}
```

---

## 10. Contact

For questions about this governance document:
- **Owner:** Doug Mackenzie
- **Project:** bvNexus
- **Organization:** Black & Veatch
