"""
Sites Page - Stub
Site management and mapping
"""

import streamlit as st


def render():
    st.markdown("### 📍 Sites")
    st.info("🚧 **Coming in Phase 2** - Site management with Folium mapping")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### Site List")
        
        # Placeholder site list
        sites = [
            {"name": "Tulsa Metro Hub", "acres": 1200, "status": "Active"},
            {"name": "Oklahoma Industrial Park", "acres": 800, "status": "Review"},
            {"name": "Texas Border Site", "acres": 2000, "status": "Prospect"},
        ]
        
        for site in sites:
            with st.container():
                st.markdown(f"**{site['name']}**")
                st.caption(f"{site['acres']} acres • {site['status']}")
                st.markdown("---")
    
    with col2:
        st.markdown("#### Map View")
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #e8f4f8 0%, #d1e8f0 100%); 
                        height: 400px; border-radius: 8px; display: flex; 
                        align-items: center; justify-content: center; color: #666;">
                📍 Map placeholder - Folium integration coming soon
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("#### Site Details")
        
        # Display site details in formatted cards instead of raw JSON
        st.markdown("**📍 Tulsa Metro Hub**")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Acreage", "1,200 ac")
            st.metric("ISO", "SPP")
        with col_b:
            st.metric("Zoning", "Industrial / M-2")
            st.metric("Queue Position", "47")
        with col_c:
            st.metric("Available Capacity", "150 MW")
            st.metric("Est. Energization", "Q2 2028")
        
        st.markdown("**🔌 Interconnection**")
        st.markdown("""
        - **Substation**: Riverside 345kV
        - **Distance**: 2.3 miles
        - **Coordinates**: 36.1234°N, 95.9876°W
        """)


if __name__ == "__main__":
    render()
