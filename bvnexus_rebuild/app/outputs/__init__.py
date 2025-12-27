"""
Output Generation Module
Generates reports, exports, and visualizations from optimization results
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime


@dataclass
class ReportConfig:
    """Configuration for report generation"""
    title: str = "bvNexus Optimization Report"
    include_executive_summary: bool = True
    include_equipment_details: bool = True
    include_dispatch_charts: bool = True
    include_proforma: bool = True
    include_constraints: bool = True
    include_recommendations: bool = True


def generate_executive_summary(results: Dict) -> str:
    """Generate executive summary text from results"""
    
    lines = [
        "# Executive Summary",
        "",
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Key Findings",
        ""
    ]
    
    for prob_num, result in results.items():
        if result:
            lines.append(f"### Problem {prob_num}")
            lines.append(f"- Status: {'Feasible' if result.get('feasible', True) else 'Issues Detected'}")
            
            if result.get('lcoe'):
                lines.append(f"- LCOE: ${result['lcoe']:.1f}/MWh")
            if result.get('capex'):
                lines.append(f"- CAPEX: ${result['capex']/1e6:.1f}M")
            if result.get('timeline'):
                lines.append(f"- Timeline: {result['timeline']} months")
            
            lines.append("")
    
    return "\n".join(lines)


def generate_equipment_table(equipment: Dict) -> pd.DataFrame:
    """Generate equipment summary table"""
    
    data = [
        {
            'Equipment Type': 'Reciprocating Engines',
            'Count': equipment.get('n_recips', 0),
            'Unit Size (MW)': 18.3 if equipment.get('n_recips', 0) > 0 else 0,
            'Total Capacity (MW)': equipment.get('recip_mw', 0),
        },
        {
            'Equipment Type': 'Gas Turbines',
            'Count': equipment.get('n_turbines', 0),
            'Unit Size (MW)': 50.0 if equipment.get('n_turbines', 0) > 0 else 0,
            'Total Capacity (MW)': equipment.get('turbine_mw', 0),
        },
        {
            'Equipment Type': 'Solar PV',
            'Count': 1 if equipment.get('solar_mw', 0) > 0 else 0,
            'Unit Size (MW)': equipment.get('solar_mw', 0),
            'Total Capacity (MW)': equipment.get('solar_mw', 0),
        },
        {
            'Equipment Type': 'Battery Storage',
            'Count': 1 if equipment.get('bess_mwh', 0) > 0 else 0,
            'Unit Size (MW)': equipment.get('bess_mw', 0),
            'Total Capacity (MW)': equipment.get('bess_mw', 0),
        },
    ]
    
    return pd.DataFrame(data)


def generate_proforma_table(
    capex: float,
    opex: float,
    discount_rate: float = 0.08,
    project_life: int = 20,
    fuel_escalation: float = 0.025
) -> pd.DataFrame:
    """Generate pro forma cash flow table"""
    
    cash_flows = []
    cumulative = 0
    
    for year in range(project_life + 1):
        if year == 0:
            cf = -capex
            opex_year = 0
        else:
            opex_year = opex * (1 + fuel_escalation) ** (year - 1)
            cf = -opex_year
        
        cumulative += cf
        npv_factor = 1 / (1 + discount_rate) ** year
        
        cash_flows.append({
            'Year': year,
            'CAPEX': -capex if year == 0 else 0,
            'OPEX': -opex_year if year > 0 else 0,
            'Net Cash Flow': cf,
            'Cumulative': cumulative,
            'NPV Factor': npv_factor,
            'Discounted CF': cf * npv_factor,
        })
    
    return pd.DataFrame(cash_flows)


def generate_constraint_table(constraints: Dict) -> pd.DataFrame:
    """Generate constraint status table"""
    
    data = []
    
    for name, status in constraints.items():
        if isinstance(status, dict):
            data.append({
                'Constraint': name.replace('_', ' ').title(),
                'Value': status.get('value', 0),
                'Limit': status.get('limit', 0),
                'Utilization (%)': status.get('value', 0) / status.get('limit', 1) * 100 if status.get('limit', 0) > 0 else 0,
                'Binding': 'Yes' if status.get('binding', False) else 'No',
            })
    
    return pd.DataFrame(data)


def export_to_json(results: Dict, filepath: str):
    """Export results to JSON"""
    
    # Convert to JSON-serializable format
    export_data = {}
    
    for prob_num, result in results.items():
        if result:
            export_data[f"problem_{prob_num}"] = {
                'feasible': result.get('feasible', True),
                'lcoe': result.get('lcoe', 0),
                'capex': result.get('capex', 0),
                'opex': result.get('opex', 0),
                'timeline': result.get('timeline', 0),
                'equipment': result.get('equipment', {}),
            }
    
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)


def export_dispatch_to_csv(dispatch_df: pd.DataFrame, filepath: str):
    """Export 8760 dispatch to CSV"""
    dispatch_df.to_csv(filepath, index=False)


def export_proforma_to_csv(proforma_df: pd.DataFrame, filepath: str):
    """Export pro forma to CSV"""
    proforma_df.to_csv(filepath, index=False)


class ReportGenerator:
    """Generate comprehensive reports from optimization results"""
    
    def __init__(self, results: Dict, config: ReportConfig = None):
        self.results = results
        self.config = config or ReportConfig()
    
    def generate_text_report(self) -> str:
        """Generate plain text report"""
        
        sections = []
        
        # Header
        sections.append("=" * 60)
        sections.append(self.config.title)
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        sections.append("=" * 60)
        sections.append("")
        
        # Executive summary
        if self.config.include_executive_summary:
            sections.append(generate_executive_summary(self.results))
        
        # Equipment details
        if self.config.include_equipment_details:
            sections.append("")
            sections.append("## Equipment Configuration")
            sections.append("")
            
            for prob_num, result in self.results.items():
                if result and result.get('equipment'):
                    sections.append(f"### Problem {prob_num}")
                    equip = result['equipment']
                    sections.append(f"- Recip Engines: {equip.get('recip_mw', 0):.1f} MW ({equip.get('n_recips', 0)} units)")
                    sections.append(f"- Gas Turbines: {equip.get('turbine_mw', 0):.1f} MW ({equip.get('n_turbines', 0)} units)")
                    sections.append(f"- Solar PV: {equip.get('solar_mw', 0):.1f} MW")
                    sections.append(f"- BESS: {equip.get('bess_mwh', 0):.1f} MWh")
                    sections.append("")
        
        # Constraints
        if self.config.include_constraints:
            sections.append("")
            sections.append("## Constraint Analysis")
            sections.append("")
            
            for prob_num, result in self.results.items():
                if result and result.get('constraints'):
                    sections.append(f"### Problem {prob_num}")
                    for name, status in result['constraints'].items():
                        if isinstance(status, dict):
                            binding = "BINDING" if status.get('binding') else "OK"
                            sections.append(f"- {name}: {status.get('value', 0):.1f} / {status.get('limit', 0):.1f} [{binding}]")
                    sections.append("")
        
        # Recommendations
        if self.config.include_recommendations:
            sections.append("")
            sections.append("## Recommendations")
            sections.append("")
            sections.append("1. Review binding constraints for optimization opportunities")
            sections.append("2. Consider sensitivity analysis on key parameters")
            sections.append("3. Validate results with Phase 2 MILP optimization")
            sections.append("")
        
        sections.append("=" * 60)
        sections.append("End of Report")
        sections.append("=" * 60)
        
        return "\n".join(sections)
    
    def save_text_report(self, filepath: str):
        """Save text report to file"""
        with open(filepath, 'w') as f:
            f.write(self.generate_text_report())
