"""
Pro Forma Cash Flow Analysis Page
15-year financial projection and economic analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS, ECONOMIC_DEFAULTS


def render():
    """Render Pro Forma page"""
    
    st.markdown("### 💰 Pro Forma Cash Flow Analysis")
    st.markdown("*15-year financial projection and economic metrics*")
    st.markdown("---")
    
    # Get results
    results = st.session_state.get('optimization_results', {})
    result = results.get(1)  # Use Problem 1 results
    
    if not result:
        st.warning("No optimization results available. Run Problem 1 (Greenfield) optimization first.")
        
        if st.button("🏗️ Go to Problem 1", type="primary"):
            st.session_state.current_page = 'problem_1'
            st.rerun()
        return
    
    # Economic parameters sidebar
    with st.sidebar:
        st.markdown("#### Economic Parameters")
        
        discount_rate = st.slider("Discount Rate", 0.05, 0.15, ECONOMIC_DEFAULTS['discount_rate'], 0.01)
        project_life = st.slider("Project Life (years)", 10, 30, ECONOMIC_DEFAULTS['project_life_years'])
        fuel_price = st.slider("Gas Price ($/MMBtu)", 2.0, 8.0, ECONOMIC_DEFAULTS['fuel_price_mmbtu'], 0.25)
        fuel_escalation = st.slider("Fuel Escalation (%/yr)", 0.0, 5.0, ECONOMIC_DEFAULTS['fuel_escalation_rate'] * 100, 0.5)
        
        st.markdown("---")
        st.markdown("#### Revenue Assumptions")
        
        energy_price = st.number_input("Energy Price ($/MWh)", 40, 150, 75)
        capacity_price = st.number_input("Capacity Price ($/kW-yr)", 0, 200, 50)
        
        st.markdown("---")
        
        if st.button("🔄 Recalculate", use_container_width=True):
            st.rerun()
    
    # Get key values
    capex = result.get('capex', 0)
    opex = result.get('opex', 0)
    equipment = result.get('equipment', {})
    
    # Tabs for different views
    tab_summary, tab_cashflow, tab_sensitivity, tab_comparison = st.tabs([
        "📊 Summary", "💵 Cash Flow", "📈 Sensitivity", "🔄 Comparison"
    ])
    
    with tab_summary:
        render_summary_tab(result, discount_rate, project_life, energy_price, capacity_price)
    
    with tab_cashflow:
        render_cashflow_tab(result, discount_rate, project_life, fuel_price, fuel_escalation)
    
    with tab_sensitivity:
        render_sensitivity_tab(result, discount_rate, project_life)
    
    with tab_comparison:
        render_comparison_tab(results)


def render_summary_tab(result, discount_rate, project_life, energy_price, capacity_price):
    """Economic summary metrics"""
    
    st.markdown("#### Key Economic Metrics")
    
    capex = result.get('capex', 0)
    opex = result.get('opex', 0)
    lcoe = result.get('lcoe', 0)
    equipment = result.get('equipment', {})
    
    # Calculate key metrics
    crf = (discount_rate * (1 + discount_rate) ** project_life) / ((1 + discount_rate) ** project_life - 1)
    
    # Annual generation estimate
    total_capacity = equipment.get('total_firm_mw', 0) + equipment.get('solar_mw', 0)
    avg_cf = 0.70
    annual_gen_mwh = total_capacity * avg_cf * 8760
    
    # Annual revenue
    annual_revenue = annual_gen_mwh * energy_price + total_capacity * 1000 * capacity_price
    
    # NPV calculations
    npv_capex = capex
    npv_opex = opex * sum(1 / (1 + discount_rate) ** y for y in range(1, project_life + 1))
    npv_revenue = annual_revenue * sum(1 / (1 + discount_rate) ** y for y in range(1, project_life + 1))
    
    npv = npv_revenue - npv_capex - npv_opex
    
    # Simple payback
    annual_net = annual_revenue - opex
    simple_payback = capex / annual_net if annual_net > 0 else float('inf')
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("NPV", f"${npv/1e6:.1f}M", 
                 delta="Positive" if npv > 0 else "Negative")
    
    with col2:
        st.metric("LCOE", f"${lcoe:.1f}/MWh")
    
    with col3:
        st.metric("Simple Payback", f"{simple_payback:.1f} years" if simple_payback < 100 else "N/A")
    
    with col4:
        irr = calculate_irr(capex, annual_net, project_life)
        st.metric("IRR", f"{irr:.1%}" if irr else "N/A")
    
    st.markdown("---")
    
    # Cost breakdown
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("##### Capital Cost Breakdown")
        
        # Estimate CAPEX breakdown
        recip_capex = equipment.get('recip_mw', 0) * 1000 * 1650
        turbine_capex = equipment.get('turbine_mw', 0) * 1000 * 1300
        solar_capex = equipment.get('solar_mw', 0) * 1e6 * 0.95 * 0.70  # With ITC
        bess_capex = equipment.get('bess_mwh', 0) * 1000 * 236 * 0.70  # With ITC
        other_capex = capex - (recip_capex + turbine_capex + solar_capex + bess_capex)
        
        capex_data = [
            {'Category': 'Recip Engines', 'Amount ($M)': recip_capex / 1e6},
            {'Category': 'Gas Turbines', 'Amount ($M)': turbine_capex / 1e6},
            {'Category': 'Solar PV', 'Amount ($M)': solar_capex / 1e6},
            {'Category': 'BESS', 'Amount ($M)': bess_capex / 1e6},
            {'Category': 'Other/BOP', 'Amount ($M)': max(0, other_capex) / 1e6},
        ]
        
        fig = px.pie(capex_data, values='Amount ($M)', names='Category',
                    color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("##### Annual Operating Costs")
        
        # Estimate OPEX breakdown
        fuel_cost = equipment.get('recip_mw', 0) * 0.70 * 8760 * (7.7/1000) * 3.50  # Rough fuel estimate
        fuel_cost += equipment.get('turbine_mw', 0) * 0.35 * 8760 * (8.5/1000) * 3.50
        
        vom = equipment.get('recip_mw', 0) * 0.70 * 8760 * 8.5 + equipment.get('turbine_mw', 0) * 0.35 * 8760 * 6.5
        fom = equipment.get('recip_mw', 0) * 1000 * 18.5 + equipment.get('turbine_mw', 0) * 1000 * 12.5
        
        opex_data = [
            {'Category': 'Fuel', 'Amount ($M)': fuel_cost / 1e6},
            {'Category': 'Variable O&M', 'Amount ($M)': vom / 1e6},
            {'Category': 'Fixed O&M', 'Amount ($M)': fom / 1e6},
        ]
        
        fig = px.pie(opex_data, values='Amount ($M)', names='Category',
                    color_discrete_sequence=['#e53e3e', '#f6ad55', '#48bb78'])
        fig.update_layout(height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Key assumptions
    st.markdown("##### Key Assumptions")
    
    assumptions = pd.DataFrame({
        'Parameter': ['Discount Rate', 'Project Life', 'Energy Price', 'Capacity Price', 'Average CF'],
        'Value': [f"{discount_rate:.1%}", f"{project_life} years", f"${energy_price}/MWh", 
                 f"${capacity_price}/kW-yr", f"{avg_cf:.0%}"]
    })
    
    st.dataframe(assumptions, use_container_width=True, hide_index=True)


def render_cashflow_tab(result, discount_rate, project_life, fuel_price, fuel_escalation):
    """Detailed year-by-year cash flow"""
    
    st.markdown("#### Year-by-Year Cash Flow")
    
    capex = result.get('capex', 0)
    opex = result.get('opex', 0)
    
    # Generate yearly cash flows
    years = list(range(0, project_life + 1))
    
    cash_flows = []
    cumulative = 0
    cumulative_discounted = 0
    
    for year in years:
        if year == 0:
            cf = -capex
            opex_year = 0
        else:
            # Escalate OPEX
            opex_year = opex * (1 + fuel_escalation / 100) ** (year - 1)
            cf = -opex_year
        
        cumulative += cf
        npv_factor = 1 / (1 + discount_rate) ** year
        discounted_cf = cf * npv_factor
        cumulative_discounted += discounted_cf
        
        cash_flows.append({
            'Year': year,
            'CAPEX': -capex if year == 0 else 0,
            'OPEX': -opex_year if year > 0 else 0,
            'Net Cash Flow': cf,
            'Cumulative': cumulative,
            'NPV Factor': npv_factor,
            'Discounted CF': discounted_cf,
            'Cumulative NPV': cumulative_discounted,
        })
    
    cf_df = pd.DataFrame(cash_flows)
    
    # Format for display
    display_df = cf_df.copy()
    for col in ['CAPEX', 'OPEX', 'Net Cash Flow', 'Cumulative', 'Discounted CF', 'Cumulative NPV']:
        display_df[col] = display_df[col].apply(lambda x: f"${x/1e6:.1f}M")
    display_df['NPV Factor'] = display_df['NPV Factor'].apply(lambda x: f"{x:.3f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # Cash flow chart
    st.markdown("##### Cash Flow Visualization")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Bar chart for annual CF
    fig.add_trace(
        go.Bar(x=cf_df['Year'], y=cf_df['Net Cash Flow']/1e6, name='Annual CF ($M)',
               marker_color=np.where(cf_df['Net Cash Flow'] < 0, '#e53e3e', '#48bb78')),
        secondary_y=False
    )
    
    # Line for cumulative
    fig.add_trace(
        go.Scatter(x=cf_df['Year'], y=cf_df['Cumulative']/1e6, name='Cumulative ($M)',
                  line=dict(color='#4299e1', width=2)),
        secondary_y=True
    )
    
    fig.update_layout(
        height=350,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="Annual Cash Flow ($M)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative ($M)", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    csv = cf_df.to_csv(index=False)
    st.download_button("📥 Download Cash Flow (CSV)", csv, "bvnexus_proforma.csv", "text/csv")


def render_sensitivity_tab(result, discount_rate, project_life):
    """Sensitivity analysis"""
    
    st.markdown("#### Sensitivity Analysis")
    
    capex = result.get('capex', 0)
    opex = result.get('opex', 0)
    lcoe = result.get('lcoe', 0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### LCOE Sensitivity to CAPEX")
        
        capex_range = np.linspace(capex * 0.7, capex * 1.3, 10)
        lcoe_range = lcoe * capex_range / capex  # Simplified linear relationship
        
        fig = px.line(x=capex_range/1e6, y=lcoe_range)
        fig.add_vline(x=capex/1e6, line_dash="dash", line_color="red")
        fig.update_layout(
            height=300,
            xaxis_title="CAPEX ($M)",
            yaxis_title="LCOE ($/MWh)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### LCOE Sensitivity to Discount Rate")
        
        rates = np.linspace(0.05, 0.15, 10)
        lcoe_by_rate = []
        
        for r in rates:
            # Recalculate LCOE with different discount rate
            crf = (r * (1 + r) ** project_life) / ((1 + r) ** project_life - 1)
            adjusted_lcoe = lcoe * crf / ECONOMIC_DEFAULTS['crf_20yr_8pct']
            lcoe_by_rate.append(adjusted_lcoe)
        
        fig = px.line(x=rates * 100, y=lcoe_by_rate)
        fig.add_vline(x=discount_rate * 100, line_dash="dash", line_color="red")
        fig.update_layout(
            height=300,
            xaxis_title="Discount Rate (%)",
            yaxis_title="LCOE ($/MWh)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tornado chart
    st.markdown("##### Tornado Chart - LCOE Sensitivity")
    
    # Define sensitivities
    sensitivities = [
        {'Factor': 'CAPEX', 'Low': -20, 'High': +20, 'Impact_Low': -15, 'Impact_High': +15},
        {'Factor': 'Fuel Price', 'Low': -30, 'High': +30, 'Impact_Low': -8, 'Impact_High': +12},
        {'Factor': 'Capacity Factor', 'Low': -10, 'High': +10, 'Impact_Low': +8, 'Impact_High': -7},
        {'Factor': 'O&M Costs', 'Low': -20, 'High': +20, 'Impact_Low': -5, 'Impact_High': +5},
        {'Factor': 'Project Life', 'Low': -25, 'High': +25, 'Impact_Low': +4, 'Impact_High': -3},
    ]
    
    sens_df = pd.DataFrame(sensitivities)
    
    fig = go.Figure()
    
    for i, row in sens_df.iterrows():
        fig.add_trace(go.Bar(
            y=[row['Factor']],
            x=[row['Impact_High'] - row['Impact_Low']],
            base=[row['Impact_Low']],
            orientation='h',
            name=row['Factor'],
            marker_color=px.colors.qualitative.Set2[i % 8]
        ))
    
    fig.update_layout(
        height=300,
        xaxis_title="LCOE Change (%)",
        showlegend=False,
        barmode='relative'
    )
    
    fig.add_vline(x=0, line_width=2, line_color="black")
    
    st.plotly_chart(fig, use_container_width=True)


def render_comparison_tab(results):
    """Compare economics across problem statements"""
    
    st.markdown("#### Cross-Problem Economic Comparison")
    
    comparison_data = []
    
    for prob_num, result in results.items():
        if result and result.get('capex', 0) > 0:
            prob_info = PROBLEM_STATEMENTS.get(prob_num, {})
            comparison_data.append({
                'Problem': f"P{prob_num}: {prob_info.get('short_name', '')}",
                'CAPEX ($M)': result.get('capex', 0) / 1e6,
                'OPEX ($M/yr)': result.get('opex', 0) / 1e6 if result.get('opex') else 0,
                'LCOE ($/MWh)': result.get('lcoe', 0) if result.get('lcoe') else 0,
            })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Bar chart
        fig = px.bar(df, x='Problem', y='CAPEX ($M)', color='Problem',
                    color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run multiple problem optimizations to compare economics.")


def calculate_irr(capex, annual_cf, years):
    """Calculate IRR using Newton-Raphson method"""
    
    if annual_cf <= 0:
        return None
    
    # Cash flows: -CAPEX at year 0, +annual_cf for years 1 to n
    def npv(rate):
        return -capex + sum(annual_cf / (1 + rate) ** y for y in range(1, years + 1))
    
    # Newton-Raphson
    rate = 0.10  # Initial guess
    for _ in range(100):
        npv_val = npv(rate)
        
        # Derivative
        dnpv = sum(-y * annual_cf / (1 + rate) ** (y + 1) for y in range(1, years + 1))
        
        if abs(dnpv) < 1e-10:
            break
        
        new_rate = rate - npv_val / dnpv
        
        if abs(new_rate - rate) < 1e-6:
            return new_rate
        
        rate = new_rate
        
        # Bounds check
        if rate < -0.99 or rate > 1.0:
            return None
    
    return rate


if __name__ == "__main__":
    render()
