"""
Sites Management Page
Create, edit, and manage site library
"""

import streamlit as st
from app.utils.site_loader import load_sites


def render():
    st.markdown("### 📍 Sites Management")
    
    # Load existing sites
    sites = load_sites()
    
    # Header actions
    col_header, col_actions = st.columns([3, 1])
    
    with col_header:
        st.markdown("Manage your datacenter sites and their configurations")
    
    with col_actions:
        if st.button("➕ New Site", type="primary", use_container_width=True):
            st.session_state.editing_site = "new"
            st.rerun()
    
    # Show existing sites
    st.markdown("---")
    st.markdown("#### 📋 Existing Sites")
    
    if not sites:
        st.info("No sites found. Click 'New Site' to create your first site.")
    else:
        # Create site cards
        for idx, site in enumerate(sites):
            with st.container():
                col1, col2, col3, col4, col_btn = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{site.get('Site_Name', 'Unknown')}**")
                    st.caption(f"{site.get('State', '')}, {site.get('ISO', 'N/A')}")
                
                with col2:
                    st.metric("IT Capacity", f"{site.get('IT_Capacity_MW', 0)} MW", label_visibility="collapsed")
                    st.caption("IT Capacity")
                
                with col3:
                    st.metric("Total MW", f"{site.get('Total_Facility_MW', 0)} MW", label_visibility="collapsed")
                    st.caption("Total Load")
                
                with col4:
                    st.metric("PUE", f"{site.get('Design_PUE', 0)}", label_visibility="collapsed")
                    st.caption("PUE")
                
                with col_btn:
                    if st.button("✏️ Edit", key=f"edit_{idx}", use_container_width=True):
                        st.session_state.editing_site = site.get('Site_ID')
                        st.session_state.editing_site_data = site
                        st.rerun()
                
                st.markdown("---")
    
    # Edit/Create Site Form
    if 'editing_site' in st.session_state:
        st.markdown("---")
        
        if st.session_state.editing_site == "new":
            st.markdown("#### ➕ Create New Site")
            site_data = {}
        else:
            st.markdown(f"#### ✏️ Edit Site: {st.session_state.get('editing_site_data', {}).get('Site_Name', 'Unknown')}")
            site_data = st.session_state.get('editing_site_data', {})
        
        # Site Information Form
        with st.form("site_form"):
            st.markdown("##### Basic Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                site_name = st.text_input("Site Name *", value=site_data.get('Site_Name', ''))
                state = st.text_input("State", value=site_data.get('State', ''))
                city = st.text_input("City", value=site_data.get('City', ''))
                
            with col2:
                site_id = st.text_input("Site ID", value=site_data.get('Site_ID', ''), 
                                       help="Auto-generated if left blank")
                iso = st.selectbox("ISO/RTO", 
                                  ["ERCOT", "PJM", "MISO", "SPP", "CAISO", "NYISO", "ISO-NE"],
                                  index=["ERCOT", "PJM", "MISO", "SPP", "CAISO", "NYISO", "ISO-NE"].index(site_data.get('ISO', 'ERCOT')) if site_data.get('ISO') in ["ERCOT", "PJM", "MISO", "SPP", "CAISO", "NYISO", "ISO-NE"] else 0)
                status = st.selectbox("Status", ["Planning", "Active", "On Hold", "Completed"],
                                    index=["Planning", "Active", "On Hold", "Completed"].index(site_data.get('Status', 'Planning')) if site_data.get('Status') in ["Planning", "Active", "On Hold", "Completed"] else 0)
            
            st.markdown("##### Location")
            col3, col4, col5 = st.columns(3)
            
            with col3:
                latitude = st.number_input("Latitude", value=float(site_data.get('Latitude', 0.0)), 
                                         min_value=-90.0, max_value=90.0, format="%.4f")
            with col4:
                longitude = st.number_input("Longitude", value=float(site_data.get('Longitude', 0.0)),
                                          min_value=-180.0, max_value=180.0, format="%.4f")
            with col5:
                altitude_ft = st.number_input("Altitude (ft)", value=int(site_data.get('Altitude_ft', 0)),
                                            min_value=0, max_value=15000)
            
            st.markdown("##### Facility Parameters")
            col6, col7, col8, col9 = st.columns(4)
            
            with col6:
                it_capacity = st.number_input("IT Capacity (MW) *", value=float(site_data.get('IT_Capacity_MW', 100)),
                                            min_value=1.0, max_value=1000.0)
            with col7:
                design_pue = st.number_input("Design PUE *", value=float(site_data.get('Design_PUE', 1.25)),
                                           min_value=1.0, max_value=3.0, step=0.01)
            with col8:
                total_mw = st.number_input("Total Facility (MW)", value=float(site_data.get('Total_Facility_MW', it_capacity * design_pue)),
                                         min_value=1.0, max_value=1000.0, help="Auto-calculated as IT × PUE if not specified")
            with col9:
                load_factor = st.number_input("Load Factor (%)", value=float(site_data.get('Load_Factor_Pct', 70)),
                                            min_value=0.0, max_value=100.0)
            
            notes = st.text_area("Notes", value=site_data.get('Notes', ''))
            
            # Form buttons
            col_submit, col_cancel = st.columns([1, 1])
            
            with col_submit:
                submitted = st.form_submit_button("💾 Save Site", type="primary", use_container_width=True)
            
            with col_cancel:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if submitted:
                # Validate required fields
                if not site_name:
                    st.error("Site Name is required")
                elif not it_capacity:
                    st.error("IT Capacity is required")
                else:
                    # Generate Site ID if not provided
                    if not site_id:
                        import re
                        site_id = f"SITE-{state[:2].upper()}-{re.sub(r'[^A-Z0-9]', '', site_name.upper())[:8]}"
                    
                    # Calculate total MW if not provided
                    if not total_mw or total_mw == 0:
                        total_mw = it_capacity * design_pue
                    
                    # Create site dict
                    new_site = {
                        'Site_ID': site_id,
                        'Site_Name': site_name,
                        'State': state,
                        'City': city,
                        'ISO': iso,
                        'Latitude': latitude,
                        'Longitude': longitude,
                        'Altitude_ft': altitude_ft,
                        'Avg_Temp_F': 65,  # Default
                        'IT_Capacity_MW': it_capacity,
                        'Design_PUE': design_pue,
                        'Total_Facility_MW': total_mw,
                        'Load_Factor_Pct': load_factor,
                        'Status': status,
                        'Created_Date': site_data.get('Created_Date', '2025-12-21'),
                        'Notes': notes
                    }
                    
                    # TODO: Save to Google Sheets
                    st.success(f"✅ Site '{site_name}' saved successfully!")
                    st.info("💡 Note: Site saving to Google Sheets will be implemented in next step")
                    
                    # Clear editing state
                    del st.session_state.editing_site
                    if 'editing_site_data' in st.session_state:
                        del st.session_state.editing_site_data
                    
                    st.rerun()
            
            if cancelled:
                # Clear editing state
                del st.session_state.editing_site
                if 'editing_site_data' in st.session_state:
                    del st.session_state.editing_site_data
                st.rerun()


if __name__ == "__main__":
    render()
