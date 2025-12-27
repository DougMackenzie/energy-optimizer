"""
Site Context Helper for Load Composer
Add this at the top of render() function
"""

import streamlit as st

def display_site_context(selected_site=None):
    """Display current site context and load site-specific data"""
    
    # Use passed site or fall back to session state
    site_name = selected_site if selected_site else st.session_state.get('current_site')
    
    if site_name:
        stage = st.session_state.get('current_stage', 'screening')
        
        # Get site data
        site = None
        if 'sites_list' in st.session_state:
            site = next((s for s in st.session_state.sites_list if s.get('name') == site_name), None)
        
        if site:
            # Site info banner
            col_ctx1, col_ctx2, col_ctx3, col_ctx4 = st.columns([2, 2, 1, 1])
            with col_ctx1:
                st.info(f"**📍 Site:** {site['name']}")
            with col_ctx2:
                st.info(f"**📍 Location:** {site['location']}")
            with col_ctx3:
                st.info(f"**⚡ IT:** {site['it_capacity_mw']} MW")
            with col_ctx4:
                stage_labels = {
                    'screening': '1️⃣ Screening',
                    'concept': '2️⃣ Concept',
                    'preliminary': '3️⃣ Preliminary',
                    'detailed': '4️⃣ Detailed'
                }
                st.info(f"**{stage_labels.get(stage, stage)}**")
            
            # Load site-specific load profile from Google Sheets
            if 'load_profile_dr' not in st.session_state or st.session_state.get('_site_context_loaded') != site_name:
                try:
                    from app.utils.site_backend import load_site_load_profile
                    site_load = load_site_load_profile(site_name)
                    if site_load:
                        st.session_state.load_profile_dr = site_load.get('load_profile', {})
                        st.session_state._site_context_loaded = site_name
                        st.success(f"✓ Loaded saved load profile for {site_name}")
                except Exception as e:
                    print(f"Could not load site load profile: {e}")
                    # Set flag to prevent repeated load attempts
                    st.session_state._site_context_loaded = site_name
                    
            st.markdown("---")
            return True
        else:
            st.warning(f"⚠️ Site '{site_name}' not found in sites list")
            return False
    else:
        st.info("💡 **No site selected.** Navigate to **Dashboard → Sites & Infrastructure** to select a site and start optimization.")
        st.markdown("---")
        return False


def save_load_profile_to_backend():
    """Auto-save current load profile to Google Sheets"""
    
    if not st.session_state.get('current_site'):
        return False
    
    if 'load_profile_dr' not in st.session_state:
        return False
    
    try:
        from app.utils.site_backend import save_site_load_profile
        
        load_data = {
            'load_profile': st.session_state.load_profile_dr,
            'workload_mix': st.session_state.load_profile_dr.get('workload_mix', {}),
            'dr_params': {
                'cooling_flex': st.session_state.load_profile_dr.get('cooling_flex', 0),
                'enabled_products': st.session_state.load_profile_dr.get('enabled_dr_products', [])
            }
        }
        
        result = save_site_load_profile(st.session_state.current_site, load_data)
        return result
    except Exception as e:
        print(f"Error saving load profile: {e}")
        return False
