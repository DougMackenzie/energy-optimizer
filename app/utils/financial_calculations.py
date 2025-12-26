"""
Financial Calculations Module
NPV, IRR, payback period, and portfolio aggregations
"""

import numpy as np
from typing import Dict, List, Any

def calculate_site_financials(site: Dict, optimization_result: Dict) -> Dict:
    """
    Calculate financial metrics for a single site
    
    Args:
        site: Site configuration dict
        optimization_result: Optimization results dict
    
    Returns:
        Dict with financial metrics
    """
    # Extract data
    lcoe = optimization_result.get('lcoe', 0)
    npv_stored = optimization_result.get('npv', None)
    
    # Get equipment from results
    equipment = optimization_result.get('equipment', {})
    
    # Calculate CapEx from equipment costs
    capex_m = calculate_capex_from_equipment(equipment, site)
    
    # Calculate annual OpEx from equipment
    opex_annual_m = calculate_opex_from_equipment(equipment, site)
    
    # Use stored NPV if available, otherwise calculate
    if npv_stored and npv_stored != 0:
        npv_m = float(npv_stored) / 1_000_000  # Convert from $ to $M
    else:
        npv_m = calculate_npv(capex_m, opex_annual_m, lcoe, site.get('it_capacity_mw', 0))
    
    # Calculate IRR (improved method)
    irr_pct = calculate_irr_improved(capex_m, opex_annual_m, lcoe, site.get('it_capacity_mw', 0))
    
    # Calculate payback period
    payback_years = calculate_payback(capex_m, opex_annual_m, lcoe, site.get('it_capacity_mw', 0))
    
    return {
        'lcoe': lcoe,
        'capex_m': capex_m,
        'opex_annual_m': opex_annual_m,
        'npv_m': npv_m,
        'irr_pct': irr_pct,
        'payback_years': payback_years
    }


def calculate_capex_from_equipment(equipment: Dict, site: Dict) -> float:
    """
    Calculate total CapEx from equipment specifications
    
    Args:
        equipment: Equipment dict from optimization results
        site: Site configuration dict
    
    Returns:
        Total CapEx in millions
    """
    total_capex = 0.0
    
    # Equipment unit costs ($/kW) - rough estimates
    equipment_costs = {
        'recip': 1500,      # Reciprocating engine: $1,500/kW
        'turbine': 1200,    # Gas turbine: $1,200/kW
        'bess': 400,        # Battery storage: $400/kW
        'solar': 1000,      # Solar PV: $1,000/kW
        'wind': 1500,       # Wind: $1,500/kW
    }
    
    # Calculate from equipment JSON
    if equipment:
        for eq_type, capacity_mw in equipment.items():
            eq_key = eq_type.lower()
            if eq_key in equipment_costs:
                capacity_kw = capacity_mw * 1000
                cost_usd = capacity_kw * equipment_costs[eq_key]
                total_capex += cost_usd
    
    # If no equipment data, use rough estimate
    if total_capex == 0:
        it_capacity = site.get('it_capacity_mw', 0)
        total_capex = it_capacity * 1_500_000  # $1.5M per MW IT
    
    # Convert to millions
    capex_m = total_capex / 1_000_000
    
    return capex_m


def calculate_opex_from_equipment(equipment: Dict, site: Dict) -> float:
    """
    Calculate annual OpEx from equipment
    
    Args:
        equipment: Equipment dict from optimization results
        site: Site configuration dict
    
    Returns:
        Annual OpEx in millions
    """
    # OpEx components:
    # 1. Maintenance (% of CapEx)
    # 2. Fuel costs (already in LCOE)
    # 3. Labor
    # 4. Insurance
    
    # Simplified: 2.5-3.5% of CapEx as annual OpEx
    capex_m = calculate_capex_from_equipment(equipment, site)
    opex_annual_m = capex_m * 0.03  # 3% of CapEx
    
    return opex_annual_m


def calculate_npv(capex_m: float, opex_annual_m: float, lcoe: float, 
                  capacity_mw: float, discount_rate: float = 0.08, horizon_years: int = 20) -> float:
    """
    Calculate Net Present Value
    
    Args:
        capex_m: Capital expenditure in millions
        opex_annual_m: Annual operating expenditure in millions
        lcoe: Levelized cost of energy ($/MWh)
        capacity_mw: IT capacity in MW
        discount_rate: Discount rate (default 8%)
        horizon_years: Analysis horizon (default 20 years)
    
    Returns:
        NPV in millions
    """
    # Assume 8760 hours/year, 95% availability
    annual_mwh = capacity_mw * 8760 * 0.95
    
    # Annual revenue = LCOE * MWh (simplified)
    annual_revenue_m = (lcoe * annual_mwh) / 1_000_000
    
    # Calculate cash flows
    cash_flows = [-capex_m]  # Initial investment
    
    for year in range(1, horizon_years + 1):
        annual_cash_flow = annual_revenue_m - opex_annual_m
        discounted_cf = annual_cash_flow / ((1 + discount_rate) ** year)
        cash_flows.append(discounted_cf)
    
    npv = sum(cash_flows)
    return npv


