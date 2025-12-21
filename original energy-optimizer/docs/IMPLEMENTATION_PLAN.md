# Antigravity Energy Optimizer - Implementation Plan

## Overview

This document outlines the phased approach to building the Antigravity Energy Optimizer from the UI mockup to a functional prototype. The plan is designed for iterative development with working deliverables at each phase.

---

## Phase 0: Project Setup (Day 1)
**Goal**: Development environment ready, basic app running

### Tasks
- [ ] Create project folder structure
- [ ] Set up virtual environment
- [ ] Install core dependencies
- [ ] Create basic Streamlit app with navigation
- [ ] Set up Google Sheets connection (or local JSON for offline dev)
- [ ] Copy UI mockup to docs/ for reference

### Deliverables
- Running Streamlit app with sidebar navigation
- All pages stubbed out with placeholder content

### Commands
```bash
cd antigravity-optimizer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

---

## Phase 1: Data Models & Load Composer (Week 1)
**Goal**: Define core data structures, functional Load Composer page

### 1.1 Data Models
- [ ] `LoadProfile` class - workload mix, PUE, facility parameters
- [ ] `Equipment` base class with subclasses (Recip, GT, BESS, Solar, Grid)
- [ ] `Site` class - location, interconnection, constraints
- [ ] `Project` class - container for all project data

### 1.2 Load Composer Page
- [ ] Facility parameters form (IT capacity, PUE, cooling, UPS)
- [ ] Workload mix sliders with real-time MW calculation
- [ ] Quick presets (Training, Inference, Balanced, Cloud)
- [ ] PUE seasonal variation inputs
- [ ] Composite profile calculation (weighted utilization, transient magnitude)
- [ ] Save/load profile to backend

### 1.3 Backend Integration
- [ ] Google Sheets helper functions (read/write)
- [ ] Session state management
- [ ] Data persistence between pages

### Deliverables
- Functional Load Composer with working sliders
- Data saved to Google Sheets on "Save Profile"
- Profile loads on page refresh

### Key Code
```python
# models/load_profile.py
@dataclass
class WorkloadMix:
    pre_training: float = 0.40
    fine_tuning: float = 0.15
    batch_inference: float = 0.20
    realtime_inference: float = 0.10
    rl_training: float = 0.05
    cloud_hpc: float = 0.10
    
    def validate(self) -> bool:
        return abs(sum(self.__dict__.values()) - 1.0) < 0.001
```

---

## Phase 2: Equipment Library & Sites (Week 2)
**Goal**: Equipment database, site management, basic optimizer setup

### 2.1 Equipment Library
- [ ] Equipment data model with full specs
- [ ] YAML-based equipment database
- [ ] Equipment card UI component
- [ ] Add/edit/delete equipment
- [ ] Equipment selection for project
- [ ] Quantity controls per equipment type

### 2.2 Sites Page
- [ ] Site data model (location, acreage, zoning, interconnection)
- [ ] Site list with selection
- [ ] Folium map integration
- [ ] Site details panel
- [ ] Interconnection info (queue position, study status, timeline)

### 2.3 Data Integration
- [ ] Link equipment selections to project
- [ ] Calculate total nameplate capacity
- [ ] Validate N-1 capacity

### Deliverables
- Equipment library with 10+ pre-loaded equipment types
- Functional site management with map
- Equipment selections persist

### Key Data
```yaml
# config/equipment_defaults.yaml
recip_engines:
  - id: wartsila_50sg
    name: "Wärtsilä 50SG"
    type: recip
    capacity_mw: 18.8
    efficiency_pct: 48.2
    heat_rate_btu_kwh: 7084
    start_time_min: 2
    ramp_rate_mw_min: 3.0
    nox_g_hphr: 0.5
    lead_time_months: [12, 24]
    capex_per_kw: 850
    fixed_om_per_kw_yr: 15
    variable_om_per_mwh: 8
```

---

## Phase 3: Optimizer Core (Weeks 3-4)
**Goal**: Working optimization engine with constraints and objectives

### 3.1 Constraint System
- [ ] Hard constraint definitions (capacity, availability, NOx, time, LCOE, ramp)
- [ ] Constraint validation functions
- [ ] Constraint violation reporting

### 3.2 Optimization Engine
- [ ] Pyomo model setup
- [ ] Decision variables (equipment counts, dispatch)
- [ ] Objective functions (time, LCOE, CAPEX, carbon)
- [ ] ε-constraint implementation for Pareto frontier
- [ ] Gurobi/CBC solver integration

### 3.3 Optimizer Page UI
- [ ] Hard constraints form
- [ ] Objectives selection
- [ ] Solver settings
- [ ] Run button with progress indicator
- [ ] Results summary

### 3.4 Scenario Generation
- [ ] Equipment combination enumeration
- [ ] Feasibility screening (quick constraint check)
- [ ] Full optimization for feasible scenarios

### Deliverables
- Run optimization on 100 scenarios
- Identify feasible vs infeasible
- Basic Pareto frontier

### Key Code
```python
# models/optimizer.py
from pyomo.environ import *

