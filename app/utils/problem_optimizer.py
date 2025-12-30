"""
Unified Problem Optimizer Interface

Provides a unified interface for running both Phase 1 (Heuristic) and Phase 2 (MILP)
optimizations for all 5 problem statements.
"""

from typing import Dict, Any, Optional
import streamlit as st
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.optimization import (
    GreenFieldHeuristic,
    BrownfieldHeuristic,
    LandDevHeuristic,
    GridServicesHeuristic,
    BridgePowerHeuristic,
    create_heuristic_optimizer,
)
from config.settings import PROBLEM_STATEMENTS


def run_problem_optimizer(
    problem_num: int,
    phase: int,
    site: Dict[str, Any],
    load_trajectory: Dict[int, float],
    constraints: Dict[str, Any],
    equipment_options: Optional[Dict] = None,
    economic_params: Optional[Dict] = None,
    **problem_specific_params
) -> Dict[str, Any]:
    """
    Run optimization for a specific problem type and phase.
    
    Args:
        problem_num: Problem number (1-5)
        phase: Optimization phase (1=Heuristic, 2=MILP)
        site: Site configuration dict
        load_trajectory: {year: load_mw} mapping
        constraints: Constraint limits
        equipment_options: Optional equipment selection
        economic_params: Optional economic parameters
        **problem_specific_params: Additional problem-specific parameters
    
    Returns:
        Dictionary with optimization results
    """
    
    if phase == 1:
        return _run_phase1_heuristic(
            problem_num=problem_num,
            site=site,
            load_trajectory=load_trajectory,
            constraints=constraints,
            equipment_options=equipment_options,
            economic_params=economic_params,
            **problem_specific_params
        )
    elif phase == 2:
        return _run_phase2_milp(
            problem_num=problem_num,
            site=site,
            load_trajectory=load_trajectory,
            constraints=constraints,
            equipment_options=equipment_options,
            economic_params=economic_params,
            **problem_specific_params
        )
    else:
        raise ValueError(f"Invalid phase: {phase}. Must be 1 or 2.")


def _run_phase1_heuristic(
    problem_num: int,
    site: Dict,
    load_trajectory: Dict[int, float],
    constraints: Dict,
    equipment_options: Optional[Dict] = None,
    economic_params: Optional[Dict] = None,
    **problem_specific_params
) -> Dict[str, Any]:
    """Run Phase 1 heuristic optimization"""
    
    # Create appropriate optimizer
    optimizer = create_heuristic_optimizer(
        problem_type=problem_num,
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints,
        equipment_options=equipment_options,
        economic_params=economic_params,
        **problem_specific_params
    )
    
    # Run optimization
    result = optimizer.optimize()
    
    # Format for unified return
    return {
        'phase': 1,
        'problem_num': problem_num,
        'result': result,
        'lcoe': result.lcoe if hasattr(result, 'lcoe') else None,
        'capex': result.capex_total,
        'opex': result.opex_annual,
        'equipment': result.equipment_config,
        'dispatch_summary': result.dispatch_summary,
        'feasible': result.feasible,
        'timeline': result.timeline_months,
        'constraints': result.constraint_status,
        'violations': result.violations,
        'solve_time': result.solve_time_seconds,
        'objective_value': result.objective_value,
    }


def _run_phase2_milp(
    problem_num: int,
    site: Dict,
    load_trajectory: Dict[int, float],
    constraints: Dict,
    equipment_options: Optional[Dict] = None,
    economic_params: Optional[Dict] = None,
    **problem_specific_params
) -> Dict[str, Any]:
    """
    Run Phase 2 MILP optimization
    
    This integrates with the existing MILP wrapper to run detailed optimization.
    """
    
    # Import MILP wrapper
    try:
        from app.utils.milp_optimizer_wrapper_fast import run_milp_optimization
    except ImportError:
        raise ImportError("MILP optimizer not available. Check installation.")
    
    # Prepare inputs for MILP
    milp_inputs = prepare_milp_inputs(
        problem_num=problem_num,
        site=site,
        load_trajectory=load_trajectory,
        constraints=constraints,
        equipment_options=equipment_options,
        economic_params=economic_params,
        **problem_specific_params
    )
    
    # Run MILP optimization
    milp_result = run_milp_optimization(**milp_inputs)
    
    # Format for unified return
    return format_milp_results(milp_result, problem_num)


