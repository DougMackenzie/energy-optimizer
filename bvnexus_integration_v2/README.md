# bvNexus Integration Package v2

## Overview

This package provides complete integration between bvNexus optimization engine and external power systems validation tools:

- **ETAP** - Electrical transient analysis (load flow, short circuit, arc flash)
- **PSS/e** - Power system simulation (power flow, stability, dynamics)
- **Windchill RAM** - Reliability, Availability, Maintainability analysis

## Package Contents

```
bvnexus_integration_v2/
├── app/
│   └── pages_custom/
│       ├── page_integration_export.py   # Export Hub with visual previews
│       └── page_integration_import.py   # Import Hub with validation dashboard
├── sample_files/
│   ├── ETAP/
│   │   ├── ETAP_Equipment_Import.csv    # Equipment for DataX import
│   │   ├── ETAP_Scenarios.csv           # Study scenarios (N-1, N-2)
│   │   ├── ETAP_LoadFlow_Results_PASS.csv
│   │   ├── ETAP_LoadFlow_Results_FAIL.csv
│   │   └── ETAP_ShortCircuit_Results.csv
│   ├── PSSe/
│   │   ├── bvNexus_Network.raw          # PSS/e RAW format network model
│   │   ├── PSSe_Scenarios.csv           # Scenario definitions
│   │   └── PSSe_PowerFlow_Results.csv   # Sample results format
│   └── Windchill_RAM/
│       ├── RAM_Component_Data.csv       # Component MTBF/MTTR data
│       ├── RAM_RBD_Structure.csv        # Reliability block diagram
│       ├── RAM_FMEA_Template.csv        # Failure modes template
│       ├── RAM_Results_PASS.csv         # Passing availability results
│       └── RAM_Results_FAIL.csv         # Failing availability results
└── README.md                            # This file
```

## Installation

### 1. Copy Pages to Your Streamlit App

```bash
cp app/pages_custom/page_integration_export.py your_app/pages/
cp app/pages_custom/page_integration_import.py your_app/pages/
```

### 2. Add to Navigation

In your main app.py or navigation configuration:

```python
pages = {
    # ... existing pages ...
    "🔗 Integration Export": "pages/page_integration_export.py",
    "📥 Integration Import": "pages/page_integration_import.py",
}
```

### 3. Dependencies

Ensure these are in your requirements.txt:

```
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.21.0
openpyxl>=3.0.0
```

---

## Sample File Formats

### ETAP Equipment Import (CSV/Excel)

```csv
ID,Name,Type,Bus_ID,Rated_kV,Rated_MW,Rated_MVA,Rated_PF,Xd_pu,Xd_prime_pu,Xd_double_prime_pu,H_inertia_sec,Status
GEN_RECIP_01,Recip Engine 1,Synchronous Generator,BUS_100,13.8,18.3,21.5,0.85,1.80,0.25,0.18,1.5,Online
GEN_GT_01,Gas Turbine 1,Synchronous Generator,BUS_120,13.8,50.0,58.8,0.85,1.50,0.22,0.15,3.0,Online
```

**Key Columns:**
| Column | Description | Unit |
|--------|-------------|------|
| ID | Unique equipment identifier | - |
| Rated_kV | Nominal voltage | kV |
| Rated_MW | Active power rating | MW |
| Rated_MVA | Apparent power rating | MVA |
| Xd_pu | Synchronous reactance | per-unit |
| Xd_prime_pu | Transient reactance | per-unit |
| Xd_double_prime_pu | Subtransient reactance | per-unit |
| H_inertia_sec | Inertia constant | seconds |

### ETAP Scenarios (CSV)

```csv
Scenario_ID,Name,Type,Load_MW,Load_PF,Tripped_Equipment,Description
BASE_100,Base Case - 100% Load,Normal,200.0,0.95,,All equipment online
N1_RECIP_01,N-1: Recip 1 Trip,N-1 Contingency,200.0,0.95,GEN_RECIP_01,Single contingency
N2_GT_BOTH,N-2: Both GTs Trip,N-2 Contingency,200.0,0.95,"GEN_GT_01,GEN_GT_02",Double contingency
```

### ETAP Load Flow Results (Import Format)

```csv
Bus_ID,Bus_Name,Voltage_kV,Voltage_pu,Angle_deg,P_MW,Q_MVAR,Loading_pct
BUS_100,RECIP_1_BUS,13.80,1.012,2.3,18.3,9.8,72.5
BUS_200,MAIN_BUS,13.80,1.000,0.0,-200.0,-65.0,75.2
```

