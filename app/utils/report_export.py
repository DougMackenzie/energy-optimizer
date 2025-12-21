"""
Portfolio Report Generator
Export complete optimization results to PDF and Word formats
"""

from typing import Dict, List
from datetime import datetime
import pandas as pd


def generate_portfolio_report_data(
    sites: List[Dict],
    scenarios: List[Dict],
    optimization_results: List[Dict],
    load_profiles: Dict = None,
    constraints: Dict = None
) -> Dict:
    """
    Compile all data needed for portfolio report
    
    Returns:
        Dict with organized report sections
    """
    
    report_data = {
        'metadata': {
            'report_title': 'Energy Optimization Portfolio Analysis',
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'num_sites': len(sites),
            'num_scenarios': len(scenarios),
            'num_optimizations': len(optimization_results)
        },
        'executive_summary': generate_executive_summary(optimization_results),
        'sites': compile_site_summaries(sites, constraints),
        'scenarios': compile_scenario_summaries(scenarios),
        'optimization_results': compile_optimization_summaries(optimization_results),
        'recommendations': generate_recommendations(optimization_results),
        'appendix': {
            'load_profiles': load_profiles or {},
            'constraints_detail': constraints or {},
            'methodology': get_methodology_text()
        }
    }
    
    return report_data


def generate_executive_summary(results: List[Dict]) -> Dict:
    """Generate executive summary from optimization results"""
    
    feasible_results = [r for r in results if r.get('feasible')]
    
    if not feasible_results:
        return {
            'status': 'No feasible solutions found',
            'recommendation': 'Review constraints and equipment availability'
        }
    
    # Find best result (lowest LCOE among feasible)
    best_result = min(feasible_results, key=lambda x: x['economics']['lcoe_mwh'])
    
    total_capex = sum(r['economics']['total_capex_m'] for r in feasible_results)
    avg_lcoe = sum(r['economics']['lcoe_mwh'] for r in feasible_results) / len(feasible_results)
    
    return {
        'num_feasible_scenarios': len(feasible_results),
        'recommended_scenario': best_result['scenario_name'],
        'recommended_lcoe': best_result['economics']['lcoe_mwh'],
        'recommended_capex': best_result['economics']['total_capex_m'],
        'recommended_timeline': best_result['timeline']['timeline_months'],
        'total_portfolio_capex': total_capex,
        'average_lcoe':avg_lcoe,
        'deployment_range_months': (
            min(r['timeline']['timeline_months'] for r in feasible_results),
            max(r['timeline']['timeline_months'] for r in feasible_results)
        )
    }


def compile_site_summaries(sites: List[Dict], constraints: Dict) -> List[Dict]:
    """Compile site information for report"""
    
    summaries = []
    for site in sites:
        summary = {
            'site_name': site.get('Site_Name', 'Unknown'),
            'location': f"{site.get('State', '')}, {site.get('ISO', '')}",
            'it_capacity_mw': site.get('IT_Capacity_MW', 0),
            'total_mw': site.get('Total_Facility_MW', 0),
            'pue': site.get('Design_PUE', 0),
            'status': site.get('Status', 'Unknown'),
            'key_constraints': extract_key_constraints(site.get('Site_ID'), constraints)
        }
        summaries.append(summary)
    
    return summaries


def extract_key_constraints(site_id: str, constraints: Dict) -> Dict:
    """Extract key constraints for a site"""
    
    if not constraints or site_id not in constraints:
        return {}
    
    site_constraints = constraints.get(site_id, {})
    
    return {
        'nox_limit_tpy': site_constraints.get('NOx_Limit_tpy', 0),
        'gas_supply_mcf_day': site_constraints.get('Gas_Supply_MCF_day', 0),
        'grid_mw': site_constraints.get('Grid_Available_MW', 0),
        'grid_timeline_months': site_constraints.get('Estimated_Interconnection_Months', 0),
        'land_acres': site_constraints.get('Available_Land_Acres', 0)
    }