class EnergyOptimizer:
    def __init__(self, project: Project):
        self.project = project
        self.model = ConcreteModel()
        
    def build_model(self):
        # Decision variables
        self.model.n_recip = Var(within=NonNegativeIntegers, bounds=(0, 20))
        self.model.bess_mwh = Var(within=NonNegativeReals, bounds=(0, 500))
        # ... etc
        
    def add_constraints(self, constraints: dict):
        # Capacity constraint
        self.model.capacity_con = Constraint(
            expr=self._total_capacity() >= constraints['min_capacity_mw']
        )
        # ... etc
        
    def solve(self, objective='time_to_power'):
        solver = SolverFactory('gurobi')  # or 'cbc' for free solver
        results = solver.solve(self.model)
        return self._extract_results(results)
```

---

## Phase 4: Results & Dispatch (Weeks 5-6)
**Goal**: Rich results visualization, 8760 dispatch simulation

### 4.1 Results Page
- [ ] Scenario comparison table
- [ ] Constraint violation breakdown chart
- [ ] Pareto frontier visualization (Plotly)
- [ ] Scenario cards with key metrics
- [ ] Scenario selection for detailed view

### 4.2 8760 Dispatch Engine
- [ ] Hourly load profile generation
- [ ] Merit order dispatch logic
- [ ] Engine start/stop tracking
- [ ] BESS charge/discharge optimization
- [ ] Solar production modeling (simple capacity factor)
- [ ] Grid import as balancing resource

### 4.3 Dispatch Page
- [ ] Annual stacked area chart
- [ ] Zoom controls (year → month → week → day)
- [ ] Equipment operating statistics table
- [ ] Fuel consumption / emissions totals

### 4.4 Sub-Second View
- [ ] Synthetic transient event visualization
- [ ] BESS vs engine response illustration
- [ ] Note: This is illustrative, not physics-based

### Deliverables
- Full 8760 dispatch for selected scenario
- Interactive zoom from annual to daily
- Operating statistics (hours, starts, CF)

### Key Code
```python
# models/dispatch.py
class DispatchEngine:
    def __init__(self, scenario: Scenario, load_profile: LoadProfile):
        self.scenario = scenario
        self.load_profile = load_profile
        
    def run_8760(self) -> pd.DataFrame:
        """Run hourly dispatch for full year"""
        hours = pd.date_range('2026-01-01', periods=8760, freq='H')
        results = []
        
        for hour in hours:
            load = self._get_load(hour)
            dispatch = self._dispatch_merit_order(load, hour)
            results.append(dispatch)
            
        return pd.DataFrame(results, index=hours)
    
    def _dispatch_merit_order(self, load: float, hour: datetime) -> dict:
        """Dispatch equipment in merit order"""
        remaining = load
        dispatch = {}
        
        # 1. Solar (must-take)
        solar = self._solar_output(hour)
        dispatch['solar'] = min(solar, remaining)
        remaining -= dispatch['solar']
        
        # 2. BESS (if discharging makes sense)
        # 3. Engines (base-load first, then peakers)
        # 4. Grid (balancing)
        
        return dispatch
```

---

## Phase 5: RAM Analysis (Week 7)
**Goal**: Reliability modeling with layered approach

### 5.1 RAM Data Model
- [ ] Equipment failure rates (FOR, MTBF, MTTR)
- [ ] IEEE Gold Book / NERC GADS data
- [ ] k-of-n redundancy calculations

### 5.2 Analytical RAM
- [ ] System availability calculation
- [ ] Series/parallel reliability blocks
- [ ] MTBF / MTTR system rollup
- [ ] Expected outages per year

### 5.3 Monte Carlo (Optional)
- [ ] Basic MC simulation for validation
- [ ] Failure event sampling
- [ ] Repair time distributions
- [ ] Confidence intervals

### 5.4 RAM Page UI
- [ ] Reliability block diagram visualization
- [ ] Equipment failure data table
- [ ] System availability result
- [ ] Sensitivity analysis

### Deliverables
- RAM calculation for any scenario
- Availability meets/exceeds target check
- Sensitivity to key parameters

### Key Code
```python
# models/ram.py
class RAMAnalyzer:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        
    def calculate_availability(self) -> float:
        """Calculate system availability using k-of-n model"""
        # Engine availability (need k of n)
        engine_avail = self._k_of_n_availability(
            n=self.scenario.n_engines,
            k=self.scenario.n_engines - 1,  # N-1
            unit_avail=0.975
        )
        
        # BESS availability
        bess_avail = 0.995
        
        # System = engines AND bess (series)
        # But with grid backup (parallel)
        return self._parallel(
            self._series([engine_avail, bess_avail]),
            0.9997  # Grid availability
        )