def prepare_milp_inputs(
    problem_num: int,
    site: Dict,
    load_trajectory: Dict[int, float],
    constraints: Dict,
    equipment_options: Optional[Dict] = None,
    economic_params: Optional[Dict] = None,
    **problem_specific_params
) -> Dict[str, Any]:
    """
    Prepare inputs for MILP optimization based on problem type.
    
    Translates problem-specific parameters to MILP format.
    """
    
    # Get peak load
    peak_load = max(load_trajectory.values())
    
    # Base MILP inputs
    milp_inputs = {
        'it_capacity_mw': peak_load,
        'pue': site.get('PUE', 1.25),
        'constraints': constraints,
        'use_fast_milp': True,
    }
    
    # === DEBUG LOGGING ===
    import logging
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info(f"🐛 DEBUG: Problem {problem_num} - Preparing MILP Inputs")
    logger.info("="*80)
    logger.info(f"Peak load from trajectory: {peak_load} MW")
    logger.info(f"Load trajectory: {load_trajectory}")
    logger.info(f"Constraints dict: {constraints}")
    logger.info(f"Constraints keys: {list(constraints.keys())}")
    logger.info("="*80)
    
    # Problem-specific adjustments
    if problem_num == 1:
        # Greenfield: minimize LCOE
        milp_inputs['objective'] = 'minimize_lcoe'
        
    elif problem_num == 2:
        # Brownfield: maximize load
        milp_inputs['objective'] = 'maximize_load'
        lcoe_ceiling = problem_specific_params.get('lcoe_ceiling', 80.0)
        milp_inputs['lcoe_ceiling'] = lcoe_ceiling
        
    elif problem_num == 3:
        # Land Dev: maximize power
        milp_inputs['objective'] = 'maximize_power'
        
    elif problem_num == 4:
        # Grid Services: maximize DR revenue
        milp_inputs['objective'] = 'maximize_dr_revenue'
        workload_mix = problem_specific_params.get('workload_mix', {})
        milp_inputs['workload_mix'] = workload_mix
        
    elif problem_num == 5:
        # Bridge Power: minimize NPV
        milp_inputs['objective'] = 'minimize_npv'
        grid_available_month = problem_specific_params.get('grid_available_month', 60)
        milp_inputs['grid_available_month'] = grid_available_month
    
    return milp_inputs


def format_milp_results(milp_result: Dict[str, Any], problem_num: int) -> Dict[str, Any]:
    """
    Format MILP results to unified format matching heuristic output.
    """
    
    return {
        'phase': 2,
        'problem_num': problem_num,
        'result': milp_result,
        'lcoe': milp_result.get('lcoe_mwh'),
        'capex': milp_result.get('capex_total', 0),
        'opex': milp_result.get('opex_annual', 0),
        'equipment': milp_result.get('equipment_config', {}),
        'dispatch_summary': milp_result.get('dispatch_summary', {}),
        'feasible': milp_result.get('solver_status') == 'optimal',
        'timeline': milp_result.get('timeline_months', 0),
        'constraints': milp_result.get('constraint_status', {}),
        'violations': milp_result.get('violations', []),
        'solve_time': milp_result.get('solve_time_seconds', 0),
        'objective_value': milp_result.get('objective_value'),
    }


def compare_phase_results(phase1_result: Dict, phase2_result: Dict) -> Dict[str, Any]:
    """
    Compare Phase 1 and Phase 2 results for the same problem.
    
    Returns comparison metrics and deltas.
    """
    
    comparison = {
        'lcoe_delta_pct': _calc_delta_pct(
            phase1_result.get('lcoe'),
            phase2_result.get('lcoe')
        ),
        'capex_delta_pct': _calc_delta_pct(
            phase1_result.get('capex'),
            phase2_result.get('capex')
        ),
        'solve_time_ratio': (
            phase2_result.get('solve_time', 0) / 
            max(phase1_result.get('solve_time', 1), 0.1)
        ),
        'accuracy_improvement': 'Class 5 → Class 3',
        'phase1_summary': {
            'lcoe': phase1_result.get('lcoe'),
            'time': phase1_result.get('solve_time'),
            'feasible': phase1_result.get('feasible'),
        },
        'phase2_summary': {
            'lcoe': phase2_result.get('lcoe'),
            'time': phase2_result.get('solve_time'),
            'feasible': phase2_result.get('feasible'),
        }
    }
    
    return comparison


def _calc_delta_pct(val1: Optional[float], val2: Optional[float]) -> Optional[float]:
    """Calculate percentage delta between two values"""
    if val1 is None or val2 is None or val1 == 0:
        return None
    return ((val2 - val1) / val1) * 100


def get_problem_info(problem_num: int) -> Dict[str, str]:
    """Get problem statement information"""
    return PROBLEM_STATEMENTS.get(problem_num, {})
