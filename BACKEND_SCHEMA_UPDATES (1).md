# BACKEND_SCHEMA_UPDATES.md

## Required Google Sheets Schema Additions for v2.1.1

**Version:** 2.1.1  
**Date:** December 2025  
**Status:** REQUIRED for production deployment

---

## 1. Overview

The Greenfield Heuristic v2.1.1 requires additional columns in the Google Sheets backend to support:

- **Lead time enforcement** - Equipment can only deploy after lead time elapsed
- **Ramp rate sizing** - Dynamic ramp calculation based on workload mix
- **Land allocation** - Priority-based land use with solar threshold
- **Economic dispatch** - Merit order comparing grid vs thermal costs

This document specifies the exact schema additions required.

---

## 2. Equipment Tab Additions

### 2.1 New Columns Required

Add these 4 columns to the **Equipment** tab:

| Column Name | Data Type | Unit | Description |
|-------------|-----------|------|-------------|
| `lead_time_months` | Integer | months | Months from order to commercial operation |
| `ramp_rate_pct_per_min` | Float | %/min | Ramp rate as % of capacity per minute |
| `time_to_full_load_min` | Float | min | Minutes to reach 100% output from cold start |
| `land_acres_per_mw` | Float | acres/MW | Land footprint per MW of capacity |

### 2.2 Values by Equipment Type

| equipment_id | lead_time_months | ramp_rate_pct_per_min | time_to_full_load_min | land_acres_per_mw |
|--------------|------------------|-----------------------|-----------------------|-------------------|
| recip_engine | 24 | 100.0 | 5.0 | 0.5 |
| gas_turbine | 30 | 50.0 | 10.0 | 0.5 |
| gas_turbine_aero | 30 | 50.0 | 10.0 | 0.5 |
| gas_turbine_frame | 36 | 17.5 | 25.0 | 0.5 |
| bess | 6 | 100.0 | 0.1 | 0.25 |
| solar_pv | 12 | - | - | 5.0 |
| grid | 60 | 100.0 | 0.0 | 0.1 |

### 2.3 Notes on Equipment Values

**Lead Times (per user specification):**
- Recip: 24 months (corrected from 12 months)
- Gas Turbine: 30 months (corrected from 18 months)
- BESS: 6 months (standard)
- Solar: 12 months (standard)
- Grid: 60 months default (site-specific override available)

**Ramp Rates (from uploaded research):**
- Recip: 100%/min - can reach full load in < 5 min
- Aero Turbine: 50%/min - reaches full load in 8-10 min
- Frame Turbine: 17.5%/min (midpoint of 10-25% range) - 20-30 min to full
- BESS: Instantaneous (modeled as 100%/min with 0.1 min startup)

---

## 3. Global_Parameters Tab Additions

### 3.1 New Parameters Required

Add these 12 rows to the **Global_Parameters** tab:

| parameter_name | value | unit | category | description |
|----------------|-------|------|----------|-------------|
| `datacenter_mw_per_acre` | 3.0 | MW/acre | land | MW of IT load per acre of datacenter footprint |
| `solar_land_threshold_acres` | 800 | acres | land | Minimum remaining land to enable solar |
| `thermal_land_per_mw` | 0.5 | acres/MW | land | Land required per MW of thermal generation |
| `solar_land_per_mw` | 5.0 | acres/MW | land | Land required per MW of solar PV |
| `bess_land_per_mw` | 0.25 | acres/MW | land | Land required per MW of BESS |
| `bess_capacity_credit_pct` | 0.25 | decimal | capacity | BESS contribution to firm capacity (25%) |
| `voll_penalty` | 50000 | $/MWh | reliability | Value of Lost Load penalty |
| `recip_lead_time_months` | 24 | months | lead_time | Reciprocating engine lead time |
| `gt_lead_time_months` | 30 | months | lead_time | Gas turbine lead time |
| `bess_lead_time_months` | 6 | months | lead_time | BESS lead time |
| `solar_lead_time_months` | 12 | months | lead_time | Solar PV lead time |
| `default_grid_lead_time_months` | 60 | months | lead_time | Default grid interconnection lead time |

### 3.2 Existing Parameters (Verify Present)

Ensure these existing parameters are present:

| parameter_name | value | unit | category |
|----------------|-------|------|----------|
| `discount_rate` | 0.08 | decimal | economic |
| `analysis_period_years` | 15 | years | economic |
| `electricity_price` | 80.0 | $/MWh | economic |
| `gas_price` | 5.0 | $/MCF | economic |
| `capacity_price` | 150.0 | $/kW-year | economic |
| `default_availability` | 0.95 | decimal | reliability |
| `n_minus_1_default` | TRUE | boolean | reliability |

