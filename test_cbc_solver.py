#!/usr/bin/env python3
"""
Test CBC Solver Installation
Verifies CBC is available and working for MILP optimization
"""

print("=" * 60)
print("CBC SOLVER VERIFICATION TEST")
print("=" * 60)

# Test 1: Check Pyomo
print("\n[1/4] Checking Pyomo installation...")
try:
    from pyomo.environ import *
    print("  ✓ Pyomo imported successfully")
except ImportError as e:
    print(f"  ✗ Pyomo import failed: {e}")
    exit(1)

# Test 2: Check CBC availability
print("\n[2/4] Checking CBC solver...")
try:
    opt = SolverFactory('cbc')
    if opt is None:
        print("  ✗ CBC solver not found (SolverFactory returned None)")
        exit(1)
    
    if not opt.available():
        print("  ✗ CBC solver not available")
        print("  Install: conda install -c conda-forge coincbc")
        exit(1)
    
    print("  ✓ CBC solver is available!")
except Exception as e:
    print(f"  ✗ CBC check failed: {e}")
    exit(1)

# Test 3: Check GLPK (fallback)
print("\n[3/4] Checking GLPK solver (fallback)...")
try:
    opt_glpk = SolverFactory('glpk')
    if opt_glpk and opt_glpk.available():
        print("  ✓ GLPK solver is available (fallback)")
    else:
        print("  ⚠ GLPK not available (not critical if CBC works)")
except:
    print("  ⚠ GLPK check failed (not critical if CBC works)")

# Test 4: Solve simple MILP
print("\n[4/4] Testing CBC with simple MILP problem...")
try:
    # Create tiny test problem
    model = ConcreteModel()
    model.x = Var(within=NonNegativeIntegers, bounds=(0, 10))
    model.y = Var(within=NonNegativeReals, bounds=(0, 20))
    
    model.obj = Objective(expr=model.x + 2*model.y, sense=minimize)
    model.con1 = Constraint(expr=model.x + model.y >= 5)
    
    # Solve
    opt = SolverFactory('cbc')
    opt.options['seconds'] = 10
    opt.options['ratioGap'] = 0.05
    
    results = opt.solve(model, tee=False)
    
    # Check solution
    if results.solver.termination_condition == TerminationCondition.optimal:
        x_val = value(model.x)
        y_val = value(model.y)
        obj_val = value(model.obj)
        
        print(f"  ✓ CBC solved successfully!")
        print(f"    Solution: x={x_val}, y={y_val}, objective={obj_val:.2f}")
    else:
        print(f"  ✗ CBC solve failed: {results.solver.termination_condition}")
        exit(1)
        
except Exception as e:
    print(f"  ✗ Test solve failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Success!
print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - CBC IS READY!")
print("=" * 60)
print("\nYou can now use fast MILP optimization with CBC solver.")
print("Expected performance: 10x faster than GLPK")
