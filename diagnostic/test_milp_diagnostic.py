#!/usr/bin/env python3
"""
MILP Diagnostic Test Script
============================

Run this script directly to diagnose MILP issues:
    python test_milp_diagnostic.py

Put this file in your energy-optimizer root directory.
"""

import sys
import traceback

print("="*70)
print("MILP DIAGNOSTIC TEST")
print("="*70)

# ============================================================================
# TEST 1: Python version
# ============================================================================
print(f"\n[TEST 1] Python version: {sys.version}")

# ============================================================================
# TEST 2: Core imports
# ============================================================================
print("\n[TEST 2] Core imports...")

try:
    import numpy as np
    print(f"  ✓ numpy {np.__version__}")
except ImportError as e:
    print(f"  ✗ numpy FAILED: {e}")
    np = None

try:
    import pandas as pd
    print(f"  ✓ pandas {pd.__version__}")
except ImportError as e:
    print(f"  ✗ pandas FAILED: {e}")

# ============================================================================
# TEST 3: Pyomo
# ============================================================================
print("\n[TEST 3] Pyomo...")

try:
    import pyomo
    print(f"  ✓ pyomo {pyomo.__version__}")
except ImportError as e:
    print(f"  ✗ pyomo FAILED: {e}")
    print("  → Install: pip install pyomo")
    sys.exit(1)

try:
    from pyomo.environ import *
    print(f"  ✓ pyomo.environ imported")
except ImportError as e:
    print(f"  ✗ pyomo.environ FAILED: {e}")
    sys.exit(1)

# ============================================================================
# TEST 4: Solvers
# ============================================================================
print("\n[TEST 4] MILP Solvers...")

solver_found = False
for solver_name in ['glpk', 'cbc', 'gurobi', 'cplex']:
    try:
        opt = SolverFactory(solver_name)
        if opt is not None and opt.available():
            print(f"  ✓ {solver_name} AVAILABLE")
            solver_found = True
        else:
            print(f"  ✗ {solver_name} not available")
    except Exception as e:
        print(f"  ✗ {solver_name} error: {e}")

if not solver_found:
    print("\n  ⚠️  NO SOLVER FOUND!")
    print("  Install one of:")
    print("    brew install glpk          # macOS")
    print("    apt-get install glpk-utils # Ubuntu")
    print("    conda install -c conda-forge glpk")

# ============================================================================
# TEST 5: Simple MILP solve
# ============================================================================
print("\n[TEST 5] Simple MILP solve test...")

if solver_found:
    try:
        # Create a trivial model
        m = ConcreteModel()
        m.x = Var(within=NonNegativeReals)
        m.y = Var(within=NonNegativeReals)
        m.obj = Objective(expr=m.x + m.y, sense=minimize)
        m.con1 = Constraint(expr=m.x + m.y >= 10)
        
        # Solve
        for solver_name in ['glpk', 'cbc', 'gurobi']:
            try:
                opt = SolverFactory(solver_name)
                if opt is not None and opt.available():
                    results = opt.solve(m, tee=False)
                    if results.solver.termination_condition == TerminationCondition.optimal:
                        print(f"  ✓ Simple solve with {solver_name}: x={value(m.x)}, y={value(m.y)}")
                        break
            except:
                continue
        else:
            print("  ✗ Could not solve simple model")
    except Exception as e:
        print(f"  ✗ Simple solve FAILED: {e}")
        traceback.print_exc()

# ============================================================================
# TEST 6: Import MILP model
# ============================================================================
print("\n[TEST 6] Import bvNexusMILP_DR...")

# Add parent directory to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.optimization.milp_model_dr import bvNexusMILP_DR
    print("  ✓ bvNexusMILP_DR imported successfully")
except ImportError as e:
    print(f"  ✗ Import FAILED: {e}")
    print("\n  Full traceback:")
    traceback.print_exc()
    print("\n  → Check that app/optimization/milp_model_dr.py exists and has no syntax errors")
except Exception as e:
    print(f"  ✗ Import error: {e}")
    traceback.print_exc()

# ============================================================================
# TEST 7: Build and solve MILP model
# ============================================================================
print("\n[TEST 7] Build and solve full MILP model...")

try:
    from app.optimization.milp_model_dr import bvNexusMILP_DR
    
    # Generate test data
    if np is not None:
        np.random.seed(42)
        base_load = 160 * 0.75 * 1.25  # 160 MW IT, 75% LF, 1.25 PUE
        load_8760 = base_load * (1 + 0.1 * np.sin(2 * np.pi * np.arange(8760) / 24))
        load_8760 = np.maximum(load_8760, base_load * 0.5).tolist()
    else:
        import math
        base_load = 160 * 0.75 * 1.25
        load_8760 = [base_load * (1 + 0.1 * math.sin(2 * 3.14159 * h / 24)) for h in range(8760)]
    
    print(f"  Load profile: {len(load_8760)} hours, base={base_load:.1f} MW")
    
    # Build model
    optimizer = bvNexusMILP_DR()
    
    print("  Building model...")
    optimizer.build(
        site={'name': 'Test'},
        constraints={
            'NOx_Limit_tpy': 100,
            'Gas_Supply_MCF_day': 50000,
            'Available_Land_Acres': 500,
        },
        load_data={
            'total_load_mw': load_8760,
            'pue': 1.25,
        },
        workload_mix={
            'pre_training': 0.30,
            'fine_tuning': 0.20,
            'batch_inference': 0.30,
            'realtime_inference': 0.20,
        },
        years=list(range(2026, 2031)),  # Shorter horizon for faster test
        grid_config={'available_year': 2030},
    )
    print("  ✓ Model built")
    
    # Solve
    print("  Solving (this may take 30-60 seconds)...")
    solution = optimizer.solve(solver='glpk', time_limit=120, verbose=False)
    
    print(f"  Status: {solution.get('status')}")
    print(f"  Termination: {solution.get('termination')}")
    
    if solution.get('termination') in ['optimal', 'feasible']:
        print(f"  ✓ SOLVE SUCCESSFUL!")
        print(f"  LCOE: ${solution.get('objective_lcoe', 0):.2f}/MWh")
        
        # Print equipment for 2030
        eq = solution.get('equipment', {}).get(2030, {})
        print(f"  Equipment (2030): {eq.get('n_recip', 0)} recips, {eq.get('n_turbine', 0)} turbines")
        
        cov = solution.get('power_coverage', {}).get(2030, {})
        print(f"  Coverage (2030): {cov.get('coverage_pct', 0):.1f}%")
    else:
        print(f"  ✗ Solve failed: {solution.get('termination')}")
        
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    print("\n  Full traceback:")
    traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("DIAGNOSTIC SUMMARY")
print("="*70)

print("""
If all tests passed:
  → The MILP system is working. Check your Streamlit integration.

If TEST 4 failed (no solver):
  → Install GLPK: brew install glpk (mac) or apt install glpk-utils (linux)

If TEST 6 failed (import error):
  → Check app/optimization/milp_model_dr.py for syntax errors
  → Run: python -m py_compile app/optimization/milp_model_dr.py

If TEST 7 failed (solve error):
  → Share the error message for diagnosis
""")