def compile_scenario_summaries(scenarios: List[Dict]) -> List[Dict]:
    """Compile scenario information for report"""
    
    summaries = []
    for scenario in scenarios:
        summary = {
            'name': scenario.get('Scenario_Name', 'Unknown'),
            'description': scenario.get('Description', ''),
            'target_lcoe': scenario.get('Target_LCOE_MWh', 0),
            'target_timeline': scenario.get('Target_Deployment_Months', 0),
            'deployment_strategy': scenario.get('Deployment_Strategy', ''),
            'technologies': {
                'recip_engines': scenario.get('Recip_Engines') == 'True',
                'gas_turbines': scenario.get('Gas_Turbines') == 'True',
                'bess': scenario.get('BESS') == 'True',
                'solar': scenario.get('Solar_PV') == 'True',
                'grid': scenario.get('Grid_Connection') == 'True'
            }
        }
        summaries.append(summary)
    
    return summaries


def compile_optimization_summaries(results: List[Dict]) -> List[Dict]:
    """Compile optimization results for report"""
    
    summaries = []
    for result in results:
        summary = {
            'scenario_name': result.get('scenario_name', 'Unknown'),
            'feasible': result.get('feasible', False),
            'lcoe_mwh': result['economics']['lcoe_mwh'] if result.get('feasible') else None,
            'capex_m': result['economics']['total_capex_m'] if result.get('feasible') else None,
            'timeline_months': result['timeline']['timeline_months'] if result.get('feasible') else None,
            'deployment_speed': result['timeline']['deployment_speed'] if result.get('feasible') else None,
            'total_capacity_mw': result['metrics']['total_capacity_mw'],
            'annual_generation_gwh': result['economics']['annual_generation_gwh'] if result.get('feasible') else None,
            'violations': result.get('violations', []),
            'warnings': result.get('warnings', []),
            'equipment_summary': summarize_equipment(result.get('equipment_config', {}))
        }
        summaries.append(summary)
    
    return summaries


def summarize_equipment(equipment_config: Dict) -> str:
    """Create text summary of equipment configuration"""
    
    items = []
    
    recip_count = len(equipment_config.get('recip_engines', []))
    if recip_count > 0:
        items.append(f"{recip_count} Reciprocating Engines")
    
    turbine_count = len(equipment_config.get('gas_turbines', []))
    if turbine_count > 0:
        items.append(f"{turbine_count} Gas Turbines")
    
    bess_count = len(equipment_config.get('bess', []))
    if bess_count > 0:
        items.append(f"{bess_count} BESS Units")
    
    solar_mw = equipment_config.get('solar_mw_dc', 0)
    if solar_mw > 0:
        items.append(f"{solar_mw:.1f} MW Solar PV")
    
    grid_mw = equipment_config.get('grid_import_mw', 0)
    if grid_mw > 0:
        items.append(f"{grid_mw:.1f} MW Grid")
    
    return ", ".join(items) if items else "No equipment configured"


