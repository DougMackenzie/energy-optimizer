"""
Dashboard Page
Overview of project status and 5 problem statement progress
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS, OPTIMIZATION_TIERS


def render():
    """Render the Dashboard page"""
    
    st.markdown("### 📊 bvNexus Dashboard")
    st.markdown("*Co-located Power, Energy and Load Optimization for AI Datacenters*")
    st.markdown("---")
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Count completed problems
    phase1_complete = sum(1 for k, v in st.session_state.get('phase_1_complete', {}).items() if v)
    phase2_complete = sum(1 for k, v in st.session_state.get('phase_2_complete', {}).items() if v)
    
    with col1:
        site_name = st.session_state.get('current_site', {}).get('Site_Name', 'Not Selected')
        st.metric("Active Site", site_name[:15] + "..." if len(site_name) > 15 else site_name)
    
    with col2:
        st.metric("Phase 1 Complete", f"{phase1_complete}/5")
    
    with col3:
        st.metric("Phase 2 Complete", f"{phase2_complete}/5")
    
    with col4:
        # Get best LCOE from results
        best_lcoe = None
        for prob_num, result in st.session_state.get('optimization_results', {}).items():
            if result and result.get('lcoe'):
                if best_lcoe is None or result['lcoe'] < best_lcoe:
                    best_lcoe = result['lcoe']
        
        if best_lcoe:
            st.metric("Best LCOE", f"${best_lcoe:.0f}/MWh")
        else:
            st.metric("Best LCOE", "—")
    
    with col5:
        st.metric("Problems", "5 Available")
    
    st.markdown("---")
    
    # Problem Status Cards
    st.markdown("#### 🎯 Problem Statement Status")
    
    # Create two rows of cards
    row1_cols = st.columns(3)
    row2_cols = st.columns(2)
    
    for i, (prob_num, prob_info) in enumerate(PROBLEM_STATEMENTS.items()):
        # Determine which column
        if i < 3:
            col = row1_cols[i]
        else:
            col = row2_cols[i - 3]
        
        with col:
            # Get status
            p1_done = st.session_state.get('phase_1_complete', {}).get(prob_num, False)
            p2_done = st.session_state.get('phase_2_complete', {}).get(prob_num, False)
            result = st.session_state.get('optimization_results', {}).get(prob_num, None)
            
            # Status indicator
            if p2_done:
                status_color = "#48bb78"  # Green
                status_text = "✓ Complete"
            elif p1_done:
                status_color = "#ecc94b"  # Yellow
                status_text = "⏳ Phase 1 Done"
            else:
                status_color = "#e2e8f0"  # Gray
                status_text = "○ Not Started"
            
            st.markdown(f"""
            <div style="background: white; border-radius: 12px; padding: 20px; 
                        border: 2px solid {status_color}; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-size: 28px;">{prob_info['icon']}</span>
                    <span style="background: {status_color}20; color: {status_color}; 
                                 padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                        {status_text}
                    </span>
                </div>
                <div style="font-size: 16px; font-weight: 700; color: {COLORS['text']}; margin-bottom: 4px;">
                    Problem {prob_num}: {prob_info['short_name']}
                </div>
                <div style="font-size: 13px; color: {COLORS['text_light']}; margin-bottom: 12px;">
                    {prob_info['objective']}
                </div>
                <div style="font-size: 12px; color: {COLORS['text_light']}; 
                            background: #f7fafc; padding: 8px; border-radius: 6px;">
                    {prob_info['question'][:80]}...
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Open Problem {prob_num}", key=f"dash_prob_{prob_num}", use_container_width=True):
                st.session_state.current_page = f'problem_{prob_num}'
                st.session_state.selected_problem = prob_num
                st.rerun()
    
    st.markdown("---")
    
    # Quick Actions and Workflow Guide
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("#### 🚀 Quick Start Workflow")
        
        st.markdown("""
        <div style="background: #f7fafc; padding: 16px; border-radius: 8px; border-left: 4px solid #4299e1;">
            <ol style="margin: 0; padding-left: 20px; color: #2d3748;">
                <li style="margin-bottom: 8px;"><strong>Configure Site & Load</strong> - Define your datacenter parameters</li>
                <li style="margin-bottom: 8px;"><strong>Select Problem Type</strong> - Choose the optimization question to answer</li>
                <li style="margin-bottom: 8px;"><strong>Run Phase 1 (Heuristic)</strong> - Get quick indicative results (30-60 sec)</li>
                <li style="margin-bottom: 8px;"><strong>Review Results</strong> - Analyze 8760 dispatch, pro forma, forecasts</li>
                <li style="margin-bottom: 0;"><strong>Run Phase 2 (MILP)</strong> - Full optimization with HiGHS (coming soon)</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("")
        
        if st.button("🎯 Go to Problem Selection", use_container_width=True, type="primary"):
            st.session_state.current_page = 'problem_selection'
            st.rerun()
    
    with col_right:
        st.markdown("#### 📊 Optimization Tiers")
        
        for tier_num, tier_info in OPTIMIZATION_TIERS.items():
            if tier_num == 1:
                bg_color = "#e6fffa"
                border_color = "#38b2ac"
                status = "✓ Available"
            else:
                bg_color = "#f7fafc"
                border_color = "#e2e8f0"
                status = "🔜 Coming Soon"
            
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 12px 16px; border-radius: 8px; 
                        border: 1px solid {border_color}; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 600; color: #2d3748;">Tier {tier_num}: {tier_info['name']}</span>
                        <span style="font-size: 11px; color: #718096; margin-left: 8px;">({tier_info['runtime']})</span>
                    </div>
                    <span style="font-size: 11px; font-weight: 500;">{status}</span>
                </div>
                <div style="font-size: 12px; color: #718096; margin-top: 4px;">
                    {tier_info['accuracy']} • {tier_info['label']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent Results Summary (if any)
    if st.session_state.get('optimization_results'):
        st.markdown("#### 📈 Recent Optimization Results")
        
        results_data = []
        for prob_num, result in st.session_state.get('optimization_results', {}).items():
            if result:
                prob_info = PROBLEM_STATEMENTS[prob_num]
                results_data.append({
                    'Problem': f"P{prob_num}: {prob_info['short_name']}",
                    'Objective': prob_info['objective'],
                    'Result': f"${result.get('lcoe', 0):.1f}/MWh" if result.get('lcoe') else result.get('primary_result', '—'),
                    'Phase': 'Phase 1' if not st.session_state.get('phase_2_complete', {}).get(prob_num) else 'Phase 2',
                    'Status': '✓ Feasible' if result.get('feasible', True) else '✗ Issues',
                })
        
        if results_data:
            df = pd.DataFrame(results_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.caption(
        "💡 **Tip:** Start with Problem 1 (Greenfield) if you're optimizing a new datacenter with a known load trajectory. "
        "Use Problem 5 (Bridge Power) if you need temporary generation while waiting for grid interconnection."
    )


if __name__ == "__main__":
    render()
