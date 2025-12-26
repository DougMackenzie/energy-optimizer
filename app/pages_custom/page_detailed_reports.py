"""
Detailed Reports Page
Customizable report generation and export to Word/PDF/PowerPoint
"""

import streamlit as st

def render():
    """Render the Detailed Reports page"""
    
    st.markdown("## 📄 Detailed Reports")
    st.caption("Generate comprehensive reports with customizable content for Word, PDF, or PowerPoint export")
    st.markdown("---")
    
    # Load sites
    if 'sites_list' not in st.session_state or len(st.session_state.sites_list) == 0:
        st.warning("⚠️ No sites configured yet. Please configure sites in the Dashboard first.")
        st.info("💡 Go to **📊 Dashboard** to set up your sites and run optimizations before generating reports.")
        return
    
    # =============================================================================
    # Report Configuration
    # =============================================================================
    st.markdown("### 📋 Report Configuration")
    
    col_conf1, col_conf2 = st.columns(2)
    
    with col_conf1:
        st.markdown("#### Site Selection")
        
        # Site selection
        site_options = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
        site_options.insert(0, "📊 Entire Portfolio")
        
        selected_sites = st.multiselect(
            "Select Sites",
            site_options,
            default=["📊 Entire Portfolio"],
            help="Choose individual sites or entire portfolio"
        )
        
        st.markdown("")
        st.markdown("#### Report Type")
        
        report_type = st.selectbox(
            "Select Template",
            [
                "📊 Executive Summary (2 pages)",
                "💼 Investor Deck (10-15 pages)",
                "🏗️ Engineering Report (30-50 pages)",
                "📈 Portfolio Overview (5-10 pages)",
                "🔍 Site Deep Dive (20-30 pages)"
            ]
        )
        
        st.markdown("")
        st.markdown("#### Export Format")
        
        export_format = st.radio(
            "Output Format",
            ["📝 Word (.docx)", "📄 PDF (.pdf)", "📊 PowerPoint (.pptx)"],
            horizontal=True
        )
    
    with col_conf2:
        st.markdown("#### Content Selection")
        
        # Detect which Gemini model is available
        gemini_model_name = "Gemini API"
        try:
            from app.utils.gemini_client import GeminiReportClient
            client = GeminiReportClient()
            gemini_model_name = client.model_name
        except:
            gemini_model_name = "Gemini Flash"
        
        # AI Analysis Toggle
        use_ai_analysis = st.checkbox(
            f"🤖 Enable AI-Generated Analysis ({gemini_model_name})",
            value=True,
            help="Use Gemini API to generate executive summary, financial analysis, and recommendations"
        )
        
        # Show data availability
        with st.expander("📊 Data Availability", expanded=False):
            from app.utils.portfolio_data import load_all_site_results
            try:
                site_results = load_all_site_results()
                st.success(f"✅ {len(site_results)} sites with optimization results available")
                for sr in site_results[:5]:  # Show first 5
                    st.caption(f"• {sr.get('site_name')}: {sr.get('stage')} stage - LCOE ${sr.get('lcoe', 0):.1f}/MWh")
                if len(site_results) > 5:
                    st.caption(f"... and {len(site_results) - 5} more")
            except:
                st.warning("⚠️ Unable to fetch optimization results from Google Sheets")
        
        st.markdown("")
        
        # Content checkboxes in expandable sections
        with st.expander("📌 Executive Summary", expanded=True):
            include_exec_overview = st.checkbox("Project Overview", value=True)
            include_exec_metrics = st.checkbox("Key Metrics", value=True)
            include_exec_highlights = st.checkbox("Investment Highlights", value=True)
        
        with st.expander("🔧 Technical Analysis"):
            include_load_profile = st.checkbox("Load Profile (8760 Sample Week)", value=True)
            include_equipment = st.checkbox("Equipment Specifications", value=True)
            include_optimization = st.checkbox("Optimization Results by Stage", value=True)
            include_dispatch = st.checkbox("Dispatch Simulation", value=False)
        
        with st.expander("💰 Financial Analysis"):
            include_cash_flow = st.checkbox("Cash Flow Projections & CapEx Breakdown", value=True)
            include_npv_irr = st.checkbox("NPV & IRR Analysis", value=True)
            include_sensitivity = st.checkbox("Sensitivity Analysis", value=False)
            include_lcoe_breakdown = st.checkbox("LCOE Breakdown & Comparison", value=True)
        
        with st.expander("📍 Site Information"):
            include_location_map = st.checkbox("Location Map (GeoJSON)", value=True)
            include_infrastructure = st.checkbox("Infrastructure Layers", value=True)
            include_land_details = st.checkbox("Land Details", value=False)
            include_permits = st.checkbox("Permits & Approvals", value=False)
        
        with st.expander("📊 Comparison"):
            include_stage_progression = st.checkbox("15-Year Energy Stack", value=True)
            include_lcoe_trend = st.checkbox("LCOE Trend Chart", value=True)
            include_equipment_evolution = st.checkbox("Equipment Evolution", value=True)
        
        with st.expander("📚 Appendices"):
            include_equipment_db = st.checkbox("Equipment Database", value=False)
            include_assumptions = st.checkbox("Assumptions", value=True)
            include_sources = st.checkbox("Data Sources", value=False)
    
    st.markdown("---")
    
    # =============================================================================
    # Report Preview
    # =============================================================================
    st.markdown("### 👀 Report Preview")
    
    # Show what will be included
    sections_count = sum([
        include_exec_overview, include_exec_metrics, include_exec_highlights,
        include_load_profile, include_equipment, include_optimization, include_dispatch,
        include_cash_flow, include_npv_irr, include_sensitivity, include_lcoe_breakdown,
        include_location_map, include_infrastructure, include_land_details, include_permits,
        include_stage_progression, include_lcoe_trend, include_equipment_evolution,
        include_equipment_db, include_assumptions, include_sources
    ])
    
    col_prev1, col_prev2, col_prev3 = st.columns(3)
    
    with col_prev1:
        st.metric("Sites Selected", len(selected_sites))
    
    with col_prev2:
        st.metric("Sections Included", sections_count)
    
    with col_prev3:
        estimated_pages = sections_count * 2  # Rough estimate
        st.metric("Est. Page Count", f"~{estimated_pages}")
    
    st.markdown("")
    
    # Preview of sections
    with st.expander("📄 View Section List"):
        sections = []
        
        if include_exec_overview:
            sections.append("1. Executive Summary - Project Overview")
        if include_exec_metrics:
            sections.append("2. Executive Summary - Key Metrics")
        if include_exec_highlights:
            sections.append("3. Executive Summary - Investment Highlights")
        if include_load_profile:
            sections.append("4. Technical Analysis - Load Profile")
        if include_equipment:
            sections.append("5. Technical Analysis - Equipment Specifications")
        if include_optimization:
            sections.append("6. Technical Analysis - Optimization Results")
        if include_dispatch:
            sections.append("7. Technical Analysis - Dispatch Simulation")
        if include_cash_flow:
            sections.append("8. Financial Analysis - Cash Flow Projections")
        if include_npv_irr:
            sections.append("9. Financial Analysis - NPV & IRR")
        if include_sensitivity:
            sections.append("10. Financial Analysis - Sensitivity Analysis")
        if include_lcoe_breakdown:
            sections.append("11. Financial Analysis - LCOE Breakdown")
        if include_location_map:
            sections.append("12. Site Information - Location Map")
        if include_infrastructure:
            sections.append("13. Site Information - Infrastructure Layers")
        if include_land_details:
            sections.append("14. Site Information - Land Details")
        if include_permits:
            sections.append("15. Site Information - Permits")
        if include_stage_progression:
            sections.append("16. Comparison - Stage Progression")
        if include_lcoe_trend:
            sections.append("17. Comparison - LCOE Trend")
        if include_equipment_evolution:
            sections.append("18. Comparison - Equipment Evolution")
        if include_equipment_db:
            sections.append("Appendix A - Equipment Database")
        if include_assumptions:
            sections.append("Appendix B - Assumptions")
        if include_sources:
            sections.append("Appendix C - Data Sources")
        
        for section in sections:
            st.markdown(f"- {section}")
    
    st.markdown("---")
    
    # =============================================================================
    # Generate Report
    # =============================================================================
    st.markdown("### 🚀 Generate Report")
    
    col_gen1, col_gen2, col_gen3 = st.columns([1, 1, 1])
    
    with col_gen2:
        if st.button("📥 Generate & Download Report", use_container_width=True, type="primary"):
            # Prepare content options dict
            content_dict = {
                'include_exec_overview': include_exec_overview,
                'include_exec_metrics': include_exec_metrics,
                'include_exec_highlights': include_exec_highlights,
                'include_load_profile': include_load_profile,
                'include_equipment': include_equipment,
                'include_optimization': include_optimization,
                'include_dispatch': include_dispatch,
                'include_cash_flow': include_cash_flow,
                'include_npv_irr': include_npv_irr,
                'include_sensitivity': include_sensitivity,
                'include_lcoe_breakdown': include_lcoe_breakdown,
                'include_location_map': include_location_map,
                'include_infrastructure': include_infrastructure,
                'include_land_details': include_land_details,
                'include_permits': include_permits,
                'include_stage_progression': include_stage_progression,
                'include_lcoe_trend': include_lcoe_trend,
                'include_equipment_evolution': include_equipment_evolution,
                'include_equipment_db': include_equipment_db,
                'include_assumptions': include_assumptions,
                'include_sources': include_sources
            }
            
            # Generate report based on format
            if "Word" in export_format:
                # Show estimated time
                est_time = len(selected_sites) * 15  # ~15 seconds per site
                st.info(f"⏱️ Estimated generation time: ~{est_time} seconds")
                
                with st.spinner(f"Generating enhanced Word document with real data from Google Sheets... This may take {est_time}-{est_time+30} seconds"):
                    from datetime import datetime
                    
                    # Try to use enhanced builder first
                    try:
                        from app.utils.enhanced_report_builder import generate_enhanced_word_report
                        
                        # Generate document with AI and real data
                        doc_bytes = generate_enhanced_word_report(
                            selected_sites,
                            content_dict,
                            st.session_state.sites_list,
                            use_ai=use_ai_analysis
                        )
                        
                        st.success("✅ Enhanced report generated with real Google Sheets data!")
                        if use_ai_analysis:
                            # Show which model was actually used
                            try:
                                from app.utils.gemini_client import GeminiReportClient
                                client = GeminiReportClient()
                                st.info(f"🤖 AI-generated insights included ({client.model_name})")
                            except:
                                st.info("🤖 AI-generated insights included (Gemini Flash)")
                        
                    except Exception as e:
                        st.warning(f"Enhanced builder unavailable ({str(e)}), using fallback...")
                        
                        # Fallback to basic builder
                        from app.utils.report_builder import generate_word_report
                        doc_bytes = generate_word_report(
                            selected_sites,
                            content_dict,
                            st.session_state.sites_list
                        )
                        st.info("ℹ️ Basic report generated (enhanced features unavailable)")
                    
                    # Create download button
                    st.download_button(
                        label="💾 Download Report.docx",
                        data=doc_bytes,
                        file_name=f"Energy_Optimization_Report_{datetime.now().strftime('%Y%m%d')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary"
                    )
            
            elif "PDF" in export_format:
                st.info("📄 PDF export coming soon - use Word export and convert to PDF")
            
            elif "PowerPoint" in export_format:
                st.info("📊 PowerPoint export coming in Phase 5")
    
    st.markdown("")
    st.caption("💡 Tip: Start with a smaller report (Executive Summary) to test the export functionality")
