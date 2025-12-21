"""
Dashboard Page
Overview of current project status and key metrics
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import COLORS


def render():
    """Render the Dashboard page"""
    
    # Header
    st.markdown("### 📊 Dashboard")
    st.markdown("---")
    
    # Project info
    project = st.session_state.get('project', {})
    project_name = project.get('name', 'Tulsa Metro Hub')
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Active Project",
            value=project_name,
            help="Current project being analyzed"
        )
        st.caption("SPP Territory • 200 MW")
    
    with col2:
        st.metric(
            label="Best Scenario",
            value="14 mo",
            delta="Time to Power",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="Feasible Scenarios",
            value="47",
            delta="of 100 analyzed"
        )
    
    with col4:
        st.metric(
            label="Best LCOE",
            value="$62",
            delta="per MWh"
        )
    
    with col5:
        st.metric(
            label="Est. CAPEX Range",
            value="$280-350M",
        )
    
    st.markdown("---")
    
    # Two column layout
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### Project Status")
        
        # Progress bar
        progress = 1.0  # 100%
        st.progress(progress, text="Analysis Progress: 100%")
        
        # Status table
        status_data = {
            "Stage": ["Load Profile", "Equipment Selection", "Optimization Run", "RAM Analysis", "Transient Screening", "ETAP Validation"],
            "Status": ["✅ Complete", "✅ Complete", "✅ Complete", "✅ Complete", "⚠️ 4 Pass / 1 Warn", "⏳ Pending"]
        }
        
        st.dataframe(
            status_data,
            use_container_width=True,
            hide_index=True
        )
    
    with col_right:
        st.markdown("#### Quick Actions")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("📊 View Results", use_container_width=True):
                st.session_state.current_page = 'results'
                st.rerun()
                
            if st.button("🎯 Re-run Optimizer", use_container_width=True):
                st.session_state.current_page = 'optimizer'
                st.rerun()
                
            if st.button("📤 ETAP Export", use_container_width=True):
                st.info("ETAP export coming soon...")
        
        with col_b:
            if st.button("⚙️ Dispatch Analysis", use_container_width=True):
                st.session_state.current_page = 'dispatch'
                st.rerun()
                
            if st.button("📄 Export Report", use_container_width=True):
                st.info("Report export coming soon...")
                
            if st.button("💾 Save Project", use_container_width=True):
                st.success("Project saved!")
    
    st.markdown("---")
    
    # Recommended Scenario
    st.markdown("#### ⭐ Recommended Scenario: Recip-Heavy Hybrid")
    
    st.success("**Optimal for Time-to-Power** based on current constraints")
    
    cols = st.columns(6)
    
    metrics = [
        ("Configuration", "6× Wärtsilä 50SG + 100 MWh BESS + 50 MW Solar"),
        ("Time-to-Power", "14 months"),
        ("LCOE", "$68/MWh"),
        ("CAPEX", "$295M"),
        ("Availability", "99.92%"),
        ("Carbon", "385 kg/MWh"),
    ]
    
    for i, (label, value) in enumerate(metrics):
        with cols[i]:
            if i == 0:
                st.markdown(f"**{label}**")
                st.markdown(f"<small>{value}</small>", unsafe_allow_html=True)
            else:
                st.metric(label=label, value=value)
    
    # Footer note
    st.markdown("---")
    st.caption(
        "💡 **Tip:** Start with the Load Composer to define your facility workload mix, "
        "then configure equipment and constraints in the Optimizer."
    )


if __name__ == "__main__":
    render()
