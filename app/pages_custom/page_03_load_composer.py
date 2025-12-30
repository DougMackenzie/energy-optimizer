"""
Enhanced Load Composer Page with Demand Response Configuration
Integrates workload mix, cooling flexibility, and DR economics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from app.utils.load_profile_generator import (
    generate_load_profile_with_flexibility,
    calculate_dr_economics
)
from app.utils.site_context_helper import display_site_context


def render():
    st.markdown("### ⚡ Load Composer with Demand Response")
    
    # =========================================================================
    # SITE SELECTOR
    # =========================================================================
    st.markdown("#### 📍 Select Site")
    
    if 'sites_list' in st.session_state and st.session_state.sites_list:
        site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
        
        # Get current site or default to first
        current_site_name = st.session_state.get('current_site', site_names[0])
        current_index = site_names.index(current_site_name) if current_site_name in site_names else 0
        
        selected_site = st.selectbox(
            "Select Site for Load Configuration",
            options=site_names,
            index=current_index,
            key="load_composer_site_selector",
            help="Select the site to configure load profile for"
        )
        
        # Update current site if changed
        if selected_site != st.session_state.get('current_site'):
            st.session_state.current_site = selected_site
            st.rerun()
        
        # Display site context
        from app.utils.site_context_helper import display_site_context
        display_site_context(selected_site)
        
    else:
        st.warning("⚠️ No sites configured. Navigate to Dashboard → Sites & Infrastructure to select a site and start optimization.")
        st.info("💡 **Tip:** The Load Composer requires a site to be selected first. Each site can have its own unique load profile.")
        return
    
    # =========================================================================
    # LOAD CONFIGURATION FROM BACKEND
    # =========================================================================
    # Initialize load config from Google Sheets on first load or site change
    if ('load_config' not in st.session_state or 
        st.session_state.get('load_config_site') != selected_site):
        from app.utils.load_backend import load_load_configuration
        st.session_state.load_config = load_load_configuration(selected_site)
        st.session_state.load_config_site = selected_site
        print(f"✓ Loaded load config for {selected_site} from backend")
    
    st.markdown("---")
    # Add button to load 600MW sample problem
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.info("""
        **Configure facility load profile with demand response capabilities**
        
        Define IT workload mix, cooling flexibility, and DR participation to optimize power costs.
        """)
    
    with col_header2:
        if st.button("📥 Load 600MW Sample", type="primary", use_container_width=True, 
                     help="Load the sample 600MW AI data center problem"):
            try:
                from sample_problem_600mw import get_sample_problem
                problem = get_sample_problem()
                
                # Load problem data into session state
                st.session_state.load_profile_dr = {
                    'peak_it_mw': float(problem['load_profile']['peak_it_mw']),  # Ensure float type
                    'pue': float(problem['load_profile']['pue']),  # Ensure float type
                    'load_factor': float(problem['load_profile']['load_factor']),  # Ensure float type
                    'workload_mix': {
                        'pre_training': int(problem['load_profile']['workload_mix']['pre_training'] * 100),
                        'fine_tuning': int(problem['load_profile']['workload_mix']['fine_tuning'] * 100),
                        'batch_inference': int(problem['load_profile']['workload_mix']['batch_inference'] * 100),
                        'realtime_inference': int(problem['load_profile']['workload_mix']['realtime_inference'] * 100),
                        'rl_training': 0,
                        'cloud_hpc': 0,
                    },
                    'cooling_flex': 0.25,
                    'thermal_constant_min': 30,
                    'enabled_dr_products': ['economic_dr'],
                }
                
                # CRITICAL FIX: Also load constraints and create current_config
                # This ensures the MILP optimizer has all required data
                st.session_state.current_config = {
                    'site': {
                        'Site_Name': '600MW Sample Problem',
                        'ISO': 'ERCOT',
                        'IT_Capacity_MW': 600,
                        'Total_Facility_MW': 750,  # 600 × 1.25 PUE
                        'Design_PUE': 1.25,
                    },
                    'scenario': {
                        'Scenario_Name': 'All Technologies',
                        'Description': '600MW sample problem from diagnostic',
                        'Recip_Enabled': True,
                        'Turbine_Enabled': True,
                        'BESS_Enabled': True,
                        'Solar_Enabled': True,
                        'Grid_Enabled': True,
                        'Target_LCOE_MWh': 85,
                        'Target_Deployment_Months': 24,
                    },
                    'equipment_enabled': {
                        'recip': True,
                        'turbine': True,
                        'bess': True,
                        'solar': True,
                        'grid': True,
                    },
                    'constraints': {
                        **problem['constraints'],  # Load all constraints
                        'N_Minus_1_Required': False,  # Disable N-1 for BTM scenarios
                    },
                    'objectives': {
                        'Primary_Objective': 'Minimize_LCOE',
                        'LCOE_Max_MWh': 100,
                        'Deployment_Max_Months': 36,
                    }
                }
                
                st.success("✅ Loaded 600MW sample problem with constraints!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load sample problem: {e}")
    
    # Comprehensive session state initialization
    def ensure_load_profile_complete():
        """Ensure load_profile_dr dict has all required keys with defaults"""
        defaults = {
            'peak_it_mw': 600.0,
            'pue': 1.25,
            'load_factor': 0.85,
            'workload_mix': {
                'pre_training': 45,
                'fine_tuning': 20,
                'batch_inference': 15,
                'realtime_inference': 20,
                'rl_training': 0,
                'cloud_hpc': 0,
            },
            'cooling_flex': 0.25,
            'thermal_constant_min': 30,
            'enabled_dr_products': ['economic_dr'],
        }
        
        if 'load_profile_dr' not in st.session_state:
            st.session_state.load_profile_dr = defaults.copy()
            return
        
        # Merge missing keys (existing values take precedence)
        for key, value in defaults.items():
            if key not in st.session_state.load_profile_dr:
                st.session_state.load_profile_dr[key] = value
            elif isinstance(value, dict) and isinstance(st.session_state.load_profile_dr.get(key), dict):
                # Deep merge nested dicts like workload_mix
                for subkey, subvalue in value.items():
                    if subkey not in st.session_state.load_profile_dr[key]:
                        st.session_state.load_profile_dr[key][subkey] = subvalue
    
    # Call initialization helper
    ensure_load_profile_complete()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Basic Load", "🔄 Workload Mix", "❄️ Cooling Flexibility", "💰 DR Economics", "📈 Load Variability", "💾 Backend & Trajectory"
    ])
    
    # =========================================================================
    # TAB 6: BACKEND & TRAJECTORY (NEW)
    # =========================================================================
    with tab6:
        st.markdown("#### 💾 Load Configuration Management")
        st.caption("Configure load trajectory and sync with Google Sheets backend")
        
        # Display current configuration
        col1, col2, col3 = st.columns(3)
        with col1:
            peak_it = st.number_input(
                "Peak IT Load (MW)",
                min_value=0.0,
                max_value=2000.0,
                value=st.session_state.load_config.get('peak_it_load_mw', 600.0),
                step=10.0,
                key='backend_peak_it'
            )
            st.session_state.load_config['peak_it_load_mw'] = peak_it
        
        with col2:
            pue_backend = st.number_input(
                "PUE",
                min_value=1.0,
                max_value=2.0,
                value=st.session_state.load_config.get('pue', 1.25),
                step=0.01,
                key='backend_pue'
            )
            st.session_state.load_config['pue'] = pue_backend
        
        with col3:
            load_factor_backend = st.slider(
                "Load Factor (%)",
                min_value=50.0,
                max_value=100.0,
                value=st.session_state.load_config.get('load_factor_pct', 85.0),
                step=1.0,
                key='backend_load_factor'
            )
            st.session_state.load_config['load_factor_pct'] = load_factor_backend
        
        # Calculated metrics
        peak_facility = peak_it * pue_backend
        avg_load = peak_facility * (load_factor_backend / 100.0)
        annual_energy = avg_load * 8760 / 1000
        
        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Peak Facility Load", f"{peak_facility:.1f} MW")
        col_m2.metric("Average Load", f"{avg_load:.1f} MW")
        col_m3.metric("Annual Energy", f"{annual_energy:.1f} GWh")
        
        # Growth trajectory editor
        st.markdown("#### 📈 Load Growth Trajectory")
        
        growth_enabled = st.checkbox(
            "Enable load growth over planning horizon",
            value=st.session_state.load_config.get('growth_enabled', True),
            key='backend_growth_enabled'
        )
        st.session_state.load_config['growth_enabled'] = growth_enabled
        
        if growth_enabled:
            st.markdown("**Edit Growth Steps:**")
            st.caption("Define when IT load reaches each milestone. Facility load will be calculated as IT Load × PUE.")
            
            # Get current growth steps
            import pandas as pd
            growth_steps = st.session_state.load_config.get('growth_steps', [
                {'year': 2027, 'load_mw': 0},
                {'year': 2028, 'load_mw': 150},
                {'year': 2029, 'load_mw': 300},
                {'year': 2030, 'load_mw': 450},
                {'year': 2031, 'load_mw': 600},
            ])
            
            growth_df = pd.DataFrame(growth_steps)
            
            # Editable table
            edited_df = st.data_editor(
                growth_df,
                num_rows="dynamic",
                column_config={
                    "year": st.column_config.NumberColumn(
                        "Year",
                        min_value=2025,
                        max_value=2050,
                        step=1,
                        required=True
                    ),
                    "load_mw": st.column_config.NumberColumn(
                        "IT Load (MW)",
                        min_value=0.0,
                        max_value=peak_it,
                        step=10.0,
                        required=True
                    )
                },
                hide_index=True,
                key='trajectory_editor'
            )
            
            # Update session state
            st.session_state.load_config['growth_steps'] = edited_df.to_dict('records')
            
            # Generate and visualize trajectory
            from app.utils.load_backend import generate_full_trajectory
            trajectory = generate_full_trajectory(
                edited_df.to_dict('records'),
                pue_backend,
                planning_horizon=15
            )
            
            # Trajectory chart
            import plotly.graph_objects as go
            fig_traj = go.Figure()
            fig_traj.add_trace(go.Scatter(
                x=list(trajectory.keys()),
                y=list(trajectory.values()),
                mode='lines+markers',
                name='Facility Load',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
            fig_traj.update_layout(
                title="15-Year Load Trajectory",
                xaxis_title="Year",
                yaxis_title="Facility Load (MW)",
                height=400
            )
            st.plotly_chart(fig_traj, use_container_width=True)
        
        # Save button
        st.markdown("---")
        col_save1, col_save2 = st.columns([3, 1])
        
        with col_save1:
            if st.session_state.load_config.get('last_updated'):
                st.caption(f"💾 Last saved: {st.session_state.load_config['last_updated'][:19]}")
            else:
                st.caption("⚠️ Configuration not yet saved to backend")
        
        with col_save2:
            if st.button("💾 Save Configuration", type="primary", use_container_width=True, key='save_load_config'):
                from app.utils.load_backend import save_load_configuration
                success = save_load_configuration(selected_site, st.session_state.load_config)
                if success:
                    st.success("✅ Load configuration saved to Google Sheets!")
                    st.session_state.load_config['last_updated'] = pd.Timestamp.now().isoformat()
                    st.rerun()
                else:
                    st.error("❌ Failed to save configuration. Check terminal for errors.")
    
    # =========================================================================
    # TAB 1: BASIC FACILITY PARAMETERS
    # =========================================================================
    with tab1:
        st.markdown("#### Basic Facility Parameters")
        
        # Use load_config from backend
        col1, col2, col3 = st.columns(3)
        
        with col1:
            peak_it_mw = st.number_input(
                "Peak IT Load (MW)", 
                min_value=10.0, max_value=2000.0, 
                value=float(st.session_state.load_config.get('peak_it_load_mw', 600.0)), 
                step=10.0,
                help="Peak IT equipment load excluding cooling",
                key='tab1_peak_it'
            )
            st.session_state.load_config['peak_it_load_mw'] = peak_it_mw
            # Also update DR config for compatibility
            st.session_state.load_profile_dr['peak_it_mw'] = peak_it_mw
        
        with col2:
            pue = st.number_input(
                "PUE", 
                min_value=1.0, max_value=2.0, 
                value=float(st.session_state.load_config.get('pue', 1.25)), 
                step=0.01,
                help="Power Usage Effectiveness (1.2-1.4 typical for modern facilities)",
                key='tab1_pue'
            )
            st.session_state.load_config['pue'] = pue
            st.session_state.load_profile_dr['pue'] = pue
        
        with col3:
            load_factor = st.slider(
                "Load Factor (%)", 
                min_value=50, max_value=100, 
                value=int(st.session_state.load_config.get('load_factor_pct', 85.0)),
                help="Average utilization as % of peak",
                key='tab1_load_factor'
            )
            st.session_state.load_config['load_factor_pct'] = float(load_factor)
            st.session_state.load_profile_dr['load_factor'] = load_factor / 100.0
        
        # Calculate derived values
        peak_facility_mw = peak_it_mw * pue
        avg_facility_mw = peak_facility_mw * (load_factor / 100.0)
        
        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Peak Facility Load", f"{peak_facility_mw:.1f} MW")
        col_m2.metric("Average Load", f"{avg_facility_mw:.1f} MW")
        col_m3.metric("Annual Energy", f"{avg_facility_mw * 8760 / 1000:.1f} GWh")
        
        # TRAJECTORY EDITOR (moved from Tab 6)
        st.markdown("#### 📈 Load Growth Trajectory")
        
        enable_growth = st.checkbox(
            "Enable load growth over planning horizon",
            value=st.session_state.load_config.get('growth_enabled', True),
            key='tab1_growth_enabled'
        )
        st.session_state.load_config['growth_enabled'] = enable_growth
        
        if enable_growth:
            st.markdown("**Edit Growth Steps:**")
            st.caption("Define when IT load reaches each milestone. Facility load will be calculated as IT Load × PUE.")
            
            # Get current growth steps
            import pandas as pd
            growth_steps = st.session_state.load_config.get('growth_steps', [
                {'year': 2027, 'load_mw': 0},
                {'year': 2028, 'load_mw': 150},
                {'year': 2029, 'load_mw': 300},
                {'year': 2030, 'load_mw': 450},
                {'year': 2031, 'load_mw': 600},
            ])
            
            growth_df = pd.DataFrame(growth_steps)
            
            # Editable table
            edited_df = st.data_editor(
                growth_df,
                num_rows="dynamic",
                column_config={
                    "year": st.column_config.NumberColumn(
                        "Year",
                        min_value=2025,
                        max_value=2050,
                        step=1,
                        required=True
                    ),
                    "load_mw": st.column_config.NumberColumn(
                        "IT Load (MW)",
                        min_value=0.0,
                        max_value=peak_it_mw,
                        step=10.0,
                        required=True
                    )
                },
                hide_index=True,
                key='tab1_trajectory_editor'
            )
            
            # Update session state
            st.session_state.load_config['growth_steps'] = edited_df.to_dict('records')
            
            # Generate and visualize trajectory
            from app.utils.load_backend import generate_full_trajectory
            trajectory = generate_full_trajectory(
                edited_df.to_dict('records'),
                pue,
                planning_horizon=15
            )
            
            # Trajectory chart
            import plotly.graph_objects as go
            fig_traj = go.Figure()
            fig_traj.add_trace(go.Scatter(
                x=list(trajectory.keys()),
                y=list(trajectory.values()),
                mode='lines+markers',
                name='Facility Load',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
            fig_traj.update_layout(
                title="15-Year Load Trajectory",
                xaxis_title="Year",
                yaxis_title="Facility Load (MW)",
                height=400
            )
            st.plotly_chart(fig_traj, use_container_width=True)
            
            # Also update load_profile_dr for compatibility
            st.session_state.load_profile_dr['load_trajectory'] = trajectory
        else:
            # Flat trajectory
            trajectory = {y: peak_facility_mw for y in range(2027, 2042)}
            st.session_state.load_profile_dr['load_trajectory'] = trajectory
        
        # SAVE BUTTON
        st.markdown("---")
        col_save1, col_save2 = st.columns([3, 1])
        
        with col_save1:
            if st.session_state.load_config.get('last_updated'):
                st.caption(f"💾 Last saved: {st.session_state.load_config['last_updated'][:19]}")
            else:
                st.caption("⚠️ Configuration not yet saved to backend")
        
        with col_save2:
            if st.button("💾 Save to Backend", type="primary", use_container_width=True, key='tab1_save_config'):
                from app.utils.load_backend import save_load_configuration
                success = save_load_configuration(selected_site, st.session_state.load_config)
                if success:
                    st.success("✅ Load configuration saved to Google Sheets!")
                    st.session_state.load_config['last_updated'] = pd.Timestamp.now().isoformat()
                    st.rerun()
                else:
                    st.error("❌ Failed to save configuration. Check terminal for errors.")
    
    # =========================================================================
    # TAB 2: WORKLOAD MIX
    # =========================================================================
    with tab2:
        st.markdown("#### AI Workload Composition with DR Flexibility")
        
        st.info("""
        **Research Finding:** Different AI workloads have different flexibility characteristics.
        - **Pre-training:** 20-40% flexible, 15+ min response, checkpoint required
        - **Fine-tuning:** 40-60% flexible, 5+ min response
        - **Batch inference:** 80-100% flexible, <1 min response
        - **Real-time inference:** 0-10% flexible (SLA protected)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Helper function to normalize percentage values
            def normalize_pct(value):
                """Convert to percentage if it's a decimal value, otherwise return as-is"""
                if isinstance(value, (int, float)):
                    # If value is > 1, it's already a percentage (e.g., 45)
                    # If value is <= 1, it's a decimal (e.g., 0.45) -> convert to percentage
                    return int(value) if value > 1 else int(value * 100)
                return 0
            
            pre_training_pct = st.slider(
                "Pre-Training (%)", 0, 100, 
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('pre_training', 0)),
                help="Large model training - most interruptible but slow to stop"
            )
            fine_tuning_pct = st.slider(
                "Fine-Tuning (%)", 0, 100,
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('fine_tuning', 0)),
                help="Model customization - medium flexibility"
            )
            batch_inference_pct = st.slider(
                "Batch Inference (%)", 0, 100,
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('batch_inference', 0)),
                help="Offline predictions - highly flexible"
            )
        
        with col2:
            realtime_inference_pct = st.slider(
                "Real-Time Inference (%)", 0, 100,
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('realtime_inference', 0)),
                help="Production API serving - lowest flexibility"
            )
            rl_training_pct = st.slider(
                "RL Training (%)", 0, 100,
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('rl_training', 0)),
                help="Reinforcement learning - medium-high flexibility"
            )
            cloud_hpc_pct = st.slider(
                "Cloud HPC (%)", 0, 100,
                normalize_pct(st.session_state.load_profile_dr['workload_mix'].get('cloud_hpc', 0)),
                help="Traditional HPC workloads - low-medium flexibility"
            )
        
        # Validate sum = 100%
        total_pct = (pre_training_pct + fine_tuning_pct + batch_inference_pct + 
                     realtime_inference_pct + rl_training_pct + cloud_hpc_pct)
        
        if total_pct != 100:
            st.error(f"⚠️ Workload percentages must sum to 100%. Current: {total_pct}%")
        else:
            st.success(f"✅ Workload mix: {total_pct}%")
        
        # Update session state (convert back to 0-1 floats)
        st.session_state.load_profile_dr['workload_mix'] = {
            'pre_training': pre_training_pct / 100.0,
            'fine_tuning': fine_tuning_pct / 100.0,
            'batch_inference': batch_inference_pct / 100.0,
            'realtime_inference': realtime_inference_pct / 100.0,
            'rl_training': rl_training_pct / 100.0,
            'cloud_hpc': cloud_hpc_pct / 100.0,
        }
        
        # Workload mix pie chart
        if total_pct == 100:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Pre-Training', 'Fine-Tuning', 'Batch Inference', 
                       'Real-Time Inference', 'RL Training', 'Cloud HPC'],
                values=[pre_training_pct, fine_tuning_pct, batch_inference_pct, 
                       realtime_inference_pct, rl_training_pct, cloud_hpc_pct],
                hole=0.4,
                marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            )])
            fig_pie.update_layout(title="Workload Composition", height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # =========================================================================
    # TAB 3: COOLING FLEXIBILITY
    # =========================================================================
    with tab3:
        st.markdown("#### Cooling System Flexibility")
        
        st.info("""
        **Research Finding:** Cooling can provide 20-30% flexibility:
        - Thermal time constant: 15-60 minutes
        - Setpoint increase: 2-5°C before equipment limits
        - Power reduction: 3-5% per degree Celsius
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_setpoint_increase = st.slider(
                "Max Setpoint Increase (°C)", 1, 5, 3,
                help="Maximum temperature rise allowed"
            )
            
            power_per_degree = st.slider(
                "Power Reduction per °C (%)", 1, 8, 4,
                help="% of cooling load saved per degree"
            )
        
        with col2:
            thermal_constant = st.slider(
                "Thermal Time Constant (min)", 10, 60, 30,
                help="Time to reach new equilibrium"
            )
            
            min_chiller_time = st.slider(
                "Min Chiller On Time (min)", 10, 30, 20,
                help="Minimum runtime before cycling"
            )
        
        # Calculate cooling flexibility
        cooling_fraction = (pue - 1) / pue
        max_cooling_flex = max_setpoint_increase * power_per_degree / 100
        cooling_flex_facility = cooling_fraction * max_cooling_flex
        
        st.session_state.load_profile_dr['cooling_flex'] = max_cooling_flex
        st.session_state.load_profile_dr['thermal_constant_min'] = thermal_constant
        
        st.markdown("---")
        col_c1, col_c2, col_c3 = st.columns(3)
        col_c1.metric("Cooling Load Fraction", f"{cooling_fraction*100:.1f}%")
        col_c2.metric("Cooling Flexibility", f"{max_cooling_flex*100:.1f}%")
        col_c3.metric("Facility Contribution", f"{cooling_flex_facility*100:.1f}%")
    
    # =========================================================================
    # TAB 4: DR ECONOMICS
    # =========================================================================
    with tab4:
        st.markdown("#### Demand Response Economics")
        
        # Generate load profile only if workload mix is valid
        if total_pct == 100:
            # Generate flexibility profile
            load_data = generate_load_profile_with_flexibility(
                peak_it_load_mw=peak_it_mw,
                pue=pue,
                load_factor=load_factor,
                workload_mix=st.session_state.load_profile_dr['workload_mix'],
                cooling_flex_pct=st.session_state.load_profile_dr['cooling_flex']
            )
            
            # Summary metrics
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            flex_summary = load_data['summary']
            col_s1.metric("Avg Facility Load", f"{flex_summary['avg_load_mw']:.1f} MW")
            col_s2.metric("Avg Flexible Load", f"{flex_summary['avg_flexibility_mw']:.1f} MW")
            col_s3.metric("Flexibility %", f"{flex_summary['avg_flexibility_pct']:.1f}%")
            col_s4.metric("Firm Load", 
                         f"{flex_summary['avg_load_mw'] - flex_summary['avg_flexibility_mw']:.1f} MW")
            
            st.markdown("---")
            st.markdown("#### DR Product Analysis")
            
            # Analyze each DR product
            dr_results = []
            for product in ['spinning_reserve', 'non_spinning_reserve', 'economic_dr', 'emergency_dr']:
                result = calculate_dr_economics(load_data, product)
                dr_results.append({
                    'Product': product.replace('_', ' ').title(),
                    'Response Time': f"{result['response_time_min']} min",
                    'Available MW': f"{result['guaranteed_capacity_mw']:.1f}",
                    'Capacity Payment': f"${result['capacity_payment_annual']:,.0f}",
                    'Total Revenue': f"${result['total_annual_revenue']:,.0f}",
                    '$/MW-year': f"${result['revenue_per_mw_year']:,.0f}",
                })
            
            df_dr = pd.DataFrame(dr_results)
            st.dataframe(df_dr, use_container_width=True, hide_index=True)
            
            # Revenue chart
            fig_revenue = go.Figure()
            fig_revenue.add_trace(go.Bar(
                x=[r['Product'] for r in dr_results],
                y=[float(r['Total Revenue'].replace('$', '').replace(',', '')) for r in dr_results],
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            ))
            fig_revenue.update_layout(
                title="Annual DR Revenue by Product",
                xaxis_title="DR Product",
                yaxis_title="Annual Revenue ($)",
                height=350
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### Flexibility Profile (First Week)")
            
            # Plot first 168 hours
            hours = np.arange(168)
            
            fig = go.Figure()
            
            # Stack: Firm load on bottom, flexibility on top
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['firm_load_mw'][:168],
                name='Firm Load', fill='tozeroy',
                line=dict(color='#1f77b4', width=0),
                fillcolor='rgba(31, 119, 180, 0.7)'
            ))
            
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['total_load_mw'][:168],
                name='Total Load', fill='tonexty',
                line=dict(color='#2ca02c', width=0),
                fillcolor='rgba(44, 160, 44, 0.5)'
            ))
            
            fig.add_trace(go.Scatter(
                x=hours, y=load_data['total_flex_mw'][:168],
                name='Flexible Load', 
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ))
            
            fig.update_layout(
                title="Load Profile with Flexibility Breakdown",
                xaxis_title="Hour of Week",
                yaxis_title="Power (MW)",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Store load data in session state
            st.session_state.load_profile_dr['load_data'] = load_data
        
        else:
            st.warning("⚠️ Please fix workload mix to sum to 100% before viewing DR economics.")
    
    # =========================================================================
    # SAVE CONFIGURATION
    # =========================================================================
    st.markdown("---")
    
    col_save1, col_save2 = st.columns([3, 1])
    
    with col_save2:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            if total_pct != 100:
                st.error("Cannot save - workload mix must sum to 100%")
            else:
                # Save complete configuration for optimizer
                st.success("✅ Load profile with DR saved!")
                
                # Update main session state if needed
                if 'current_config' in st.session_state:
                    st.session_state.current_config['load_profile_dr'] = st.session_state.load_profile_dr
    
    with col_save1:
        if total_pct == 100 and 'load_data' in st.session_state.load_profile_dr:
            with st.expander("📋 View Configuration Summary"):
                summary = {
                    'Peak IT Load (MW)': peak_it_mw,
                    'PUE': pue,
                    'Peak Facility Load (MW)': peak_facility_mw,
                    'Total Flexibility (%)': f"{flex_summary['avg_flexibility_pct']:.1f}%",
                    'Flexible MW': f"{flex_summary['avg_flexibility_mw']:.1f}",
                }
                st.json(summary)

    
    
    # =========================================================================
    # SAVE LOAD PROFILE
    # =========================================================================
    st.markdown("---")
    st.markdown("### 💾 Save Load Profile")
    
    col_save_btn1, col_save_btn2, col_save_btn3 = st.columns([2, 2, 1])
    
    with col_save_btn1:
        if st.button("💾 Save Load Profile to Google Sheets", type="primary", use_container_width=True):
            if not st.session_state.get('current_site'):
                st.error("❌ No site selected. Navigate to Dashboard to select a site.")
            else:
                try:
                    from app.utils.site_backend import save_site_load_profile
                    from datetime import datetime
                    
                    # Prepare load data for saving
                    load_data_to_save = {
                        'load_profile': st.session_state.load_profile_dr.copy(),
                        'workload_mix': st.session_state.load_profile_dr.get('workload_mix', {}),
                        'dr_params': {
                            'cooling_flex': st.session_state.load_profile_dr.get('cooling_flex', 0),
                            'thermal_constant_min': st.session_state.load_profile_dr.get('thermal_constant_min', 30),
                            'enabled_dr_products': st.session_state.load_profile_dr.get('enabled_dr_products', [])
                        }
                    }
                    
                    # Save to Google Sheets
                    success = save_site_load_profile(st.session_state.current_site, load_data_to_save)
                    
                    if success:
                        st.success(f"✅ Load profile saved to Google Sheets for site: {st.session_state.current_site}")
                        st.info("This load profile will now be used in all optimizations for this site.")
                    else:
                        st.error("❌ Failed to save load profile to Google Sheets")
                        
                except Exception as e:
                    st.error(f"❌ Error saving load profile: {e}")
    
    with col_save_btn2:
        if st.session_state.get('current_site'):
            st.caption(f"📍 Current Site: **{st.session_state.current_site}**")
            st.caption(f"Peak Facility Load: **{peak_facility_mw:.1f} MW**")
        else:
            st.caption("No site selected")
    
    with col_save_btn3:
        if st.button("🔄 Refresh"):
            st.rerun()
    

    # =========================================================================
    # TAB 5: LOAD VARIABILITY ANALYSIS
    # =========================================================================
    with tab5:
        st.markdown("#### Load Variability Analysis")
        st.caption("Analyze hourly, daily, and seasonal load patterns")
        
        # Import variability page content
        from pages_custom import page_04_variability
        
        # Run variability analysis inline
        page_04_variability.render_variability_content()

if __name__ == "__main__":
    render()
