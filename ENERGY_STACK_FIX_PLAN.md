# Fix for Energy Stack Chart - Calculate Average Usage from Dispatch

The energy stack chart is currently showing INSTALLED CAPACITY (grid_mw) 
instead of ACTUAL AVERAGE USAGE.

For grid (and other sources), we need to calculate:
- Average hourly usage from dispatch_by_year
- Not the installed capacity

## Solution:

Add a helper function to energy_stack_chart.py:

```python
def _calculate_average_usage_by_year(dispatch_by_year, years):
    """
    Calculate average hourly usage for each energy source by year.
    
    Args:
        dispatch_by_year: Dict[year -> DispatchResult] from optimizer
        years: List of years to calculate for
    
    Returns:
        dict with keys: recip_avg, turbine_avg, solar_avg, bess_avg, grid_avg
        Each is a list with average MW for each year
    """
    recip_avg = []
    turbine_avg = []
    solar_avg = []
    bess_avg = []
    grid_avg = []
    
    for year in years:
        if year in dispatch_by_year:
            dispatch = dispatch_by_year[year]
            # dispatch is a DispatchResult with .dispatch_df DataFrame
            # Columns: hour, load_mw, recip_mw, turbine_mw, solar_mw, bess_discharge_mw, grid_mw, ...
            
            recip_avg.append(dispatch.dispatch_df['recip_mw'].mean())
            turbine_avg.append(dispatch.dispatch_df['turbine_mw'].mean())
            solar_avg.append(dispatch.dispatch_df['solar_mw'].mean())
            bess_avg.append(dispatch.dispatch_df['bess_discharge_mw'].mean())
            grid_avg.append(dispatch.dispatch_df['grid_mw'].mean())
        else:
            # No dispatch data for this year
            recip_avg.append(0)
            turbine_avg.append(0)
            solar_avg.append(0)
            bess_avg.append(0)
            grid_avg.append(0)
    
    return {
        'recip': recip_avg,
        'turbine': turbine_avg,
        'solar': solar_avg,
        'bess': bess_avg,
        'grid': grid_avg
    }
```

Then in render_energy_stack_forecast():
- Check if dispatch_by_year is available
- If yes, use _calculate_average_usage_by_year() instead of equipment capacities
- If no, fall back to current behavior (installed capacity)

This will show ACTUAL grid usage (which will be much smaller than installed grid_mw)
and correctly show 0 before grid_available_year.