---

## 4. Load_Profiles Tab Schema

### 4.1 Required Columns for Workload Mix

The optimizer now supports dynamic ramp calculation based on workload mix. Add these columns to Load_Profiles or create a separate Workload_Mix tab:

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `site_id` | String | Reference to Sites tab |
| `flexibility_pct` | Float | Overall load flexibility (default 30.6%) |
| `pre_training_pct` | Float | Pre-training workload % |
| `fine_tuning_pct` | Float | Fine-tuning workload % |
| `batch_inference_pct` | Float | Batch inference workload % |
| `real_time_inference_pct` | Float | Real-time inference workload % |
| `rl_training_pct` | Float | RL training workload % (optional) |
| `cloud_hpc_pct` | Float | Cloud HPC workload % (optional) |

### 4.2 Example Workload Mix Row

| site_id | flexibility_pct | pre_training_pct | fine_tuning_pct | batch_inference_pct | real_time_inference_pct |
|---------|-----------------|------------------|-----------------|---------------------|-------------------------|
| DALLAS_01 | 30.6 | 45.0 | 20.0 | 15.0 | 20.0 |

**Note:** Percentages should sum to 100%.

---

## 5. Sites Tab Schema Update

### 5.1 Grid Configuration Columns

Add these columns to support site-specific grid configuration:

| Column Name | Data Type | Unit | Description |
|-------------|-----------|------|-------------|
| `grid_available_year` | Integer | year | Year grid becomes available (e.g., 2030) |
| `grid_capacity_mw` | Float | MW | Available grid interconnection capacity |
| `grid_lead_time_months` | Integer | months | Site-specific grid lead time (overrides default) |

### 5.2 Example Sites Row

| site_id | name | location | land_area_acres | grid_available_year | grid_capacity_mw | grid_lead_time_months |
|---------|------|----------|-----------------|---------------------|------------------|-----------------------|
| DALLAS_01 | Dallas Brownfield | Dallas, TX | 500 | 2030 | 500 | 60 |

---

## 6. Implementation Instructions

### 6.1 Step-by-Step Schema Update

1. **Backup existing spreadsheet** before making changes

2. **Equipment Tab:**
   ```
   a. Add 4 new column headers (lead_time_months, ramp_rate_pct_per_min, 
      time_to_full_load_min, land_acres_per_mw)
   b. Populate values from Section 2.2 for each equipment type
   c. Verify no blank cells in new columns
   ```

3. **Global_Parameters Tab:**
   ```
   a. Add 12 new rows from Section 3.1
   b. Verify existing parameters from Section 3.2 are present
   c. Ensure value column has correct data types (numbers vs text)
   ```

4. **Load_Profiles Tab:**
   ```
   a. Add workload mix columns from Section 4.1
   b. Populate for each site
   c. Verify percentages sum to 100%
   ```

5. **Sites Tab:**
   ```
   a. Add grid configuration columns from Section 5.1
   b. Populate for each site
   c. Set grid_available_year to NULL if no grid planned
   ```

### 6.2 Validation Queries

After updating, run these checks:

```python
# Verify Equipment tab has required columns
required_equip_cols = ['lead_time_months', 'ramp_rate_pct_per_min', 
                       'time_to_full_load_min', 'land_acres_per_mw']
assert all(col in equipment_df.columns for col in required_equip_cols)

# Verify Global_Parameters has required rows
required_params = ['datacenter_mw_per_acre', 'solar_land_threshold_acres',
                   'bess_capacity_credit_pct', 'voll_penalty']
param_names = global_params_df['parameter_name'].tolist()
assert all(p in param_names for p in required_params)

# Verify workload mix sums to 100%
workload_cols = ['pre_training_pct', 'fine_tuning_pct', 
                 'batch_inference_pct', 'real_time_inference_pct']
for idx, row in load_profiles_df.iterrows():
    total = sum(row[col] for col in workload_cols if col in row)
    assert 99 <= total <= 101, f"Workload mix for {row['site_id']} sums to {total}%"
```

---

## 7. Fallback Behavior

If the optimizer cannot find new columns in the backend:

