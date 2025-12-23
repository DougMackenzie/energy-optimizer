"""
Debug page to inspect session state
"""

import streamlit as st

def render():
    st.title("🐛 Debug Session State")
    
    st.markdown("### Session State Keys")
    st.write(f"Total keys: {len(st.session_state.keys())}")
    
    for key in sorted(st.session_state.keys()):
        st.write(f"- `{key}`")
    
    st.markdown("---")
    st.markdown("### Critical Values")
    
    # Check MILP mode
    use_fast = st.session_state.get('use_fast_milp', 'NOT SET')
    st.write(f"**use_fast_milp:** `{use_fast}`")
    
    # Check if load_profile_dr exists
    has_load_profile = 'load_profile_dr' in st.session_state
    st.write(f"**has load_profile_dr:** `{has_load_profile}`")
    
    if has_load_profile:
        load_profile = st.session_state.load_profile_dr
        st.write(f"**peak_it_mw:** `{load_profile.get('peak_it_mw', 'NOT SET')}`")
        st.write(f"**pue:** `{load_profile.get('pue', 'NOT SET')}`")
        st.write(f"**workload_mix keys:** `{list(load_profile.get('workload_mix', {}).keys())}`")
    
    # Check initialized flag
    initialized = st.session_state.get('initialized', False)
    st.write(f"**initialized:** `{initialized}`")
    
    st.markdown("---")
    st.markdown("### Full Session State")
    
    if st.button("Show Full Session State"):
        st.json(dict(st.session_state))
    
    st.markdown("---")
    
    if st.button("🔄 Clear Session State & Reload"):
        st.session_state.clear()
        st.rerun()
