"""
# Last updated: 2025-12-25 09:04:24
Dispatch Page - UPDATED
8760 hourly dispatch and transient (seconds-level) analysis
Now with year selector and actual load profile integration
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render():
    st.markdown("### 📈 Dispatch")
    st.caption("Detailed dispatch results: 8760 hourly and transient second-by-second analysis")
    
    # Site, Stage, and Year Selectors
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        if 'sites_list' in st.session_state and st.session_state.sites_list:
            site_names = [s.get('name', 'Unknown') for s in st.session_state.sites_list]
            selected_site = st.selectbox("Select Site", options=site_names, key="dispatch_site")
            
            # Get site object
            site_obj = next((s for s in st.session_state.sites_list if s.get('name') == selected_site), None)
        else:
            st.warning("No sites configured")
            return
    
    with col_s2:
        stage_options = ["Screening Study", "Concept Development", "Preliminary Design", "Detailed Design"]
        stage = st.selectbox("EPC Stage", options=stage_options, key="dispatch_stage")
    
    with col_s3:
        pass  # Placeholder for third column
    
    st.markdown("---")
    
    # Display problem type prominently
    problem_num_display = site_obj.get('problem_num', 1)  # Load from site data (Google Sheets)
    from config.settings import PROBLEM_STATEMENTS
    problem_info_display = PROBLEM_STATEMENTS.get(problem_num_display, PROBLEM_STATEMENTS[1])
    
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
                padding: 16px 24px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #2b6cb0;">
        <div style="color: white; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
            {problem_info_display['icon']} PROBLEM STATEMENT
        </div>
        <div style="color: #bee3f8; font-size: 18px; font-weight: 700;">
            P{problem_num_display}: {problem_info_display['name']}
        </div>
        <div style="color: #90cdf4; font-size: 13px; margin-top: 4px;">
            {problem_info_display['objective']} — {problem_info_display['question']}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Year selector for 15-year forecast
    year_options = [f"Year {i}" for i in range(1, 16)]
    selected_year = st.selectbox("Forecast Year", options=year_options, key="dispatch_year")
    year_num = int(selected_year.split()[1])
    
    # Display site context at top (dynamic based on selections)
    if site_obj:
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        
        with col_c1:
            st.markdown(f"""
            <div style='background: #E3F2FD; padding: 15px; border-radius: 8px;'>
                <div style='color: #1565C0; font-size: 12px;'>📍 Site: <b>{selected_site}</b></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_c2:
            location = f"{site_obj.get('city', 'Unknown')}, {site_obj.get('state', 'N/A')}"
            st.markdown(f"""
            <div style='background: #FFE0B2; padding: 15px; border-radius: 8px;'>
                <div style='color: #E65100; font-size: 12px;'>📍 Location: <b>{location}</b></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_c3:
            it_load = site_obj.get('facility_mw', 0)
            # Apply year growth
            it_load_year = it_load * (1.02 ** (year_num - 1))
            st.markdown(f"""
            <div style='background: #FFF9C4; padding: 15px; border-radius: 8px;'>
                <div style='color: #F57F17; font-size: 12px;'>⚡ IT Load: <b>{it_load_year:.0f} MW</b></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_c4:
            stage_short = stage.split()[0]
            st.markdown(f"""
            <div style='background: #E1F5FE; padding: 15px; border-radius: 8px;'>
                <div style='color: #0277BD; font-size: 12px;'>ℹ️ <b>{stage_short} | {selected_year}</b></div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load optimization results
    stage_key_map = {
        "Screening Study": "screening",
        "Concept Development": "concept",
        "Preliminary Design": "preliminary",
        "Detailed Design": "detailed"
    }
    
    stage_key = stage_key_map.get(stage, "screening")
    
    # Try to load from session state first, then Google Sheets
    result_data = None
    if ('optimization_result' in st.session_state and 
        st.session_state.get('optimization_site') == selected_site and
        st.session_state.get('optimization_stage') == stage_key):
        result_data = st.session_state.optimization_result
        st.info("📝 Showing unsaved optimization results")
    else:
        try:
            from app.utils.site_backend import load_site_stage_result
            result_data = load_site_stage_result(selected_site, stage_key)
        except:
            pass
    
    if not result_data:
        st.warning(f"⚠️ No optimization results found for {selected_site} - {stage}")
        st.info("💡 Go to Configuration page to run an optimization first")
        return
    
    # Extract equipment from optimization results
    equipment = result_data.get('equipment', {})
    
    # Load actual load profile if available
    load_profile_8760 = load_actual_8760_profile(site_obj, selected_site, year_num)
    
    # Get actual dispatch from optimizer results (priority #1)
    actual_year = 2027 + (year_num - 1)  # Convert Year 1 -> 2027, Year 2 -> 2028, etc.
    dispatch_df = None
    
    if 'dispatch_by_year' in result_data and actual_year in result_data['dispatch_by_year']:
        # Use optimizer's actual dispatch
        dispatch_result = result_data['dispatch_by_year'][actual_year]
        if hasattr(dispatch_result, 'dispatch_df'):
            dispatch_df = dispatch_result.dispatch_df.copy()
            print(f"✅ Using optimizer dispatch for year {actual_year}")
        elif isinstance(dispatch_result, pd.DataFrame):
            dispatch_df = dispatch_result.copy()
            print(f"✅ Using optimizer dispatch DataFrame for year {actual_year}")
    
    # Respect grid_available_year constraint
    grid_available_year = result_data.get('constraints', {}).get('grid_available_year')
    if dispatch_df is not None and grid_available_year and actual_year < grid_available_year:
        # Zero out grid before it's available
        if 'grid_mw' in dispatch_df.columns:
            dispatch_df['grid_mw'] = 0
            print(f"⚠️ Grid zeroed - not available until {grid_available_year} (current year: {actual_year})")
    
    # Fallback: Generate synthetic dispatch if optimizer data not available
    if dispatch_df is None:
        print(f"⚠️ No optimizer dispatch for year {actual_year}, generating synthetic data")
        dispatch_df = generate_8760_dispatch(equipment, load_profile_8760)
        
        # IMPORTANT: Zero out grid if before grid_available_year (even in synthetic mode)
        if grid_available_year and actual_year < grid_available_year:
            if 'grid_mw' in dispatch_df.columns:
                dispatch_df['grid_mw'] = 0
                print(f"⚠️ Synthetic dispatch: Grid zeroed - not available until {grid_available_year}")
    
    # 8760 Hourly Dispatch Chart
    st.markdown("#### 8760 Hourly Dispatch")
    render_8760_chart(dispatch_df, equipment)
    
    st.markdown("---")
    
    # Transient Analysis
    st.markdown("#### Transient Analysis (Second-by-Second)")
    
    col_t1, col_t2 = st.columns([3, 1])
    
    with col_t1:
        hour_of_year = st.slider("Select Hour of Year", min_value=1, max_value=8760, value=4380, key="transient_hour")
    
    with col_t2:
        st.metric("Selected Hour", f"{hour_of_year}")
        st.caption("300 seconds shown")
    
    # Generate transient data in real-time
    render_transient_chart(hour_of_year, equipment, dispatch_df)
    
    st.markdown("---")
    
    # Dispatch Statistics
    st.markdown("#### Dispatch Statistics")
    render_dispatch_stats(dispatch_df, equipment)


def load_actual_8760_profile(site_obj: dict, site_name: str, year_num: int) -> np.ndarray:
    """Load actual 8760 load profile from site data or session state"""
    
    # Try to get from session state first (load_profile_dr)
    if 'load_profile_dr' in st.session_state:
        load_8760 = st.session_state.load_profile_dr
        if len(load_8760) == 8760:
            # Apply year growth
            load_8760_year = load_8760 * (1.02 ** (year_num - 1))
            return load_8760_year
    
    # Try to load from site backend
    try:
        from app.utils.site_backend import load_site_load_profile
        load_profile = load_site_load_profile(site_name)
        if load_profile and len(load_profile.get('hourly_mw', [])) == 8760:
            load_8760 = np.array(load_profile['hourly_mw'])
            load_8760_year = load_8760 * (1.02 ** (year_num - 1))
            return load_8760_year
    except:
        pass
    
    # Fallback: Generate realistic data center load profile
    base_load = site_obj.get('facility_mw', 900) * (1.02 ** (year_num - 1))
    return generate_realistic_dc_load(base_load)


def generate_realistic_dc_load(base_load_mw: float) -> np.ndarray:
    """Generate realistic data center load profile (much more stable than random)"""
    
    hours = 8760
    load_profile = np.zeros(hours)
    
    for h in range(hours):
        day_of_week = (h // 24) % 7
        hour_of_day = h % 24
        day_of_year = h // 24
        
        # Data centers have very stable load with small variations
        # Base load with minimal hourly variation (±1-2%)
        hourly_variation = 1.0 + np.random.normal(0, 0.01)
        
        # Slight daily pattern (0.98-1.02 range)
        daily_factor = 1.0 + 0.01 * np.sin((hour_of_day - 12) * np.pi / 12)
        
        # Weekday vs weekend (weekends slightly lower, 2-3%)
        weekend_factor = 0.97 if day_of_week >= 5 else 1.0
        
        # Seasonal variation (±3% summer vs winter for cooling)
        seasonal_factor = 1.0 + 0.03 * np.sin((day_of_year - 180) * 2 * np.pi / 365)
        
        load_profile[h] = base_load_mw * hourly_variation * daily_factor * weekend_factor * seasonal_factor
    
    return load_profile


def generate_8760_dispatch(equipment: dict, load_profile_8760: np.ndarray) -> pd.DataFrame:
    """Generate 8760 hourly dispatch based on actual equipment and load profile"""
    
    hours = list(range(8760))
    load_mw = load_profile_8760.tolist()
    
    # Solar generation (follows sun pattern with cloud transients)
    solar_capacity = equipment.get('solar_mw', 0)
    solar_mw = []
    for h in range(8760):
        day_of_year = h // 24
        hour_of_day = h % 24
        
        if 6 <= hour_of_day <= 18:  # Daylight hours
            # Sun angle
            sun_intensity = np.sin((hour_of_day - 6) * np.pi / 12)
            # Seasonal variation (better in summer)
            seasonal = 1.0 + 0.15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
            # Cloud factor (random 0.7-1.0)
            cloud_factor = 0.7 + 0.3 * np.random.random()
            solar_mw.append(solar_capacity * sun_intensity * seasonal * cloud_factor * 0.25)
        else:
            solar_mw.append(0)
    
    # Dispatch logic: Economically optimal stack
    recip_mw = []
    turbine_mw = []
    bess_mw = []
    bess_soc = 0.5  # Start at 50% state of charge
    grid_mw = []
    unserved_mw = []
    
    recip_cap = equipment.get('recip_mw', 0)
    turbine_cap = equipment.get('turbine_mw', 0)
    bess_power_cap = equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4)
    bess_energy_cap = equipment.get('bess_mwh', bess_power_cap * 4)
    grid_cap = equipment.get('grid_mw', 0)
    
    for h in range(8760):
        remaining_load = load_mw[h] - solar_mw[h]
        hour_of_day = h % 24
        
        # 1. Turbines for baseload (most efficient, 24/7)
        turbine_dispatch = min(turbine_cap, remaining_load * 0.9)  # Run at 90% of remaining
        remaining_load -= turbine_dispatch
        turbine_mw.append(turbine_dispatch)
        
        # 2. Recip for mid-merit (flexible)
        recip_dispatch = min(recip_cap, max(0, remaining_load))
        remaining_load -= recip_dispatch
        recip_mw.append(recip_dispatch)
        
        # 3. BESS for peak shaving (14-20) and valley filling (0-6)
        if 14 <= hour_of_day <= 20:  # Peak hours - discharge
            bess_discharge = min(bess_power_cap, remaining_load, bess_soc * bess_energy_cap)
            remaining_load -= bess_discharge
            bess_soc -= bess_discharge / bess_energy_cap
            bess_mw.append(bess_discharge)
        elif 0 <= hour_of_day <= 6:  # Off-peak - charge from solar excess
            solar_excess = max(0, solar_mw[h] - load_mw[h] * 0.5)
            bess_charge = min(bess_power_cap, solar_excess, (1.0 - bess_soc) * bess_energy_cap)
            bess_soc += bess_charge / bess_energy_cap
            bess_mw.append(-bess_charge)  # Negative for charging
        else:
            bess_mw.append(0)
        
        # Keep SOC in bounds
        bess_soc = np.clip(bess_soc, 0.1, 0.9)
        
        # 4. Grid as last resort
        grid_dispatch = min(grid_cap, max(0, remaining_load))
        remaining_load -= grid_dispatch
        grid_mw.append(grid_dispatch)
        
        # 5. Unserved load
        unserved_mw.append(max(0, remaining_load))
    
    df = pd.DataFrame({
        'hour': hours,
        'load_mw': load_mw,
        'solar_mw': solar_mw,
        'recip_mw': recip_mw,
        'turbine_mw': turbine_mw,
        'bess_mw': bess_mw,
        'grid_mw': grid_mw,
        'unserved_mw': unserved_mw
    })
    
    return df


def render_8760_chart(dispatch_df: pd.DataFrame, equipment: dict):
    """Render interactive 8760 hourly dispatch chart"""
    
    fig = go.Figure()
    
    # Stacked area chart - ordered from bottom (slowest) to top (fastest)
    
    # 1. Grid (bottom) - slowest/external
    if dispatch_df['grid_mw'].sum() > 0:
        fig.add_trace(go.Scatter(
            name='Grid', x=dispatch_df['hour'], y=dispatch_df['grid_mw'],
            mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#78909C',
            hovertemplate='Grid: %{y:.1f} MW<extra></extra>'
        ))
    
    # 2. Turbines - slower ramping
    fig.add_trace(go.Scatter(
        name='Turbines', x=dispatch_df['hour'], y=dispatch_df['turbine_mw'],
        mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#42A5F5',
        hovertemplate='Turbines: %{y:.1f} MW<extra></extra>'
    ))
    
    # 3. Recip Engines - faster ramping
    fig.add_trace(go.Scatter(
        name='Recip Engines', x=dispatch_df['hour'], y=dispatch_df['recip_mw'],
        mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#66BB6A',
        hovertemplate='Recip: %{y:.1f} MW<extra></extra>'
    ))
    
    # 4. BESS - very fast response
    fig.add_trace(go.Scatter(
        name='BESS', x=dispatch_df['hour'], y=dispatch_df['bess_mw'],
        mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#AB47BC',
        hovertemplate='BESS: %{y:.1f} MW<extra></extra>'
    ))
    
    # 5. Solar PV (top) - intermittent
    fig.add_trace(go.Scatter(
        name='Solar PV', x=dispatch_df['hour'], y=dispatch_df['solar_mw'],
        mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#FFA726',
        hovertemplate='Solar: %{y:.1f} MW<extra></extra>'
    ))
    
    # Unserved load (if any)
    if dispatch_df['unserved_mw'].sum() > 0:
        fig.add_trace(go.Scatter(
            name='Unserved', x=dispatch_df['hour'], y=dispatch_df['unserved_mw'],
            mode='lines', stackgroup='one', line=dict(width=0), fillcolor='#EF5350',
            hovertemplate='Unserved: %{y:.1f} MW<extra></extra>'
        ))
    
    # Load line
    fig.add_trace(go.Scatter(
        name='Load', x=dispatch_df['hour'], y=dispatch_df['load_mw'],
        mode='lines', line=dict(color='black', width=2, dash='dash'),
        hovertemplate='Load: %{y:.1f} MW<extra></extra>'
    ))
    
    # Calculate Y-axis max from data
    y_max = max(dispatch_df['load_mw'].max(), 
                dispatch_df[['grid_mw', 'turbine_mw', 'recip_mw', 'bess_mw', 'solar_mw']].sum(axis=1).max())
    y_max = y_max * 1.1  # Add 10% padding
    
    fig.update_layout(
        xaxis_title='Hour of Year',
        yaxis_title='Power (MW)',
        hovermode='x unified',
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=50, t=50, b=50),
        dragmode='pan',
        xaxis=dict(
            title='Hour of Year',
            range=[0, 8760],
            autorange=False,
            fixedrange=False,
            constrain='domain',
            rangeslider=dict(
                visible=True,
                thickness=0.05,
                bgcolor='white',
                borderwidth=1,
                bordercolor='gray',
                autorange=False,
                range=[0, 8760]
            )
        ),
        yaxis=dict(
            range=[0, y_max],
            autorange=False,
            fixedrange=False
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
    })
    
    st.caption("💡 Drag to pan, scroll to zoom, use range slider to navigate | Order: Grid → Turbines → Recip → BESS → Solar (slowest to fastest)")


def render_transient_chart(hour_of_year: int, equipment: dict, dispatch_df: pd.DataFrame):
    """Generate and render transient (second-by-second) chart for selected hour"""
    
    # Generate 300 seconds (5 minutes) of transient data
    seconds = list(range(300))
    
    # Get base dispatch for this hour
    hour_idx = hour_of_year - 1
    base_load = dispatch_df.iloc[hour_idx]['load_mw']
    base_solar = dispatch_df.iloc[hour_idx]['solar_mw']
    base_recip = dispatch_df.iloc[hour_idx]['recip_mw']
    base_turbine = dispatch_df.iloc[hour_idx]['turbine_mw']
    base_bess = dispatch_df.iloc[hour_idx]['bess_mw']
    
    # Add second-by-second fluctuations (data centers have very stable load)
    np.random.seed(hour_of_year)
    
    load_transient = base_load + np.random.normal(0, base_load * 0.005, 300)  # ±0.5% fluctuation (data centers are stable)
    solar_transient = base_solar + np.random.normal(0, base_solar * 0.05, 300) if base_solar > 0 else [0] * 300
    recip_transient = [base_recip] * 300  # Steady
    turbine_transient = [base_turbine] * 300  # Steady
    
    # BESS responds to load-solar mismatch
    bess_transient = load_transient - solar_transient - recip_transient - turbine_transient
    bess_power_cap = equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4)
    bess_transient = np.clip(bess_transient, -bess_power_cap, bess_power_cap)
    
    # Create chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        name='Load', x=seconds, y=load_transient,
        mode='lines', line=dict(color='black', width=2),
        hovertemplate='Load: %{y:.2f} MW<extra></extra>'
    ))
    
    if base_solar > 0:
        fig.add_trace(go.Scatter(
            name='Solar', x=seconds, y=solar_transient,
            mode='lines', line=dict(color='#FFA726', width=1.5),
            hovertemplate='Solar: %{y:.2f} MW<extra></extra>'
        ))
    
    fig.add_trace(go.Scatter(
        name='Recip', x=seconds, y=recip_transient,
        mode='lines', line=dict(color='#66BB6A', width=1.5),
        hovertemplate='Recip: %{y:.2f} MW<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        name='Turbines', x=seconds, y=turbine_transient,
        mode='lines', line=dict(color='#42A5F5', width=1.5),
        hovertemplate='Turbines: %{y:.2f} MW<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        name='BESS Response', x=seconds, y=bess_transient,
        mode='lines', line=dict(color='#AB47BC', width=2),
        hovertemplate='BESS: %{y:.2f} MW<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'Transient Analysis - Hour {hour_of_year} (second-by-second)',
        xaxis_title='Time (seconds)',
        yaxis_title='Power (MW)',
        hovermode='x unified',
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        dragmode='pan'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': True
    })
    
    st.caption("💡 Shows BESS responding to load fluctuations and solar intermittency")


def render_dispatch_stats(dispatch_df:pd.DataFrame, equipment: dict):
    """Render dispatch statistics"""
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    
    with col_stats1:
        recip_cap = equipment.get('recip_mw', 1)
        recip_util = dispatch_df['recip_mw'].mean() / recip_cap * 100 if recip_cap > 0 else 0
        st.metric("Recip Utilization", f"{recip_util:.1f}%")
    
    with col_stats2:
        # BESS cycles = total energy throughput / battery capacity
        bess_energy = dispatch_df['bess_mw'].abs().sum()
        bess_cap = equipment.get('bess_mwh', 1)
        bess_cycles = bess_energy / bess_cap if bess_cap > 0 else 0
        st.metric("BESS Cycles/Year", f"{bess_cycles:.0f}")
    
    with col_stats3:
        solar_cap = equipment.get('solar_mw', 1)
        solar_cf = dispatch_df['solar_mw'].mean() / solar_cap * 100 if solar_cap > 0 else 0
        st.metric("Solar Capacity Factor", f"{solar_cf:.1f}%")
    
    with col_stats4:
        unserved_hours = (dispatch_df['unserved_mw'] > 0.1).sum()
        st.metric("Unserved Load Hours", f"{unserved_hours}")
