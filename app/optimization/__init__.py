"""
bvNexus Optimization Module

Mixed-Integer Linear Programming (MILP) for AI datacenter power optimization
with integrated demand response capabilities.

Phase 1: Heuristic optimization for rapid screening
Phase 2: MILP optimization for detailed design

Version: 2.1.1 - Greenfield Heuristic Optimizer with gspread backend integration
"""

# Phase 2: MILP Optimization
from .milp_model_dr import bvNexusMILP_DR

# Phase 1 - NEW: Greenfield Heuristic v2.1.1 (production-ready)
from .greenfield_heuristic_v2 import (
    GreenfieldHeuristicV2,
    HeuristicResultV2,
    ConstraintResult,
    DispatchResult,
    BackendDataLoader,
    # Locked calculation functions (governed by GREENFIELD_HEURISTIC_RULES.md)
    calculate_nox_annual_tpy,
    calculate_gas_consumption_mcf_day,
    calculate_capital_recovery_factor,
    calculate_lcoe,
    calculate_firm_capacity,
    calculate_ramp_capacity,
)

# Phase 1 - LEGACY: Original heuristic optimizers (maintained for backward compatibility)
from .heuristic_optimizer import (
    HeuristicOptimizer,
    HeuristicResult,
    GreenFieldHeuristic as GreenFieldHeuristic_Legacy,
    BrownfieldHeuristic,
    LandDevHeuristic,
    GridServicesHeuristic,
    BridgePowerHeuristic,
    create_heuristic_optimizer,
)

# Backward compatibility: Map old name to new optimizer
GreenFieldHeuristic = GreenfieldHeuristicV2

__all__ = [
    # MILP
    'bvNexusMILP_DR',
    # Greenfield v2.1.1 (NEW - production)
    'GreenfieldHeuristicV2',
    'HeuristicResultV2',
    'ConstraintResult',
    'DispatchResult',
    'BackendDataLoader',
    'calculate_nox_annual_tpy',
    'calculate_gas_consumption_mcf_day',
    'calculate_capital_recovery_factor',
    'calculate_lcoe',
    'calculate_firm_capacity',
    'calculate_ramp_capacity',
    # Legacy Heuristics (backward compatibility)
    'HeuristicOptimizer',
    'HeuristicResult',
    'GreenFieldHeuristic',  # Now points to GreenfieldHeuristicV2
    'GreenFieldHeuristic_Legacy',  # Original implementation
    'BrownfieldHeuristic',
    'LandDevHeuristic',
    'GridServicesHeuristic',
    'BridgePowerHeuristic',
    'create_heuristic_optimizer',
]

__version__ = '2.1.1'
