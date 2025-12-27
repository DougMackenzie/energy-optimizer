"""
8760 Dispatch Visualization Page
Detailed hourly dispatch analysis and visualization
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys
import io

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROBLEM_STATEMENTS, COLORS


def render():
    """Render 8760 Dispatch page"""
    
    st.markdown("### 📊 8760 Dispatch Analysis")
    st.markdown("*Hourly generation dispatch visualization and analysis*")
    st.markdown("---")
    
    # Check for results with dispatch data
    results = st.session_state.get('optimization_results', {})
    
    # Problem 1 is the primary source of dispatch data
    result = results.get(1)
    
    if not result:
        st.warning("No dispatch data available. Run Problem 1 (Greenfield) optimization first.")
        
        if st.button("🏗️ Go to Problem 1", type="primary"):
            st.session_state.current_page = 'problem_1'
            st.session_state.selected_problem = 1
            st.rerun()
        return
    
    # Generate dispatch data
    equipment = result.get('equipment', {})
    load_trajectory = st.session_state.get('load_trajectory', {2025: 750})
    
    try:
        from app.optimization.heuristic_optimizer import GreenFieldHeuristic
        
        optimizer = GreenFieldHeuristic(
            site={},
            load_trajectory=load_trajectory,
            constraints={},
        )
        
        dispatch_df = optimizer.generate_8760_dispatch(equipment)
        
    except Exception as e:
        st.error(f"Failed to generate dispatch: {e}")
        return
    
    # View controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    
    with col_ctrl1:
        view_type = st.selectbox("View Type", [
            "Weekly (168 hours)",
            "Monthly Average",
            "Full Year Heatmap",
            "Duration Curve"
        ])
    
    with col_ctrl2:
        if view_type == "Weekly (168 hours)":
            week_num = st.slider("Week", 1, 52, 1)
        else:
            week_num = 1
    
    with col_ctrl3:
        show_details = st.checkbox("Show Detailed Metrics", value=True)
    
    st.markdown("---")
    
    # Main visualization based on view type
    if view_type == "Weekly (168 hours)":
        render_weekly_view(dispatch_df, week_num, show_details)
    
    elif view_type == "Monthly Average":
        render_monthly_view(dispatch_df, show_details)
    
    elif view_type == "Full Year Heatmap":
        render_heatmap_view(dispatch_df)
    
    elif view_type == "Duration Curve":
        render_duration_curve(dispatch_df)
    
    st.markdown("---")
    
    # Summary statistics
    st.markdown("#### 📈 Annual Summary Statistics")
    render_summary_stats(dispatch_df, equipment)
    
    st.markdown("---")
    
    # Export section
    st.markdown("#### 📥 Export Data")
    render_export_section(dispatch_df)


def render_weekly_view(df, week_num, show_details):
    """Render weekly dispatch view"""
    
    start_hour = (week_num - 1) * 168
    end_hour = min(start_hour + 168, len(df))
    
    week_df = df.iloc[start_hour:end_hour].copy()
    week_df['hour_of_week'] = range(len(week_df))
    
    st.markdown(f"##### Week {week_num} Dispatch (Hours {start_hour} - {end_hour})")
    
    # Stacked area chart
    fig = go.Figure()
    
    # Add generation sources in order
    fig.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['recip_mw'],
        fill='tozeroy',
        name='Recip Engines',
        line=dict(width=0.5, color='#48bb78'),
        stackgroup='generation'
    ))
    
    fig.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['turbine_mw'],
        fill='tonexty',
        name='Gas Turbines',
        line=dict(width=0.5, color='#4299e1'),
        stackgroup='generation'
    ))
    
    fig.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['solar_mw'],
        fill='tonexty',
        name='Solar PV',
        line=dict(width=0.5, color='#f6ad55'),
        stackgroup='generation'
    ))
    
    fig.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['bess_discharge_mw'],
        fill='tonexty',
        name='BESS Discharge',
        line=dict(width=0.5, color='#9f7aea'),
        stackgroup='generation'
    ))
    
    # Load line
    fig.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['load_mw'],
        name='Load',
        line=dict(width=2, color='#e53e3e', dash='dash'),
        mode='lines'
    ))
    
    fig.update_layout(
        height=400,
        margin=dict(t=30, b=50, l=60, r=20),
        xaxis_title='Hour of Week',
        yaxis_title='Power (MW)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        hovermode='x unified'
    )
    
    # Add day labels
    for i in range(7):
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        fig.add_annotation(
            x=i * 24 + 12,
            y=-0.12,
            yref='paper',
            text=day_names[i],
            showarrow=False,
            font=dict(size=10)
        )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Battery SOC chart
    st.markdown("##### Battery State of Charge")
    
    fig_soc = go.Figure()
    
    fig_soc.add_trace(go.Scatter(
        x=week_df['hour_of_week'],
        y=week_df['bess_soc_mwh'],
        fill='tozeroy',
        name='SOC',
        line=dict(color='#9f7aea')
    ))
    
    fig_soc.update_layout(
        height=200,
        margin=dict(t=20, b=40, l=60, r=20),
        xaxis_title='Hour of Week',
        yaxis_title='SOC (MWh)',
    )
    
    st.plotly_chart(fig_soc, use_container_width=True)
    
    # Weekly metrics
    if show_details:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Peak Load", f"{week_df['load_mw'].max():.0f} MW")
        with col2:
            st.metric("Avg Load", f"{week_df['load_mw'].mean():.0f} MW")
        with col3:
            total_gen = week_df[['recip_mw', 'turbine_mw', 'solar_mw', 'bess_discharge_mw']].sum().sum()
            st.metric("Total Generation", f"{total_gen/1000:.1f} GWh")
        with col4:
            solar_pct = week_df['solar_mw'].sum() / week_df['load_mw'].sum() * 100 if week_df['load_mw'].sum() > 0 else 0
            st.metric("Solar Penetration", f"{solar_pct:.1f}%")


def render_monthly_view(df, show_details):
    """Render monthly average dispatch"""
    
    st.markdown("##### Monthly Average Dispatch")
    
    # Add month column
    df['month'] = (df['hour'] // 730).astype(int) + 1
    df['month'] = df['month'].clip(1, 12)
    
    # Monthly averages
    monthly = df.groupby('month').agg({
        'load_mw': 'mean',
        'recip_mw': 'mean',
        'turbine_mw': 'mean',
        'solar_mw': 'mean',
        'bess_discharge_mw': 'mean',
        'unserved_mw': 'sum',
    }).reset_index()
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly['month_name'] = monthly['month'].apply(lambda x: months[x-1] if 1 <= x <= 12 else 'Unknown')
    
    # Stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(name='Recip', x=monthly['month_name'], y=monthly['recip_mw'],
                        marker_color='#48bb78'))
    fig.add_trace(go.Bar(name='Turbine', x=monthly['month_name'], y=monthly['turbine_mw'],
                        marker_color='#4299e1'))
    fig.add_trace(go.Bar(name='Solar', x=monthly['month_name'], y=monthly['solar_mw'],
                        marker_color='#f6ad55'))
    fig.add_trace(go.Bar(name='BESS', x=monthly['month_name'], y=monthly['bess_discharge_mw'],
                        marker_color='#9f7aea'))
    
    # Load line
    fig.add_trace(go.Scatter(
        x=monthly['month_name'],
        y=monthly['load_mw'],
        name='Avg Load',
        line=dict(color='#e53e3e', width=3),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        barmode='stack',
        height=400,
        yaxis_title='Average Power (MW)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Monthly table
    if show_details:
        display_df = monthly[['month_name', 'load_mw', 'recip_mw', 'turbine_mw', 'solar_mw']].copy()
        display_df.columns = ['Month', 'Avg Load (MW)', 'Recip (MW)', 'Turbine (MW)', 'Solar (MW)']
        
        for col in display_df.columns[1:]:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_heatmap_view(df):
    """Render full year heatmap"""
    
    st.markdown("##### Annual Dispatch Heatmap")
    
    # Reshape to day x hour
    df['day'] = df['hour'] // 24
    df['hour_of_day'] = df['hour'] % 24
    
    # Total generation
    df['total_gen'] = df['recip_mw'] + df['turbine_mw'] + df['solar_mw'] + df['bess_discharge_mw']
    
    # Pivot for heatmap
    heatmap_data = df.pivot_table(
        index='hour_of_day',
        columns='day',
        values='total_gen',
        aggfunc='mean'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=list(range(365)),
        y=list(range(24)),
        colorscale='Viridis',
        colorbar=dict(title='MW')
    ))
    
    fig.update_layout(
        height=400,
        xaxis_title='Day of Year',
        yaxis_title='Hour of Day',
        yaxis=dict(tickmode='array', tickvals=[0, 6, 12, 18, 23], ticktext=['12am', '6am', '12pm', '6pm', '11pm'])
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Solar heatmap
    st.markdown("##### Solar Generation Heatmap")
    
    solar_heatmap = df.pivot_table(
        index='hour_of_day',
        columns='day',
        values='solar_mw',
        aggfunc='mean'
    )
    
    fig2 = go.Figure(data=go.Heatmap(
        z=solar_heatmap.values,
        x=list(range(365)),
        y=list(range(24)),
        colorscale='YlOrRd',
        colorbar=dict(title='MW')
    ))
    
    fig2.update_layout(
        height=300,
        xaxis_title='Day of Year',
        yaxis_title='Hour of Day',
        yaxis=dict(tickmode='array', tickvals=[0, 6, 12, 18, 23], ticktext=['12am', '6am', '12pm', '6pm', '11pm'])
    )
    
    st.plotly_chart(fig2, use_container_width=True)


def render_duration_curve(df):
    """Render load and generation duration curves"""
    
    st.markdown("##### Duration Curves")
    
    # Sort loads
    load_sorted = df['load_mw'].sort_values(ascending=False).values
    gen_sorted = (df['recip_mw'] + df['turbine_mw'] + df['solar_mw']).sort_values(ascending=False).values
    
    hours = np.arange(len(load_sorted))
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=hours,
        y=load_sorted,
        name='Load',
        line=dict(color='#e53e3e', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=hours,
        y=gen_sorted,
        name='Generation',
        line=dict(color='#48bb78', width=2)
    ))
    
    fig.update_layout(
        height=400,
        xaxis_title='Hours',
        yaxis_title='Power (MW)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Key duration curve metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Peak Load", f"{load_sorted[0]:.0f} MW")
    with col2:
        st.metric("Baseload", f"{load_sorted[-1]:.0f} MW")
    with col3:
        st.metric("Load Factor", f"{load_sorted.mean() / load_sorted[0] * 100:.1f}%")
    with col4:
        hours_above_90 = np.sum(load_sorted >= load_sorted[0] * 0.9)
        st.metric("Hours >90% Peak", f"{hours_above_90:,}")


def render_summary_stats(df, equipment):
    """Render annual summary statistics"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Load Statistics**")
        stats = {
            'Peak Load (MW)': f"{df['load_mw'].max():.0f}",
            'Average Load (MW)': f"{df['load_mw'].mean():.0f}",
            'Minimum Load (MW)': f"{df['load_mw'].min():.0f}",
            'Total Load (GWh)': f"{df['load_mw'].sum() / 1000:.0f}",
            'Load Factor': f"{df['load_mw'].mean() / df['load_mw'].max() * 100:.1f}%",
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['Metric', 'Value']), 
                    use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**Generation Statistics**")
        total_gen = df[['recip_mw', 'turbine_mw', 'solar_mw', 'bess_discharge_mw']].sum().sum()
        
        stats = {
            'Total Generation (GWh)': f"{total_gen / 1000:.0f}",
            'Recip Generation (GWh)': f"{df['recip_mw'].sum() / 1000:.0f}",
            'Turbine Generation (GWh)': f"{df['turbine_mw'].sum() / 1000:.0f}",
            'Solar Generation (GWh)': f"{df['solar_mw'].sum() / 1000:.0f}",
            'BESS Throughput (GWh)': f"{df['bess_discharge_mw'].sum() / 1000:.0f}",
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['Metric', 'Value']),
                    use_container_width=True, hide_index=True)
    
    with col3:
        st.markdown("**Capacity Factors**")
        
        recip_cf = df['recip_mw'].mean() / equipment.get('recip_mw', 1) * 100 if equipment.get('recip_mw', 0) > 0 else 0
        turbine_cf = df['turbine_mw'].mean() / equipment.get('turbine_mw', 1) * 100 if equipment.get('turbine_mw', 0) > 0 else 0
        solar_cf = df['solar_mw'].mean() / equipment.get('solar_mw', 1) * 100 if equipment.get('solar_mw', 0) > 0 else 0
        
        stats = {
            'Recip CF': f"{recip_cf:.1f}%",
            'Turbine CF': f"{turbine_cf:.1f}%",
            'Solar CF': f"{solar_cf:.1f}%",
            'Unserved Energy (MWh)': f"{df['unserved_mw'].sum():.0f}",
            'Reliability': f"{(1 - df['unserved_mw'].sum() / df['load_mw'].sum()) * 100:.2f}%",
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['Metric', 'Value']),
                    use_container_width=True, hide_index=True)


def render_export_section(df):
    """Export options for dispatch data"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Full 8760 (CSV)",
            csv,
            "bvnexus_8760_dispatch.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        # Hourly summary
        summary_df = df[['hour', 'load_mw', 'recip_mw', 'turbine_mw', 'solar_mw', 'bess_discharge_mw', 'unserved_mw']].copy()
        summary_df['total_gen'] = summary_df['recip_mw'] + summary_df['turbine_mw'] + summary_df['solar_mw'] + summary_df['bess_discharge_mw']
        
        csv_summary = summary_df.to_csv(index=False)
        st.download_button(
            "📥 Download Summary (CSV)",
            csv_summary,
            "bvnexus_dispatch_summary.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col3:
        st.button("📊 Export to Excel (Coming Soon)", disabled=True, use_container_width=True)


if __name__ == "__main__":
    render()
