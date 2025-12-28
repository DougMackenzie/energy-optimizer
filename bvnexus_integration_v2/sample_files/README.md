# bvNexus Integration Sample Files

This package contains sample files demonstrating the data exchange formats between bvNexus and external validation tools: **ETAP**, **PSS/e**, and **Windchill RAM**.

## 📁 Directory Structure

```
sample_files/
├── ETAP/
│   ├── ETAP_Equipment_Import.csv      # Equipment data for DataX import
│   ├── ETAP_Scenarios.csv             # Study scenarios (base + contingencies)
│   ├── ETAP_LoadFlow_Results_PASS.csv # Load flow results - passing case
│   ├── ETAP_LoadFlow_Results_FAIL.csv # Load flow results - failing case
│   └── ETAP_ShortCircuit_Results.csv  # Short circuit study results
├── PSSe/
│   ├── bvNexus_Network.raw            # PSS/e RAW format network model
│   └── PSSe_PowerFlow_Results.csv     # Power flow results for import
└── Windchill_RAM/
    ├── RAM_Component_Data.csv         # Component reliability data
    ├── RAM_RBD_Structure.csv          # Reliability block diagram structure
    ├── RAM_FMEA_Template.csv          # Failure modes and effects analysis
    ├── RAM_Results_PASS.csv           # RAM results - passing (>99.95%)
    └── RAM_Results_FAIL.csv           # RAM results - failing (<99.95%)
```

---

## ⚡ ETAP Files

### Equipment Import (`ETAP_Equipment_Import.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| ID | Unique equipment identifier | GEN_RECIP_01 |
| Name | Descriptive name | Recip Engine 1 |
| Type | Equipment type | Synchronous Generator |
| Bus_ID | Connected bus | BUS_100 |
| Rated_kV | Voltage rating (kV) | 13.8 |
| Rated_MW | Power rating (MW) | 18.3 |
| Rated_MVA | Apparent power (MVA) | 21.5 |
| Rated_PF | Power factor | 0.85 |
| Xd_pu | Synchronous reactance (pu) | 1.80 |
| Xd_prime_pu | Transient reactance (pu) | 0.25 |
| Xd_double_prime_pu | Subtransient reactance (pu) | 0.18 |
| H_inertia_sec | Inertia constant (seconds) | 1.5 |
| Status | Operating status | Online |
| Redundancy_Group | Redundancy grouping | THERMAL_GEN |

**Usage:** Import via ETAP DataX → Excel Import. Map columns to ETAP equipment properties.

### Scenarios (`ETAP_Scenarios.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| Scenario_ID | Unique scenario identifier | N1_RECIP_01 |
| Name | Descriptive name | N-1: Recip 1 Trip |
| Type | Scenario category | N-1 Contingency |
| Load_MW | Load level (MW) | 200.0 |
| Load_PF | Load power factor | 0.95 |
| Tripped_Equipment | Equipment offline | GEN_RECIP_01 |
| Description | Scenario details | Single contingency... |

**Scenario Types:**
- **Normal**: All equipment online at various load levels
- **N-1 Contingency**: Single equipment trip at peak load
- **N-2 Contingency**: Double equipment trip at peak load

### Load Flow Results (`ETAP_LoadFlow_Results_*.csv`)

| Column | Description | Pass Criteria |
|--------|-------------|---------------|
| Voltage_pu | Per-unit voltage | 0.95 - 1.05 pu |
| Loading_pct | Equipment loading | < 80% (warn), < 100% (fail) |

**PASS file**: All voltages within limits, loading < 80%
**FAIL file**: Under-voltage violations (< 0.95 pu), overloading (> 100%)

### Short Circuit Results (`ETAP_ShortCircuit_Results.csv`)

| Column | Description | Pass Criteria |
|--------|-------------|---------------|
| Isc_kA | Fault current (kA) | < Breaker rating |
| Duty_pct | Breaker duty (%) | < 100% |
| X_R_Ratio | X/R ratio | < 25 (typical) |

---

## 🔌 PSS/e Files

### Network Model (`bvNexus_Network.raw`)

PSS/e RAW format (v33/34/35 compatible) containing:

| Section | Contents |
|---------|----------|
| Header | System MVA base, case title |
| BUS DATA | Bus numbers, names, voltage levels |
| LOAD DATA | Load MW/MVAR at datacenter bus |
| GENERATOR DATA | Generator ratings and impedances |
| BRANCH DATA | Lines connecting generators to main bus |
| AREA DATA | Control area definition |

**Key RAW Format Notes:**
- Each section ends with `0 / END OF <SECTION> DATA`
- File ends with `Q`
- Comments start with `/`
- Bus types: 1=Load, 2=Generator, 3=Swing

### Power Flow Results (`PSSe_PowerFlow_Results.csv`)

| Column | Description | Pass Criteria |
|--------|-------------|---------------|
| VM_PU | Voltage magnitude (pu) | 0.95 - 1.05 pu |
| VA_DEG | Voltage angle (degrees) | < 30° separation |
| P_GEN_MW | Real power generation | Matches dispatch |
| Q_GEN_MVAR | Reactive power | Within limits |

---

## 📈 Windchill RAM Files

### Component Data (`RAM_Component_Data.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| Component_ID | Unique identifier | GEN_RECIP_01 |
| Component_Type | Equipment category | RECIPROCATING_ENGINE |
| MTBF_Hours | Mean time between failures | 8760 (1 year) |
| MTTR_Hours | Mean time to repair | 24 |
| Failure_Rate_Per_Hour | λ = 1/MTBF | 1.14E-04 |
| Availability | A = MTBF/(MTBF+MTTR) | 0.9973 |
| Distribution | Failure distribution | Exponential, Weibull |
| Weibull_Beta | Shape parameter (β) | 1.0 = exponential |
| Weibull_Eta | Scale parameter (η) | = MTBF for β=1 |

