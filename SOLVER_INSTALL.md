# CBC Solver Installation Instructions

## Purpose
The bvNexus MILP model requires a Mixed-Integer Linear Programming (MILP) solver to optimize the datacenter power system. CBC is recommended as it's free, open-source, and provides good performance.

## Installation Options

### Option 1: Homebrew (Recommended for Mac)

If you have Homebrew installed:
```bash
brew tap coin-or-tools/coinor
brew install coin-or-tools/coinor/cbc
```

To install Homebrew first (if needed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Option 2: Conda

If you have conda/miniconda:
```bash
conda install -c conda-forge coincbc
```

### Option 3: Build from Source

1. Download CBC from https://github.com/coin-or/Cbc
2. Follow build instructions in repository README

### Option 4: Use GLPK (Alternative)

GLPK is another free solver, slightly slower but easier to install:

```bash
# Mac with Homebrew
brew install glpk

# Linux (Ubuntu/Debian)
sudo apt-get install glpk-utils

# Linux (Fedora/RHEL)
sudo yum install glpk-utils
```

### Option 5: Use NEOS Online Solver (No Installation)

Pyomo can submit jobs to NEOS server (free, but requires internet):

```python
# Modify solve() call in your code:
optimizer.solve(solver='cbc', neos=True)
```

## Verification

After installation, verify the solver is available:

```bash
# For CBC
cbc -help

# For GLPK  
glpsol --help
```

Or test with Python:
```python
from pyomo.environ import SolverFactory

# Test CBC
solver = SolverFactory('cbc')
print(f"CBC available: {solver.available()}")

# Test GLPK
solver = SolverFactory('glpk')
print(f"GLPK available: {solver.available()}")
```

## Testing the MILP Model

Once a solver is installed, run:
```bash
cd /Users/douglasmackenzie/energy-optimizer
python3 test_milp_quick.py
```

Expected output:
- Model builds successfully
- Solve completes in 30-60 seconds
- Returns feasible solution with LCOE and DR metrics

## Alternative: Gurobi (Commercial, Best Performance)

For best performance, consider Gurobi with free academic license:

1. Register at https://www.gurobi.com/academia/academic-program-and-licenses/
2. Download and install Gurobi
3. Request academic license
4. Install Python interface: `pip install gurobipy`

Gurobi typically solves 2-5x faster than CBC.

## Troubleshooting

**"No executable found for solver 'cbc'"**:
- Solver not in PATH
- Solution: Add solver binary directory to PATH, or reinstall

**"Solver not available"**:
- Pyomo can't find solver
- Solution: Run verification commands above

**Slow solve times (>5 minutes)**:
- Expected for GLPK (slower than CBC)
- Solution: Install CBC or Gurobi for better performance

## Current Status

✅ Pyomo installed
✅ MILP model built successfully  
✅ ~115,000 variables, 1,008 time periods
⚠️ No solver currently available on system