**Validation Criteria:**
| Parameter | Min | Max | Action if Violated |
|-----------|-----|-----|-------------------|
| Voltage_pu | 0.95 | 1.05 | Add reactive compensation |
| Loading_pct | 0 | 80 | Resize equipment |
| Loading_pct | 80 | 100 | Warning only |

### ETAP Short Circuit Results (Import Format)

```csv
Bus_ID,Bus_Name,Fault_Type,Isc_kA,X_R_Ratio,Breaker_Rating_kA,Duty_pct
BUS_200,MAIN_BUS,3-Phase,42.8,18.2,63.0,67.9
```

**Validation Criteria:**
| Parameter | Max | Action if Violated |
|-----------|-----|-------------------|
| Duty_pct | 100% | Upgrade breaker rating |
| X_R_Ratio | 25 | Consider DC offset |

---

### PSS/e RAW Format

The RAW file follows PSS/e v33/34/35 format with sections:

```
0,   100.00     / PSS/E-35    Header Line
Title Line 1
Title Line 2

/ BUS DATA
100,'RECIP_01',  13.800,1,   1,   1,   1,1.01000,   0.0000
0 / END OF BUS DATA

/ LOAD DATA
200,'1 ',1,   1,   1,   200.00,    66.00
0 / END OF LOAD DATA

/ GENERATOR DATA
100,'1 ',   18.30,    0.00,  10.75, -6.45,1.0100,     0,  21.53
0 / END OF GENERATOR DATA

/ BRANCH DATA
100,  200,'1 ', 0.00100, 0.01000, 0.00000,  100.0,  100.0,  100.0
0 / END OF BRANCH DATA

Q
```

**Section Format:**
| Section | Key Fields |
|---------|-----------|
| BUS | I, 'NAME', BASKV, IDE, AREA, ZONE, OWNER, VM, VA |
| LOAD | I, ID, STATUS, AREA, ZONE, PL, QL |
| GENERATOR | I, ID, PG, QG, QT, QB, VS, IREG, MBASE |
| BRANCH | I, J, CKT, R, X, B, RATEA, RATEB, RATEC |

### PSS/e Results (Import Format)

```csv
BUS,NAME,VM_PU,VA_DEG,P_GEN_MW,Q_GEN_MVAR,P_LOAD_MW,Q_LOAD_MVAR
100,RECIP_01,1.010,2.3,18.3,9.8,0.0,0.0
200,MAIN_BUS,1.000,0.0,0.0,0.0,200.0,66.0
```

---

### Windchill RAM Component Data

```csv
Component_ID,Component_Name,Component_Type,MTBF_Hours,MTTR_Hours,Failure_Rate_Per_Hour,Availability,Distribution,Weibull_Beta
GEN_RECIP_01,Recip Engine 1,RECIPROCATING_ENGINE,8760,24,1.14E-04,0.9973,Exponential,1.0
GEN_GT_01,Gas Turbine 1,GAS_TURBINE,17520,48,5.71E-05,0.9973,Weibull,1.5
```

**Key Parameters:**
| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| MTBF_Hours | Mean Time Between Failures | 8,760 - 175,200 |
| MTTR_Hours | Mean Time To Repair | 4 - 168 |
| Availability | A = MTBF / (MTBF + MTTR) | 0.997 - 0.9999 |
| Weibull_Beta | Shape parameter (1.0 = exponential) | 1.0 - 2.0 |

### Windchill RBD Structure

```csv
Block_ID,Block_Name,Block_Type,Components,K_Required,N_Total,Description
THERMAL_GEN,Thermal Generation,PARALLEL_K_OF_N,"GEN_RECIP_01,...,GEN_GT_02",9,10,N-1 redundancy
ELECTRICAL,Electrical Distribution,SERIES,"XFMR_MAIN,SWGR_MAIN",2,2,All required
SYSTEM,Complete System,SERIES,"THERMAL_GEN,ELECTRICAL",2,2,Top level
```

**Block Types:**
| Type | Description | Availability Calculation |
|------|-------------|-------------------------|
| SERIES | All must work | A_sys = A1 × A2 × ... × An |
| PARALLEL | Any can work | A_sys = 1 - (1-A1)(1-A2)...(1-An) |
| PARALLEL_K_OF_N | K of N must work | Binomial calculation |