**Typical MTBF Values:**
- Reciprocating Engine: 8,760 hours (1 year)
- Gas Turbine: 17,520 hours (2 years)
- BESS: 43,800 hours (5 years)
- Transformer: 175,200 hours (20 years)
- Switchgear: 87,600 hours (10 years)

### RBD Structure (`RAM_RBD_Structure.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| Block_ID | Block identifier | THERMAL_GEN |
| Block_Type | Configuration type | PARALLEL_K_OF_N |
| Components | Comma-separated list | GEN_RECIP_01,... |
| K_Required | Minimum units needed | 9 |
| N_Total | Total units available | 10 |

**Block Types:**
- **SERIES**: All components required (A = A₁ × A₂ × ... × Aₙ)
- **PARALLEL**: Any component sufficient (A = 1 - (1-A₁)(1-A₂)...(1-Aₙ))
- **PARALLEL_K_OF_N**: K of N required (binomial calculation)
- **STANDBY**: Backup with switching (not in primary path)

### FMEA Template (`RAM_FMEA_Template.csv`)

Failure Modes and Effects Analysis structure:

| Column | Description |
|--------|-------------|
| Failure_Mode | How component fails |
| Failure_Cause | Root cause |
| Local_Effect | Impact on component |
| System_Effect | Impact on system |
| Severity | Criticality rating |
| Occurrence | Frequency rating |
| Detection | Detectability rating |
| RPN | Risk Priority Number (S×O×D) |
| Mitigation | Current controls |
| Recommended_Action | Improvement actions |

### RAM Results (`RAM_Results_*.csv`)

| Column | Description | Target |
|--------|-------------|--------|
| Availability | System availability (0-1) | ≥ 0.9995 (99.95%) |
| Annual_Downtime_Hours | Hours/year unavailable | ≤ 4.38 hours |
| MTBF_Hours | System MTBF | ≥ 8,760 hours |
| Failures_Per_Year | Expected failures | Minimize |

**PASS file**: System availability = 99.952% (target: 99.95%)
**FAIL file**: System availability = 99.667% (below target)

---

## 🔄 Data Flow Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         bvNexus                                      │
│                                                                      │
│  1. Optimization produces equipment configuration                    │
│                          ↓                                           │
│  2. Export Hub generates tool-specific files                        │
│     • ETAP: Equipment + Scenarios (CSV/Excel)                       │
│     • PSS/e: Network model (RAW) + Scenarios (CSV)                  │
│     • RAM: Components + RBD + FMEA (CSV/Excel)                      │
│                          ↓                                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    External Tools                                    │
│                                                                      │
│  3. Engineers run studies manually:                                  │
│     • ETAP: Load flow, short circuit, arc flash                     │
│     • PSS/e: Power flow, contingency, stability                     │
│     • Windchill: RBD simulation, availability analysis              │
│                          ↓                                           │
│  4. Export results to CSV/Excel                                     │
│                                                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         bvNexus                                      │
│                                                                      │
│  5. Import Hub parses results                                       │
│     • Check voltage limits (0.95-1.05 pu)                           │
│     • Check equipment loading (<100%)                                │
│     • Check fault currents (<breaker ratings)                       │
│     • Check availability (≥99.95%)                                  │
│                          ↓                                           │
│  6. Generate constraint updates if validation fails                  │
│     • Increase redundancy level                                      │
│     • Upgrade breaker ratings                                        │
│     • Add reactive support                                           │
│                          ↓                                           │
│  7. Re-optimize with updated constraints                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Validation Criteria Summary

| Study | Metric | Pass | Warning | Fail |
|-------|--------|------|---------|------|
| ETAP Load Flow | Voltage (pu) | 0.95-1.05 | - | <0.95 or >1.05 |
| ETAP Load Flow | Loading (%) | <80% | 80-100% | >100% |
| ETAP Short Circuit | Breaker Duty (%) | <80% | 80-100% | >100% |
| PSS/e Power Flow | Voltage (pu) | 0.95-1.05 | - | <0.95 or >1.05 |
| PSS/e Power Flow | Angle (deg) | <30° | 30-60° | >60° |
| RAM Availability | System (%) | ≥99.95% | 99.90-99.95% | <99.90% |
| RAM Availability | Downtime (hrs/yr) | ≤4.38 | 4.38-8.76 | >8.76 |

---

## 📝 Usage Instructions

### Exporting from bvNexus

1. Complete optimization to get equipment configuration
2. Go to **Integration Export Hub**
3. Select tool (ETAP, PSS/e, or Windchill RAM)
4. Review preview of generated data
5. Download files for import into external tool

### Running External Studies

**ETAP:**
1. File → Import → DataX → Select Equipment CSV
2. Create study cases using Scenarios CSV
3. Run Load Flow / Short Circuit studies
4. Results Analyzer → Export to Excel

**PSS/e:**
1. File → Read → Power Flow Data (RAW)
2. Run Newton-Raphson power flow
3. Use dyntools or API to export results to CSV

**Windchill RAM:**
1. File → Import → Excel → Component Data
2. Build RBD using structure definition
3. Run availability simulation
4. Export results to Excel

### Importing Results to bvNexus

1. Go to **Integration Import Hub**
2. Select tool and study type
3. Upload results CSV/Excel file
4. Review parsed metrics and validation status
5. Apply suggested constraint updates if needed
6. Re-optimize with updated constraints

---

## 📧 Support

For questions about file formats or integration workflow, contact your bvNexus administrator.
