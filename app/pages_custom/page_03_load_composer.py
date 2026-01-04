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

# bvNexus Advanced Load Module
from app.utils.bvnexus_load_module import (
    COOLING_SPECS,
    ISO_PROFILES,
    WORKLOAD_SPECS,
    LoadPageConfig,
    WorkloadMix,
)
from app.utils.bvnexus_load_wrapper import (
    LoadManager,
    SiteLoadConfig,
)


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
        print(f"DEBUG - Loaded growth_steps (IT): {st.session_state.load_config.get('growth_steps')}")
        print(f"DEBUG - PUE: {st.session_state.load_config.get('pue')}")
    
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
    
    
    # Create tabs - Added Tab 6 for Engineering Exports
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Basic Load", "🔄 Workload Mix", "❄️ Cooling Flexibility",
        "💰 DR Economics", "📈 Load Variability"
    ])
    
    
    # =========================================================================
    # TAB 1: BASIC FACILITY PARAMETERS
    # =========================================================================
    with tab1:
# New version - lines 193-255
        st.markdown("#### Basic Facility Parameters")
        
        # Get peak facility from trajectory (source of truth)
        growth_steps = st.session_state.load_config.get('growth_steps', [])
        if growth_steps:
            peak_facility_mw = max(step.get('facility_load_mw', 0) for step in growth_steps)
        else:
            peak_facility_mw = float(st.session_state.load_config.get('peak_facility_load_mw', 750.0))
        
        # INPUT WIDGETS - PUE is READ-ONLY (driven by cooling technology)
        current_cooling_type = st.session_state.load_config.get('cooling_type', 'rear_door_heat_exchanger')
        # Ensure valid cooling type (fallback to default if empty or invalid)
        if not current_cooling_type or current_cooling_type not in COOLING_SPECS:
            current_cooling_type = 'rear_door_heat_exchanger'
            st.session_state.load_config['cooling_type'] = current_cooling_type
        
        cooling_spec = COOLING_SPECS[current_cooling_type]
        cooling_typical_pue = cooling_spec['pue_typical']
        
        # Set PUE from cooling technology (no manual override)
        pue = cooling_typical_pue
        st.session_state.load_config['pue'] = pue
        st.session_state.load_profile_dr['pue'] = pue
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # PUE - READ-ONLY display (set by cooling technology)
            st.metric(
                "PUE (from Cooling Tech)",
                f"{pue:.2f}",
                help=f"Automatically set by cooling technology. Typical for {cooling_spec['name']}: {cooling_typical_pue}"
            )


        
        with col2:
            # Initialize load factor to 75% if not set or if set to OLD defaults (30% or 80%)
            current_lf = st.session_state.load_config.get('load_factor_pct')
            if current_lf is None or current_lf == 80.0 or current_lf <= 30.0:
                default_lf = 75.0
            else:
                default_lf = current_lf
            
            load_factor = st.slider(
                "Load Factor (%)", 
                min_value=50, max_value=100, 
                value=int(default_lf),
                help="Average utilization as % of peak",
                key='tab1_load_factor'
            )
            st.session_state.load_config['load_factor_pct'] = float(load_factor)
            st.session_state.load_profile_dr['load_factor'] = load_factor / 100.0
        
        with col3:
            st.write("")  # Placeholder
        
        # === ADVANCED LOAD MODELING (NEW) ===
        st.markdown("---")
        st.markdown("#### 🔬 Advanced Load Modeling")
        st.caption("Configure cooling technology and grid interconnection for PSS/e, ETAP, and RAM exports")
        
        col_adv1, col_adv2 = st.columns(2)
        
        with col_adv1:
            # Cooling Type Selector
            cooling_options = list(COOLING_SPECS.keys())
            cooling_names = [COOLING_SPECS[c]["name"] for c in cooling_options]
            
            current_cooling = st.session_state.load_config.get('cooling_type', 'rear_door_heat_exchanger')
            try:
                cooling_idx = cooling_options.index(current_cooling)
            except ValueError:
                cooling_idx = 1  # Default to rear-door
            
            selected_cooling_idx = st.selectbox(
                "Cooling Technology",
                range(len(cooling_options)),
                format_func=lambda i: cooling_names[i],
                index=cooling_idx,
                key='tab1_cooling_type',
                help="Cooling technology affects PUE range, motor load distribution, and harmonic characteristics"
            )
            cooling_type = cooling_options[selected_cooling_idx]
            
            # Auto-update PUE when cooling technology changes
            cooling_spec = COOLING_SPECS[cooling_type]
            if cooling_type != current_cooling:
                # User changed cooling technology - update PUE to typical value
                new_pue = cooling_spec['pue_typical']
                st.session_state.load_config['pue'] = new_pue
                st.session_state.load_profile_dr['pue'] = new_pue
                st.info(f"ℹ️ PUE updated to {new_pue} (typical for {cooling_spec['name']}). Scroll up to see.")
                # NOTE: Don't st.rerun() - causes hang. User can see updated value on next interaction.
            
            st.session_state.load_config['cooling_type'] = cooling_type
            
            # Show cooling tech specs
            st.caption(f"PUE Range: {cooling_spec['pue_range'][0]}-{cooling_spec['pue_range'][1]} (typical: {cooling_spec['pue_typical']})")
            st.caption(f"VFD Penetration: {cooling_spec['vfd_penetration']*100:.0f}%")
        
        with col_adv2:
            # ISO Region Selector
            iso_options = list(ISO_PROFILES.keys())
            iso_names = [ISO_PROFILES[i]["name"] for i in iso_options]
            
            current_iso = st.session_state.load_config.get('iso_region', 'ercot')
            try:
                iso_idx = iso_options.index(current_iso)
            except ValueError:
                iso_idx = 0  # Default to ERCOT
            
            selected_iso_idx = st.selectbox(
                "ISO/RTO Region",
                range(len(iso_options)),
                format_func=lambda i: iso_names[i],
                index=iso_idx,
                key='tab1_iso_region',
                help="ISO region determines interconnection requirements and voltage ride-through profiles"
            )
            iso_region = iso_options[selected_iso_idx]
            st.session_state.load_config['iso_region'] = iso_region
            
            # Show ISO requirements
            iso_profile = ISO_PROFILES[iso_region]
            st.caption(f"Large Load Threshold: {iso_profile['large_load_threshold_mw']} MW")
            if iso_profile['dynamic_model_required']:
                st.caption("✅ Dynamic Model Required")
        
        # CALCULATIONS (after inputs!)
        peak_it_mw = round(peak_facility_mw / pue, 1)
        avg_facility_mw = peak_facility_mw * (load_factor / 100.0)
        st.session_state.load_config['peak_it_load_mw'] = peak_it_mw  
        st.session_state.load_profile_dr['peak_it_mw'] = peak_it_mw
        
        # METRICS
        st.markdown("---")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Peak IT", f"{peak_it_mw:.1f} MW", help="= Facility / PUE")
        col_m2.metric("Peak Facility", f"{peak_facility_mw:.1f} MW")
        col_m3.metric("Avg Load", f"{avg_facility_mw:.1f} MW")
        col_m4.metric("Annual Energy", f"{avg_facility_mw * 8760 / 1000:.1f} GWh")
        
        # TRAJECTORY EDITOR (always visible)
        st.markdown("#### 📈 Load Growth Trajectory")
        st.caption("Define when Facility load (IT + cooling) reaches each milestone. Peak IT will be calculated automatically.")
        
        # Always enabled (checkbox removed per user request)
        st.session_state.load_config['growth_enabled'] = True
            
        # Get current growth steps (FACILITY loads - source of truth)
        import pandas as pd
        growth_steps = st.session_state.load_config.get('growth_steps', [
            {'year': 2027, 'facility_load_mw': 0},
            {'year': 2028, 'facility_load_mw': 187.5},
            {'year': 2029, 'facility_load_mw': 375},
            {'year': 2030, 'facility_load_mw': 562.5},
            {'year': 2031, 'facility_load_mw': 750},
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
                "facility_load_mw": st.column_config.NumberColumn(
                    "Facility Load (MW)",
                    min_value=0.0,
                    max_value=peak_it_mw * pue,  # Max is peak facility
                    step=10.0,
                    required=True,
                    help="Total facility load (IT + cooling)"
                )
            },
            hide_index=True,
            key='tab1_trajectory_editor'
        )
        
        
        # Update session state with facility loads (source of truth)\n            st.session_state.load_config['growth_steps'] = edited_df.to_dict('records')\n            
        # Update peak facility load from trajectory
        if len(edited_df) > 0:
            peak_facility = edited_df['facility_load_mw'].max()
            st.session_state.load_config['peak_facility_load_mw'] = peak_facility
        
        # Generate and visualize trajectory (facility loads)
        from app.utils.load_backend import generate_full_trajectory_facility
        trajectory = generate_full_trajectory_facility(
            edited_df.to_dict('records'),
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
        st.plotly_chart(fig_traj, use_container_width=True, key='tab1_trajectory_chart')
        
        # Also update load_profile_dr for compatibility
        st.session_state.load_profile_dr['load_trajectory'] = trajectory
        
        # === ADVANCED LOAD CALCULATION (NEW) ===
        st.markdown("---")
        st.markdown("#### 🧮 Advanced Load Calculation")
        
        col_calc1, col_calc2 = st.columns([3, 1])
        
        with col_calc2:
            # Create cache-busting key based on inputs to force recalculation when they change
            session_pue = st.session_state.load_config.get('pue', pue)
            calc_key = f'tab1_calc_advanced_{cooling_type}_{iso_region}_{session_pue:.2f}_{peak_facility_mw:.1f}'
            
            if st.button("🔬 Calculate Advanced Model", type="primary", use_container_width=True, key=calc_key):
                try:
                    # Initialize Load Manager (always fresh)
                    st.session_state.load_manager = LoadManager()
                    manager = st.session_state.load_manager
                    
                    # Get workload mix from session state
                    workload = st.session_state.load_profile_dr.get('workload_mix', {})
                    
                    # Create configuration (FRESH each time)
                    config = SiteLoadConfig(
                        site_id=selected_site,
                        site_name=selected_site,
                        peak_load_mw=peak_facility_mw,
                        pue=pue,
                        cooling_type=cooling_type,
                        iso_region=iso_region,
                        pre_training_pct=workload.get('pre_training', 0.45) * 100,
                        fine_tuning_pct=workload.get('fine_tuning', 0.20) * 100,
                        batch_inference_pct=workload.get('batch_inference', 0.15) * 100,
                        realtime_inference_pct=workload.get('realtime_inference', 0.20) * 100,
                    )
                    
                    # Calculate composition (forces fresh calculation)
                    composition = manager.add_site(config)
                    st.session_state.load_composition = composition
                    st.session_state.load_advanced_calculated = True
                    
                    st.success(f"✅ Calculated: {cooling_type} @ PUE {pue}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Calculation error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col_calc1:
            st.caption("Calculate PSS/e fractions, equipment counts, harmonics, and DR capacity")
        
        # Show results if calculated
        if st.session_state.get('load_advanced_calculated') and 'load_composition' in st.session_state:
            comp = st.session_state.load_composition
            
            st.markdown("**📊 PSS/e CMPLDW Load Fractions:**")
            col_psse1, col_psse2, col_psse3, col_psse4 = st.columns(4)
            
            f = comp.psse_fractions
            col_psse1.metric("Electronic (GPU/TPU)", f"{f.fel*100:.1f}%", help="Server PSUs with active PFC")
            col_psse2.metric("Motor Load", f"{(f.fma+f.fmb+f.fmc+f.fmd)*100:.1f}%", help="Cooling equipment motors")
            col_psse3.metric("Static Load", f"{f.pfs*100:.1f}%", help="Lighting, facility, etc.")
            col_psse4.metric("Power Factor", f"{comp.power_factor:.3f}", help="Composite power factor")
            
            st.markdown("**🔧 Equipment Counts (for ETAP/RAM):**")
            col_eq1, col_eq2, col_eq3, col_eq4 = st.columns(4)
            
            eq = comp.equipment
            col_eq1.metric("UPS Units", f"{eq.ups_count}", help=f"{eq.ups_rating_kva:.0f} kVA each")
            col_eq2.metric("Chillers", f"{eq.chiller_count}", help=f"{eq.chiller_rating_mw:.2f} MW each")
            col_eq3.metric("CRAH Units", f"{eq.crah_count}", help=f"{eq.crah_rating_kw:.0f} kW each")
            col_eq4.metric("Pumps", f"{eq.pump_count}", help=f"{eq.pump_rating_kw:.0f} kW each")
            
            st.markdown("**⚡ Demand Response Capacity:**")
            col_dr1, col_dr2, col_dr3, col_dr4 = st.columns(4)
            
            flex = comp.flexibility
            col_dr1.metric("Total DR", f"{flex.dr_capacity_mw:.1f} MW", help="Total flexible capacity")
            col_dr2.metric("Economic DR", f"{flex.economic_dr_mw:.1f} MW", help="All workloads")
            col_dr3.metric("ERS-30", f"{flex.ers_30_mw:.1f} MW", help="≥30min response")
            col_dr4.metric("ERS-10", f"{flex.ers_10_mw:.1f} MW", help="≥10min response")
            
            # Show compliance status
            with st.expander("🏛️ ISO Compliance & Harmonics"):
                col_iso1, col_iso2 = st.columns(2)
                
                with col_iso1:
                    st.write("**ISO Requirements:**")
                    st.write(f"- Region: {comp.iso_region.upper()}")
                    st.write(f"- LLIS Study: {'✅ Required' if comp.requires_llis else '⚪ Not Required'}")
                    st.write(f"- VRT Profile: {comp.voltage_ride_through.get('profile', 'N/A')}")
                
                with col_iso2:
                    st.write("**Harmonic Analysis:**")
                    st.write(f"- THD-V: {comp.harmonics.thd_v:.2f}%")
                    st.write(f"- THD-I: {comp.harmonics.thd_i:.2f}%")
                    status = "✅ Compliant" if comp.harmonics.ieee_519_compliant else "❌ Non-Compliant"
                    st.write(f"- IEEE 519: {status}")
        
        # Note: Main save button is at bottom of tab
    
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
            st.plotly_chart(fig_pie, use_container_width=True, key='tab2_workload_pie')
    
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
            # Debug: Print load_factor value
            print(f"\n=== DR TAB DEBUG ===")
            print(f"load_factor (slider value): {load_factor}")
            print(f"load_factor / 100.0: {load_factor / 100.0}")
            print(f"peak_it_mw: {peak_it_mw}")
            print(f"pue: {pue}")
            
            # Generate flexibility profile
            # Ensure load_factor is a fraction (safeguard)
            lf_fraction = load_factor / 100.0
            if lf_fraction > 1.0:
                st.warning(f"⚠️ load_factor was {load_factor}, using 0.{load_factor} instead")
                lf_fraction = load_factor / 1000.0  # Assume typo
            
            st.info(f"🔍 Using load_factor: {lf_fraction:.2f} (from slider: {load_factor}%)")
            
            load_data = generate_load_profile_with_flexibility(
                peak_it_load_mw=peak_it_mw,
                pue=pue,
                load_factor=lf_fraction,
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
            st.plotly_chart(fig_revenue, use_container_width=True, key='tab4_dr_revenue')
            
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
            
            st.plotly_chart(fig, use_container_width=True, key='tab4_flexibility_profile')
            
            # Store load data in session state for DR page
            st.session_state.load_profile_dr['load_data'] = load_data
            
            # ALSO store 8760 arrays for optimizer use
            st.session_state['load_8760_mw'] = load_data['total_load_mw']  # Total facility load
            st.session_state['firm_load_8760_mw'] = load_data['firm_load_mw']  # Non-flexible portion
            st.session_state['flex_load_8760_mw'] = load_data['total_flex_mw']  # Flexible portion
            
            # Store metadata
            st.session_state['load_8760_metadata'] = {
                'peak_it_mw': peak_it_mw,
                'peak_facility_mw': load_data['summary']['peak_facility_mw'],
                'pue': pue,
                'load_factor': load_factor / 100.0,
                'workload_mix': st.session_state.load_profile_dr['workload_mix'],
                'cooling_flex_pct': st.session_state.load_profile_dr['cooling_flex']
            }
        
        else:
            st.warning("⚠️ Please fix workload mix to sum to 100% before viewing DR economics.")
    
    # Note: Main save button is below

    
    
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
                    from app.utils.load_backend import save_load_configuration
                    import traceback
                    
                    print(f"\n=== SAVE DEBUG ===")
                    print(f"Site name: {st.session_state.current_site}")
                    
                    # Include 8760 profile if available
                    if 'load_8760_mw' in st.session_state:
                        st.session_state.load_config['load_8760_mw'] = st.session_state['load_8760_mw']
                        print(f"Added 8760 profile")
                    
                    # Extract advanced load data from LoadComposition (if calculated)
                    if 'load_composition' in st.session_state:
                        comp = st.session_state.load_composition
                        
                        # PSS/e CMPLDW fractions - Calculate aggregated values
                        # Electronic = fel (GPU/TPU)
                        # Motor = fma + fmb + fmc + fmd (all motor types)
                        # Static = pfs (static load)
                        pf = comp.psse_fractions
                        total_motor = pf.fma + pf.fmb + pf.fmc + pf.fmd
                        st.session_state.load_config['psse_electronic_pct'] = pf.fel * 100
                        st.session_state.load_config['psse_motor_pct'] = total_motor * 100
                        st.session_state.load_config['psse_static_pct'] = pf.pfs * 100
                        st.session_state.load_config['psse_power_factor'] = comp.power_factor
                        
                        # ISO region from LoadComposition (already set by SiteLoadConfig, but ensure it's correct)
                        st.session_state.load_config['iso_region'] = comp.iso_region
                        
                        # Equipment counts - Use correct attribute names
                        eq = comp.equipment
                        st.session_state.load_config['equipment_ups'] = eq.ups_count  # NOT ups_units
                        st.session_state.load_config['equipment_chillers'] = eq.chiller_count  # NOT chillers
                        st.session_state.load_config['equipment_crah'] = eq.crah_count  # NOT crah_units
                        st.session_state.load_config['equipment_pumps'] = eq.pump_count  # NOT pumps
                        
                        # DR capacity - From flexibility object with correct attribute names
                        flex = comp.flexibility
                        st.session_state.load_config['dr_total_mw'] = flex.dr_capacity_mw  # NOT total_dr_mw
                        st.session_state.load_config['dr_economic_mw'] = flex.economic_dr_mw
                        st.session_state.load_config['dr_ers30_mw'] = flex.ers_30_mw  # NOT ers_30min_mw
                        st.session_state.load_config['dr_ers10_mw'] = flex.ers_10_mw  # NOT ers_10min_mw
                        
                        # Harmonics
                        st.session_state.load_config['harmonics_thd_v'] = comp.harmonics.thd_v
                        st.session_state.load_config['harmonics_thd_i'] = comp.harmonics.thd_i
                        st.session_state.load_config['harmonics_ieee519_compliant'] = comp.harmonics.ieee_519_compliant
                        
                        # Workload mix
                        workload = st.session_state.load_profile_dr.get('workload_mix', {})
                        st.session_state.load_config['workload_pretraining_pct'] = workload.get('pre_training', 45.0)
                        st.session_state.load_config['workload_finetuning_pct'] = workload.get('fine_tuning', 20.0)
                        st.session_state.load_config['workload_batch_inference_pct'] = workload.get('batch_inference', 15.0)
                        st.session_state.load_config['workload_realtime_inference_pct'] = workload.get('realtime_inference', 20.0)
                        
                        print(f"Added advanced load data from LoadComposition")
                    
                    
                    # Save to Google Sheets
                    success = save_load_configuration(
                        st.session_state.current_site, 
                        st.session_state.load_config
                    )
                    
                    if success:
                        st.success(f"✅ Saved!")
                        st.info("💡 8760 profile saved")
                    else:
                        st.error("❌ Save returned False")
                        
                except Exception as e:
                    print(f"\n=== ERROR ===\n{traceback.format_exc()}")
                    st.error(f"❌ Error: {str(e)}")
                    with st.expander("Details"):
                        st.code(traceback.format_exc())
    
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
    
    # =========================================================================
    # TAB 6: ENGINEERING EXPORTS (NEW)
    # =========================================================================

if __name__ == "__main__":
    render()
