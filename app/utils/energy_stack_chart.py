"""
15-Year Energy Stack Forecast Chart - FIXED VERSION
Properly uses optimizer's equipment_by_year and respects grid_available_year

Key fixes:
1. Uses equipment_by_year from optimizer results (not constant values)
2. Respects grid_available_year constraint (grid=0 before that year)
3. Uses load_trajectory from backend (not assumed 2% growth)
4. Falls back gracefully if optimizer data not available
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import json
from typing import Dict, List, Optional


def render_energy_stack_forecast(
    equipment: dict, 
    selected_site: str,
    equipment_by_year: Dict[int, dict] = None,
    load_trajectory: Dict[int, float] = None,
    grid_available_year: int = None,
    grid_capacity_mw: float = 0,
):
    """
    Render the 15-year energy stack forecast chart.
    
    Args:
        equipment: Final year equipment config (fallback if equipment_by_year not provided)
        selected_site: Name of selected site
        equipment_by_year: Dict mapping year -> equipment config (from optimizer)
        load_trajectory: Dict mapping year -> load_mw (from backend)
        grid_available_year: Year when grid becomes available (from constraints)
        grid_capacity_mw: Grid capacity in MW (from constraints)
    """
    
    # Determine year range
    base_year = 2025
    years = list(range(base_year, base_year + 15))
    
    # === LOAD TRAJECTORY ===
    # Priority: 1) Passed load_trajectory, 2) Session state, 3) Calculated fallback
    target_load = []
    
    if load_trajectory and len(load_trajectory) > 0:
        # Use provided load trajectory
        for year in years:
            if year in load_trajectory:
                target_load.append(load_trajectory[year])
            else:
                # Interpolate or use nearest year
                known_years = sorted(load_trajectory.keys())
                if year < min(known_years):
                    target_load.append(0)  # Before first load year
                elif year > max(known_years):
                    target_load.append(load_trajectory[max(known_years)])  # Hold at final
                else:
                    # Linear interpolation
                    for i, ky in enumerate(known_years[:-1]):
                        if ky <= year < known_years[i+1]:
                            ratio = (year - ky) / (known_years[i+1] - ky)
                            interp = load_trajectory[ky] + ratio * (load_trajectory[known_years[i+1]] - load_trajectory[ky])
                            target_load.append(interp)
                            break
    else:
        # Try to get from session state
        site_data = _get_site_data(selected_site)
        if site_data and site_data.get('load_trajectory_json'):
            try:
                traj = json.loads(site_data['load_trajectory_json'])
                load_trajectory = {int(k): float(v) for k, v in traj.items()}
                # Recursively call with parsed trajectory
                return render_energy_stack_forecast(
                    equipment=equipment,
                    selected_site=selected_site,
                    equipment_by_year=equipment_by_year,
                    load_trajectory=load_trajectory,
                    grid_available_year=grid_available_year or site_data.get('grid_available_year'),
                    grid_capacity_mw=grid_capacity_mw or site_data.get('grid_capacity_mw', 0),
                )
            except Exception as e:
                print(f"Warning: Could not parse load_trajectory_json: {e}")
        
        # Fallback: Use facility_mw with 2% growth (old behavior)
        base_load = site_data.get('facility_mw', 600) if site_data else 600
        target_load = [base_load * (1.02 ** i) for i in range(15)]
    
    # === GRID AVAILABLE YEAR ===
    # Priority: 1) Passed value, 2) Session state, 3) None (grid always available)
    if grid_available_year is None:
        site_data = _get_site_data(selected_site)
        if site_data and site_data.get('grid_available_year'):
            try:
                grid_available_year = int(site_data['grid_available_year'])
            except:
                pass
        if site_data and site_data.get('grid_capacity_mw') and grid_capacity_mw == 0:
            try:
                grid_capacity_mw = float(site_data['grid_capacity_mw'])
            except:
                pass
    
    # === EQUIPMENT BY YEAR ===
    # Priority: 1) Passed equipment_by_year, 2) Session state optimization results, 3) Constant fallback
    
    recip_capacity = []
    turbine_capacity = []
    solar_capacity = []
    bess_capacity = []
    grid_capacity = []
    
    if equipment_by_year and len(equipment_by_year) > 0:
        # DEBUG: Print grid_mw values
        print("\n🔍 CHART: equipment_by_year grid_mw:")
        for y in sorted(equipment_by_year.keys()):
            print(f"  {y}: {equipment_by_year[y].get('grid_mw', 0):.1f} MW")
        # Use optimizer's year-by-year results
        for year in years:
            if year in equipment_by_year:
                config = equipment_by_year[year]
            else:
                # Find nearest year
                known_years = sorted(equipment_by_year.keys())
                if year < min(known_years):
                    config = {'recip_mw': 0, 'turbine_mw': 0, 'solar_mw': 0, 'bess_mw': 0, 'bess_mwh': 0, 'grid_mw': 0}
                else:
                    # Use most recent year's config
                    nearest = max(y for y in known_years if y <= year)
                    config = equipment_by_year[nearest]
            
            recip_capacity.append(config.get('recip_mw', 0))
            turbine_capacity.append(config.get('turbine_mw', 0))
            solar_capacity.append(config.get('solar_mw', 0))
            bess_capacity.append(config.get('bess_mw', config.get('bess_mwh', 0) / 4))
            
            # CRITICAL: Respect grid_available_year
            if grid_available_year and year < grid_available_year:
                grid_capacity.append(0)  # Grid NOT available yet
            else:
                grid_capacity.append(config.get('grid_mw', grid_capacity_mw))
    else:
        # Try to get from session state optimization results
        opt_result = st.session_state.get('optimization_result')
        if opt_result and 'equipment_by_year' in opt_result:
            # Recursively call with optimizer results
            return render_energy_stack_forecast(
                equipment=equipment,
                selected_site=selected_site,
                equipment_by_year=opt_result['equipment_by_year'],
                load_trajectory=load_trajectory,
                grid_available_year=grid_available_year,
                grid_capacity_mw=grid_capacity_mw,
            )
        
        # Fallback: Use constant equipment (old behavior) BUT respect grid_available_year
        for i, year in enumerate(years):
            recip_capacity.append(equipment.get('recip_mw', 0))
            turbine_capacity.append(equipment.get('turbine_mw', 0))
            solar_capacity.append(equipment.get('solar_mw', 0))
            bess_capacity.append(equipment.get('bess_mw', equipment.get('bess_mwh', 0) / 4))
            
            # CRITICAL: Even in fallback mode, respect grid_available_year
            if grid_available_year and year < grid_available_year:
                grid_capacity.append(0)
            else:
                grid_capacity.append(equipment.get('grid_mw', 0))
    
    # === CALCULATE UNSERVED LOAD ===
    total_capacity = np.array(recip_capacity) + np.array(turbine_capacity) + \
                     np.array(solar_capacity) + np.array(bess_capacity) + np.array(grid_capacity)
    unserved = [max(0, target_load[i] - total_capacity[i]) for i in range(15)]
    
    # === CREATE CHART ===
    fig = go.Figure()
    
    # Add equipment stacks (bottom to top)
    fig.add_trace(go.Bar(
        name='Recip Engines', 
        x=years, 
        y=recip_capacity,
        marker_color='#2E7D32',  # Green
        hovertemplate='Recip: %{y:.0f} MW<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Turbines', 
        x=years, 
        y=turbine_capacity,
        marker_color='#1565C0',  # Blue
        hovertemplate='Turbines: %{y:.0f} MW<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Solar PV', 
        x=years, 
        y=solar_capacity,
        marker_color='#F57C00',  # Orange
        hovertemplate='Solar: %{y:.0f} MW<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='BESS', 
        x=years, 
        y=bess_capacity,
        marker_color='#7B1FA2',  # Purple
        hovertemplate='BESS: %{y:.0f} MW<extra></extra>'
    ))
    
    # Grid - only show if there's any grid capacity
    if any(g > 0 for g in grid_capacity):
        fig.add_trace(go.Bar(
            name='Grid', 
            x=years, 
            y=grid_capacity,
            marker_color='#424242',  # Dark gray
            hovertemplate='Grid: %{y:.0f} MW<extra></extra>'
        ))
    
    # Unserved load (if any)
    if any(u > 0 for u in unserved):
        fig.add_trace(go.Bar(
            name='Unserved Load', 
            x=years, 
            y=unserved,
            marker_color='#C62828',  # Red
            hovertemplate='Unserved: %{y:.0f} MW<extra></extra>'
        ))
    
    # Target load line
    fig.add_trace(go.Scatter(
        name='Target Load', 
        x=years, 
        y=target_load,
        mode='lines+markers',
        line=dict(color='black', width=2, dash='dash'),
        marker=dict(size=6),
        hovertemplate='Target: %{y:.0f} MW<extra></extra>'
    ))
    
    # Layout
    fig.update_layout(
        barmode='stack',
        xaxis_title='Year',
        yaxis_title='Capacity (MW)',
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # === SUMMARY STATS ===
    # Calculate coverage for first and last year
    total_cap_first = recip_capacity[0] + turbine_capacity[0] + solar_capacity[0] + bess_capacity[0] + grid_capacity[0]
    total_cap_last = recip_capacity[-1] + turbine_capacity[-1] + solar_capacity[-1] + bess_capacity[-1] + grid_capacity[-1]
    
    coverage_first = min(100, total_cap_first / target_load[0] * 100) if target_load[0] > 0 else 100
    coverage_last = min(100, total_cap_last / target_load[-1] * 100) if target_load[-1] > 0 else 100
    
    # Grid availability note
    grid_note = ""
    if grid_available_year:
        grid_note = f" | Grid available from {grid_available_year}"
    
    st.caption(
        f"📊 Coverage: {coverage_first:.0f}% (Year 1) → {coverage_last:.0f}% (Year 15) | "
        f"Total Installed: {total_cap_last:.0f} MW{grid_note}"
    )


def _get_site_data(selected_site: str) -> Optional[dict]:
    """Helper to get site data from session state."""
    if 'sites_list' in st.session_state and st.session_state.sites_list:
        return next(
            (s for s in st.session_state.sites_list if s.get('name') == selected_site),
            None
        )
    return None


# === WRAPPER FOR BACKWARD COMPATIBILITY ===
# This allows existing code to call the function with just (equipment, selected_site)
# while new code can pass the full optimizer results

def render_energy_stack_forecast_from_result(result: dict, selected_site: str):
    """
    Render energy stack from a full optimization result dict.
    
    This is the preferred way to call this function when you have optimizer results.
    
    Args:
        result: Full optimization result dict containing:
            - equipment or equipment_config: Final equipment
            - equipment_by_year: Year-by-year equipment (optional but preferred)
            - constraints or load_trajectory: Load and constraint data
        selected_site: Site name
    """
    # Extract equipment
    equipment = result.get('equipment', result.get('equipment_config', {}))
    
    # Extract equipment_by_year if available
    equipment_by_year = result.get('equipment_by_year')
    
    # Extract load trajectory
    load_trajectory = result.get('load_trajectory')
    
    # Extract grid constraints
    constraints = result.get('constraints', {})
    grid_available_year = constraints.get('grid_available_year')
    grid_capacity_mw = constraints.get('grid_capacity_mw', 0)
    
    return render_energy_stack_forecast(
        equipment=equipment,
        selected_site=selected_site,
        equipment_by_year=equipment_by_year,
        load_trajectory=load_trajectory,
        grid_available_year=grid_available_year,
        grid_capacity_mw=grid_capacity_mw,
    )
