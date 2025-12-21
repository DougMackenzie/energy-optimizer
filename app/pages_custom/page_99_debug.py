"""
Debug page to verify optimization features are loaded
"""

import streamlit as st


def render():
    st.markdown("### 🔬 Optimization Engine Debug")
    
    st.markdown("#### 1. Check scipy installation")
    try:
        import scipy
        st.success(f"✅ scipy installed: version {scipy.__version__}")
    except ImportError as e:
        st.error(f"❌ scipy not installed: {e}")
    
    st.markdown("#### 2. Check optimization engine")
    try:
        from app.utils.optimization_engine import optimize_equipment_configuration, OptimizationEngine
        st.success("✅ optimization_engine.py imports successfully")
        st.code("from app.utils.optimization_engine import optimize_equipment_configuration")
    except Exception as e:
        st.error(f"❌ optimization_engine.py import failed: {e}")
    
    st.markdown("#### 3. Check grid config widget")
    try:
        from app.components.grid_config import render_grid_configuration
        st.success("✅ grid_config.py imports successfully")
        st.code("from app.components.grid_config import render_grid_configuration")
    except Exception as e:
        st.error(f"❌ grid_config.py import failed: {e}")
    
    st.markdown("#### 4. Check multi_scenario updates")
    try:
        from app.utils.multi_scenario import auto_size_equipment_optimized
        st.success("✅ auto_size_equipment_optimized() exists")
        st.code("from app.utils.multi_scenario import auto_size_equipment_optimized")
    except Exception as e:
        st.error(f"❌ auto_size_equipment_optimized() not found: {e}")
    
    st.markdown("#### 5. Check session state for grid_config")
    if 'grid_config' in st.session_state:
        st.success("✅ grid_config found in session state")
        st.json(st.session_state.grid_config)
    else:
        st.warning("⚠️ grid_config not in session state (visit Equipment Library page first)")
    
    st.markdown("---")
    st.markdown("#### 🎯 Quick Test")
    
    if st.button("Test Optimizer Import"):
        try:
            from app.utils.optimization_engine import OptimizationEngine
            st.success("Successfully imported OptimizationEngine class!")
            
            # Show some methods
            st.code("""
OptimizationEngine methods:
- __init__(site, constraints, scenario, equipment_data, grid_config)
- optimize(objective_weights)
- constraint_nox_emissions(x)
- constraint_co_emissions(x)
- constraint_gas_supply(x)
- constraint_land_area(x)
- constraint_grid_capacity(x)
- constraint_n_minus_1_reliability(x)
- objective_lcoe(x)
- objective_timeline(x)
- objective_emissions(x)
            """)
        except Exception as e:
            st.error(f"Import failed: {e}")
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    render()
