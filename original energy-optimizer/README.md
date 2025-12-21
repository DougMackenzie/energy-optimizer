# Antigravity Energy Optimizer

A HOMER-like energy system optimization tool for behind-the-meter (BTM) power solutions targeting AI datacenter loads. Built with Streamlit, designed for B&V consulting engagements.

## 🎯 Purpose

Optimize BTM power configurations for AI datacenters (50 MW - 2+ GW) considering:
- **Time-to-power** as primary objective (speed matters for AI infrastructure)
- Equipment selection (recip engines, gas turbines, BESS, solar, grid)
- Reliability/availability (RAM analysis)
- Permitting constraints (NOx limits for minor source)
- Economic analysis (LCOE, CAPEX)
- Load variability from different AI workloads

## 📁 Project Structure

```
antigravity-optimizer/
├── app/
│   ├── main.py                 # Streamlit entry point
│   ├── pages/                  # Multi-page Streamlit app
│   │   ├── 01_dashboard.py
│   │   ├── 02_sites.py
│   │   ├── 03_load_composer.py
│   │   ├── 04_variability.py
│   │   ├── 05_transient_screening.py
│   │   ├── 06_equipment.py
│   │   ├── 07_optimizer.py
│   │   ├── 08_ram_analysis.py
│   │   ├── 09_results.py
│   │   └── 10_dispatch.py
│   ├── components/             # Reusable UI components
│   │   ├── __init__.py
│   │   ├── charts.py
│   │   ├── metrics.py
│   │   ├── forms.py
│   │   └── tables.py
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   ├── calculations.py
│   │   ├── data_io.py
│   │   └── formatting.py
│   └── models/                 # Data models & optimization
│       ├── __init__.py
│       ├── equipment.py
│       ├── load_profile.py
│       ├── optimizer.py
│       ├── ram.py
│       └── dispatch.py
├── config/
│   ├── settings.py             # App configuration
│   ├── equipment_defaults.yaml # Default equipment library
│   └── constraints.yaml        # Default constraint values
├── data/
│   ├── templates/              # Load profile templates
│   │   └── workload_presets.yaml
│   └── equipment/              # Equipment spec sheets
│       └── README.md
├── docs/
│   ├── IMPLEMENTATION_PLAN.md  # Phased build plan
│   ├── ARCHITECTURE.md         # Technical architecture
│   └── UI_MOCKUP.html          # Reference UI design
├── tests/
│   ├── test_optimizer.py
│   ├── test_ram.py
│   └── test_dispatch.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud credentials (for Sheets integration) OR
- Microsoft 365 credentials (for SharePoint integration)

### Installation

```bash
# Clone or copy this folder
cd antigravity-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run the app
streamlit run app/main.py
```

### First Run
1. App opens at http://localhost:8501
2. Start with **Load Composer** to define your facility
3. Configure **Equipment Library** with available options
4. Set **Constraints** in Optimizer page
5. Run optimization
6. Review results and dispatch analysis

## 🔧 Configuration

### Backend Options

**Google Sheets (Current)**
```python
# config/settings.py
BACKEND = "google_sheets"
SHEET_ID = "your-google-sheet-id"
```

**SharePoint Lists (Migration Target)**
```python
# config/settings.py
BACKEND = "sharepoint"
SHAREPOINT_SITE = "your-site-url"
LIST_NAME = "AntigravityProjects"
```

### Environment Variables
```bash
# .env
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json
OPENAI_API_KEY=sk-...  # For Gemini/Claude analysis features
```

## 📊 Key Features

### Load Analysis
- **Workload Composer**: Mix AI workloads (pre-training, inference, RL, etc.)
- **Variability Analysis**: Understand mitigation stack (UPS → algorithms → BESS → engines)
- **Transient Screening**: Simplified physics checks before ETAP validation

### Optimization
- **Multi-objective**: Time-to-power, LCOE, CAPEX, carbon
- **ε-Constraint Method**: Trace Pareto frontier
- **Hard Constraints**: Capacity, availability, NOx, ramp rate, timeline

### Results
- **Scenario Comparison**: Side-by-side feasible configurations
- **8760 Dispatch**: Full-year hourly simulation
- **Sub-second Analysis**: Transient event visualization
- **RAM Analysis**: Reliability modeling with Monte Carlo validation

## 🛠️ Development

### Adding New Equipment
1. Edit `config/equipment_defaults.yaml`
2. Or use Equipment Library page in app

### Modifying Constraints
1. Edit `config/constraints.yaml` for defaults
2. Override in app UI per project

### Running Tests
```bash
pytest tests/
```

## 📈 Roadmap

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed phased build plan.

**Phase 1** (Weeks 1-2): Core data models, basic UI  
**Phase 2** (Weeks 3-4): Optimization engine, constraints  
**Phase 3** (Weeks 5-6): 8760 dispatch, results visualization  
**Phase 4** (Weeks 7-8): RAM analysis, transient screening  
**Phase 5** (Weeks 9-10): Polish, export, deployment

## 📝 License

Internal JLL/B&V tool - Not for distribution

## 🤝 Contributors

- Doug (JLL Powered Land) - Product Owner
- Claude (Anthropic) - Development Assistant
