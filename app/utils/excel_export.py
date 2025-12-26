"""
Excel Export Module
Generate Excel workbooks with financial data and charts
"""

import pandas as pd
import io
from typing import List, Dict
from datetime import datetime

def create_portfolio_excel(portfolio_data: List[Dict], portfolio_metrics: Dict) -> bytes:
    """
    Create Excel workbook with portfolio financial data
    
    Args:
        portfolio_data: List of site financial dicts
        portfolio_metrics: Portfolio-level metrics dict
    
    Returns:
        Excel file as bytes (BytesIO buffer)
    """
    # Create BytesIO buffer
    output = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1f4788',
            'font_color': 'white',
            'border': 1
        })
        
        currency_format = workbook.add_format({'num_format': '$#,##0.0'})
        percent_format = workbook.add_format({'num_format': '0.0%'})
        number_format = workbook.add_format({'num_format': '#,##0.0'})
        
        # =============================================================================
        # Sheet 1: Portfolio Summary
        # =============================================================================
        summary_data = {
            'Metric': [
                'Total Portfolio NPV',
                'Weighted Average LCOE',
                'Total CapEx Required',
                'Portfolio IRR',
                'Total Capacity'
            ],
            'Value': [
                portfolio_metrics['total_npv'],
                portfolio_metrics['weighted_lcoe'],
                portfolio_metrics['total_capex'],
                portfolio_metrics['portfolio_irr'] / 100,  # Convert to decimal for %
                portfolio_metrics['total_capacity_mw']
            ],
            'Unit': [
                '$M',
                '$/MWh',
                '$M',
                '%',
                'MW'
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Portfolio Summary', index=False, startrow=2)
        
        # Format summary sheet
        worksheet = writer.sheets['Portfolio Summary']
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 10)
        
        # Add title
        title_format = workbook.add_format({'bold': True, 'font_size': 16})
        worksheet.write('A1', 'Portfolio Financial Summary', title_format)
        worksheet.write('A2', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        # =============================================================================
        # Sheet 2: Site Details
        # =============================================================================
        df_sites = pd.DataFrame(portfolio_data)
        
        # Reorder and rename columns
        df_sites_display = df_sites[[
            'site', 'stage', 'capacity_mw', 'capex_m', 'opex_annual_m',
            'npv_m', 'irr_pct', 'lcoe', 'payback_years'
        ]].copy()
        
        df_sites_display.columns = [
            'Site', 'Stage', 'Capacity (MW)', 'CapEx ($M)', 'Annual OpEx ($M)',
            'NPV ($M)', 'IRR (%)', 'LCOE ($/MWh)', 'Payback (years)'
        ]
        
        df_sites_display.to_excel(writer, sheet_name='Site Details', index=False, startrow=1)
        
        # Format site details sheet
        worksheet2 = writer.sheets['Site Details']
        worksheet2.set_column('A:A', 20)  # Site name
        worksheet2.set_column('B:B', 12)  # Stage
        worksheet2.set_column('C:I', 15)  # Metrics
        
        # Add title
        worksheet2.write('A1', 'Site-by-Site Financial Details', title_format)
        
        # Apply number formats
        for row in range(2, len(df_sites_display) + 2):
            worksheet2.write(f'D{row}', df_sites_display.iloc[row-2]['CapEx ($M)'], currency_format)
            worksheet2.write(f'E{row}', df_sites_display.iloc[row-2]['Annual OpEx ($M)'], currency_format)
            worksheet2.write(f'F{row}', df_sites_display.iloc[row-2]['NPV ($M)'], currency_format)
            worksheet2.write(f'G{row}', df_sites_display.iloc[row-2]['IRR (%)'], number_format)
            worksheet2.write(f'H{row}', df_sites_display.iloc[row-2]['LCOE ($/MWh)'], currency_format)
            worksheet2.write(f'I{row}', df_sites_display.iloc[row-2]['Payback (years)'], number_format)
        
        # =============================================================================
        # Sheet 3: NPV Analysis
        # =============================================================================
        npv_data = df_sites[['site', 'npv_m', 'irr_pct', 'payback_years']].copy()
        npv_data.columns = ['Site', 'NPV ($M)', 'IRR (%)', 'Payback (years)']
        npv_data = npv_data.sort_values('NPV ($M)', ascending=False)
        
        npv_data.to_excel(writer, sheet_name='NPV Analysis', index=False, startrow=1)
        
        # Format NPV analysis sheet
        worksheet3 = writer.sheets['NPV Analysis']
        worksheet3.set_column('A:A', 20)
        worksheet3.set_column('B:D', 15)
        
        worksheet3.write('A1', 'NPV Ranking', title_format)
        
        # Add chart
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'NPV ($M)',
            'categories': f'=\'NPV Analysis\'!$A$3:$A${len(npv_data) + 2}',
            'values': f'=\'NPV Analysis\'!$B$3:$B${len(npv_data) + 2}',
            'fill': {'color': '#10b981'}
        })
        chart.set_title({'name': 'NPV by Site'})
        chart.set_x_axis({'name': 'Site'})
        chart.set_y_axis({'name': 'NPV ($M)'})
        chart.set_size({'width': 600, 'height': 400})
        
        worksheet3.insert_chart('F2', chart)
        
        # =============================================================================
        # Sheet 4: Cash Flow Template
        # =============================================================================
        # Create 20-year cash flow template for first site as example
        if portfolio_data:
            first_site = portfolio_data[0]
            
            years = list(range(0, 21))
            capex = [-first_site['capex_m']] + [0] * 20
            opex = [0] + [-first_site['opex_annual_m']] * 20
            
            # Estimate revenue from LCOE
            annual_mwh = first_site['capacity_mw'] * 8760 * 0.95
            annual_revenue = (first_site['lcoe'] * annual_mwh) / 1_000_000
            revenue = [0] + [annual_revenue] * 20
            
            net_cf = [capex[i] + opex[i] + revenue[i] for i in range(21)]
            cumulative_cf = []
            running_total = 0
            for cf in net_cf:
                running_total += cf
                cumulative_cf.append(running_total)
            
            cf_data = pd.DataFrame({
                'Year': years,
                'CapEx ($M)': capex,
                'OpEx ($M)': opex,
                'Revenue ($M)': revenue,
                'Net Cash Flow ($M)': net_cf,
                'Cumulative CF ($M)': cumulative_cf
            })
            
            cf_data.to_excel(writer, sheet_name='Cash Flow (Example)', index=False, startrow=2)
            
            # Format cash flow sheet
            worksheet4 = writer.sheets['Cash Flow (Example)']
            worksheet4.set_column('A:F', 18)
            
            worksheet4.write('A1', f'20-Year Cash Flow Analysis - {first_site["site"]}', title_format)
            worksheet4.write('A2', 'All values in millions ($M)')
    
    # Get the value of the BytesIO buffer
    output.seek(0)
    return output.getvalue()