```

---

## Phase 6: Variability & Transient Screening (Week 8)
**Goal**: Load variability analysis and honest transient checks

### 6.1 Variability Analysis Page
- [ ] Mitigation stack visualization
- [ ] "What BTM Sees" calculation
- [ ] Residual variability by timescale
- [ ] UPS smoothing effect

### 6.2 Transient Screening
- [ ] BESS energy for ramp coverage
- [ ] Combined ramp rate check
- [ ] N-1 spinning reserve
- [ ] Inertia / RoCoF screening
- [ ] UPS ride-through duration
- [ ] "Needs ETAP" flagging

### 6.3 Screening Report
- [ ] Pass/Warn/Fail/Needs-Study status
- [ ] Calculation details shown
- [ ] ETAP study scope recommendations

### Deliverables
- Screening checks for any scenario
- Clear distinction: screening vs simulation
- Export ETAP study scope

---

## Phase 7: Polish & Export (Weeks 9-10)
**Goal**: Production-ready polish, export capabilities

### 7.1 Dashboard
- [ ] Project overview metrics
- [ ] Status indicators
- [ ] Quick actions
- [ ] Recommended scenario highlight

### 7.2 Export Capabilities
- [ ] PDF report generation
- [ ] Excel export (8760 data)
- [ ] PowerPoint summary
- [ ] ETAP input file format

### 7.3 UI Polish
- [ ] Consistent styling
- [ ] Loading states
- [ ] Error handling
- [ ] Help tooltips
- [ ] Mobile responsiveness (basic)

### 7.4 Testing & Documentation
- [ ] Unit tests for core calculations
- [ ] Integration tests for optimizer
- [ ] User documentation
- [ ] API documentation

### Deliverables
- Complete working prototype
- Export to PDF/Excel/PPT
- Ready for user testing

---

## Phase 8: Deployment (Week 11+)
**Goal**: Production deployment on Azure

### 8.1 Azure Setup
- [ ] Azure App Service configuration
- [ ] SharePoint Lists migration
- [ ] Authentication setup (Azure AD)
- [ ] CI/CD pipeline

### 8.2 SharePoint Integration
- [ ] Graph API connection
- [ ] SharePoint Lists as backend
- [ ] Document library for exports

### 8.3 Monitoring
- [ ] Application Insights
- [ ] Error logging
- [ ] Usage analytics

---

## Dependencies & Risks

### Technical Dependencies
| Dependency | Mitigation |
|------------|------------|
| Gurobi license | Use CBC (free) for development, Gurobi for production |
| Google Sheets API | Can develop with local JSON files |
| Folium maps | Falls back gracefully if no internet |

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Optimization takes too long | High | Pre-screen scenarios, limit search space |
| RAM calculations incorrect | High | Validate against known examples, Monte Carlo check |
| UI too complex | Medium | User testing, iterate on feedback |

---

## Success Criteria

### MVP (Phase 4 Complete)
- [ ] Define 200 MW facility with workload mix
- [ ] Select from equipment library
- [ ] Run optimization with constraints
- [ ] View Pareto frontier
- [ ] See 8760 dispatch for selected scenario

### Full Prototype (Phase 7 Complete)
- [ ] All 10 pages functional
- [ ] RAM analysis working
- [ ] Transient screening with honest caveats
- [ ] Export to PDF/Excel
- [ ] Ready for client demo

### Production (Phase 8 Complete)
- [ ] Deployed on Azure
- [ ] SharePoint integration
- [ ] Multi-user support
- [ ] JLL IT approved

---

## Resource Estimates

| Phase | Effort (hrs) | Elapsed Time |
|-------|--------------|--------------|
| Phase 0: Setup | 4 | 1 day |
| Phase 1: Load Composer | 16 | 1 week |
| Phase 2: Equipment & Sites | 16 | 1 week |
| Phase 3: Optimizer | 32 | 2 weeks |
| Phase 4: Results & Dispatch | 32 | 2 weeks |
| Phase 5: RAM | 16 | 1 week |
| Phase 6: Variability | 16 | 1 week |
| Phase 7: Polish | 24 | 1.5 weeks |
| Phase 8: Deployment | 16 | 1 week |
| **Total** | **~170 hrs** | **~11 weeks** |

*Note: Estimates assume dedicated development time. Actual calendar time may vary based on availability and iteration cycles.*

---

## Next Steps

1. **Review this plan** - Confirm scope and priorities
2. **Set up development environment** - Run Phase 0 tasks
3. **Start Phase 1** - Begin with data models
4. **Weekly check-ins** - Review progress, adjust plan

Ready to start? Run:
```bash
cd antigravity-optimizer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```
