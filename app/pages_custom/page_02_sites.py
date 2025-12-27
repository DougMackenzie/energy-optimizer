"""
Sites Page with Interactive Infrastructure Map
Features: Leaflet map with GeoJSON layers + Site Management
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from pathlib import Path
import pandas as pd

# Paths to GeoJSON files
SAMPLE_DATA_DIR = Path(__file__).parent.parent.parent / "sample_data"


def render():
    """Render the Sites page with interactive map"""
    
    st.markdown("## 📍 Sites & Infrastructure")
    st.caption("Interactive map showing site boundaries and utility infrastructure")
    st.markdown("---")
    
    # Initialize sites in session state
    if 'sites_list' not in st.session_state:
        st.session_state.sites_list = []
    
    # =========================================================================
    # SECTION 1: INTERACTIVE MAP
    # =========================================================================
    st.markdown("### 🗺️ Site Infrastructure Map")
    
    # Site selector dropdown
    if st.session_state.sites_list:
        # User has configured sites - show dropdown
        col_sel1, col_sel2 = st.columns([2, 3])
        
        with col_sel1:
            site_names = ["Sample Site (Demo)"] + [s['name'] for s in st.session_state.sites_list]
            selected_site_name = st.selectbox(
                "Select Site to View",
                site_names,
                help="Choose a site to view its infrastructure map"
            )
        
        with col_sel2:
            if selected_site_name == "Sample Site (Demo)":
                st.caption("📍 Tulsa, OK Area • 500 acres • Sample infrastructure data")
            else:
                # Find the selected site
                site_idx = site_names.index(selected_site_name) - 1
                site = st.session_state.sites_list[site_idx]
                st.caption(f"📍 {site['location']} • {site['land_acres']} acres • {site['it_capacity_mw']} MW IT")
        
        # Determine which site data to use
        if selected_site_name == "Sample Site (Demo)":
            center_coords = [36.1512, -95.9607]
            zoom_level = 13
            site_name_display = "Sample Datacenter Site"
        else:
            # For now, use sample coordinates for user sites
            # In production, you'd geocode the location or store lat/lon
            center_coords = [36.1512, -95.9607]  # Placeholder
            zoom_level = 13
            site_name_display = selected_site_name
            st.info("💡 **Tip:** Add GPS coordinates to your site configuration for accurate map positioning")
    else:
        # No user sites - show sample only
        st.caption("📍 Sample datacenter site with transmission, gas, fiber, and water infrastructure")
        center_coords = [36.1512, -95.9607]
        zoom_level = 13
        site_name_display = "Sample Datacenter Site"
    
    # Create basemap
    m = folium.Map(
        location=center_coords,
        zoom_start=zoom_level,
        tiles='CartoDB positron'
    )
    
    # Load and add GeoJSON layers
    try:
        # Layer 1: Site Boundary (yellow/gold)
        site_boundary_path = SAMPLE_DATA_DIR / "site_boundary.geojson"
        if site_boundary_path.exists():
            with open(site_boundary_path) as f:
                site_data = json.load(f)
            
            folium.GeoJson(
                site_data,
                name='Site Boundary',
                style_function=lambda x: {
                    'fillColor': '#fbbf24',
                    'color': '#f59e0b',
                    'weight': 3,
                    'fillOpacity': 0.3
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'area_acres', 'available_acres', 'zoning'],
                    aliases=['Site:', 'Total Area:', 'Available:', 'Zoning:']
                )
            ).add_to(m)
        
        # Layer 2: Transmission (red)
        transmission_path = SAMPLE_DATA_DIR / "transmission.geojson"
        if transmission_path.exists():
            with open(transmission_path) as f:
                transmission_data = json.load(f)
            
            folium.GeoJson(
                transmission_data,
                name='Transmission',
                style_function=lambda x: {
                    'color': '#ef4444',
                    'weight': 4,
                    'opacity': 0.8
                },
                marker=folium.CircleMarker(radius=8, fill=True, fillColor='#ef4444', color='#dc2626', weight=2),
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'voltage_kv', 'capacity_mw'],
                    aliases=['Facility:', 'Voltage:', 'Capacity:']
                )
            ).add_to(m)
        
        # Layer 3: Gas Pipeline (orange)
        gas_path = SAMPLE_DATA_DIR / "gas_pipeline.geojson"
        if gas_path.exists():
            with open(gas_path) as f:
                gas_data = json.load(f)
            
            folium.GeoJson(
                gas_data,
                name='Natural Gas',
                style_function=lambda x: {
                    'color': '#f97316',
                    'weight': 3,
                    'opacity': 0.7,
                    'dashArray': '10, 5'
                },
                marker=folium.CircleMarker(radius=6, fill=True, fillColor='#f97316', color='#ea580c', weight=2),
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'diameter_inches', 'capacity_mcf_day'],
                    aliases=['Pipeline:', 'Diameter:', 'Capacity:']
                )
            ).add_to(m)
        
        # Layer 4: Fiber (purple)
        fiber_path = SAMPLE_DATA_DIR / "fiber.geojson"
        if fiber_path.exists():
            with open(fiber_path) as f:
                fiber_data = json.load(f)
            
            folium.GeoJson(
                fiber_data,
                name='Fiber',
                style_function=lambda x: {
                    'color': '#a855f7',
                    'weight': 2,
                    'opacity': 0.7,
                    'dashArray': '5, 5'
                },
                marker=folium.CircleMarker(radius=5, fill=True, fillColor='#a855f7', color='#9333ea', weight=2),
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'capacity_gbps', 'provider'],
                    aliases=['Route:', 'Capacity:', 'Provider:']
                )
            ).add_to(m)
        
        # Layer 5: Water (blue)
        water_path = SAMPLE_DATA_DIR / "water.geojson"
        if water_path.exists():
            with open(water_path) as f:
                water_data = json.load(f)
            
            folium.GeoJson(
                water_data,
                name='Water',
                style_function=lambda x: {
                    'color': '#3b82f6',
                    'weight': 3,
                    'opacity': 0.6
                },
                marker=folium.CircleMarker(radius=6, fill=True, fillColor='#3b82f6', color='#2563eb', weight=2),
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'type'],
                    aliases=['Feature:', 'Type:']
                )
            ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 180px; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px;">
        <p style="margin: 0; font-weight: bold;">Infrastructure Layers</p>
        <p style="margin: 5px 0;"><span style="color: #fbbf24;">█</span> Site Boundary</p>
        <p style="margin: 5px 0;"><span style="color: #ef4444;">█</span> Transmission (345kV)</p>
        <p style="margin: 5px 0;"><span style="color: #f97316;">█</span> Natural Gas</p>
        <p style="margin: 5px 0;"><span style="color: #a855f7;">█</span> Fiber Optic</p>
        <p style="margin: 5px 0;"><span style="color: #3b82f6;">█</span> Water</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
    except Exception as e:
        st.warning(f"Could not load some GeoJSON layers: {e}")
    
    # Display map
    st_folium(m, width=None, height=500)
    
    st.markdown("---")
    
    # =========================================================================
    # SECTION 2: SITE MANAGEMENT
    # =========================================================================
    st.markdown("### 📋 Site Management")
    st.caption("Add and configure sites with detailed parameters")
    
    # Add/Edit Site Form
    with st.expander("➕ Add New Site", expanded=len(st.session_state.sites_list) == 0):
        render_site_form()
    
    # Display existing sites
    if st.session_state.sites_list:
        st.markdown("#### Configured Sites")
        
        for idx, site in enumerate(st.session_state.sites_list):
            with st.container(border=True):
                col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
                
                with col_h1:
                    st.markdown(f"### 📍 {site['name']}")
                    st.caption(f"{site['location']} • {site['iso']}")
                
                with col_h2:
                    st.metric("IT Capacity", f"{site['it_capacity_mw']} MW")
                    st.caption(f"Facility: {site['facility_mw']} MW @ PUE {site['pue']}")
                
                with col_h3:
                    if st.button("✏️ Edit", key=f"edit_{idx}", use_container_width=True):
                        st.session_state.editing_site_idx = idx
                        st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_{idx}", use_container_width=True):
                        st.session_state.sites_list.pop(idx)
                        st.rerun()
                
                # Show site details in tabs
                with st.expander("📊 View Details"):
                    tab1, tab2, tab3 = st.tabs(["Basic Info", "Constraints", "Infrastructure"])
                    
                    with tab1:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"""
                            **Location:** {site['location']}  
                            **ISO/RTO:** {site['iso']}  
                            **IT Capacity:** {site['it_capacity_mw']} MW  
                            **PUE:** {site['pue']}
                            """)
                        with col2:
                            st.markdown(f"""
                            **Facility Load:** {site['facility_mw']} MW  
                            **Land Area:** {site.get('land_acres', '—')} acres  
                            **Zoning:** {site.get('zoning', 'Not specified')}
                            """)
                    
                    with tab2:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Air Quality**")
                            st.markdown(f"NOx Limit: {site.get('nox_limit_tpy', '—')} tpy")
                            st.markdown(f"Permit Type: {site.get('permit_type', '—')}")
                        
                        with col2:
                            st.markdown("**Resources**")
                            st.markdown(f"Gas Supply: {site.get('gas_supply_mcf', '—')} MCF/day")
                            st.markdown(f"Water: {site.get('water_available', 'Not specified')}")
                    
                    with tab3:
                        st.markdown("**Grid**")
                        st.markdown(f"Voltage: {site.get('voltage_kv', '—')} kV")
                        st.markdown(f"Queue Position: {site.get('queue_position', '—')}")
                        st.markdown(f"Interconnection Date: {site.get('interconnection_date', '—')}")
    else:
        st.info("📋 No sites configured yet. Add your first site above.")


def render_site_form():
    """Render the site creation/editing form"""
    
    st.markdown("#### Basic Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        site_name = st.text_input("Site Name *", placeholder="e.g., Phoenix DC-1")
        location = st.text_input("Location *", placeholder="e.g., Phoenix, AZ")
    
    with col2:
        iso = st.selectbox("ISO/RTO *", [
            "ERCOT", "PJM", "CAISO", "MISO", "SPP", "NYISO", "ISO-NE", "Other"
        ])
        it_capacity = st.number_input("IT Capacity (MW) *", min_value=10, max_value=2000, value=600, step=50)
    
    with col3:
        pue = st.number_input("PUE *", min_value=1.0, max_value=2.0, value=1.25, step=0.05)
        facility_mw = it_capacity * pue
        st.metric("Facility Load", f"{facility_mw:.1f} MW")
    
    st.markdown("#### Site Constraints")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.markdown("**Air Permitting**")
        permit_type = st.selectbox("Permit Type", ["Minor Source", "Major Source (PSD)", "Synthetic Minor", "Title V"])
        nox_limit = st.number_input("NOx Limit (tpy)", min_value=0, max_value=1000, value=100, step=10)
    
    with col_c2:
        st.markdown("**Land & Gas**")
        land_acres = st.number_input("Available Land (acres)", min_value=0, max_value=2000, value=500, step=50)
        gas_supply = st.number_input("Gas Supply (MCF/day)", min_value=0, max_value=200000, value=75000, step=1000)
    
    with col_c3:
        st.markdown("**Grid**")
        voltage_kv = st.number_input("Interconnection Voltage (kV)", min_value=69, max_value=765, value=345, step=1)
        queue_position = st.number_input("Queue Position", min_value=1, max_value=1000, value=50)
    
    st.markdown("#### Additional Details")
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        zoning = st.text_input("Zoning", placeholder="e.g., Industrial")
        water_available = st.selectbox("Water Availability", ["Municipal", "Groundwater", "Surface Water", "Multiple Sources", "Limited"])
    
    with col_d2:
        interconnection_date = st.date_input("Target Interconnection Date")
        n_minus_1 = st.checkbox("N-1 Redundancy Required", value=True)
    
    # Save button
    if st.button("💾 Save Site", type="primary", use_container_width=True):
        if not site_name:
            st.error("Site name is required")
        elif not location:
            st.error("Location is required")
        else:
            new_site = {
                'name': site_name,
                'location': location,
                'iso': iso,
                'it_capacity_mw': it_capacity,
                'pue': pue,
                'facility_mw': facility_mw,
                'permit_type': permit_type,
                'nox_limit_tpy': nox_limit,
                'land_acres': land_acres,
                'gas_supply_mcf': gas_supply,
                'voltage_kv': voltage_kv,
                'queue_position': queue_position,
                'zoning': zoning,
                'water_available': water_available,
                'interconnection_date': str(interconnection_date),
                'n_minus_1': n_minus_1,
            }
            
            st.session_state.sites_list.append(new_site)
            st.success(f"✅ Site '{site_name}' saved successfully!")
            st.rerun()


if __name__ == "__main__":
    render()
