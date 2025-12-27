#!/usr/bin/env python3
"""Add trend charts to comparison page"""

# Read the file
with open('app/pages_custom/page_comparison.py', 'r') as f:
    lines = f.readlines()

# Find where to insert
for i, line in enumerate(lines):
    if 'st.markdown("**LCOE Progression**")' in line:
        # Found it - replace the next line (the info placeholder)
        # Remove the placeholder lines
        if 'st.info(' in lines[i+1]:
            # Replace with chart code
            chart_code = '''        
        # Extract LCOE data
        import plotly.graph_objects as go
        
        stages_list = list(stage_keys.keys())
        lcoe_values = []
        
        for stage in stages_list:
            lcoe_str = comparison_data.get(stage, ['TBD'])[0]
            if lcoe_str != 'TBD':
                try:
                    lcoe_values.append(float(lcoe_str))
                except:
                    lcoe_values.append(None)
            else:
                lcoe_values.append(None)
        
        # Only show chart if we have at least one value
        if any(v is not None for v in lcoe_values):
            fig_lcoe = go.Figure()
            fig_lcoe.add_trace(go.Scatter(
                x=stages_list,
                y=lcoe_values,
                mode='lines+markers',
                name='LCOE',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=10)
            ))
            
            fig_lcoe.update_layout(
                yaxis_title="LCOE ($/MWh)",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_lcoe, use_container_width=True)
        else:
            st.info("📉 Complete stages to see LCOE trend")
'''
            lines[i+1] = chart_code
            break

# Now find equipment chart
for i, line in enumerate(lines):
    if 'st.markdown("**Equipment Capacity Evolution**")' in line:
        if 'st.info(' in lines[i+1]:
            equip_chart = '''        
        # Extract equipment data for chart
        import plotly.graph_objects as go
        
        recip_data = []
        turbine_data = []
        bess_data = []
        solar_data = []
        
        for stage in stages_list:
            stage_data = comparison_data.get(stage, ['TBD']*12)
            try:
                recip_data.append(float(stage_data[2]) if stage_data[2] != 'TBD' else 0)
                turbine_data.append(float(stage_data[3]) if stage_data[3] != 'TBD' else 0)
                bess_data.append(float(stage_data[4]) if stage_data[4] != 'TBD' else 0)
                solar_data.append(float(stage_data[5]) if stage_data[5] != 'TBD' else 0)
            except:
                recip_data.append(0)
                turbine_data.append(0)
                bess_data.append(0)
                solar_data.append(0)
        
        if sum(recip_data + turbine_data + bess_data + solar_data) > 0:
            fig_equip = go.Figure()
            
            fig_equip.add_trace(go.Bar(name='Recip Engines', x=stages_list, y=recip_data, marker_color='#ef4444'))
            fig_equip.add_trace(go.Bar(name='Turbines', x=stages_list, y=turbine_data, marker_color='#f59e0b'))
            fig_equip.add_trace(go.Bar(name='BESS', x=stages_list, y=bess_data, marker_color='#8b5cf6'))
            fig_equip.add_trace(go.Bar(name='Solar PV', x=stages_list, y=solar_data, marker_color='#10b981'))
            
            fig_equip.update_layout(
                barmode='stack',
                yaxis_title="Capacity (MW/MWh)",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_equip, use_container_width=True)
        else:
            st.info("📊 Complete stages to see equipment evolution")
'''
            lines[i+1] = equip_chart
            break

with open('app/pages_custom/page_comparison.py', 'w') as f:
    f.writelines(lines)

print("✅ Added trend analysis charts to comparison page")
