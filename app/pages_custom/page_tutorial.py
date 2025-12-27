"""
Tutorial & Overview Page
Provides instructions on how to use the Energy Optimizer tool
"""

import streamlit as st
from config.settings import APP_NAME, APP_VERSION, PROBLEM_STATEMENTS

def render():
    st.markdown("### 📚 Tutorial & Overview")
    st.markdown("*Learn how to use the Energy Optimizer for datacenter power optimization*")
    st.markdown("---")
    
    # Introduction
    st.markdown("## Welcome to Antigravity Energy Optimizer")
    
    st.markdown(f"""
    **Version {APP_VERSION}** is a comprehensive tool for optimizing datacenter energy infrastructure 
    across the full project lifecycle—from initial screening through detailed engineering.
    
    This tool helps you:
    - 📊 **Analyze** datacenter power requirements and load profiles
    - 🗺️ **Evaluate** multiple sites and infrastructure configurations
    - 🔧 **Optimize** equipment mix across different EPC stages
    - 📈 **Compare** scenarios and track project development
    - 💰 **Estimate** LCOE, NPV, and detailed economics
    """)
    
    st.markdown("---")
    
    # Workflow Overview
    st.markdown("## 🔄 Complete Workflow")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 1️⃣ Site Configuration
        **Dashboard → Sites & Infrastructure**
        
        - Configure site parameters (location, capacity, constraints)
        - View infrastructure maps (transmission, gas, fiber, water)
        - Assign problem type to site
        - Track optimization progress through EPC stages
        
        **Key Metrics:**
        - IT Capacity (MW)
        - PUE (Power Usage Effectiveness)
        - NOx emissions limit
        - Gas supply capacity
        - Land availability
        """)
        
        st.markdown("""
        ### 3️⃣ Problem-Specific Optimization
        **Problem Pages (P1-P5)**
        
        Run optimizations tailored to your specific problem:
        
        - **P1: Greenfield** - New datacenter on available land
        - **P2: Brownfield** - Existing infrastructure retrofit
        - **P3: Land Development** - Site with land constraints
        - **P4: Grid Services** - Revenue from grid participation
        - **P5: Bridge Power** - Temporary power solution
        
        Each problem has unique constraints and objectives.
        """)
    
    with col2:
        st.markdown("""
        ### 2️⃣ Load Profile Configuration
        **Load Composer**
        
        Define your datacenter's power requirements:
        
        - Annual IT load trajectory (MW)
        - Workload mix (AI training, inference, HPC, etc.)
        - Cooling flexibility for demand response
        - DR program participation
        
        **Pro Tip:** Load profiles are site-specific and auto-saved!
        """)
        
        st.markdown("""
        ### 4️⃣ EPC Stage Progression
        **Progressive Refinement**
        
        Each site progresses through 4 optimization stages:
        
        1. **Screening Study** (Heuristic) - Days
           - Fast feasibility check
           - Rough equipment sizing
           - Initial LCOE estimate
        
        2. **Concept Development** (MILP.1) - Weeks
           - Detailed optimization
           - Equipment schedules
           - Economic analysis
        
        3. **Preliminary Design** (MILP.2) - Months
           - Refined constraints
           - Procurement planning
           - Vendor selection
        
        4. **Detailed Design** (MILP.3) - Months+
           - Final optimization
           - Construction scheduling
           - As-built parameters
        """)
    
    st.markdown("---")
    
    # Step-by-Step Guide
    st.markdown("## 📝 Step-by-Step Gettingstarted Guide")
    
    with st.expander("🚀 Quick Start (5 minutes)", expanded=True):
        st.markdown("""
        ### Your First Optimization
        
        **Step 1: Select a Site**
        1. Navigate to **Dashboard** → **Sites & Infrastructure** tab
        2. Select "Site 1: Phoenix AI Campus" from dropdown
        3. Review site parameters (750 MW IT, Phoenix, AZ)
        
        **Step 2: Assign Problem Type**
        1. Scroll to "Optimization Workflow Tracker"
        2. Select "P1: Greenfield" from Problem Type dropdown
        
        **Step 3: Configure Load**
        1. Click "Run Screening" button or "Open Optimizer"
        2. Navigate to **Load Composer**
        3. Review/adjust load profile (default 600 MW loaded)
        4. Configure workload mix (AI training, inference, etc.)
        
        **Step 4: Run Screening Study**
        1. Navigate to **Problem 1: Greenfield**
        2. Review default constraints
        3. Click "🚀 Run Phase 1 Optimization" button
        4. Wait 30-60 seconds for heuristic optimization
        
        **Step 5: Review Results**
        1. View equipment recommendations (recip, turbine, BESS, solar)
        2. Check LCOE and NPV estimates
        3. Review 8760 dispatch profile
        4. Explore constraint utilization
        
        **Done!** Results are automatically saved to Google Sheets for this site and stage.
        """)
    
    with st.expander("🏗️ Advanced: Multi-Stage Workflow"):
        st.markdown("""
        ### Complete EPC Process
        
        For a full project lifecycle optimization:
        
        **Phase 1: Screening (Week 1)**
        - Run Screening Study for initial feasibility
        - Compare multiple sites if evaluating locations
        - Identify show-stoppers early (emissions, gas, etc.)
        
        **Phase 2: Concept (Weeks 2-4)**
        - Run Concept Development MILP for selected site
        - Refine load projections based on customer commitments
        - Update constraints with utility interconnection feedback
        - Generate preliminary cost estimates
        
        **Phase 3: Preliminary (Months 2-6)**
        - Run Preliminary Design MILP with vendor quotes
        - Update equipment costs from RFPs
        - Refine dispatch based on actual tariff structures
        - Develop procurement strategy
        
        **Phase 4: Detailed (Months 6-18)**
        - Run Detailed Design MILP with as-built parameters
        - Incorporate construction schedule constraints
        - Finalize commissioning sequence
        - Generate operations & maintenance plan
        
        Each stage builds on previous results while refining assumptions and constraints.
        """)
    
    with st.expander("📊 Understanding Results"):
        st.markdown("""
        ### Key Metrics Explained
        
        **LCOE (Levelized Cost of Energy)**
        - Total lifetime cost per MWh delivered
        - Includes capex, fuel, O&M, financing
        - Lower is better (typical range: $60-120/MWh)
        
        **NPV (Net Present Value)**
        - Present value of all cash flows over project life
        - Higher (less negative) is better
        - Negative NPV common for BTM solutions (offset by avoided grid costs)
        
        **Equipment Capacity**
        - Recip Engines: Flexible, fast start, high emissions
        - Turbines: Efficient at scale, slower response
        - BESS: Fast response, energy shifting, no emissions
        - Solar: Low opex, intermittent, land intensive
        - Grid: Reliable backup, long lead time
        
        **8760 Dispatch**
        - Hourly equipment output for full year
        - Shows load following behavior
        - Identifies curtailment opportunities
        - Validates equipment sizing
        """)
    
    st.markdown("---")
    
    # Pro Tips
    st.markdown("## 💡 Pro Tips")
    
    col_tips1, col_tips2 = st.columns(2)
    
    with col_tips1:
        st.success("""
        **✅ Best Practices**
        
        - Always select a site before running optimizations
        - Configure load profile specific to each site
        - Start with Screening Study before detailed MILP
        - Save aggressive constraints for later stages
        - Compare multiple sites at Screening stage
        - Update costs as vendor quotes come in
        """)
    
    with col_tips2:
        st.warning("""
        **⚠️ Common Pitfalls**
        
        - Forgetting to assign problem type to site
        - Running MILP without load profile configured
        - Setting constraints too tight (causes infeasibility)
        - Ignoring interconnection timelines (grid delays)
        - Not accounting for land use restrictions
        - Overlooking NOx and emissions limits
        """)
    
    st.markdown("---")
    
    # Problem Types Reference
    st.markdown("## 🎯 Problem Types Reference")
    
    for prob_num, prob in PROBLEM_STATEMENTS.items():
        with st.expander(f"{prob['icon']} P{prob_num}: {prob['name']}"):
            st.markdown(f"**{prob['question']}**")
            st.markdown(f"**Objective:** {prob['objective']}")
            st.markdown(f"\n**Typical Use Cases:**")
            
            use_cases = {
                1: ["New datacenter on greenfield site", "Master-planned development", "Large campus builds"],
                2: ["Existing facility expansion", "Equipment refresh", "Capacity upgrades"],
                3: ["Constrained urban sites", "Phased development", "Mixed-use properties"],
                4: ["Grid services revenue", "Demand response programs", "Ancillary services"],
                5: ["Temporary power needs", "Interconnection delays", "Rapid deployment"]
            }
            
            for use_case in use_cases.get(prob_num, []):
                st.markdown(f"- {use_case}")
    
    st.markdown("---")
    
    # Getting Help
    st.markdown("## 🆘 Getting Help")
    
    st.info("""
    **Need assistance?**
    
    - 📖 **Documentation**: Review this tutorial and hover tooltips throughout the app
    - 🐛 **Issues**: Check the Developer → Debug page for diagnostics
    - 💾 **Data**: All results are saved to Google Sheets automatically
    - 🔄 **Refresh**: If something seems wrong, try refreshing the browser
    
    **Remember**: This tool is designed for progressive refinement. Start simple with Screening Studies, 
    then add complexity as your project matures through the EPC process.
    """)
