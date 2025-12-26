"""
Investor Portal Page
Financial metrics, ROI, and portfolio analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

def render():
    """Render the Investor Portal page"""
    
    st.markdown("## 💰 Investor Portal")
    st.caption("Financial metrics, returns analysis, and portfolio performance")
    st.markdown("---")
    
    # Load sites and optimization results
    if 'sites_list' not in st.session_state or len(st.session_state.sites_list) == 0:
        st.warning("⚠️ No sites configured yet. Please configure sites in the Dashboard first.")
        st.info("💡 Go to **📊 Dashboard** to set up your sites and run optimizations.")
        return
    
    # Initialize portfolio financial data
    from app.utils.financial_calculations import (
        calculate_portfolio_metrics,
        calculate_site_financials
    )
    
    # Load optimization results from Google Sheets for all sites
    from app.utils.site_backend import load_site_stage_result
    
    portfolio_data = []
    sites_without_results = []
    
    for site in st.session_state.sites_list:
        site_name = site.get('name', 'Unknown')
        
        # Get latest completed stage results
        found_result = False
        for stage in ['detailed', 'preliminary', 'concept', 'screening']:
            try:
                result = load_site_stage_result(site_name, stage)
                if result and str(result.get('complete', '')).upper() == 'TRUE':
                    # Calculate financial metrics
                    financials = calculate_site_financials(site, result)
                    portfolio_data.append({
                        'site': site_name,
                        'stage': stage.capitalize(),
                        'capacity_mw': site.get('it_capacity_mw', 0),
                        **financials
                    })
                    found_result = True
                    break
            except Exception as e:
                st.error(f"Error loading {site_name} - {stage}: {str(e)}")
                continue
        
        if not found_result:
            sites_without_results.append(site_name)
    
    # Show warning if some sites have no results
    if sites_without_results:
        with st.expander(f"⚠️ {len(sites_without_results)} site(s) have no optimization results", expanded=False):
            st.warning(
                f"The following sites need optimization results:\n\n" +
                "\n".join([f"• {name}" for name in sites_without_results])
            )
            st.info("💡 Run optimizations for these sites to include them in portfolio analysis.")
    
    if not portfolio_data:
        st.error("❌ No optimization results found for any site.")
        st.info("Please run optimizations on at least one site to view financial analysis.")
        st.markdown("### Next Steps:")
        st.markdown("1. Go to **⚙️ Configuration** to set up site parameters")
        st.markdown("2. Navigate to **📊 Executive Summary** to run optimizations")
        st.markdown("3. Return here to view portfolio financial metrics")
        return
    
    # Calculate portfolio-level metrics
    portfolio_metrics = calculate_portfolio_metrics(portfolio_data)
    
    # =============================================================================
    # Portfolio Summary Metrics
    # =============================================================================
    st.markdown("### Portfolio Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Portfolio NPV",
            f"${portfolio_metrics['total_npv']:.1f}M",
            help="Sum of Net Present Value across all sites"
        )
    
    with col2:
        st.metric(
            "Weighted Avg LCOE",
            f"${portfolio_metrics['weighted_lcoe']:.1f}/MWh",
            help="Capacity-weighted average Levelized Cost of Energy"
        )
    
    with col3:
        st.metric(
            "Total CapEx",
            f"${portfolio_metrics['total_capex']:.1f}M",
            help="Total Capital Expenditure required"
        )
    
    with col4:
        st.metric(
            "Portfolio IRR",
            f"{portfolio_metrics['portfolio_irr']:.1f}%",
            help="Internal Rate of Return (estimated)"
        )
    
    st.markdown("")
    
    # =============================================================================
    # Site-by-Site Financial Table
    # =============================================================================
    st.markdown("### Site Financial Comparison")
    
    # Create DataFrame
    df = pd.DataFrame(portfolio_data)
    
    # Format and display
    if not df.empty:
        display_df = df[['site', 'stage', 'capacity_mw', 'capex_m', 'opex_annual_m', 
                         'npv_m', 'irr_pct', 'lcoe', 'payback_years']].copy()
        
        display_df.columns = ['Site', 'Stage', 'Capacity (MW)', 'CapEx ($M)', 
                              'OpEx ($/yr)', 'NPV ($M)', 'IRR (%)', 'LCOE ($/MWh)', 'Payback (yr)']
        
        # Format numbers
        for col in ['CapEx ($M)', 'OpEx ($/yr)', 'NPV ($M)']:
            display_df[col] = display_df[col].apply(lambda x: f"${x:.1f}M" if pd.notna(x) else "—")
        
        for col in ['IRR (%)', 'Payback (yr)']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
        
        display_df['LCOE ($/MWh)'] = display_df['LCOE ($/MWh)'].apply(lambda x: f"${x:.1f}" if pd.notna(x) else "—")
        display_df['Capacity (MW)'] = display_df['Capacity (MW)'].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # =============================================================================
    # Financial Charts
    # =============================================================================
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### NPV by Site")
        from app.utils.investor_charts import create_npv_chart
        fig_npv = create_npv_chart(portfolio_data)
        st.plotly_chart(fig_npv, use_container_width=True)
    
    with col_chart2:
        st.markdown("#### IRR Comparison")
        from app.utils.investor_charts import create_irr_chart
        fig_irr = create_irr_chart(portfolio_data)
        st.plotly_chart(fig_irr, use_container_width=True)
    
    st.markdown("")
    
    col_chart3, col_chart4 = st.columns(2)
    
    with col_chart3:
        st.markdown("#### LCOE vs Capacity")
        from app.utils.investor_charts import create_lcoe_capacity_bubble
        fig_bubble = create_lcoe_capacity_bubble(portfolio_data)
        st.plotly_chart(fig_bubble, use_container_width=True)
    
    with col_chart4:
        st.markdown("#### Cash Flow Waterfall")
        from app.utils.investor_charts import create_cash_flow_waterfall
        # Use first site as example
        fig_waterfall = create_cash_flow_waterfall(portfolio_data[0])
        st.plotly_chart(fig_waterfall, use_container_width=True)
    
    st.markdown("---")
    
    # =============================================================================
    # Export Options
    # =============================================================================
    st.markdown("### Export Options")
    st.caption("Download portfolio financial data in various formats")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        if st.button("📥 Download Excel Model", use_container_width=True, type="primary", 
                     help="Export complete financial model with charts to Excel"):
            try:
                # Generate Excel file
                from app.utils.excel_export import create_portfolio_excel
                import io
                
                excel_buffer = create_portfolio_excel(portfolio_data, portfolio_metrics)
                
                # Download button
                st.download_button(
                    label="💾 Download Portfolio_Financials.xlsx",
                    data=excel_buffer,
                    file_name=f"Portfolio_Financials_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                st.success("✅ Excel file ready! Click above to download.")
            except Exception as e:
                st.error(f"❌ Error generating Excel file: {str(e)}")
                st.info("Please try again or contact support if the issue persists.")
    
    with col_exp2:
        if st.button("📥 Download PDF Summary", use_container_width=True,
                     help="Export 2-page executive summary as PDF (coming soon)"):
            st.info("📄 PDF export coming soon - use Excel or Word export for now")
    
    with col_exp3:
        if st.button("📥 Export CSV Data", use_container_width=True,
                     help="Export raw data as CSV for custom analysis"):
            if not df.empty:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"portfolio_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                st.success("✅ CSV ready! Click above to download.")