| Missing Column | Fallback Value | Warning Logged |
|----------------|----------------|----------------|
| `lead_time_months` | Use type-specific default | Yes |
| `ramp_rate_pct_per_min` | 100.0 | Yes |
| `time_to_full_load_min` | 5.0 | Yes |
| `land_acres_per_mw` | 0.5 | Yes |
| `datacenter_mw_per_acre` | 3.0 | Yes |
| `solar_land_threshold_acres` | 800.0 | Yes |
| `bess_capacity_credit_pct` | 0.25 | Yes |
| `voll_penalty` | 50000 | Yes |

**Important:** Fallback is acceptable for development/testing but NOT for production. All columns must be present in production.

---

## 8. Migration Notes

### 8.1 From v2.0 to v2.1.1

If upgrading from v2.0:

1. **New dependencies:**
   - `gspread` library required for backend connectivity
   - Install: `pip install gspread`

2. **Backend columns:**
   - All columns from Sections 2-5 are NEW
   - v2.0 did not have lead time, ramp rate, or land columns

3. **Code changes:**
   - `sheets_client` parameter added to optimizer constructor
   - `spreadsheet_id` parameter added to optimizer constructor
   - `load_profile_data` now expects `workload_mix` dict

### 8.2 Compatibility

- v2.1.1 is backward compatible with v2.0 if backend columns are missing (uses defaults)
- Production deployments MUST have all columns populated
- Testing can proceed with defaults while backend is updated

---

## 9. Sample Google Sheets Structure

### 9.1 Equipment Tab Layout

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| equipment_id | name | type | capacity_mw | capex_per_mw | opex_annual_per_mw | heat_rate_btu_kwh | nox_rate_lb_mmbtu | gas_consumption_mcf_mwh | efficiency | lifetime_years | **lead_time_months** | **ramp_rate_pct_per_min** | **time_to_full_load_min** | **land_acres_per_mw** |
| recip_engine | Recip Engine | thermal | 10 | 1800000 | 45000 | 8500 | 0.15 | 7.2 | 0.42 | 25 | **24** | **100** | **5** | **0.5** |
| gas_turbine | Gas Turbine | thermal | 50 | 1200000 | 35000 | 10500 | 0.10 | 8.5 | 0.35 | 25 | **30** | **50** | **10** | **0.5** |
| bess | BESS | storage | 1 | 250000 | 5000 | - | - | - | 0.90 | 15 | **6** | **100** | **0.1** | **0.25** |
| solar_pv | Solar PV | renewable | 1 | 1000000 | 12000 | - | - | - | 0.20 | 30 | **12** | **-** | **-** | **5** |
| grid | Grid | import | 1 | 500000 | 0 | - | - | - | 1.0 | 50 | **60** | **100** | **0** | **0.1** |

**Bold columns are NEW in v2.1.1**

### 9.2 Global_Parameters Tab Layout

| A | B | C | D | E |
|---|---|---|---|---|
| parameter_name | value | unit | category | description |
| discount_rate | 0.08 | decimal | economic | Discount rate for NPV calculations |
| analysis_period_years | 15 | years | economic | Project analysis period |
| electricity_price | 80 | $/MWh | economic | Grid electricity price |
| gas_price | 5 | $/MCF | economic | Natural gas price |
| **datacenter_mw_per_acre** | **3.0** | **MW/acre** | **land** | **MW per acre of DC footprint** |
| **solar_land_threshold_acres** | **800** | **acres** | **land** | **Min land for solar** |
| **thermal_land_per_mw** | **0.5** | **acres/MW** | **land** | **Thermal land use** |
| **solar_land_per_mw** | **5.0** | **acres/MW** | **land** | **Solar land use** |
| **bess_land_per_mw** | **0.25** | **acres/MW** | **land** | **BESS land use** |
| **bess_capacity_credit_pct** | **0.25** | **decimal** | **capacity** | **BESS firm capacity credit** |
| **voll_penalty** | **50000** | **$/MWh** | **reliability** | **Value of lost load** |
| **recip_lead_time_months** | **24** | **months** | **lead_time** | **Recip lead time** |
| **gt_lead_time_months** | **30** | **months** | **lead_time** | **GT lead time** |
| **bess_lead_time_months** | **6** | **months** | **lead_time** | **BESS lead time** |
| **solar_lead_time_months** | **12** | **months** | **lead_time** | **Solar lead time** |
| **default_grid_lead_time_months** | **60** | **months** | **lead_time** | **Grid lead time** |

**Bold rows are NEW in v2.1.1**

---

## 10. Contact

For questions about backend schema:
- **Owner:** Doug Mackenzie
- **Project:** bvNexus
- **Organization:** Black & Veatch
