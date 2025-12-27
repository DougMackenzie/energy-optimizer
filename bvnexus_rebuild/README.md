# bvNexus

**Co-located Power, Energy and Load Optimization for AI Datacenters**

A multi-objective optimization tool designed for behind-the-meter (BTM) power solutions targeting AI datacenter loads. Built with Streamlit, featuring a two-phase optimization approach with heuristic screening and MILP optimization.

## 🎯 Overview

bvNexus addresses the critical challenge of powering AI datacenters when grid interconnection queues span multiple years. It optimizes equipment selection, sizing, and dispatch across:

- **Reciprocating Engines** - Fast deployment, modular
- **Gas Turbines** - Large scale, lower emissions  
- **Battery Storage (BESS)** - Grid services, load shaping
- **Solar PV** - Zero emissions, hedge against fuel
- **Grid Connection** - When available

## 📊 Five Problem Statements

| Problem | Objective | Key Question |
|---------|-----------|--------------|
| **P1: Greenfield** | Minimize LCOE | What's the cheapest way to reliably serve my load trajectory? |
| **P2: Brownfield** | Maximize Load | How much can I expand within my LCOE ceiling? |
| **P3: Land Development** | Maximize Capacity | How much power can this site support? |
| **P4: Grid Services** | Maximize DR Revenue | What grid services should I participate in? |
| **P5: Bridge Power** | Minimize NPV | What's the optimal BTM-to-grid transition strategy? |

## 🚀 Quick Start

### Installation

```bash
# Clone or copy the repository
cd bvnexus_rebuild

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/main.py
```

### First Use

1. **Configure Site** - Go to Sites & Load, enter your datacenter parameters
2. **Set Load Trajectory** - Define phased deployment schedule
3. **Select Problem** - Choose the optimization question to answer
4. **Run Phase 1** - Get quick heuristic results (30-60 seconds)
5. **Review Results** - Analyze 8760 dispatch, pro forma, constraints

## 📁 Project Structure

```
bvnexus_rebuild/
├── app/
│   ├── main.py                      # Streamlit entry point
│   ├── pages/                       # UI pages
│   │   ├── page_dashboard.py        # Overview dashboard
│   │   ├── page_sites_load.py       # Site configuration
│   │   ├── page_equipment.py        # Equipment library
│   │   ├── page_problem_selection.py
│   │   ├── page_problem_1_greenfield.py
│   │   ├── page_problem_2_brownfield.py
│   │   ├── page_problem_3_land_dev.py
│   │   ├── page_problem_4_grid_services.py
│   │   ├── page_problem_5_bridge.py
│   │   ├── page_results.py          # Consolidated results
│   │   ├── page_dispatch.py         # 8760 visualization
│   │   ├── page_proforma.py         # Cash flow analysis
│   │   └── page_ram.py              # Reliability analysis
│   ├── optimization/                # Optimization engines
│   │   ├── __init__.py
│   │   └── heuristic_optimizer.py   # Phase 1 heuristic
│   └── outputs/                     # Report generation
│       └── __init__.py
├── config/
│   └── settings.py                  # App configuration
├── requirements.txt
└── README.md
```

## ⚙️ Optimization Approach

### Phase 1: Heuristic Screening (Available Now)
- **Runtime**: 30-60 seconds
- **Accuracy**: ±50% (Class 5 estimate)
- **Method**: Deterministic rules, merit-order dispatch
- **Use Case**: Rapid iteration, initial screening

### Phase 2: MILP Optimization (Coming Soon)
- **Runtime**: 5-60 minutes  
- **Accuracy**: ±20% (Class 3 estimate)
- **Method**: HiGHS via Pyomo APPSI, representative weeks
- **Use Case**: Detailed design, final sizing

### Tier 3: LP Validation (Coming Soon)
- **Runtime**: 15-30 minutes
- **Accuracy**: ±15% (Class 3 estimate)
- **Method**: Full 8760 dispatch at 15-minute resolution
- **Use Case**: Demand charge validation, final economics

## 📈 Key Outputs

- **Equipment Sizing**: Optimal mix and count
- **8760 Dispatch**: Hourly generation schedule
- **Pro Forma**: 15-year cash flow projection
- **Constraint Analysis**: Shadow prices on binding limits
- **Deployment Timeline**: Gantt chart with milestones
- **RAM Analysis**: K-of-N availability calculations

## 🔧 Configuration

### Equipment Parameters (config/settings.py)

```python
EQUIPMENT_DEFAULTS = {
    'recip': {
        'capacity_mw': 18.3,
        'heat_rate_btu_kwh': 7700,
        'nox_lb_mwh': 0.50,
        'capex_per_kw': 1650,
        ...
    },
    ...
}
```

### Constraint Defaults

```python
CONSTRAINT_DEFAULTS = {
    'nox_tpy_annual': 100,      # Minor source threshold
    'gas_supply_mcf_day': 50000,
    'land_area_acres': 500,
    ...
}
```

## 🧪 Development

### Adding a New Problem Type

1. Create optimizer class in `app/optimization/heuristic_optimizer.py`
2. Create page in `app/pages/page_problem_N_name.py`
3. Register in `app/main.py` router
4. Add to `PROBLEM_STATEMENTS` in `config/settings.py`

### Testing

```bash
# Run tests (when implemented)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app
```

## 📋 Roadmap

### Current Release (v2.0.0)
- [x] 5 problem statements defined
- [x] Phase 1 heuristic optimization
- [x] 8760 dispatch simulation
- [x] Pro forma cash flow
- [x] RAM analysis
- [x] Streamlit UI

### Next Release (v2.1.0)
- [ ] Phase 2 MILP with HiGHS
- [ ] Representative period selection (tsam)
- [ ] Kotzur inter-period storage linking
- [ ] Shadow price output

### Future (v3.0.0)
- [ ] 15-minute demand charge validation
- [ ] Multi-year capacity expansion
- [ ] Stochastic scenarios
- [ ] API integration (ETAP, PSS/e)

## 📚 References

- Implementation Guide v3.2 (project knowledge)
- Power Systems Optimization Tools Comparison
- AI HPC Data Centers and Demand Response Technical Guide

## 👤 Author

Doug Mackenzie | Black & Veatch

## 📄 License

Proprietary - Black & Veatch Internal Use Only
