# Configuration Page Manual Save Update

Replace the auto-save logic in page_configuration.py starting at line 238:

```python
if result and result.get('feasible'):
    # Store in session state (don't auto-save)
    st.session_state.optimization_result = result  
    st.session_state.optimization_site = site_name
    st.session_state.optimization_stage = selected_stage
    
    st.success(f"""
    ✅ **Optimization Complete!**
    
    **LCOE:** ${result.get('lcoe', 0):.1f}/MWh  
    **Equipment:** {result.get('equipment', {}).get('recip_mw', 0):.0f} MW Recip + {result.get('equipment', {}).get('turbine_mw', 0):.0f} MW Turbine + {result.get('equipment', {}).get('bess_mwh', 0):.0f} MWh BESS + {result.get('equipment', {}).get('solar_mw', 0):.0f} MW Solar  
    **Runtime:** {result.get('runtime_seconds', 0):.1f} seconds
    """)
    
    st.info("💡 Results ready. Use 'Save to Sheets' button below.")
```

Then add this section at the end of the file (after line 283):

```python
# Save Results Section
if 'optimization_result' in st.session_state and st.session_state.get('optimization_site') == site_name:
    st.markdown("---")
    st.markdown("### 💾 Save Results")
    
    col_sv1, col_sv2, col_sv3 = st.columns([2,1,1])
    
    with col_sv1:
        save_option = st.radio(
            "Save as:",
            options=['new', 'overwrite'],
            format_func=lambda x: "🆕 New Version" if x == 'new' else "♻️ Overwrite",
            horizontal=True
        )
    
    with col_sv2:
        if st.button("💾 Save", type="primary", use_container_width=True):
            from app.utils.site_backend import save_site_stage_result
            
            result = st.session_state.optimization_result
            result['version'] = 1  # TODO: Get next version number
            
            save_site_stage_result(
                site_name=st.session_state.optimization_site,
                stage=st.session_state.optimization_stage,
                result_data=result
            )
            
            st.success(f"✅ Saved!")
            del st.session_state.optimization_result
            st.rerun()
    
    with col_sv3:
        if st.button("📊 View", use_container_width=True):
            st.session_state.current_page = 'exec_summary'
            st.rerun()
```
