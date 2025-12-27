"""
bvNexus Dashboard - Problem-Centric Optimization Tracking
Focus: Problem Statement Progress, Site Tracking & Portfolio Map
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import json
from pathlib import Path
from config.settings import PROBLEM_STATEMENTS, COLORS

# Paths to data
SAMPLE_DATA_DIR = Path(__file__).parent.parent.parent / "sample_data"


def render():
    """Render the bvNexus-focused dashboard"""
    
    # Page header
    st.markdown("## 📊 bvNexus Energy Optimizer")
    st.markdown("*Problem-centric optimization for AI datacenter power systems*")
    st.markdown("---")
    
    # Initialize session state for site tracking
    if 'site_tracker' not in st.session_state:
        st.session_state.site_tracker = []
    
    if 'phase_1_complete' not in st.session_state:
        st.session_state.phase_1_complete = {}
    
    if 'phase_2_complete' not in st.session_state:
        st.session_state.phase_2_complete = {}
    
    # Create tabs for different dashboard views
    tab1, tab2, tab3 = st.tabs(["📊 Site Workflows", "🗺️ Sites & Infrastructure", "🌎 Portfolio Map"])
    
    # ====================================================================================
    # TAB 1: PROBLEM STATEMENT PROGRESS
    # ====================================================================================
    with tab1:
        render_problem_progress_tab()
    
    # ====================================================================================
    # TAB 2: SITES & INFRASTRUCTURE (with integrated tracking)
    # ====================================================================================
    with tab2:
        render_sites_infrastructure_tab()
    
    # ====================================================================================
    # TAB 3: PORTFOLIO MAP
    # ====================================================================================
    with tab3:
        render_portfolio_map_tab()


def render_problem_progress_tab():
    """Render the Site Workflow Trackers tab"""
    
    st.markdown("### 📊 Site Optimization Workflow Trackers")
    st.caption("Track project development through EPC stages for all sites")
    
    # Initialize sites list if needed
    if 'sites_list' not in st.session_state:
        st.session_state.sites_list = []
    
    if len(st.session_state.sites_list) == 0:
        st.info("No sites configured yet. Go to 'Sites & Infrastructure' tab to add sites.")
        return
    
    # Initialize site-specific tracker data structure
    if 'site_optimization_stages' not in st.session_state:
        st.session_state.site_optimization_stages = {}
    
    # Load stage completion from Google Sheets for all sites
    from app.utils.site_backend import load_site_stage_result
    
    # Display stage headers at the top
    st.markdown("#### EPC Development Stages")
    
    # Create header row with stage descriptions
    col_spacer, col_s1, col_s2, col_s3, col_s4, col_prog = st.columns([3, 1.2, 1.2, 1.2, 1.2, 0.8])
    
    with col_s1:
        st.markdown("**① Screening**")
        st.caption("Heuristic")
    with col_s2:
        st.markdown("**② Concept**")
        st.caption("MILP Opt 1")
    with col_s3:
        st.markdown("**③ Preliminary**")
        st.caption("MILP Opt 2")
    with col_s4:
        st.markdown("**④ Detailed**")
        st.caption("MILP Opt 3")
    with col_prog:
        st.markdown("**Progress**")
        st.caption(" ")
    
    st.markdown("---")
    
    # Loop through all sites and display as matrix rows
    for site_idx, site in enumerate(st.session_state.sites_list):
        site_key = site.get('name', 'Unknown')
        
        # Initialize tracker for this site if not exists
        if site_key not in st.session_state.site_optimization_stages:
            st.session_state.site_optimization_stages[site_key] = {
                'problem_num': None,
                'problem_name': 'Not Assigned',
                'stages': {
                    'screening': {'complete': False, 'lcoe': None, 'date': None},
                    'concept': {'complete': False, 'lcoe': None, 'date': None},
                    'preliminary': {'complete': False, 'lcoe': None, 'date': None},
                    'detailed': {'complete': False, 'lcoe': None, 'date': None},
                }
            }
        
        site_tracker = st.session_state.site_optimization_stages[site_key]
        
        # Load problem type from Google Sheets (site object)
        if site.get('problem_num') and not site_tracker.get('problem_num'):
            site_tracker['problem_num'] = int(site.get('problem_num'))
            site_tracker['problem_name'] = site.get('problem_name', 'Not Assigned')
        
        # Load stage completion from Google Sheets
        for stage_key in ['screening', 'concept', 'preliminary', 'detailed']:
            result = load_site_stage_result(site_key, stage_key)
            if result and result.get('complete'):
                site_tracker['stages'][stage_key]['complete'] = True
                site_tracker['stages'][stage_key]['lcoe'] = result.get('lcoe')
                site_tracker['stages'][stage_key]['date'] = result.get('completion_date')
        
        # Calculate overall progress
        stages = site_tracker['stages']
        total_stages = 4
        completed_stages = sum(1 for s in stages.values() if s['complete'])
        progress_pct = (completed_stages / total_stages) * 100
        
        # Render site row in matrix format
        with st.container(border=True):
            # Column layout: Site Info | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Progress
            col_info, col_s1, col_s2, col_s3, col_s4, col_pbar = st.columns([3, 1.2, 1.2, 1.2, 1.2, 0.8])
            
            # Left column: Site info, problem type, optimizer button
            with col_info:
                st.markdown(f"**📍 {site.get('name', 'Unknown')}**")
                st.caption(f"{site.get('location', '')} • {site.get('it_capacity_mw', 0)} MW IT")
                
                # Problem type assignment (more compact)
                problem_options = ["Not Assigned", "P1: Greenfield", "P2: Brownfield", "P3: Land Dev", "P4: Grid Services", "P5: Bridge Power"]
                
                current_prob = site_tracker.get('problem_num')
                current_idx = current_prob if current_prob else 0
                
                col_prob, col_btn = st.columns([1.5, 1])
                
                with col_prob:
                    selected_problem = st.selectbox(
                        "Problem",
                        problem_options,
                        index=current_idx if current_idx < len(problem_options) else 0,
                        key=f"site_prob_matrix_{site_idx}",
                        label_visibility="collapsed"
                    )
                    
                    # Update tracker if changed
                    if selected_problem != "Not Assigned":
                        prob_num = int(selected_problem.split(":")[0].replace("P", ""))
                        site_tracker['problem_num'] = prob_num
                        site_tracker['problem_name'] = selected_problem.split(": ")[1]
                        
                        # Save to Google Sheets
                        from app.utils.site_backend import update_site
                        update_site(site.get('name'), {
                            'problem_num': prob_num,
                            'problem_name': site_tracker['problem_name']
                        })
                
                with col_btn:
                    # Quick optimize button (compact)
                    if site_tracker.get('problem_num'):
                        if st.button("🚀", use_container_width=True, type="primary", key=f"opt_matrix_{site_idx}", help="Open Optimizer"):
                            st.session_state.current_site = site.get('name', 'Unknown')
                            st.session_state.current_stage = 'screening'
                            
                            from app.utils.site_backend import save_site
                            save_site(site)
                            
                            st.session_state.current_page = f"problem_{site_tracker['problem_num']}"
                            st.session_state.selected_problem = site_tracker['problem_num']
                            st.rerun()
            
            # Stage columns: Show compact status + LCOE
            def render_stage_cell(col, stage_key, stage_label):
                with col:
                    stage_data = stages[stage_key]
                    is_complete = stage_data['complete']
                    
                    if is_complete:
                        # Green checkmark + LCOE
                        st.markdown(f"""
                        <div style="background: #10b981; color: white; padding: 8px; 
                                    border-radius: 6px; text-align: center; min-height: 60px;">
                            <div style="font-size: 20px; margin-bottom: 4px;">✓</div>
                            <div style="font-size: 11px;">${stage_data['lcoe']:.1f}/MWh</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Gray number (not started)
                        st.markdown(f"""
                        <div style="background: #6b7280; color: white; padding: 8px; 
                                    border-radius: 6px; text-align: center; min-height: 60px;">
                            <div style="font-size: 20px; margin-bottom: 4px;">{stage_label}</div>
                            <div style="font-size: 11px;">—</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            render_stage_cell(col_s1, 'screening', '1')
            render_stage_cell(col_s2, 'concept', '2')
            render_stage_cell(col_s3, 'preliminary', '3')
            render_stage_cell(col_s4, 'detailed', '4')
            
            # Progress column: Vertical progress bar + metric
            with col_pbar:
                st.metric("", f"{completed_stages}/4", label_visibility="collapsed")
                st.progress(progress_pct / 100)
        
        # Small spacing between sites
        st.markdown("")



def render_site_tracker_tab():
    """Render the Site Tracker tab"""
    
    st.markdown("### 📍 Site Tracker")
    st.caption("Track individual sites through optimization workflows")
    
    # Add new site
    with st.expander("➕ Add New Site", expanded=len(st.session_state.site_tracker) == 0):
        col_add1, col_add2, col_add3, col_add4 = st.columns(4)
        
        with col_add1:
            site_name = st.text_input("Site Name", placeholder="e.g., Phoenix DC-1")
        
        with col_add2:
            site_location = st.text_input("Location", placeholder="e.g., Phoenix, AZ")
        
        with col_add3:
            site_problem = st.selectbox(
                "Problem Type",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: f"P{x}: {PROBLEM_STATEMENTS[x]['short_name']}"
            )
        
        with col_add4:
            site_capacity = st.number_input("IT Capacity (MW)", min_value=10, max_value=2000, value=600, step=50)
        
        if st.button("➕ Add Site", type="primary"):
            if site_name:
                new_site = {
                    'name': site_name,
                    'location': site_location,
                    'problem_num': site_problem,
                    'problem_name': PROBLEM_STATEMENTS[site_problem]['short_name'],
                    'capacity_mw': site_capacity,
                    'phase_1_done': False,
                    'phase_2_done': False,
                    'status': 'Not Started',
                    'lcoe': None,
                }
                st.session_state.site_tracker.append(new_site)
                st.success(f"✅ Added {site_name}")
                st.rerun()
            else:
                st.error("Site name is required")
    
    # Display site tracker table
    if st.session_state.site_tracker:
        st.markdown("#### Active Sites")
        
        # Build display dataframe
        site_data = []
        for idx, site in enumerate(st.session_state.site_tracker):
            # Determine status indicator
            if site['phase_2_done']:
                status_icon = "🟢"
                status_text = "Phase 2 ✓✓"
            elif site['phase_1_done']:
                status_icon = "🟡"
                status_text = "Phase 1 ✓"
            else:
                status_icon = "⚪"
                status_text = "Not Started"
            
            site_data.append({
                'Status': status_icon,
                'Site Name': site.get('name', 'Unknown'),
                'Location': site.get('location', ''),
                'Capacity': f"{site['capacity_mw']} MW",
                'Problem': f"P{site['problem_num']}: {site['problem_name']}",
                'Progress': status_text,
                'LCOE': f"${site['lcoe']:.1f}/MWh" if site['lcoe'] else "—",
                'Index': idx,
            })
        
        df_sites = pd.DataFrame(site_data)
        
        # Display as interactive table with action buttons
        for idx, row in df_sites.iterrows():
            site_idx = row['Index']
            site = st.session_state.site_tracker[site_idx]
            
            with st.container(border=True):
                col_s1, col_s2, col_s3, col_s4 = st.columns([0.5, 2, 2, 1])
                
                with col_s1:
                    st.markdown(f"### {row['Status']}")
                
                with col_s2:
                    st.markdown(f"**{row['Site Name']}**")
                    st.caption(f"{row['Location']} • {row['Capacity']}")
                
                with col_s3:
                    st.markdown(f"**{row['Problem']}**")
                    st.caption(f"Status: {row['Progress']} • LCOE: {row['LCOE']}")
                
                with col_s4:
                    if st.button(f"🚀 Optimize", key=f"opt_{site_idx}", use_container_width=True, type="primary"):
                        # Navigate to the problem page
                        st.session_state.current_page = f"problem_{site['problem_num']}"
                        st.session_state.selected_problem = site['problem_num']
                        st.rerun()
                    
                    if st.button(f"🗑️ Remove", key=f"del_{site_idx}", use_container_width=True):
                        st.session_state.site_tracker.pop(site_idx)
                        st.rerun()
    else:
        st.info("📋 No sites tracked yet. Add your first site above to get started.")


def render_sites_infrastructure_tab():
    """Render the Sites & Infrastructure Map tab with site management"""
    
    st.markdown("### 🗺️ Sites & Infrastructure")
    st.caption("Select a site to view infrastructure map and edit configuration")
    
    # Initialize sites list if needed
    if 'sites_list' not in st.session_state:
        # Add 2 sample sites for testing
        st.session_state.sites_list = [
            {
                'name': 'Phoenix AI Campus',
                'location': 'Phoenix, AZ',
                'iso': 'CAISO',
                'it_capacity_mw': 750,
                'pue': 1.20,
                'facility_mw': 900,
                'land_acres': 450,
                'nox_limit_tpy': 120,
                'gas_supply_mcf': 150000,
                'voltage_kv': 500,
                'coordinates': [33.448, -112.074],
                'geojson_prefix': 'phoenix'
            },
            {
                'name': 'Dallas Hyperscale DC',
                'location': 'Dallas, TX',
                'iso': 'ERCOT',
                'it_capacity_mw': 600,
                'pue': 1.25,
                'facility_mw': 750,
                'land_acres': 600,
                'nox_limit_tpy': 150,
                'gas_supply_mcf': 200000,
                'voltage_kv': 345,
                'coordinates': [32.776, -96.797],
                'geojson_prefix': 'dallas'
            }
        ]
    
    # Site selector dropdown
    col_sel1, col_sel2, col_sel3 = st.columns([2, 3, 1])
    
    with col_sel1:
        # Build site options
        site_options = ["Sample Site (Demo)"]
        for idx, site in enumerate(st.session_state.sites_list):
            site_options.append(f"Site {idx + 1}: {site.get('name', 'Unknown')}")
        site_options.append("➕ Create New Site")
        
        selected_option = st.selectbox(
            "Select Site",
            site_options,
            help="Choose a site to view and edit"
        )
    
    # Determine selected site and GeoJSON file prefix
    if selected_option == "Sample Site (Demo)":
        selected_site_idx = None
        is_new_site = False
        is_sample = True
        geojson_prefix = ""  # No prefix for Tulsa sample
    elif selected_option == "➕ Create New Site":
        selected_site_idx = None
        is_new_site = True
        is_sample = False
        geojson_prefix = ""
    else:
        # Extract site index from "Site X: Name"
        selected_site_idx = int(selected_option.split(":")[0].replace("Site ", "")) - 1
        is_new_site = False
        is_sample = False
        site = st.session_state.sites_list[selected_site_idx]
        geojson_prefix = site.get('geojson_prefix', '')
    
    # Display site info in header
    with col_sel2:
        if is_sample:
            st.caption("📍 Tulsa, OK Area • 500 acres • Sample infrastructure data")
        elif is_new_site:
            st.caption("📝 Fill in details below to create a new site configuration")
        else:
            site = st.session_state.sites_list[selected_site_idx]
            st.caption(f"📍 {site.get('location', '')} • {site.get('land_acres', 0)} acres • {site['it_capacity_mw']} MW IT")
    
    with col_sel3:
        if not is_sample and not is_new_site:
            if st.button("🗑️ Delete Site", type="secondary", use_container_width=True, key="delete_current_site"):
                st.session_state.sites_list.pop(selected_site_idx)
                st.success("Site deleted")
                st.rerun()
    
    st.markdown("---")
    
    # =================================================================================
    # MAP SECTION
    # =================================================================================
    
    # Determine map center based on selection
    if is_sample:
        center_coords = [36.1512, -95.9607]  # Tulsa, OK
        zoom_level = 13
    elif is_new_site:
        center_coords = [39.8283, -98.5795]  # US center
        zoom_level = 4
    else:
        # Use site-specific coordinates
        site = st.session_state.sites_list[selected_site_idx]
        coords_str = site.get('coordinates', '36.1512, -95.9607')
        
        # Parse coordinates string to list of floats
        # Format: "lat, lng" -> [lat, lng]
        try:
            if isinstance(coords_str, str):
                coords_parts = coords_str.split(',')
                center_coords = [float(coords_parts[0].strip()), float(coords_parts[1].strip())]
            else:
                center_coords = coords_str  # Already a list
        except (ValueError, IndexError):
            # Fallback to default if parsing fails
            center_coords = [36.1512, -95.9607]
        
        zoom_level = 13
    
    # Create infrastructure map
    m = folium.Map(
        location=center_coords,
        zoom_start=zoom_level,
        tiles='CartoDB positron'
    )
    
    # Load GeoJSON layers (only if not creating new site)
    if not is_new_site:
        try:
            # Determine file suffix based on location
            file_suffix = f"_{geojson_prefix}" if geojson_prefix else ""
            
            # Load multi-layer GeoJSON from Google Sheets
            site_geojson_str = site.get('geojson', '')
            
            if site_geojson_str:
                try:
                    geojson_data = json.loads(site_geojson_str)
                    
                    # Process each feature/layer in the GeoJSON
                    if 'features' in geojson_data:
                        for feature in geojson_data['features']:
                            props = feature.get('properties', {})
                            layer_type = props.get('layer_type', 'unknown')
                            
                            # Determine layer name and style based on layer_type
                            if layer_type == 'site_boundary':
                                layer_name = 'Site Boundary'
                                style_fn = lambda x: {'fillColor': '#fbbf24', 'color': '#f59e0b', 'weight': 3, 'fillOpacity': 0.3}
                                tooltip_fields = ['name', 'area_acres']
                                tooltip_aliases = ['Site:', 'Area:']
                            elif layer_type == 'transmission':
                                layer_name = 'Transmission'
                                style_fn = lambda x: {'color': '#ef4444', 'weight': 4, 'opacity': 0.8}
                                tooltip_fields = ['name', 'voltage_kv']
                                tooltip_aliases = ['Facility:', 'Voltage:']
                            elif layer_type == 'gas':
                                layer_name = 'Natural Gas'
                                style_fn = lambda x: {'color': '#f97316', 'weight': 3, 'opacity': 0.7, 'dashArray': '10, 5'}
                                tooltip_fields = ['name']
                                tooltip_aliases = ['Pipeline:']
                            elif layer_type == 'fiber':
                                layer_name = 'Fiber'
                                style_fn = lambda x: {'color': '#a855f7', 'weight': 2, 'opacity': 0.7, 'dashArray': '5, 5'}
                                tooltip_fields = ['name']
                                tooltip_aliases = ['Route:']
                            elif layer_type == 'water':
                                layer_name = 'Water'
                                style_fn = lambda x: {'color': '#3b82f6', 'weight': 3, 'opacity': 0.6}
                                tooltip_fields = ['name', 'type']
                                tooltip_aliases = ['Feature:', 'Type:']
                            else:
                                continue  # Skip unknown layer types
                            
                            # Add feature to map
                            feature_collection = {
                                "type": "FeatureCollection",
                                "features": [feature]
                            }
                            
                            folium.GeoJson(
                                feature_collection,
                                name=layer_name,
                                style_function=style_fn,
                                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)
                            ).add_to(m)
                    
                except Exception as e:
                    print(f"Error parsing multi-layer GeoJSON from Google Sheets: {e}")
                    pass  # GeoJSON from Sheets required
            
        except Exception as e:
            st.error(f"Error loading GeoJSON layers: {e}")
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display map
    st_folium(m, width=1200, height=600)

    st.markdown("---")
    
    # =================================================================================
    # WORKFLOW TRACKER SECTION (if not creating new site)
    # =================================================================================
    if not is_sample and not is_new_site:
        st.markdown("### 📊 Optimization Workflow Tracker")
        st.caption("Track project development through EPC stages with progressive optimization refinement")
        
        # Get current site
        site = st.session_state.sites_list[selected_site_idx]
        
        # Initialize site-specific tracker data structure
        if 'site_optimization_stages' not in st.session_state:
            st.session_state.site_optimization_stages = {}
        
        site_key = site.get('name', 'Unknown')
        if site_key not in st.session_state.site_optimization_stages:
            st.session_state.site_optimization_stages[site_key] = {
                'problem_num': None,
                'problem_name': 'Not Assigned',
                'stages': {
                    'screening': {'complete': False, 'lcoe': None, 'date': None},
                    'concept': {'complete': False, 'lcoe': None, 'date': None},
                    'preliminary': {'complete': False, 'lcoe': None, 'date': None},
                    'detailed': {'complete': False, 'lcoe': None, 'date': None},
                }
            }
        
        site_tracker = st.session_state.site_optimization_stages[site_key]

        # Load problem type from Google Sheets (site object)
        if site.get('problem_num') and not site_tracker.get('problem_num'):
            site_tracker['problem_num'] = int(site.get('problem_num'))
            site_tracker['problem_name'] = site.get('problem_name', 'Not Assigned')
        
        # Load stage completion from Google Sheets
        from app.utils.site_backend import load_site_stage_result
        for stage_key in ['screening', 'concept', 'preliminary', 'detailed']:
            result = load_site_stage_result(site_key, stage_key)
            if result and result.get('complete'):
                site_tracker['stages'][stage_key]['complete'] = True
                site_tracker['stages'][stage_key]['lcoe'] = result.get('lcoe')
                site_tracker['stages'][stage_key]['date'] = result.get('completion_date')
        
        
        # Site header with problem assignment
        with st.container(border=True):
            col_h1, col_h2, col_h3 = st.columns([3, 2, 2])
            
            with col_h1:
                st.markdown(f"#### 📍 {site.get('name', 'Unknown')}")
                st.caption(f"{site.get('location', '')} • {site['it_capacity_mw']} MW IT • {site['facility_mw']:.0f} MW Facility")
            
            with col_h2:
                # Problem type assignment
                problem_options = ["Not Assigned", "P1: Greenfield", "P2: Brownfield", "P3: Land Dev", "P4: Grid Services", "P5: Bridge Power"]
                
                current_prob = site_tracker.get('problem_num')
                if current_prob:
                    current_idx = current_prob
                else:
                    current_idx = 0
                
                selected_problem = st.selectbox(
                    "Assigned Problem Type",
                    problem_options,
                    index=current_idx if current_idx < len(problem_options) else 0,
                    key=f"site_prob_assign_{selected_site_idx}"
                )
                
                # Update tracker if changed
                if selected_problem != "Not Assigned":
                    prob_num = int(selected_problem.split(":")[0].replace("P", ""))
                    site_tracker['problem_num'] = prob_num
                    site_tracker['problem_name'] = selected_problem.split(": ")[1]
                    
                    # Save to Google Sheets
                    from app.utils.site_backend import update_site
                    update_site(site.get('name'), {
                        'problem_num': prob_num,
                        'problem_name': site_tracker['problem_name']
                    })
            
            with col_h3:
                # Quick optimize button
                if site_tracker.get('problem_num'):
                    if st.button("🚀 Open Optimizer", use_container_width=True, type="primary", key=f"site_opt_btn_{selected_site_idx}"):
                        # Set current site context in session state
                        st.session_state.current_site = site.get('name', 'Unknown')
                        st.session_state.current_stage = 'screening'  # Default to first stage
                        
                        # Save site to Google Sheets if it doesn't exist
                        from app.utils.site_backend import save_site
                        save_site(site)
                        
                        # Navigate to problem page
                        st.session_state.current_page = f"problem_{site_tracker['problem_num']}"
                        st.session_state.selected_problem = site_tracker['problem_num']
                        st.rerun()
                else:
                    st.info("Assign problem type first", icon="ℹ️")
        
        st.markdown("")
        
        # EPC Workflow Stages
        st.markdown("#### EPC Development Stages")
        
        stages = site_tracker['stages']
        
        # Calculate overall progress
        total_stages = 4
        completed_stages = sum(1 for s in stages.values() if s['complete'])
        progress_pct = (completed_stages / total_stages) * 100
        
        # Overall progress bar
        col_prog1, col_prog2 = st.columns([3, 1])
        with col_prog1:
            st.progress(progress_pct / 100)
        with col_prog2:
            st.metric("Progress", f"{completed_stages}/{total_stages}")
        
        st.markdown("")
        
        # Stage cards in 4 columns
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        # Stage 1: Screening Study (Heuristic)
        with col_s1:
            stage_1_complete = stages['screening']['complete']
            stage_1_color = "#10b981" if stage_1_complete else "#6b7280"
            stage_1_text_color = "white"
            stage_1_icon = "✓" if stage_1_complete else "1"
            
            st.markdown(f"""
            <div style="background: {stage_1_color}; color: {stage_1_text_color}; padding: 12px; 
                        border-radius: 8px; text-align: center; min-height: 100px;">
                <div style="font-size: 24px; margin-bottom: 8px;">{stage_1_icon}</div>
                <strong>Screening Study</strong><br>
                <span style="font-size: 12px;">Heuristic Analysis</span>
            </div>
            """, unsafe_allow_html=True)
            
            if stages['screening']['lcoe']:
                st.caption(f"LCOE: ${stages['screening']['lcoe']:.1f}/MWh")

        
        # Stage 2: Concept Development (MILP 1)
        with col_s2:
            stage_2_complete = stages['concept']['complete']
            stage_2_color = "#10b981" if stage_2_complete else "#6b7280"
            stage_2_text_color = "white"
            stage_2_icon = "✓" if stage_2_complete else "2"
            
            st.markdown(f"""
            <div style="background: {stage_2_color}; color: {stage_2_text_color}; padding: 12px; 
                        border-radius: 8px; text-align: center; min-height: 100px;">
                <div style="font-size: 24px; margin-bottom: 8px;">{stage_2_icon}</div>
                <strong>Concept Development</strong><br>
                <span style="font-size: 12px;">MILP Optimization 1</span>
            </div>
            """, unsafe_allow_html=True)
            
            if stages['concept']['lcoe']:
                st.caption(f"LCOE: ${stages['concept']['lcoe']:.1f}/MWh")
        
        # Stage 3: Preliminary Design (MILP 2)
        with col_s3:
            stage_3_complete = stages['preliminary']['complete']
            stage_3_color = "#10b981" if stage_3_complete else "#6b7280"
            stage_3_text_color = "white"
            stage_3_icon = "✓" if stage_3_complete else "3"
            
            st.markdown(f"""
            <div style="background: {stage_3_color}; color: {stage_3_text_color}; padding: 12px; 
                        border-radius: 8px; text-align: center; min-height: 100px;">
                <div style="font-size: 24px; margin-bottom: 8px;">{stage_3_icon}</div>
                <strong>Preliminary Design</strong><br>
                <span style="font-size: 12px;">MILP Optimization 2</span>
            </div>
            """, unsafe_allow_html=True)
            
            if stages['preliminary']['lcoe']:
                st.caption(f"LCOE: ${stages['preliminary']['lcoe']:.1f}/MWh")
        
        # Stage 4: Detailed Design (MILP 3)
        with col_s4:
            stage_4_complete = stages['detailed']['complete']
            stage_4_color = "#10b981" if stage_4_complete else "#6b7280"
            stage_4_text_color = "white"
            stage_4_icon = "✓" if stage_4_complete else "4"
            
            st.markdown(f"""
            <div style="background: {stage_4_color}; color: {stage_4_text_color}; padding: 12px; 
                        border-radius: 8px; text-align: center; min-height: 100px;">
                <div style="font-size: 24px; margin-bottom: 8px;">{stage_4_icon}</div>
                <strong>Detailed Design</strong><br>
                <span style="font-size: 12px;">MILP Optimization 3</span>
            </div>
            """, unsafe_allow_html=True)
            
            if stages['detailed']['lcoe']:
                st.caption(f"LCOE: ${stages['detailed']['lcoe']:.1f}/MWh")
        
        st.markdown("---")



def render_portfolio_map_tab():
    """Render the National Portfolio Map tab"""
    
    st.markdown("### 🗺️ National Portfolio Map")
    st.caption("View all sites across development stages from screening to operation")
    
    # Map controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    
    with col_ctrl1:
        stage_filter = st.multiselect(
            "Filter by Stage",
            ["Screening Analysis", "Interconnection Filing", "Detailed Design", "Construction", "Operation"],
            default=["Screening Analysis", "Interconnection Filing", "Detailed Design", "Construction", "Operation"]
        )
    
    with col_ctrl2:
        selected_site_focus = st.selectbox(
            "Focus on Site",
            ["National View"] + [f"Phoenix DC-1", "Dallas DC-2", "Atlanta DC-3", "Chicago DC-4", "Portland DC-5", 
                                 "Northern Virginia DC-6", "Columbus DC-7", "Reno DC-8"],
            help="Zoom to specific site or view full portfolio"
        )
    
    with col_ctrl3:
        if st.button("🌎 National View", use_container_width=True, type="secondary"):
            selected_site_focus = "National View"
            st.rerun()
    
    # Load portfolio data
    try:
        portfolio_path = SAMPLE_DATA_DIR / "portfolio_sites.geojson"
        with open(portfolio_path) as f:
            portfolio_data = json.load(f)
        
        # Determine map center and zoom based on selection
        if selected_site_focus == "National View":
            map_center = [39.8283, -98.5795]  # US geographic center
            zoom_level = 4
        else:
            # Find the selected site coordinates
            for feature in portfolio_data['features']:
                if feature['properties']['site_name'] == selected_site_focus:
                    coords = feature['geometry']['coordinates']
                    map_center = [coords[1], coords[0]]  # lat, lon
                    zoom_level = 10
                    break
            else:
                map_center = [39.8283, -98.5795]
                zoom_level = 4
        
        # Create map
        m = folium.Map(
            location=map_center,
            zoom_start=zoom_level,
            tiles='CartoDB positron'
        )
        
        # Add sites as circle markers color-coded by stage
        for feature in portfolio_data['features']:
            props = feature['properties']
            
            # Check if stage matches filter
            if props['stage'] not in stage_filter:
                continue
            
            coords = feature['geometry']['coordinates']
            
            # Create popup content
            popup_html = f"""
            <div style="font-family: sans-serif; min-width: 200px;">
                <h4 style="margin: 0 0 8px 0;">{props['site_name']}</h4>
                <p style="margin: 4px 0;"><strong>Location:</strong> {props['location']}</p>
                <p style="margin: 4px 0;"><strong>Capacity:</strong> {props['capacity_mw']} MW</p>
                <p style="margin: 4px 0;"><strong>Stage:</strong> {props['stage']}</p>
                <p style="margin: 4px 0;"><strong>Progress:</strong> {props['completion_pct']}%</p>
                <p style="margin: 4px 0;"><strong>Target COD:</strong> {props['commercial_date']}</p>
                <p style="margin: 4px 0;"><strong>Problem:</strong> {props['problem_type']}</p>
            </div>
            """
            
            folium.CircleMarker(
                location=[coords[1], coords[0]],
                radius=10 + (props['capacity_mw'] / 100),  # Size by capacity
                color=props['stage_color'],
                fill=True,
                fillColor=props['stage_color'],
                fillOpacity=0.7,
                weight=2,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{props['site_name']} - {props['stage']}"
            ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 220px; height: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px;">
        <p style="margin: 0 0 8px 0; font-weight: bold;">Development Stage</p>
        <p style="margin: 5px 0;"><span style="color: #6b7280;">●</span> Screening Analysis</p>
        <p style="margin: 5px 0;"><span style="color: #a855f7;">●</span> Interconnection Filing</p>
        <p style="margin: 5px 0;"><span style="color: #3b82f6;">●</span> Detailed Design</p>
        <p style="margin: 5px 0;"><span style="color: #f59e0b;">●</span> Construction</p>
        <p style="margin: 5px 0;"><span style="color: #10b981;">●</span> Operation</p>
        <p style="margin-top: 10px; font-size: 10px; color: #6b7280;">Marker size ~ capacity</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Display map
        st_folium(m, width=None, height=600)
        
        # Summary statistics
        st.markdown("---")
        st.markdown("#### Portfolio Statistics")
        
        # Calculate stats
        total_sites = len([f for f in portfolio_data['features'] if f['properties']['stage'] in stage_filter])
        total_capacity = sum(f['properties']['capacity_mw'] for f in portfolio_data['features'] if f['properties']['stage'] in stage_filter)
        operational_capacity = sum(f['properties']['capacity_mw'] for f in portfolio_data['features'] 
                                   if f['properties']['stage'] == 'Operation' and f['properties']['stage'] in stage_filter)
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            st.metric("Total Sites", total_sites)
        
        with col_stat2:
            st.metric("Portfolio Capacity", f"{total_capacity} MW")
        
        with col_stat3:
            st.metric("Operational Capacity", f"{operational_capacity} MW")
        
        with col_stat4:
            operational_pct = (operational_capacity / total_capacity * 100) if total_capacity > 0 else 0
            st.metric("Operational %", f"{operational_pct:.0f}%")
        
    except Exception as e:
        st.error(f"Could not load portfolio data: {e}")
        st.info("Sample portfolio data file not found. Portfolio map will be available when data is configured.")


def render_problem_card(column, prob_num):
    """Render a compact problem status card"""
    
    prob = PROBLEM_STATEMENTS[prob_num]
    
    # Check completion status
    phase_1 = st.session_state.phase_1_complete.get(prob_num, False)
    phase_2 = st.session_state.phase_2_complete.get(prob_num, False)
    
    # Status indicator
    if phase_2:
        status_color = "#48bb78"  # Green
        status_icon = "✓✓"
        status_text = "Phase 2"
    elif phase_1:
        status_color = "#ecc94b"  # Yellow
        status_icon = "✓"
        status_text = "Phase 1"
    else:
        status_color = "#cbd5e0"  # Gray
        status_icon = "○"
        status_text = "Not Started"
    
    with column:
        with st.container(border=True):
            # Problem header
            st.markdown(f"#### {prob['icon']} P{prob_num}")
            st.markdown(f"**{prob['short_name']}**")
            
            # Status badge
            st.markdown(f"""
            <div style="background: {status_color}; color: white; padding: 4px 8px; 
                        border-radius: 12px; text-align: center; font-size: 11px; 
                        font-weight: 600; margin: 8px 0;">
                {status_icon} {status_text}
            </div>
            """, unsafe_allow_html=True)
            
            st.caption(prob['objective'])
            
            # Action button
            btn_label = "View Results" if phase_1 else "Start"
            btn_type = "secondary" if phase_1 else "primary"
            
            if st.button(btn_label, key=f"prob_card_{prob_num}", use_container_width=True, type=btn_type):
                st.session_state.current_page = f'problem_{prob_num}'
                st.session_state.selected_problem = prob_num
                st.rerun()


if __name__ == "__main__":
    render()