def generate_recommendations(results: List[Dict]) -> str:
    """Generate recommendations based on optimization results"""
    
    feasible_results = [r for r in results if r.get('feasible')]
    
    if not feasible_results:
        return """
        **No Feasible Solutions Found**
        
        Recommendations:
        1. Review air permit limits - consider larger minor source threshold
        2. Evaluate additional gas supply capacity
        3. Consider smaller equipment units for better modularity
        4. Explore alternative deployment strategies
        """
    
    # Find fastest and cheapest
    fastest = min(feasible_results, key=lambda x: x['timeline']['timeline_months'])
    cheapest = min(feasible_results, key=lambda x: x['economics']['lcoe_mwh'])
    
    recommendations = f"""
    **Recommended Strategy: {cheapest['scenario_name']}**
    
    This scenario offers the best balance of cost and feasibility:
    - LCOE: ${cheapest['economics']['lcoe_mwh']:.2f}/MWh
    - CAPEX: ${cheapest['economics']['total_capex_m']:.1f}M
    - Timeline: {cheapest['timeline']['timeline_months']} months
    
    **Alternative for Fastest Deployment: {fastest['scenario_name']}**
    - Can be operational in {fastest['timeline']['timeline_months']} months
    - LCOE: ${fastest['economics']['lcoe_mwh']:.2f}/MWh (premium of ${fastest['economics']['lcoe_mwh'] - cheapest['economics']['lcoe_mwh']:.2f}/MWh)
    
    **Next Steps:**
    1. Finalize site selection and equipment specifications
    2. Initiate environmental permitting process
    3. Begin procurement for long-lead equipment
    4. Develop detailed project schedule
    5. Secure financing and execute contracts
    """
    
    return recommendations


def get_methodology_text() -> str:
    """Get methodology explanation for appendix"""
    
    return """
    **Optimization Methodology**
    
    This analysis uses a multi-criteria optimization approach:
    
    1. **Load Modeling**: 8760-hour annual load profiles based on site capacity and workload characteristics
    
    2. **Equipment Sizing**: Automated sizing algorithms configure equipment to meet site requirements while respecting constraints
    
    3. **Constraint Validation**: Hard constraints (air permits, gas supply, land, N-1 reliability) are validated before optimization
    
    4. **Economic Analysis**: LCOE calculated using NPV method with 20-year project life, equipment-specific CAPEX/OPEX
    
    5. **Deployment Timeline**: Critical path analysis considering equipment lead times, permitting, and construction
    
    6. **Scenario Ranking**: Multi-objective scoring using weighted factors (LCOE, deployment speed, reliability)
    
    **Key Assumptions:**
    - Natural gas price: $3.00-3.75/MMBtu
    - Discount rate: 8%
    - Project life: 20 years
    - Equipment availability: 99.5% (recip), 99.0% (turbines), 99.95% (BESS/solar)
    """


# Simplified export functions (full implementation would use reportlab/python-docx)
def export_to_text_summary(report_data: Dict) -> str:
    """
    Export report as formatted text
    This is a simplified version - full PDF/Word export would use proper libraries
    """
    
    text = f"""
{'='*80}
{report_data['metadata']['report_title']}
Generated: {report_data['metadata']['generated_date']}
{'='*80}

EXECUTIVE SUMMARY
{'-'*80}

Feasible Scenarios: {report_data['executive_summary'].get('num_feasible_scenarios', 0)}
Recommended: {report_data['executive_summary'].get('recommended_scenario', 'N/A')}
LCOE: ${report_data['executive_summary'].get('recommended_lcoe', 0):.2f}/MWh
Timeline: {report_data['executive_summary'].get('recommended_timeline', 0)} months

SITES ANALYZED
{'-'*80}
"""
    
    for site in report_data['sites']:
        text += f"\n{site['site_name']} ({site['location']})\n"
        text += f"  Capacity: {site['total_mw']} MW | PUE: {site['pue']}\n"
    
    text += f"\n\nOPTIMIZATION RESULTS\n{'-'*80}\n"
    
    for result in report_data['optimization_results']:
        status = "✓ FEASIBLE" if result['feasible'] else "✗ INFEASIBLE"
        text += f"\n{result['scenario_name']}: {status}\n"
        if result['feasible']:
            text += f"  LCOE: ${result['lcoe_mwh']:.2f}/MWh | CAPEX: ${result['capex_m']:.1f}M | {result['timeline_months']} months\n"
            text += f"  Equipment: {result['equipment_summary']}\n"
    
    text += f"\n\nRECOMMENDATIONS\n{'-'*80}\n"
    text += report_data['recommendations']
    
    text += f"\n\n{'='*80}\nEnd of Report\n{'='*80}\n"
    
    return text
