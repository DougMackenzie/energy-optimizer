"""
Problem Selection Page
Visual selection interface for the 5 optimization problem statements
"""

import streamlit as st
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS


def render():
    """Render the Problem Selection page"""
    
    st.markdown("### 🎯 Select Optimization Problem")
    st.markdown("*Choose the question you want bvNexus to answer*")
    st.markdown("---")
    
    # Introduction
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ebf8ff 0%, #e6fffa 100%); 
                padding: 20px; border-radius: 12px; margin-bottom: 24px;">
        <div style="font-size: 16px; font-weight: 600; color: #2c5282; margin-bottom: 8px;">
            Each problem statement addresses a different optimization question
        </div>
        <div style="font-size: 14px; color: #4a5568;">
            Select the problem that best matches your analysis needs. Each problem has Phase 1 (Heuristic) 
            optimization available now, with Phase 2 (MILP with HiGHS) coming soon.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Problem Cards - Row 1 (Problems 1-3)
    st.markdown("#### Capacity Planning Problems")
    
    cols1 = st.columns(3)
    
    for i, prob_num in enumerate([1, 2, 3]):
        prob = PROBLEM_STATEMENTS[prob_num]
        
        with cols1[i]:
            # Check if this problem has results
            has_results = prob_num in st.session_state.get('optimization_results', {})
            p1_done = st.session_state.get('phase_1_complete', {}).get(prob_num, False)
            
            # Card styling based on state
            border_color = prob['color'] if has_results else "#e2e8f0"
            
            # Use Streamlit container instead of raw HTML
            with st.container(border=True):
                st.markdown(f"### {prob['icon']}")
                st.markdown(f"<p style='color: {prob['color']}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0;'>PROBLEM {prob_num}</p>", unsafe_allow_html=True)
                st.markdown(f"**{prob['name']}**")
                st.markdown(f"<span style='background: rgba(100,100,100,0.1); color: {prob['color']}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{prob['objective']}</span>", unsafe_allow_html=True)
                st.markdown("")
                st.caption(prob['question'])
                st.markdown("---")
                st.caption(f"**Key Output:** {prob['key_output']}")
            
            # Button
            btn_label = "✓ View Results" if p1_done else "Start Analysis →"
            btn_type = "secondary" if p1_done else "primary"
            
            if st.button(btn_label, key=f"select_prob_{prob_num}", use_container_width=True, type=btn_type):
                st.session_state.current_page = f'problem_{prob_num}'
                st.session_state.selected_problem = prob_num
                st.rerun()
    
    st.markdown("")
    st.markdown("#### Operational & Transition Problems")
    
    # Problem Cards - Row 2 (Problems 4-5)
    cols2 = st.columns([1, 1, 1])
    
    for i, prob_num in enumerate([4, 5]):
        prob = PROBLEM_STATEMENTS[prob_num]
        
        with cols2[i]:
            has_results = prob_num in st.session_state.get('optimization_results', {})
            p1_done = st.session_state.get('phase_1_complete', {}).get(prob_num, False)
            border_color = prob['color'] if has_results else "#e2e8f0"
            
            # Use Streamlit container instead of raw HTML
            with st.container(border=True):
                st.markdown(f"### {prob['icon']}")
                st.markdown(f"<p style='color: {prob['color']}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0;'>PROBLEM {prob_num}</p>", unsafe_allow_html=True)
                st.markdown(f"**{prob['name']}**")
                st.markdown(f"<span style='background: rgba(100,100,100,0.1); color: {prob['color']}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{prob['objective']}</span>", unsafe_allow_html=True)
                st.markdown("")
                st.caption(prob['question'])
                st.markdown("---")
                st.caption(f"**Key Output:** {prob['key_output']}")
            
            btn_label = "✓ View Results" if p1_done else "Start Analysis →"
            btn_type = "secondary" if p1_done else "primary"
            
            if st.button(btn_label, key=f"select_prob_{prob_num}", use_container_width=True, type=btn_type):
                st.session_state.current_page = f'problem_{prob_num}'
                st.session_state.selected_problem = prob_num
                st.rerun()
    
    # Comparison guidance
    with cols2[2]:
        with st.container(border=True):
            st.markdown("### 🤔")
            st.markdown("**Not sure which to choose?**")
            st.markdown("")
            st.caption("**New datacenter?**  \n→ Start with **Problem 1: Greenfield**")
            st.caption("**Grid delayed 5+ years?**  \n→ Use **Problem 5: Bridge Power**")
            st.caption("**Existing facility expansion?**  \n→ Try **Problem 2: Brownfield**")
    
    st.markdown("---")
    
    # Comparison Table
    st.markdown("#### 📊 Problem Comparison Matrix")
    
    comparison_data = {
        'Problem': [f"P{n}: {p['short_name']}" for n, p in PROBLEM_STATEMENTS.items()],
        'Objective': [p['objective'] for p in PROBLEM_STATEMENTS.values()],
        'Key Output': [p['key_output'] for p in PROBLEM_STATEMENTS.values()],
        'Resolution': ['6-12 rep weeks', '6-12 rep weeks', 'Multiple scenarios', 'Hourly + response', 'Monthly (72 periods)'],
        'Typical Use Case': [
            'New AI datacenter with known load ramp',
            'Adding capacity to existing facility',
            'Evaluating site development potential',
            'Optimizing demand response participation',
            'Managing grid queue delays'
        ]
    }
    
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.caption(
        "💡 **Note:** All problems use the same site and load configuration from the Sites & Load page. "
        "Configure your site first, then select a problem to optimize."
    )


if __name__ == "__main__":
    render()
