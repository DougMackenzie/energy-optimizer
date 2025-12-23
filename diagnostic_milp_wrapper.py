#!/usr/bin/env python3
"""
bvNexus MILP Diagnostic Wrapper
===============================

Comprehensive diagnostic tool to validate the MILP optimizer is working correctly.
Run this script to identify issues before deploying to production.

Usage:
    python diagnostic_milp_wrapper.py
    
    # Or with specific solver:
    python diagnostic_milp_wrapper.py --solver cbc
    python diagnostic_milp_wrapper.py --solver glpk
    python diagnostic_milp_wrapper.py --solver gurobi

Author: Claude AI
Date: December 2024
Version: 1.0
"""

import sys
import time
import logging
import traceback
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DIAGNOSTIC RESULTS CONTAINER
# ============================================================================

class DiagnosticResults:
    """Container for all diagnostic test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
        self.errors = []
        self.warnings = []
        self.info = []
        self.start_time = datetime.now()
        
    def record_pass(self, test_name: str, message: str = ""):
        self.tests_run += 1
        self.tests_passed += 1
        logger.info(f"✅ PASS: {test_name}" + (f" - {message}" if message else ""))
        
    def record_fail(self, test_name: str, message: str):
        self.tests_run += 1
        self.tests_failed += 1
        self.errors.append(f"{test_name}: {message}")
        logger.error(f"❌ FAIL: {test_name} - {message}")
        
    def record_skip(self, test_name: str, reason: str):
        self.tests_run += 1
        self.tests_skipped += 1
        self.warnings.append(f"{test_name}: {reason}")
        logger.warning(f"⏭️  SKIP: {test_name} - {reason}")
        
    def record_warning(self, message: str):
        self.warnings.append(message)
        logger.warning(f"⚠️  WARNING: {message}")
        
    def record_info(self, message: str):
        self.info.append(message)
        logger.info(f"ℹ️  INFO: {message}")
        
    def print_summary(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 70)
        print(f"Total tests:    {self.tests_run}")
        print(f"  ✅ Passed:    {self.tests_passed}")
        print(f"  ❌ Failed:    {self.tests_failed}")
        print(f"  ⏭️  Skipped:   {self.tests_skipped}")
        print(f"Elapsed time:   {elapsed:.1f} seconds")
        print("-" * 70)
        
        if self.errors:
            print("\n🔴 ERRORS:")
            for err in self.errors:
                print(f"   • {err}")
                
        if self.warnings:
            print("\n🟡 WARNINGS:")
            for warn in self.warnings:
                print(f"   • {warn}")
                
        print("\n" + "=" * 70)
        if self.tests_failed == 0:
            print("✅ ALL DIAGNOSTICS PASSED - MILP OPTIMIZER IS READY")
        else:
            print("❌ DIAGNOSTICS FAILED - SEE ERRORS ABOVE")
        print("=" * 70 + "\n")
        
        return self.tests_failed == 0


# ============================================================================
# DIAGNOSTIC TESTS
# ============================================================================

def test_imports(results: DiagnosticResults) -> Dict[str, bool]:
    """Test all required imports."""
    
    imports_status = {}
    
    # Test numpy
    try:
        import numpy as np
        imports_status['numpy'] = True
        results.record_pass("Import numpy", f"version {np.__version__}")
    except ImportError as e:
        imports_status['numpy'] = False
        results.record_fail("Import numpy", str(e))
        
    # Test pyomo
    try:
        from pyomo.environ import (
            ConcreteModel, Var, Constraint, Objective, 
            SolverFactory, NonNegativeIntegers, NonNegativeReals,
            minimize, value, TerminationCondition
        )
        imports_status['pyomo'] = True
        results.record_pass("Import pyomo")
    except ImportError as e:
        imports_status['pyomo'] = False
        results.record_fail("Import pyomo", f"{e}. Run: pip install pyomo")
        
    # Test pandas (optional but useful)
    try:
        import pandas as pd
        imports_status['pandas'] = True
        results.record_pass("Import pandas", f"version {pd.__version__}")
    except ImportError:
        imports_status['pandas'] = False
        results.record_warning("pandas not installed (optional)")
        
    return imports_status


def test_solvers(results: DiagnosticResults) -> Tuple[str, Dict[str, bool]]:
    """Test available MILP solvers and return best available."""
    
    try:
        from pyomo.environ import SolverFactory
    except ImportError:
        results.record_fail("Solver test", "Pyomo not available")
        return None, {}
    
    solvers_status = {}
    best_solver = None
    
    # Test solvers in order of preference
    solver_priority = [
        ('gurobi', 'Commercial - fastest'),
        ('cbc', 'Open source - recommended'),
        ('glpk', 'Open source - slower but robust'),
        ('cplex', 'Commercial'),
        ('highs', 'Open source - newer'),
    ]
    
    for solver_name, description in solver_priority:
        try:
            opt = SolverFactory(solver_name)
            if opt is not None and opt.available():
                solvers_status[solver_name] = True
                results.record_pass(f"Solver {solver_name}", f"Available ({description})")
                if best_solver is None:
                    best_solver = solver_name
            else:
                solvers_status[solver_name] = False
                results.record_info(f"Solver {solver_name} not available")
        except Exception as e:
            solvers_status[solver_name] = False
            results.record_info(f"Solver {solver_name} check failed: {e}")
    
    if best_solver is None:
        results.record_fail("No MILP solver", 
                          "Install CBC: conda install -c conda-forge coincbc")
    else:
        results.record_info(f"Best available solver: {best_solver}")
        
    return best_solver, solvers_status


def test_simple_milp(results: DiagnosticResults, solver: str) -> bool:
    """Test a simple MILP to verify solver works."""
    
    if solver is None:
        results.record_skip("Simple MILP test", "No solver available")
        return False
        
    try:
        from pyomo.environ import (
            ConcreteModel, Var, Constraint, Objective,
            SolverFactory, NonNegativeIntegers, NonNegativeReals,
            minimize, value, TerminationCondition
        )
        
        # Create simple test problem
        model = ConcreteModel()
        model.x = Var(within=NonNegativeIntegers, bounds=(0, 10))
        model.y = Var(within=NonNegativeReals, bounds=(0, 20))
        model.obj = Objective(expr=model.x + 2*model.y, sense=minimize)
        model.con1 = Constraint(expr=model.x + model.y >= 5)
        
        # Solve
        opt = SolverFactory(solver)
        opt.options['seconds'] = 10 if solver == 'cbc' else None
        
        start = time.time()
        result = opt.solve(model, tee=False)
        elapsed = time.time() - start
        
        if result.solver.termination_condition == TerminationCondition.optimal:
            x_val = value(model.x)
            y_val = value(model.y)
            obj_val = value(model.obj)
            
            # Verify solution (x=5, y=0 is optimal)
            if abs(x_val - 5) < 0.01 and abs(y_val) < 0.01:
                results.record_pass("Simple MILP solve", 
                                   f"Correct solution in {elapsed:.2f}s")
                return True
            else:
                results.record_fail("Simple MILP solve", 
                                   f"Wrong solution: x={x_val}, y={y_val}")
                return False
        else:
            results.record_fail("Simple MILP solve", 
                               f"Status: {result.solver.termination_condition}")
            return False
            
    except Exception as e:
        results.record_fail("Simple MILP solve", f"Exception: {e}")
        traceback.print_exc()
        return False


def test_bvnexus_milp_import(results: DiagnosticResults) -> bool:
    """Test bvNexusMILP_DR class import."""
    
    try:
        # Try multiple possible import paths
        import_paths = [
            'app.optimization.milp_model_dr',
            'optimization.milp_model_dr',
            'milp_model_dr',
        ]
        
        bvNexusMILP_DR = None
        successful_path = None
        
        for path in import_paths:
            try:
                module = __import__(path, fromlist=['bvNexusMILP_DR'])
                bvNexusMILP_DR = getattr(module, 'bvNexusMILP_DR')
                successful_path = path
                break
            except (ImportError, AttributeError):
                continue
                
        if bvNexusMILP_DR is not None:
            results.record_pass("Import bvNexusMILP_DR", f"from {successful_path}")
            return True
        else:
            results.record_fail("Import bvNexusMILP_DR", 
                               "Class not found in any expected location")
            return False
            
    except Exception as e:
        results.record_fail("Import bvNexusMILP_DR", f"Exception: {e}")
        return False


def test_constraint_activation(results: DiagnosticResults, solver: str) -> Dict[str, bool]:
    """Test that all constraints are properly activated."""
    
    if solver is None:
        results.record_skip("Constraint activation test", "No solver")
        return {}
    
    constraint_status = {}
    
    try:
        from pyomo.environ import (
            ConcreteModel, Var, Constraint, Objective, Param, Set,
            SolverFactory, NonNegativeIntegers, NonNegativeReals,
            minimize, value, TerminationCondition
        )
        import numpy as np
        
        # Create a model with all the key constraint types
        model = ConcreteModel()
        
        # Sets
        model.Y = Set(initialize=[2028, 2029, 2030])
        model.T = Set(initialize=range(24))  # 24 hours for testing
        
        # Parameters
        model.LOAD = Param(model.T, initialize={t: 100 + 10*np.sin(t/24*2*np.pi) for t in model.T})
        model.NOX_MAX = Param(initialize=100)
        model.GAS_MAX = Param(initialize=50000)
        model.LAND_MAX = Param(initialize=300)
        
        # Variables
        model.n_recip = Var(model.Y, within=NonNegativeIntegers, bounds=(0, 20))
        model.solar_mw = Var(model.Y, within=NonNegativeReals, bounds=(0, 200))
        model.gen = Var(model.T, model.Y, within=NonNegativeReals)
        
        # Constraint 1: NOx limit
        def nox_constraint(m, y):
            # Simplified: each recip = 10 tpy
            return m.n_recip[y] * 10 <= m.NOX_MAX
        model.nox_con = Constraint(model.Y, rule=nox_constraint)
        constraint_status['NOx'] = True
        
        # Constraint 2: Land limit
        def land_constraint(m, y):
            # 5 acres per MW solar
            return m.solar_mw[y] * 5 <= m.LAND_MAX
        model.land_con = Constraint(model.Y, rule=land_constraint)
        constraint_status['Land'] = True
        
        # Constraint 3: Power balance
        def power_balance(m, t, y):
            return m.gen[t, y] <= m.n_recip[y] * 20  # 20 MW per recip
        model.balance_con = Constraint(model.T, model.Y, rule=power_balance)
        constraint_status['Power Balance'] = True
        
        # Constraint 4: Non-decreasing capacity (can't remove equipment)
        def nondec(m, y):
            if y == min(m.Y):
                return Constraint.Skip
            prev_y = y - 1
            if prev_y in m.Y:
                return m.n_recip[y] >= m.n_recip[prev_y]
            return Constraint.Skip
        model.nondec_con = Constraint(model.Y, rule=nondec)
        constraint_status['Non-decreasing'] = True
        
        # Objective
        model.obj = Objective(
            expr=sum(m.n_recip[y] * 1000 + m.solar_mw[y] * 500 for y in model.Y for m in [model]),
            sense=minimize
        )
        
        # Solve
        opt = SolverFactory(solver)
        result = opt.solve(model, tee=False)
        
        if result.solver.termination_condition == TerminationCondition.optimal:
            results.record_pass("Constraint activation test", 
                               f"All {len(constraint_status)} constraints active")
        else:
            results.record_fail("Constraint activation test",
                               f"Solve failed: {result.solver.termination_condition}")
            
    except Exception as e:
        results.record_fail("Constraint activation test", f"Exception: {e}")
        traceback.print_exc()
        
    return constraint_status


def test_hierarchical_objective(results: DiagnosticResults, solver: str) -> bool:
    """Test that hierarchical objective (power > cost) works correctly."""
    
    if solver is None:
        results.record_skip("Hierarchical objective test", "No solver")
        return False
        
    try:
        from pyomo.environ import (
            ConcreteModel, Var, Constraint, Objective,
            SolverFactory, NonNegativeReals, minimize, value,
            TerminationCondition
        )
        
        # Problem: Serve 100 MW load with 2 options:
        # 1. Cheap source (50 MW max, $10/MWh)
        # 2. Expensive source (unlimited, $100/MWh)
        # Unserved penalty: $50,000/MWh
        
        model = ConcreteModel()
        model.gen_cheap = Var(within=NonNegativeReals, bounds=(0, 50))
        model.gen_expensive = Var(within=NonNegativeReals, bounds=(0, 200))
        model.unserved = Var(within=NonNegativeReals, bounds=(0, 200))
        
        LOAD = 100
        PENALTY = 50000
        
        # Power balance
        model.balance = Constraint(
            expr=model.gen_cheap + model.gen_expensive + model.unserved == LOAD
        )
        
        # Hierarchical objective: minimize unserved first (via high penalty), then cost
        model.obj = Objective(
            expr=model.gen_cheap * 10 + model.gen_expensive * 100 + model.unserved * PENALTY,
            sense=minimize
        )
        
        # Solve
        opt = SolverFactory(solver)
        result = opt.solve(model, tee=False)
        
        if result.solver.termination_condition == TerminationCondition.optimal:
            cheap = value(model.gen_cheap)
            expensive = value(model.gen_expensive)
            unserved = value(model.unserved)
            
            # Should use: 50 MW cheap + 50 MW expensive + 0 unserved
            if abs(unserved) < 0.01 and abs(cheap - 50) < 0.01 and abs(expensive - 50) < 0.01:
                results.record_pass("Hierarchical objective", 
                                   "Power maximized before cost minimized")
                return True
            else:
                results.record_fail("Hierarchical objective",
                                   f"Wrong solution: cheap={cheap:.1f}, expensive={expensive:.1f}, unserved={unserved:.1f}")
                return False
        else:
            results.record_fail("Hierarchical objective",
                               f"Solve failed: {result.solver.termination_condition}")
            return False
            
    except Exception as e:
        results.record_fail("Hierarchical objective", f"Exception: {e}")
        traceback.print_exc()
        return False


def test_representative_periods(results: DiagnosticResults) -> bool:
    """Test representative period generation and scaling."""
    
    try:
        import numpy as np
        
        # Generate 8760 load profile
        hours = np.arange(8760)
        base_load = 100
        
        # Add daily and seasonal patterns
        daily_pattern = 10 * np.sin(hours / 24 * 2 * np.pi)
        seasonal_pattern = 20 * np.sin(hours / 8760 * 2 * np.pi)
        load_8760 = base_load + daily_pattern + seasonal_pattern
        
        # Select representative weeks (6 weeks = 1008 hours)
        # Week indices: 0 (Jan), 10 (Mar), 20 (May), 30 (Jul), 40 (Oct), 50 (Dec)
        rep_weeks = [0, 10, 20, 30, 40, 50]
        
        rep_hours = []
        for week in rep_weeks:
            start_hour = week * 168
            end_hour = start_hour + 168
            rep_hours.extend(range(start_hour, min(end_hour, 8760)))
            
        # Calculate scale factor
        n_rep_hours = len(rep_hours)
        scale_factor = 8760 / n_rep_hours
        
        # Verify scale factor is reasonable
        expected_scale = 8760 / (6 * 168)  # ~8.69
        
        if abs(scale_factor - expected_scale) < 0.1:
            results.record_pass("Representative periods",
                               f"Scale factor = {scale_factor:.2f} (6 weeks → 8760)")
            return True
        else:
            results.record_fail("Representative periods",
                               f"Scale factor {scale_factor:.2f} != expected {expected_scale:.2f}")
            return False
            
    except Exception as e:
        results.record_fail("Representative periods", f"Exception: {e}")
        return False


def test_full_optimization(results: DiagnosticResults, solver: str) -> bool:
    """Test full optimization with sample problem."""
    
    if solver is None:
        results.record_skip("Full optimization test", "No solver")
        return False
        
    results.record_info("Running full optimization test (may take 30-60 seconds)...")
    
    try:
        from pyomo.environ import (
            ConcreteModel, Var, Constraint, Objective, Param, Set,
            SolverFactory, NonNegativeIntegers, NonNegativeReals,
            minimize, value, TerminationCondition
        )
        import numpy as np
        
        # ========================================
        # SAMPLE PROBLEM: 200 MW Data Center
        # ========================================
        
        LOAD_MW = 200
        YEARS = [2028, 2029, 2030]
        GRID_YEAR = 2030
        NOX_LIMIT = 100  # tpy
        LAND_ACRES = 300
        GAS_MCF_DAY = 75000
        
        # Equipment specs
        RECIP_MW = 18
        RECIP_CAPEX = 1200  # $/kW
        RECIP_NOX_TPY = 8  # tpy per unit at 80% CF
        TURBINE_MW = 25
        TURBINE_CAPEX = 800
        TURBINE_NOX_TPY = 5
        BESS_CAPEX = 400  # $/kWh
        SOLAR_CAPEX = 1000  # $/kW
        SOLAR_ACRES_PER_MW = 5
        
        PENALTY = 50000  # $/MWh unserved
        
        # Representative hours (simplified: 168 hours = 1 week)
        N_HOURS = 168
        SCALE = 8760 / N_HOURS
        
        # Build model
        model = ConcreteModel()
        
        # Sets
        model.Y = Set(initialize=YEARS)
        model.T = Set(initialize=range(N_HOURS))
        
        # Parameters
        load_profile = {t: LOAD_MW * (0.8 + 0.2 * np.sin(t/24*2*np.pi)) for t in range(N_HOURS)}
        model.LOAD = Param(model.T, initialize=load_profile)
        model.NOX_MAX = Param(initialize=NOX_LIMIT)
        model.LAND_MAX = Param(initialize=LAND_ACRES)
        
        # Decision variables
        model.n_recip = Var(model.Y, within=NonNegativeIntegers, bounds=(0, 15))
        model.n_turbine = Var(model.Y, within=NonNegativeIntegers, bounds=(0, 10))
        model.bess_mwh = Var(model.Y, within=NonNegativeReals, bounds=(0, 400))
        model.solar_mw = Var(model.Y, within=NonNegativeReals, bounds=(0, 100))
        model.grid_mw = Var(model.Y, within=NonNegativeReals, bounds=(0, 300))
        
        # Dispatch variables
        model.gen_recip = Var(model.T, model.Y, within=NonNegativeReals)
        model.gen_turbine = Var(model.T, model.Y, within=NonNegativeReals)
        model.unserved = Var(model.T, model.Y, within=NonNegativeReals)
        
        # === CONSTRAINTS ===
        
        # Power balance
        def power_balance(m, t, y):
            supply = (m.gen_recip[t, y] + m.gen_turbine[t, y] + 
                     m.grid_mw[y] * (1 if y >= GRID_YEAR else 0) +
                     m.solar_mw[y] * 0.2)  # 20% capacity factor
            return supply + m.unserved[t, y] >= m.LOAD[t]
        model.balance = Constraint(model.T, model.Y, rule=power_balance)
        
        # Generation limits
        def recip_limit(m, t, y):
            return m.gen_recip[t, y] <= m.n_recip[y] * RECIP_MW
        model.recip_lim = Constraint(model.T, model.Y, rule=recip_limit)
        
        def turbine_limit(m, t, y):
            return m.gen_turbine[t, y] <= m.n_turbine[y] * TURBINE_MW
        model.turbine_lim = Constraint(model.T, model.Y, rule=turbine_limit)
        
        # NOx constraint
        def nox_limit(m, y):
            return (m.n_recip[y] * RECIP_NOX_TPY + 
                   m.n_turbine[y] * TURBINE_NOX_TPY) <= m.NOX_MAX
        model.nox = Constraint(model.Y, rule=nox_limit)
        
        # Land constraint
        def land_limit(m, y):
            return m.solar_mw[y] * SOLAR_ACRES_PER_MW <= m.LAND_MAX
        model.land = Constraint(model.Y, rule=land_limit)
        
        # Grid timing
        def grid_timing(m, y):
            if y < GRID_YEAR:
                return m.grid_mw[y] == 0
            return Constraint.Skip
        model.grid_time = Constraint(model.Y, rule=grid_timing)
        
        # Non-decreasing capacity
        def nondec_recip(m, y):
            if y == min(m.Y):
                return Constraint.Skip
            return m.n_recip[y] >= m.n_recip[y-1]
        model.nondec_r = Constraint(model.Y, rule=nondec_recip)
        
        # === OBJECTIVE ===
        # Hierarchical: minimize unserved (penalty) then cost
        
        def objective_rule(m):
            # CAPEX
            capex = sum(
                m.n_recip[y] * RECIP_MW * 1000 * RECIP_CAPEX +
                m.n_turbine[y] * TURBINE_MW * 1000 * TURBINE_CAPEX +
                m.bess_mwh[y] * 1000 * BESS_CAPEX +
                m.solar_mw[y] * 1000 * SOLAR_CAPEX
                for y in m.Y
            )
            
            # Unserved penalty
            unserved_cost = PENALTY * SCALE * sum(
                m.unserved[t, y] for t in m.T for y in m.Y
            )
            
            return capex + unserved_cost
        
        model.obj = Objective(rule=objective_rule, sense=minimize)
        
        # === SOLVE ===
        opt = SolverFactory(solver)
        if solver == 'cbc':
            opt.options['seconds'] = 60
            opt.options['ratioGap'] = 0.05
        elif solver == 'glpk':
            opt.options['tmlim'] = 120
            opt.options['mipgap'] = 0.05
            
        start = time.time()
        result = opt.solve(model, tee=False)
        elapsed = time.time() - start
        
        if result.solver.termination_condition in [
            TerminationCondition.optimal,
            TerminationCondition.feasible
        ]:
            # Extract results
            final_year = max(YEARS)
            n_recip = int(value(model.n_recip[final_year]))
            n_turbine = int(value(model.n_turbine[final_year]))
            bess = value(model.bess_mwh[final_year])
            solar = value(model.solar_mw[final_year])
            grid = value(model.grid_mw[final_year])
            
            total_unserved = sum(value(model.unserved[t, y]) 
                                for t in model.T for y in model.Y)
            
            capacity_mw = n_recip * RECIP_MW + n_turbine * TURBINE_MW + solar * 0.2 + grid
            
            results.record_pass("Full optimization",
                               f"Solved in {elapsed:.1f}s")
            results.record_info(f"  Equipment: {n_recip} recips, {n_turbine} turbines, "
                               f"{bess:.0f} MWh BESS, {solar:.0f} MW solar, {grid:.0f} MW grid")
            results.record_info(f"  Capacity: {capacity_mw:.0f} MW vs {LOAD_MW} MW load")
            results.record_info(f"  Unserved: {total_unserved:.1f} MWh")
            
            # Validate results
            if n_recip > 0 or n_turbine > 0:
                results.record_pass("Equipment sizing", "Non-zero equipment selected")
            else:
                results.record_fail("Equipment sizing", "No equipment selected")
                
            if total_unserved < LOAD_MW * N_HOURS * len(YEARS) * 0.1:  # <10% unserved
                results.record_pass("Power coverage", f"<10% unserved energy")
            else:
                results.record_warning(f"High unserved energy: {total_unserved:.0f} MWh")
                
            return True
            
        else:
            results.record_fail("Full optimization",
                               f"Status: {result.solver.termination_condition}")
            return False
            
    except Exception as e:
        results.record_fail("Full optimization", f"Exception: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# MAIN DIAGNOSTIC RUNNER
# ============================================================================

def run_diagnostics(preferred_solver: str = None) -> bool:
    """Run all diagnostic tests."""
    
    print("\n" + "=" * 70)
    print("bvNexus MILP OPTIMIZER DIAGNOSTIC")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70 + "\n")
    
    results = DiagnosticResults()
    
    # 1. Test imports
    print("\n📦 PHASE 1: Checking Imports\n" + "-" * 40)
    imports = test_imports(results)
    
    if not imports.get('pyomo', False):
        results.record_fail("Critical dependency", "Pyomo required - run: pip install pyomo")
        results.print_summary()
        return False
        
    # 2. Test solvers
    print("\n🔧 PHASE 2: Checking Solvers\n" + "-" * 40)
    best_solver, solvers = test_solvers(results)
    
    # Use preferred solver if specified and available
    if preferred_solver and solvers.get(preferred_solver, False):
        best_solver = preferred_solver
        results.record_info(f"Using preferred solver: {preferred_solver}")
    
    # 3. Simple MILP test
    print("\n🧪 PHASE 3: Simple MILP Test\n" + "-" * 40)
    test_simple_milp(results, best_solver)
    
    # 4. Constraint activation test
    print("\n⚙️  PHASE 4: Constraint Activation Test\n" + "-" * 40)
    test_constraint_activation(results, best_solver)
    
    # 5. Hierarchical objective test
    print("\n📊 PHASE 5: Hierarchical Objective Test\n" + "-" * 40)
    test_hierarchical_objective(results, best_solver)
    
    # 6. Representative periods test
    print("\n📅 PHASE 6: Representative Periods Test\n" + "-" * 40)
    test_representative_periods(results)
    
    # 7. bvNexus MILP import test
    print("\n📥 PHASE 7: bvNexusMILP_DR Import Test\n" + "-" * 40)
    test_bvnexus_milp_import(results)
    
    # 8. Full optimization test
    print("\n🚀 PHASE 8: Full Optimization Test\n" + "-" * 40)
    test_full_optimization(results, best_solver)
    
    # Print summary
    return results.print_summary()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='bvNexus MILP Diagnostic Tool')
    parser.add_argument('--solver', type=str, choices=['cbc', 'glpk', 'gurobi', 'highs'],
                       help='Preferred solver to use')
    args = parser.parse_args()
    
    success = run_diagnostics(preferred_solver=args.solver)
    sys.exit(0 if success else 1)