### Windchill RAM Results (Import Format)

```csv
Block_ID,Block_Name,Availability,MTBF_Hours,MTTR_Hours,Annual_Downtime_Hours
THERMAL_GEN,Thermal Generation,0.99987,76923,10,1.14
ELECTRICAL,Electrical Distribution,0.99985,67308,10,1.31
SYSTEM,Complete System,0.99972,35714,10,2.45
```

**Validation Criteria:**
| Parameter | Target | Action if Failed |
|-----------|--------|-----------------|
| System Availability | ≥ 99.95% | Increase redundancy |
| Annual Downtime | ≤ 4.38 hrs | Reduce MTTR or add spares |

---

## Workflow

### Complete Validation Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    bvNexus Optimization                          │
│                         ↓                                        │
│              Equipment Configuration                             │
│              + Scenario Definitions                              │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                  EXPORT HUB (Page 1)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ETAP Excel  │  │ PSS/e RAW   │  │ Windchill RAM Excel     │  │
│  │ - Equipment │  │ - Network   │  │ - Components            │  │
│  │ - Scenarios │  │ - Scenarios │  │ - RBD Structure         │  │
│  └─────────────┘  └─────────────┘  │ - FMEA Template         │  │
│                                     └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │      EXTERNAL TOOL STUDIES          │
        │  • ETAP: Load Flow, Short Circuit   │
        │  • PSS/e: Power Flow, Stability     │
        │  • Windchill: RAM Simulation        │
        └─────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                  IMPORT HUB (Page 2)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              VALIDATION DASHBOARD                        │    │
│  │  ✅ Stage 1: Screening         PASSED                   │    │
│  │  ✅ Stage 2a: ETAP Load Flow   PASSED                   │    │
│  │  ✅ Stage 2b: ETAP Short Circ  PASSED                   │    │
│  │  ⚠️ Stage 2c: PSS/e Stability  WARNING                  │    │
│  │  ❌ Stage 3: RAM Analysis      FAILED                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           CONSTRAINT UPDATES                             │    │
│  │  • redundancy_level: 1 → 2 (N+1 to N+2)                 │    │
│  │  • Reason: Availability 99.72% < 99.95% target          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          ↓
              Back to bvNexus Optimization
              (with updated constraints)
```

### Demo Mode

The Import Hub includes a **Demo Mode** tab that loads sample results to demonstrate the workflow:

1. **All Pass** - Shows successful validation across all tools
2. **RAM Fail** - Demonstrates availability failure with constraint feedback
3. **ETAP Fail (Voltage)** - Shows voltage violation handling
4. **ETAP Fail (Short Circuit)** - Shows breaker duty exceedance

---

## Visual Features

### Export Hub

1. **Single Line Diagram** - Auto-generated SVG showing equipment topology
2. **RBD Diagram** - Reliability block diagram with parallel/series blocks
3. **File Previews** - See exactly what will be exported before download
4. **Sample File Structures** - Reference formats for each tool

### Import Hub

1. **Validation Dashboard** - Stage-by-stage progress tracking
2. **Metrics Display** - Key values with pass/fail indicators
3. **Violation Highlighting** - Clear display of what failed and why
4. **Constraint Updates** - Suggested parameter changes with justification

---

## Validation Criteria Summary

### ETAP Load Flow
| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Voltage (pu) | 0.95-1.05 | - | <0.95 or >1.05 |
| Loading (%) | <80 | 80-100 | >100 |

### ETAP Short Circuit
| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Breaker Duty (%) | <80 | 80-100 | >100 |
| X/R Ratio | <15 | 15-25 | >25 |

### PSS/e Power Flow
| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Voltage (pu) | 0.95-1.05 | - | <0.95 or >1.05 |
| Angle (deg) | <30 | 30-60 | >60 |

### Windchill RAM
| Metric | Pass | Fail |
|--------|------|------|
| Availability | ≥99.95% | <99.95% |
| Annual Downtime | ≤4.38 hrs | >4.38 hrs |

---

## Support

For questions about file formats or integration workflow, contact:
- bvNexus Development Team
- Black & Veatch Power Systems Engineering

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Dec 2024 | Enhanced UI with visual previews, sample files, demo mode |
| 1.0 | Dec 2024 | Initial export/import functionality |