def calculate_irr_improved(capex_m: float, opex_annual_m: float, lcoe: float, 
                          capacity_mw: float, horizon_years: int = 20) -> float:
    """
    Calculate Internal Rate of Return using Newton's method
    
    Args:
        capex_m: Capital expenditure in millions
        opex_annual_m: Annual operating expenditure in millions
        lcoe: Levelized cost of energy ($/MWh)
        capacity_mw: IT capacity in MW
        horizon_years: Analysis horizon (default 20 years)
    
    Returns:
        IRR as percentage
    """
    # Build cash flow array
    annual_mwh = capacity_mw * 8760 * 0.95
    annual_revenue_m = (lcoe * annual_mwh) / 1_000_000
    annual_net_cf = annual_revenue_m - opex_annual_m
    
    cash_flows = [-capex_m]  # Initial investment
    for _ in range(horizon_years):
        cash_flows.append(annual_net_cf)
    
    # Use Newton's method for IRR calculation
    return calculate_irr_newton(cash_flows)


def calculate_irr_newton(cash_flows: list, max_iterations: int = 100, tolerance: float = 1e-6) -> float:
    """
    Calculate IRR using Newton's method
    
    Args:
        cash_flows: List of cash flows (negative for investment, positive for returns)
        max_iterations: Maximum iterations
        tolerance: Convergence tolerance
    
    Returns:
        IRR as percentage
    """
    # Initial guess: 10%
    rate = 0.10
    
    for _ in range(max_iterations):
        # Calculate NPV and derivative at current rate
        npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))
        npv_prime = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows))
        
        if abs(npv) < tolerance:
            return rate * 100
        
        if abs(npv_prime) < 1e-10:
            break
        
        # Newton's method update
        rate = rate - npv / npv_prime
        
        # Constrain to reasonable range
        if rate < -0.99 or rate > 10.0:
            break
    
    # If no convergence, return estimate
    if len(cash_flows) > 1 and cash_flows[0] < 0:
        avg_annual_cf = sum(cash_flows[1:]) / len(cash_flows[1:])
        simple_return = (avg_annual_cf / abs(cash_flows[0])) * 100 * 0.7
        return max(0, simple_return)
    
    return 0.0


def calculate_payback(capex_m: float, opex_annual_m: float, lcoe: float, 
                      capacity_mw: float) -> float:
    """
    Calculate simple payback period in years
    
    Args:
        capex_m: Capital expenditure in millions
        opex_annual_m: Annual operating expenditure in millions
        lcoe: Levelized cost of energy ($/MWh)
        capacity_mw: IT capacity in MW
    
    Returns:
        Payback period in years
    """
    annual_mwh = capacity_mw * 8760 * 0.95
    annual_revenue_m = (lcoe * annual_mwh) / 1_000_000
    annual_net_cf = annual_revenue_m - opex_annual_m
    
    if annual_net_cf <= 0:
        return 99.9  # Never pays back
    
    payback = capex_m / annual_net_cf
    return payback


def calculate_portfolio_metrics(portfolio_data: List[Dict]) -> Dict:
    """
    Calculate portfolio-level summary metrics
    
    Args:
        portfolio_data: List of site financial dicts
    
    Returns:
        Dict with portfolio metrics
    """
    if not portfolio_data:
        return {
            'total_npv': 0,
            'weighted_lcoe': 0,
            'total_capex': 0,
            'portfolio_irr': 0,
            'total_capacity_mw': 0
        }
    
    # Sum NPV across all sites
    total_npv = sum(site.get('npv_m', 0) for site in portfolio_data)
    
    # Calculate capacity-weighted LCOE
    total_capacity = sum(site.get('capacity_mw', 0) for site in portfolio_data)
    
    if total_capacity > 0:
        weighted_lcoe = sum(
            site.get('lcoe', 0) * site.get('capacity_mw', 0)
            for site in portfolio_data
        ) / total_capacity
    else:
        weighted_lcoe = 0
    
    # Sum CapEx
    total_capex = sum(site.get('capex_m', 0) for site in portfolio_data)
    
    # Calculate portfolio IRR (simplified as capacity-weighted average)
    if total_capacity > 0:
        portfolio_irr = sum(
            site.get('irr_pct', 0) * site.get('capacity_mw', 0)
            for site in portfolio_data
        ) / total_capacity
    else:
        portfolio_irr = 0
    
    return {
        'total_npv': total_npv,
        'weighted_lcoe': weighted_lcoe,
        'total_capex': total_capex,
        'portfolio_irr': portfolio_irr,
        'total_capacity_mw': total_capacity
    }
