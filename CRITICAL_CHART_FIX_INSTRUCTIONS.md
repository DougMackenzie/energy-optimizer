# CRITICAL INTEGRATION FIX FOR bvNexus
# Date: December 30, 2025
# Issue: Chart displays Grid from Year 1 instead of respecting grid_available_year=2031

## ROOT CAUSE SUMMARY

The `energy_stack_chart.py` function ignores:
1. `equipment_by_year` from optimizer (uses constant equipment for all 15 years)
2. `grid_available_year` constraint (shows grid from Year 1)
3. `load_trajectory_json` from backend (uses 2% growth assumption instead)

## FILES TO UPDATE

### 1. REPLACE: `app/utils/energy_stack_chart.py`
Replace entire file with `energy_stack_chart_FIXED.py` (provided separately)

### 2. UPDATE: Where chart is called (multiple locations)

#### Location A: `app/pages_custom/page_exec_summary.py` or similar

FIND code like:
```python
from app.utils.energy_stack_chart import render_energy_stack_forecast
# ...
render_energy_stack_forecast(equipment, selected_site)
```

REPLACE with:
```python
from app.utils.energy_stack_chart import render_energy_stack_forecast

# Get optimization result from session state
opt_result = st.session_state.get('optimization_result', {})

# Get site data for grid constraints
site_data = st.session_state.get('selected_site', {})

# Extract data for chart
equipment = opt_result.get('equipment', opt_result.get('equipment_config', {}))
equipment_by_year = opt_result.get('equipment_by_year')

# Parse load trajectory from backend
load_trajectory = None
if site_data.get('load_trajectory_json'):
    import json
    try:
        traj = json.loads(site_data['load_trajectory_json'])
        load_trajectory = {int(k): float(v) for k, v in traj.items()}
    except:
        pass

# Get grid constraints
grid_available_year = None
grid_capacity_mw = 0
if site_data.get('grid_available_year'):
    try:
        grid_available_year = int(site_data['grid_available_year'])
    except:
        pass
if site_data.get('grid_capacity_mw'):
    try:
        grid_capacity_mw = float(site_data['grid_capacity_mw'])
    except:
        pass

# Render chart with full data
render_energy_stack_forecast(
    equipment=equipment,
    selected_site=selected_site,
    equipment_by_year=equipment_by_year,
    load_trajectory=load_trajectory,
    grid_available_year=grid_available_year,
    grid_capacity_mw=grid_capacity_mw,
)
```

#### Location B: `app/utils/optimizer_backend.py` - Result dict

FIND the result dict construction (around line 400+):
```python
result_dict = {
    'feasible': ...,
    'lcoe': ...,
    'equipment': ...,
    ...
}
```

ADD these fields to the result dict:
```python
result_dict = {
    'feasible': ...,
    'lcoe': ...,
    'equipment': {
        'recip_mw': ...,
        'turbine_mw': ...,
        'solar_mw': ...,
        'bess_mwh': ...,
        'grid_mw': ...,
    },
    
    # ADD THESE NEW FIELDS:
    'equipment_by_year': getattr(result, 'equipment_by_year', None) if not isinstance(result, dict) else result.get('equipment_by_year'),
    'load_trajectory': load_trajectory,  # The dict we parsed from backend
    'constraints': {
        'grid_available_year': constraints.get('grid_available_year'),
        'grid_capacity_mw': constraints.get('grid_capacity_mw', 0),
        'nox_tpy_annual': constraints.get('nox_tpy_annual'),
        'gas_supply_mcf_day': constraints.get('gas_supply_mcf_day'),
        'land_area_acres': constraints.get('land_area_acres'),
    },
    ...
}
```

### 3. VERIFY: `greenfield_heuristic_v2.py` returns `equipment_by_year`

The optimizer should already return this. Verify the result object includes:
```python
@dataclass
class HeuristicResultV2:
    ...
    equipment_by_year: Dict[int, Dict]  # Should be present
    ...
```

And in the optimize() method:
```python
return HeuristicResultV2(
    ...
    equipment_by_year=equipment_by_year,  # Should be passed
    ...
)
```

## QUICK TEST

After applying fixes, the chart should show:
- Years 2025-2030: Grid = 0 MW (gray bar absent)
- Years 2031+: Grid = 732 MW (gray bar appears)
- Load line follows: 150 → 300 → 450 → 600 → 610 MW (from backend JSON)
- NOT: constant 600 MW with 2% growth

## EXPECTED VISUAL RESULT

BEFORE (broken):
```
Year:  2026  2027  2028  2029  2030  2031  2032  ...
Grid:  562   562   562   562   562   562   562   (always present)
Load:  610   622   635   647   660   673   686   (2% growth)
```

AFTER (fixed):
```
Year:  2026  2027  2028  2029  2030  2031  2032  ...
Grid:  0     0     0     0     0     732   732   (appears at 2031)
Load:  0     150   300   450   600   610   610   (from backend JSON)
```

## COPY-PASTE COMMAND FOR ANTIGRAVITY

```
Please make these changes to fix the 15-Year Energy Stack chart:

1. Replace app/utils/energy_stack_chart.py with the fixed version that:
   - Uses equipment_by_year from optimizer results (not constant values)
   - Respects grid_available_year (grid=0 before that year)
   - Uses load_trajectory from backend JSON (not 2% growth assumption)

2. Update the chart call sites to pass:
   - equipment_by_year from optimization result
   - load_trajectory parsed from site_data['load_trajectory_json']
   - grid_available_year from site_data['grid_available_year']
   - grid_capacity_mw from site_data['grid_capacity_mw']

3. Update optimizer_backend.py result dict to include:
   - equipment_by_year
   - load_trajectory
   - constraints (with grid_available_year and grid_capacity_mw)

The root cause is that the chart function ignores all optimizer output and 
makes its own assumptions. Grid should NOT appear until 2031, not from Year 1.
```
