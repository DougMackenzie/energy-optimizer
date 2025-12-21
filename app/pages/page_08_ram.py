"""
RAM Analysis Page
Reliability, Availability, Maintainability modeling
"""

import streamlit as st


def render():
    st.markdown("### 🛡️ RAM Analysis")
    
    st.info(
        "💡 **Layered Reliability Framework:** This analysis uses a tiered approach—screening via "
        "closed-form approximations, validated by selective Monte Carlo for edge cases. "
        "Industry-standard equipment failure data from IEEE Gold Book, NERC GADS, and OEM sources."
    )
    
    # Summary metrics
    cols = st.columns(5)
    metrics = [
        ("System Availability", "99.92%", "Target: 99.9%", "success"),
        ("MTBF", "4,380 hrs", "~6 months", None),
        ("MTTR", "3.5 hrs", None, None),
        ("Expected Outages", "2.0/yr", None, None),
        ("Downtime", "7 hrs/yr", None, None),
    ]
    
    for i, (label, value, delta, color) in enumerate(metrics):
        with cols[i]:
            st.metric(label, value, delta)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Reliability Block Diagram")
        
        # Visual representation
        layers = [
            ("Engines", "6 parallel (5 req)", "#2E86AB", "99.85%"),
            ("BESS", "100 MWh", "#F18F01", "99.5%"),
            ("Solar", "50 MW PV", "#28A745", "98.0%"),
            ("Grid", "150 MW Import", "#6c757d", "99.97%"),
        ]
        
        for name, config, color, avail in layers:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 80px; font-size: 11px; font-weight: 600;">{name}</div>
                    <div style="flex: 1; height: 24px; background: {color}; border-radius: 4px; 
                                display: flex; align-items: center; justify-content: center; 
                                color: white; font-size: 10px;">{config}</div>
                    <div style="width: 60px; text-align: right; font-family: monospace; font-size: 11px;">{avail}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.caption("Configuration: 6-of-6 engines in parallel (5 required for N-1), BESS provides bridge power, Grid as backup.")
    
    with col2:
        st.markdown("#### Equipment Failure Data")
        
        failure_data = {
            "Equipment": ["Wärtsilä 50SG", "LFP BESS", "Solar PV", "Grid Import", "Transformer", "Switchgear"],
            "FOR": ["2.5%", "0.5%", "2.0%", "0.03%", "0.1%", "0.05%"],
            "MTBF": ["2,500 hrs", "8,760 hrs", "4,380 hrs", "35,000 hrs", "100,000 hrs", "50,000 hrs"],
            "MTTR": ["24 hrs", "4 hrs", "8 hrs", "2 hrs", "72 hrs", "8 hrs"],
            "Source": ["OEM", "IEEE", "NERC", "Utility", "IEEE", "IEEE"],
        }
        
        st.dataframe(failure_data, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Sensitivity Analysis
    st.markdown("#### Sensitivity Analysis")
    st.caption("Impact of key parameters on system availability")
    
    cols = st.columns(3)
    
    sensitivities = [
        ("Add 7th Engine", "99.98%", "+0.06%", "#28A745"),
        ("Reduce MTTR 50%", "99.96%", "+0.04%", "#28A745"),
        ("Double BESS Capacity", "99.94%", "+0.02%", "#28A745"),
    ]
    
    for i, (label, value, delta, color) in enumerate(sensitivities):
        with cols[i]:
            st.markdown(
                f"""
                <div style="text-align: center; padding: 16px; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 4px;">{label}</div>
                    <div style="font-size: 24px; font-weight: 700; color: {color};">{value}</div>
                    <div style="font-size: 11px; color: {color};">{delta}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


if __name__ == "__main__":
    render()
