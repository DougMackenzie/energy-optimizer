"""
Configuration Page  
Configure site, problem type, and run optimization
"""

import streamlit as st
from app.utils.site_context_helper import display_site_context
from config.settings import PROBLEM_STATEMENTS


def render():
    st.markdown("### ⚙️ Configuration")
    st.caption("Configure site parameters, select problem type, and run optimization")
    
    # Display site context
    display_site_context()
    
    # Site selector
    st.markdown("#### Site Selection")
    
    if 'sites_list' in st.session_state and st.session_state.sites_list:
        site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
        selected_site_idx = st.selectbox(
            "Select Site to Optimize",
            options=range(len(site_names)),
            format_func=lambda i: site_names[i],
            index=0 if not st.session_state.get('current_site') else 
                  (site_names.index(st.session_state.current_site) if st.session_state.current_site in site_names else 0),
            key="config_site_selector"
        )
        
        selected_site = st.session_state.sites_list[selected_site_idx]
        site_name = selected_site.get('name')
        
        # Update current site
        if site_name != st.session_state.get('current_site'):
            st.session_state.current_site = site_name
            st.rerun()
    else:
        st.warning("No sites configured. Please create a site in Dashboard → Sites & Infrastructure")
        return
    
    st.markdown("---")
    
    # Site Parameters Display
    st.markdown("#### Site Parameters")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.info(f"""
        **Location:** {selected_site.get('location', 'N/A')}  
        **ISO:** {selected_site.get('iso', 'N/A')}  
        **Voltage:** {selected_site.get('voltage_kv', 'N/A')} kV
        """)
    
    with col_p2:
        st.info(f"""
        **IT Capacity:** {selected_site.get('it_capacity_mw', 'N/A')} MW  
        **PUE:** {selected_site.get('pue', 'N/A')}  
        **Facility MW:** {selected_site.get('facility_mw', 'N/A')} MW
        """)
    
    with col_p3:
        st.info(f"""
        **Land:** {selected_site.get('land_acres', 'N/A')} acres  
        **NOx Limit:** {selected_site.get('nox_limit_tpy', 'N/A')} tons/yr  
        **Gas Supply:** {selected_site.get('gas_supply_mcf', 'N/A')} MCF
        """)
    
    st.markdown("---")
    

    # Display problem type prominently
    problem_num_display = st.session_state.get('optimization_problem_num', selected_site.get('problem_num', 1)) if st.session_state.get('optimization_site') == selected_site['name'] else selected_site.get('problem_num', 1)
    from config.settings import PROBLEM_STATEMENTS
    problem_info_display = PROBLEM_STATEMENTS.get(problem_num_display, PROBLEM_STATEMENTS[1])
    
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%); 
                padding: 16px 24px; 
                border-radius: 8px; 
                margin-bottom: 20px;
                border-left: 4px solid #2b6cb0;">
        <div style="color: white; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
            {problem_info_display['icon']} PROBLEM STATEMENT
        </div>
        <div style="color: #bee3f8; font-size: 18px; font-weight: 700;">
            P{problem_num_display}: {problem_info_display['name']}
        </div>
        <div style="color: #90cdf4; font-size: 13px; margin-top: 4px;">
            {problem_info_display['objective']} — {problem_info_display['question']}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Problem Type Selection
    st.markdown("#### Problem Type Selection")
    
    # Get current problem type for this site
    current_problem = selected_site.get('problem_num', 1)
    
    problem_options = {
        prob_num: f"{prob['icon']} {prob['name']}"
        for prob_num, prob in PROBLEM_STATEMENTS.items()
    }
    
    selected_problem = st.selectbox(
        "Select Problem Statement",
        options=list(problem_options.keys()),
        format_func=lambda p: problem_options[p],
        index=current_problem - 1 if current_problem in problem_options else 0,
        key="config_problem_selector"
    )
    
    # Show problem details
    prob_info = PROBLEM_STATEMENTS[selected_problem]
    
    st.markdown(f"""
    **Objective:** {prob_info['objective']}  
    **Question:** {prob_info['question']}  
    **Key Output:** {prob_info['key_output']}
    """)
    
    # Save problem type to site
    if selected_problem != current_problem:
        selected_site['problem_num'] = selected_problem
        selected_site['problem_name'] = prob_info['name']
        
        # Store in session state for immediate use
        st.session_state.optimization_problem_num = selected_problem
        st.session_state.optimization_site = selected_site['name']
        
        # Save to Google Sheets
        try:
            from app.utils.site_backend import update_site
            update_site(selected_site['name'], {
                'problem_num': selected_problem,
                'problem_name': prob_info['name']
            })
            st.success(f"✓ Problem type saved to Google Sheets: {prob_info['name']}")
        except Exception as e:
            st.warning(f"Problem type updated in session (Sheets save failed: {str(e)})")
    
    st.markdown("---")
    
    # Load Configuration
    st.markdown("#### Load Profile")
    
    col_l1, col_l2 = st.columns([3, 1])
    
    with col_l1:
        if 'load_profile_dr' in st.session_state:
            load_config = st.session_state.load_profile_dr
            peak_mw = load_config.get('peak_it_mw', 0) * load_config.get('pue', 1.25)
            st.info(f"""
            **Peak IT Load:** {load_config.get('peak_it_mw', 0):.0f} MW  
            **PUE:** {load_config.get('pue', 1.25):.2f}  
            **Peak Facility Load:** {peak_mw:.0f} MW
            """)
        else:
            st.warning("⚠️ No load profile configured for this site")
    
    with col_l2:
        if st.button("📈 Edit Load", use_container_width=True):
            st.session_state.current_page = 'load_composer'
            st.rerun()
    
    st.markdown("---")
    
    # EPC Stage Selection
    st.markdown("#### EPC Stage Selection")
    
    stage_options = {
        'screening': '1️⃣ Screening Study (Heuristic)',
        'concept': '2️⃣ Concept Development (MILP)',
        'preliminary': '3️⃣ Preliminary Design (MILP)',
        'detailed': '4️⃣ Detailed Design (MILP)'
    }
    
    selected_stage = st.radio(
        "Select Optimization Stage",
        options=list(stage_options.keys()),
        format_func=lambda s: stage_options[s],
        index=0,
        key="config_stage_selector",
        horizontal=True
    )
    
    # Update current stage
    st.session_state.current_stage = selected_stage
    
    # Show stage details
    stage_info = {
        'screening': {
            'solver': 'Heuristic',
            'runtime': '30-60 seconds',
            'accuracy': '±50% (Class 5)',
            'description': 'Fast feasibility check with rough equipment sizing'
        },
        'concept': {
            'solver': 'MILP',
            'runtime': '5-15 minutes',
            'accuracy': '±20% (Class 3)',
            'description': 'Detailed optimization with equipment schedules and economics'
        },
        'preliminary': {
            'solver': 'MILP',
            'runtime': '10-30 minutes',
            'accuracy': '±10% (Class 2)',
            'description': 'Refined optimization with vendor quotes and actual constraints'
        },
        'detailed': {
            'solver': 'MILP',
            'runtime': '15-60 minutes',
            'accuracy': '±5% (Class 1)',
            'description': 'Final optimization with as-built parameters and construction schedule'
        }
    }
    
    info = stage_info[selected_stage]
    
    st.info(f"""
    **Solver:** {info['solver']}  
    **Estimated Runtime:** {info['runtime']}  
    **Accuracy:** {info['accuracy']}  
    **Description:** {info['description']}
    """)
    
    st.markdown("---")
    
    # Run Optimization
    st.markdown("#### Run Optimization")
    
    col_run1, col_run2, col_run3 = st.columns([2, 1, 1])
    
    with col_run1:
        st.success(f"""
        **Ready to run:**  
        Site: {site_name}  
        Problem: {prob_info['name']}  
        Stage: {stage_options[selected_stage]}
        """)
    
    with col_run2:
        run_button = st.button(
            "🚀 Run Optimization",
            type="primary",
            use_container_width=True,
            key="run_optimization_btn"
        )
    
    with col_run3:
        if st.button("📊 View Results", use_container_width=True):
            st.session_state.current_page = 'exec_summary'
            st.rerun()
    

    if run_button:
        # Check stage
        if selected_stage == 'screening':
            # Run heuristic optimization
            with st.spinner(f"⏳ Running heuristic optimization for {site_name}..."):
                try:
                    from app.utils.optimizer_backend import run_heuristic_optimization
                    from app.utils.site_backend import save_site_stage_result
                    
                    # Run optimization
                    result = run_heuristic_optimization(
                        site_data=selected_site,
                        problem_num=selected_problem,
                        load_profile=st.session_state.get('load_profile_dr')
                    )
                    
                    if result and result.get('feasible'):
                        # Store in session state (don't auto-save)
                        st.session_state.optimization_result = result
                        st.session_state.optimization_site = site_name
                        st.session_state.optimization_stage = selected_stage
                        
                        st.success(f"""
                        ✅ **Optimization Complete!**
                        
                        **LCOE:** ${result.get('lcoe', 0):.1f}/MWh  
                        **Equipment:** {result.get('equipment', {}).get('recip_mw', 0):.0f} MW Recip + {result.get('equipment', {}).get('turbine_mw', 0):.0f} MW Turbine + {result.get('equipment', {}).get('bess_mwh', 0):.0f} MWh BESS + {result.get('equipment', {}).get('solar_mw', 0):.0f} MW Solar  
                        **Runtime:** {result.get('runtime_seconds', 0):.1f} seconds
                        """)
                        
                        st.info("💡 Results ready. Use 'Save Results' button below to save to Google Sheets.")
                    else:
                        st.error(f"❌ Optimization infeasible: {result.get('error', 'Unknown error')}")
                        if 'violations' in result:
                            st.warning("**Constraint Violations:**")
                            for violation in result['violations']:
                                st.write(f"- {violation}")
                
                except Exception as e:
                    st.error(f"❌ Error running optimization: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            # MILP stages
            st.warning(f"⚠️ {stage_options[selected_stage]} not yet implemented")
            st.info("""
            **MILP Optimization Coming Soon!**
            
            For now, only Screening Study (Heuristic) is available.
            """)
    
    # Manual Save Results Section
    if 'optimization_result' in st.session_state and st.session_state.get('optimization_site') == site_name:
        st.markdown("---")
        st.markdown("### 💾 Save Optimization Results")
        
        col_sv1, col_sv2, col_sv3 = st.columns([2, 1, 1])
        
        with col_sv1:
            save_option = st.radio(
                "Save as:",
                options=['new', 'overwrite'],
                format_func=lambda x: "🆕 New Version (recommended)" if x == 'new' else "♻️ Overwrite Version 1",
                horizontal=True,
                key="save_option_radio"
            )
        
        with col_sv2:
            if st.button("💾 Save to Sheets", type="primary", use_container_width=True, key="save_results_btn"):
                try:
                    from app.utils.site_backend import save_site_stage_result
                    
                    result = st.session_state.optimization_result
                    result['version'] = 1  # TODO: Implement version tracking
                    
                    save_site_stage_result(
                        site_name=st.session_state.optimization_site,
                        stage=st.session_state.optimization_stage,
                        result_data=result
                    )
                    
                    st.success(f"✅ Results saved to Google Sheets!")
                    
                    # Clear stored result
                    del st.session_state.optimization_result
                    del st.session_state.optimization_site
                    del st.session_state.optimization_stage
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col_sv3:
            if st.button("📊 View Results", use_container_width=True, key="view_results_btn"):
                st.session_state.current_page = 'exec_summary'
                st.rerun()

